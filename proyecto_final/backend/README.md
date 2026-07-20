# Backend — Plataforma de extraccion y analisis de sentimientos

API que recibe un query del usuario, extrae comentarios de forma concurrente desde varias redes sociales, clasifica su sentimiento y expone los resultados.

Reutiliza la Practica 6 (orquestador de hilos + contrato de datos + extractores) y la Practica 7 (clasificacion con `pysentimiento` sobre un pool de procesos).

## Arranque

```
uv sync                  # instala; la 1a vez baja ~2 GB (torch + pesos de HF)
uv run uvicorn plataforma.main:app --reload
```

Credenciales en `.env` (copiar de `.env.example`). Cada red en vivo pide lo suyo:

| Red | Credencial |
|---|---|
| bluesky | `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD` (app password, no la clave de la cuenta) |
| youtube | `YOUTUBE_API_KEY` (Google Cloud Console, habilitar "YouTube Data API v3") |
| x | ninguna variable: sesion capturada a mano (ver "Ritual de X") |
| mastodon | ninguna: timelines publicos por hashtag |

Ojo con el parser de `uv --env-file`: un valor con espacios sin comillas rompe el parseo de las variables siguientes.

## API

El contrato completo lo publica FastAPI en **`/docs`** (Swagger) y **`/openapi.json`**. Esa es la fuente para el frontend: no hace falta coordinar tipos a mano.

| Metodo | Ruta | Que hace |
|---|---|---|
| GET | `/redes` | lista las redes disponibles en vivo |
| POST | `/busquedas` | crea una busqueda (`query`, `redes` opcional). Responde 202 con el id |
| GET | `/busquedas/{id}` | estado de la busqueda (`en_curso` / `terminada` / `error`) |
| GET | `/busquedas/{id}/registros` | registros con su sentimiento (filtros: `red`, `limite`, `desplazamiento`) |
| GET | `/busquedas/{id}/resumen` | conteos de sentimiento global, por red y odio por red |

La extraccion tarda decenas de segundos, asi que `POST /busquedas` **no bloquea**: arranca la busqueda en segundo plano y devuelve el id de inmediato. El cliente consulta `GET /busquedas/{id}` hasta que el estado deja de ser `en_curso`, y entonces pide registros y resumen.

## Decisiones de arquitectura

Esta seccion es la fuente de la que se escribe la seccion de Metodologia del articulo. Si una decision cambia, se cambia aca primero.

### Por que Python 3.12

Las dos practicas no podian coexistir en un mismo interprete:

| Practica | Interprete | Motivo |
|---|---|---|
| P6 (extraccion) | 3.14 free-threaded | hilos sin GIL |
| P7 (sentimiento) | 3.11–3.13 | torch no tiene ruedas para 3.14t |

Los rangos eran mutuamente excluyentes y la plataforma necesita las dos mitades (query → extraer → clasificar → mostrar). Se unifico en **3.12**, que es el techo que impone torch.

La justificacion de hilos de P6 **no se ve afectada**: es I/O-bound (el GIL se libera esperando la red), que fue siempre el argumento real. El free-threading era una mejora, no un requisito. P6 conserva su `.python-version` en 3.14t y sigue corriendo igual por su cuenta; solo se amplio su `requires-python` a `>=3.12` para que este backend pueda instalarlo como dependencia local.

### Por que SQLite

El orquestador de P6 es un productor/consumidor: N hilos extractores encolan `Registro` y **un solo hilo controlador** los consume. Todas las escrituras pasan por ese hilo, asi que la concurrencia de escritura no es un requisito del sistema — la arquitectura ya la elimino por diseño. Un motor cliente/servidor (PostgreSQL) resolveria un problema que no tenemos, a cambio de sobrecosto operativo. Es el mismo razonamiento con el que P6 eligio hilos sobre procesos: no sobredimensionar.

SQLite en modo **WAL** permite ademas que la UI lea mientras el consumidor
escribe, sin bloquearse.

### Por que dos modelos de paralelismo

Se conserva el contraste de las practicas, porque cada etapa tiene un cuello distinto:

- **Hilos** (`threading` + `queue.Queue`) para extraer: es I/O-bound, esperar red.
- **Procesos** (`ProcessPoolExecutor`) para clasificar: es CPU-bound. Medido en P7: speedup 2.61x con 6 procesos.

El pool de clasificacion se crea **al arrancar el servidor y se mantiene caliente**: cada proceso carga ~4 GB de pysentimiento una sola vez. Levantar un pool por peticion recargaria los modelos en cada busqueda.

### Extraccion en vivo vs. corpus

La rubrica pide extraccion concurrente disparada por el query del usuario. El pipeline de P6 estaba afinado para cosecha nocturna (corridas de horas, sin throttle). Se conservan los dos regimenes:

- **En vivo, acotado**: pocos criterios y pocos resultados por red, para que la busqueda responda en decenas de segundos. Es lo que sirve la API.
- **Batch**: el corpus ya recolectado (396.841 registros de 5 redes) sigue siendo la base del analisis del articulo.

Latencias medidas en P6 (`practica_06/evidencia/corrida_multifuente.log`), las tres redes en paralelo:

| Red | Registros | Duracion |
|---|---|---|
| bluesky | 15 | 2.78 s |
| x | 15 | 17.37 s |
| youtube | 0 | 106.68 s (throttle) |

Bluesky y X son viables en vivo tal cual. YouTube no, y por eso cambia de mecanismo (ver abajo).

Una vez migrado YouTube y sumada la cuarta red, se midio la plataforma completa de punta a punta (query `Ecuador`, tope 5 registros por red, las cuatro en paralelo):

| Red | Registros | Duracion |
|---|---|---|
| bluesky | 5 | 1.47 s |
| youtube | 5 | 1.23 s |
| mastodon | 5 | 1.18 s |
| x | 5 | 9.26 s |

Tiempo de pared: **9.27 s**, practicamente igual al maximo por red y no a la suma (13.15 s). Es la prueba de que los extractores corren de verdad en paralelo: el total lo marca la red mas lenta (X), no la acumulacion. Despues el pool de procesos clasifico los 20 registros y `bd.resumen` devolvio los conteos de sentimiento global y por red. Si una red falla (sesion de X caducada, por ejemplo), el orquestador la aisla y la busqueda termina con las demas.

### Redes en vivo

Cuatro redes se extraen en vivo, disparadas por el query:

| Red | En vivo | Nota |
|---|---|---|
| bluesky | si | busca por texto libre; la mas rapida |
| x | si | busca por texto libre; requiere sesion manual |
| youtube | si | Data API v3 (`search.list` + `commentThreads.list`), no el scraper de P6 |
| mastodon | si | fediverso; el query se mapea a hashtag; sin credenciales |
| tumblr | no | queda como respaldo (`_Pendiente`), fuera del set en vivo |
| tiktok | no | captura semi-manual; solo aporta su corpus |
| reddit | no | en 2026 cerro el registro self-service de su Data API |

Cada red se adapta al modelo de acceso que impone su plataforma; ese es el criterio de diseño de la capa de extraccion.

**YouTube cambia de mecanismo.** P6 usa `yt-dlp` + `youtube-comment-downloader`, que raspan la API interna. Eso fue lo correcto para el corpus (sin cuota, trajo 300k+ comentarios, es la red mas productiva), pero en vivo falla por dos motivos a la vez: Google rate-limita por IP el acceso no autorizado, y el extractor no busca por texto sino que itera una lista de videos fija. La **Data API v3** resuelve los dos: `search.list` acepta el query, `commentThreads.list` baja los comentarios, y al ser acceso autorizado no hay throttle por IP. Cuota gratuita: 10.000 unidades/dia (`search.list` = 100, `commentThreads.list` = 1). El extractor en vivo (`extractores/youtube_api.py`) habla HTTP directo contra la API, sin `google-api-python-client`. El scraper de P6 se conserva para la cosecha batch: cada regimen usa el mecanismo que le conviene.

**La cuarta red es Mastodon, y sustituye a Reddit.** La candidata natural era Reddit —busca por texto y sus hilos de comentarios son ricos—, pero en 2026 Reddit cerro el registro self-service de la Data API: ahora exige aprobacion por ticket con un caso de uso de moderacion, y el camino oficial (Devvit) son apps que corren dentro de Reddit, no clientes externos que consuman datos. Mastodon ofrece lo mismo que Bluesky sin friccion de credenciales: es un protocolo abierto y sus timelines publicos por hashtag se leen sin token. El query del usuario se mapea a un hashtag (`World Cup 2026` -> `worldcup2026`); se usa el timeline por hashtag (`GET /api/v1/timelines/tag/:tag`) y no la busqueda full-text porque esta es opt-in por usuario y exige token, con recall bajo. El contenido llega en HTML y se limpia a texto plano antes de mapear al contrato. Limitacion asumida: un hashtag generico trae ruido (turismo, fotografia); rinde con hashtags de evento (`Mundial2026`, cruces de selecciones).

## Ritual de X (obligatorio antes de una demo)

El `--login` automatizado **no funciona**: X y Google bloquean el navegador automatizado. El unico metodo que sirve:

1. Cerrar Chromium y abrirlo con `--remote-debugging-port=9222`.
2. Loguearse a mano en X (usuario+contraseña, **no** el boton de Google).
3. Con esa ventana abierta, desde `practica_06/`: `uv run --group x python scripts/recoleccion_x.py --conectar-cdp`

Exporta las cookies a `practica_06/data/x_session.json`. Dura ~semanas.

Limitaciones conocidas de X, que la plataforma asume:

- Se throttlea tras **~10-13 queries seguidas**, y el throttle **escala con la frecuencia** (reintentar lo empeora). Con 1-2 criterios por busqueda alcanza para ~5-6 busquedas seguidas.
- Si la sesion caduca o aparece un captcha, X cae. El orquestador **aisla el fallo por red**: las demas siguen y la busqueda no se cae.

## Estructura

```
src/plataforma/
├── bd.py          persistencia SQLite (esquema en esquema.sql)
├── esquema.sql    DDL
├── config.py      limites y rutas, por variables de entorno
├── esquemas.py    modelos de la API (Pydantic)
├── sentimiento.py pool de procesos caliente
├── busqueda.py    orquestacion: query → extractores → BD
└── main.py        app FastAPI
```

## Tests

```
uv run pytest
```

- `tests/test_bd.py` no necesita P6 ni red: la capa de datos recibe los `Registro` por duck-typing y solo usa `sqlite3`.
- `tests/test_busqueda.py` cubre el cableado de `busqueda.py` (la sesion de X se apunta con ruta absoluta a `practica_06/data/`, si no daria `FaltanSesion` desde el cwd del backend).

Los extractores en vivo (YouTube Data API, Mastodon) tienen sus tests en `practica_06/tests/` (mapeo al contrato, marcado por lexico, topes y aislamiento de fallos), sin tocar la red.
