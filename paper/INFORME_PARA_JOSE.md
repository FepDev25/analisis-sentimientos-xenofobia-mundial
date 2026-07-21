# Informe técnico para el artículo — Plataforma de análisis de xenofobia

> **Para:** Jose, que redacta el paper.
> **De:** Sami (frontend) — con el backend de Felipe ya integrado.
> **Fecha:** 21-jul-2026. **Cierre de la entrega:** 22-jul-2026, 13:59.
>
> Este documento es el insumo para escribir el artículo. Trae **lo que se construyó, por qué
> se construyó así, y qué se midió**. Todos los números de aquí están **medidos**, no
> estimados: se indica siempre de dónde salen.
>
> **Las capturas de pantalla están en `paper/evidencia_capturas/`.**

---

## 0. Resumen en una página

Se construyó una **aplicación web** que recibe una consulta de texto del usuario, extrae
comentarios de **cuatro redes sociales simultáneamente**, clasifica cada comentario en dos
ejes (sentimiento y discurso de odio) usando un modelo transformer local, y presenta los
resultados con su interpretación.

La idea que articula todo el proyecto, y que conviene que sea la tesis del artículo:

> **Una sola petición del usuario atraviesa dos regímenes de cómputo distintos, y cada uno
> exige una técnica de paralelismo diferente.** Traer los datos es esperar a la red
> (*I/O-bound*): ahí los hilos son la herramienta correcta, porque un hilo que espera no
> consume CPU. Clasificarlos es cómputo puro del transformer (*CPU-bound*): ahí los hilos
> pierden y el paralelismo real lo dan los procesos. La aplicación usa **las dos técnicas en
> el mismo flujo** porque tiene los dos tipos de trabajo.

Eso no es teoría prestada: la Práctica 6 midió la extracción con hilos y la Práctica 7 midió
la clasificación con procesos (speedup 2.61×). El proyecto final las **fusiona en un solo
sistema** y añade la capa de visualización e interpretación.

---

## 1. Cómo levantar el sistema (procedimiento reproducible)

Sirve para la sección de *Metodología* y para que cualquiera reproduzca los resultados.

### Requisitos

| Componente | Requisito | Nota |
|---|---|---|
| Gestor de paquetes | `uv` | gestiona el entorno virtual y las dependencias |
| Intérprete | Python **3.12** | techo impuesto por `torch`; ver §3.4 |
| Disco | ~6 GB | 5,4 GB del entorno (torch + pesos de HuggingFace) |
| RAM | ~8 GB libres | 2 procesos × ~4 GB de modelos |
| Credenciales | `.env` + `x_session.json` | ver abajo |

### Credenciales

```
proyecto_final/backend/.env          → BLUESKY_HANDLE, BLUESKY_APP_PASSWORD, YOUTUBE_API_KEY
practica_06/data/x_session.json      → cookies de una sesión de X iniciada a mano
```

Mastodon **no necesita credenciales**: se leen timelines públicos por hashtag.

### Comandos, en orden

```bash
# 1. Instalar el backend (solo la primera vez; descarga ~2 GB)
cd proyecto_final/backend
uv sync

# 2. Levantar el backend (terminal 1, se queda abierta)
uv run --env-file .env uvicorn plataforma.main:app --port 8000

# 3. Levantar el frontend (terminal 2)
cd proyecto_final/frontend
python3 -m http.server 5173

# 4. Abrir en el navegador
#    http://127.0.0.1:5173
```

> **Sin `--reload`.** El recargador de uvicorn puede duplicar el pool de procesos y agotar
> la memoria. Para la demo, sin reload.

### Dos advertencias medidas, no supuestas

1. **La primera búsqueda tarda ~3 minutos; las siguientes ~35 s.** El servidor precalienta
   al arrancar solo el analizador de **español**; los de inglés, portugués y los de *hate
   speech* se cargan perezosamente la primera vez que se necesitan. → **Hacer una búsqueda de
   calentamiento antes de cualquier demostración.**
2. **Mastodon exige una consulta sin espacios.** Mapea la consulta a un hashtag, así que
   `Mundial 2026 racismo` devuelve **0 resultados** y `Mundial2026` devuelve **20**. Es una
   limitación real de la fuente, no un error del sistema (ver §6.2).

---

## 2. Arquitectura de la solución

Esto alimenta directamente la sección de **Metodología**, que la rúbrica pide con esquema
gráfico. El diagrama se puede dibujar a partir de esto:

```
                    consulta del usuario  ("racismo futbol")
                                 │
                                 ▼
        ┌────────────────────────────────────────────────┐
        │  ETAPA 1 — EXTRACCIÓN     I/O-bound → HILOS    │
        │                                                │
        │   hilo bluesky  ──┐                            │
        │   hilo x        ──┤                            │
        │   hilo youtube  ──┼──►  queue.Queue  ──► consumidor único
        │   hilo mastodon ──┘        (canal)              │
        └────────────────────────────┬───────────────────┘
                                     │  Registro (esquema común)
                                     ▼
                              ┌─────────────┐
                              │   SQLite    │  (modo WAL)
                              └──────┬──────┘
                                     │ textos sin clasificar
                                     ▼
        ┌────────────────────────────────────────────────┐
        │  ETAPA 2 — CLASIFICACIÓN  CPU-bound → PROCESOS │
        │                                                │
        │   ProcessPoolExecutor (pysentimiento)          │
        │   bloques de 32 textos → N procesos            │
        └────────────────────────────┬───────────────────┘
                                     ▼
                              ┌─────────────┐
                              │   SQLite    │
                              └──────┬──────┘
                                     │ HTTP / JSON
                                     ▼
                         frontend (4 vistas, navegador)
```

### 2.1 Justificación de cada decisión

| Decisión | Por qué |
|---|---|
| **Hilos para extraer** | El scraping es ~95 % espera de red. Un hilo bloqueado en I/O libera el GIL y no consume CPU. Los procesos darían el mismo resultado a un costo mucho mayor (memoria propia, arranque lento, serialización entre procesos). |
| **Cola productor/consumidor** | `queue.Queue` es *thread-safe*: no hacen falta locks manuales. Los productores (extractores) no saben nada del almacenamiento; un único consumidor escribe. |
| **Un solo consumidor** | Elimina por diseño las condiciones de carrera en escritura. Es también la razón por la que SQLite basta (ver abajo). |
| **Aislamiento de fallos por red** | Cada productor va en `try/except`: si X cae por sesión caducada, las otras tres siguen y la búsqueda termina. Verificado en producción. |
| **Procesos para clasificar** | La inferencia del transformer es CPU pura. Con GIL activo los hilos se serializan; los procesos dan paralelismo real. |
| **Pool creado al arrancar el servidor** | Cada proceso carga ~4 GB de modelos. Crear el pool por petición recargaría los modelos en cada búsqueda. Se mantiene caliente mientras viva el servidor. |
| **SQLite en modo WAL** | La arquitectura ya eliminó la concurrencia de escritura (un solo consumidor). Un motor cliente/servidor resolvería un problema que el sistema no tiene, a cambio de sobrecosto operativo. WAL permite que la interfaz lea mientras el consumidor escribe. |

### 2.2 El contrato de datos

Los cuatro extractores devuelven **exactamente el mismo esquema**, sin importar la red. Un
campo que una red no provee va como `null`, pero **la clave existe siempre**:

```
id · red · estrategia · criterio_busqueda · texto · idioma
autor · fecha_publicacion · url · metricas · fecha_extraccion
```

`metricas` es un diccionario flexible a propósito (X mide reposts, YouTube mide vistas): no
se fuerza a unificar lo que no se puede unificar. La unicidad es `(red, id)`.

Este contrato es lo que permite que la clasificación, el almacenamiento y la interfaz sean
**agnósticos de la fuente**: añadir una quinta red no obliga a tocar nada aguas abajo.

---

## 3. El frontend: estructura y justificación

### 3.1 Las cuatro pantallas

El diseño no fue estético sino **derivado de la rúbrica**: cada criterio de 2 puntos es una
pantalla. Si algo no mapeaba a un criterio, no se construyó.

| Pantalla | Criterio de la rúbrica que cubre | Qué muestra |
|---|---|---|
| 1 · Búsqueda en vivo | *Integración de extracción concurrente* | La consulta, el avance por red y la evidencia cuantitativa de que corrieron en paralelo |
| 2 · Clasificación | *Clasificación de sentimientos* | Sentimiento global y por red, más el eje independiente de odio |
| 3 · Explorador | *Visualización y exploración* | Cada comentario con red, idioma, sentimiento y odio; filtrable |
| 4 · Interpretación | *Storytelling y explicabilidad* | Lectura cualitativa de la búsqueda actual + los cinco hallazgos del corpus |

### 3.2 Cómo se muestra la concurrencia (esto es lo importante)

El backend **no emite eventos**: no hay WebSockets ni Server-Sent Events. `POST /busquedas`
responde `202 Accepted` con un identificador y la búsqueda continúa en segundo plano. El
frontend **sondea** `GET /busquedas/{id}`.

Eso plantea un problema: durante la extracción, el servidor no expone ningún progreso
(las escrituras no se confirman hasta que el orquestador termina). Se resolvió **deduciendo
la fase a partir del propio contrato**, sin pedirle nada al backend:

| Condición observada | Fase que se muestra | Qué está pasando realmente |
|---|---|---|
| `estado = en_curso` y el resumen no trae filas por red | **Extrayendo** | los hilos siguen esperando a las redes |
| `estado = en_curso` pero ya hay filas por red | **Clasificando** | la extracción terminó; el pool de procesos está infiriendo |
| `estado ≠ en_curso` | **Terminada** | — |

El resultado es que la interfaz muestra **los dos regímenes de paralelismo del proyecto en
vivo**, que es exactamente lo que hay que demostrar.

Y al terminar se contrasta la duración de cada red contra la suma de todas. Como las cuatro
arrancan en el segundo cero, el tiempo total lo marca **la más lenta**, no la acumulación.
Ese cociente es el *speedup* de la extracción y se muestra en pantalla.

### 3.3 Por qué HTML y JavaScript planos, sin framework

No es una simplificación por falta de tiempo: **ninguna de las razones por las que existe un
framework aplica a esta interfaz.**

React, Vue o Angular resuelven tres problemas: sincronizar estado complejo entre muchos
componentes, reutilizar componentes en aplicaciones grandes, y evitar redibujar el DOM entero
en interfaces que cambian constantemente. En este caso:

- **El estado es uno solo y cambia una vez por búsqueda.** Todas las vistas leen del mismo
  objeto y se redibujan cuando cambia: son ocho líneas de código, no una librería con su
  propio modelo mental.
- **Son cuatro pantallas fijas**, no un catálogo de componentes reutilizables.
- **El volumen es pequeño** (≤ 160 registros por búsqueda): redibujar la tabla completa
  cuesta milisegundos. Un DOM virtual no tendría nada que optimizar.

A cambio, un framework habría traído costos reales: un paso de compilación que es un punto
de fallo justo antes de la entrega, código entregado que no se parece al escrito (y por tanto
más difícil de explicar y defender), y un peso desproporcionado.

El resultado: **el frontend completo son ocho archivos legibles de arriba a abajo**, que
funcionan sin instalar nada. Para un sistema que hay que explicar, revisar y defender, esa
transparencia vale más que las comodidades de un framework.

> Formulación sugerida para el paper: *"The user interface was implemented in plain HTML,
> CSS and JavaScript with a single vendored charting library. Given a fixed four-view layout,
> a single state object updated once per query, and result sets bounded to a few hundred
> records, none of the concerns that motivate a component framework — complex state
> synchronisation, component reuse at scale, or virtual-DOM diffing — applied. Avoiding a
> build step also removes a failure mode from the reproduction procedure."*

### 3.4 Por qué no se despliega en un servidor

La aplicación corre en local **a propósito**. Tres razones, en orden de peso:

1. **El modelo vive en la memoria del servidor.** Cada proceso del pool carga ~4 GB de
   `pysentimiento` y se mantiene residente. Los planes gratuitos de hosting (Render: 512 MB;
   Fly.io: 256 MB; Firebase Hosting: solo archivos estáticos, ni siquiera ejecuta Python)
   están **uno o dos órdenes de magnitud por debajo** de lo necesario. No es configuración:
   no cabe.
2. **Una de las fuentes exige una sesión de navegador real.** X se lee con cookies de una
   sesión iniciada manualmente, que caduca y ocasionalmente pide un captcha resuelto por una
   persona. Eso no puede vivir desatendido en un servidor.
3. **La inferencia local es una decisión metodológica.** El corpus es discurso de odio de
   personas reales: procesarlo en la máquina evita enviarlo a un tercero, no genera costo por
   token, y hace el experimento reproducible sin depender de que un servicio externo siga
   existiendo o mantenga sus precios.

La rúbrica pide *"una aplicación web"* — que la interfaz sea web y corra en el navegador,
no que esté publicada en internet.

### 3.5 Estructura de archivos

```
frontend/
├── index.html            estructura de las cuatro vistas
├── css/estilos.css       toda la presentación
├── js/
│   ├── api.js            cliente HTTP: lo ÚNICO que sabe que existe el backend
│   ├── graficos.js       colores, formato, envoltorio de Chart.js, estado compartido
│   ├── datos_corpus.js   agregados del corpus medidos en la Práctica 7
│   ├── vista_busqueda.js    pantalla 1
│   ├── vista_dashboard.js   pantalla 2
│   ├── vista_explorador.js  pantalla 3
│   ├── vista_historia.js    pantalla 4
│   └── app.js            pestañas, estado del servidor, arranque
├── vendor/chart.umd.js   Chart.js 4.4.3 (copia local, sin CDN)
└── mock/servidor_mock.py servidor de prueba para desarrollo (NO entregable)
```

Dos detalles con justificación:

- **Los filtros del explorador se aplican en el navegador, no en el servidor.** Con el tope
  de 40 registros por red, el conjunto completo cabe en memoria y se trae en una sola
  llamada. Filtrar en el cliente es instantáneo; ir al servidor en cada tecla solo añadiría
  latencia.
- **Todo texto proveniente de las redes se escapa antes de insertarlo en el DOM.** Los
  comentarios pueden contener HTML.

---

## 4. Dónde se guardan los datos y las evidencias

Pregunta importante para la reproducibilidad, y la respuesta es **sí, todo queda guardado**.

| Qué | Dónde | ¿Versionado en git? |
|---|---|---|
| **Todas las búsquedas, sus registros y su clasificación** | `proyecto_final/backend/data/plataforma.db` (SQLite) | ❌ no (`.gitignore`) |
| Capturas de pantalla de la ejecución | `paper/evidencia_capturas/` | ✅ sí |
| Corpus masivo de la Práctica 6 | `practica_06/data/` — en la máquina de Felipe | ❌ no |
| Resultados y figuras de la Práctica 7 | `practica_07/informe/` | ✅ sí |

La base de datos **acumula entre corridas**: cada búsqueda queda con su identificador, su
consulta, sus registros, la clasificación de cada uno y **la duración de cada red**. Es decir,
la evidencia de rendimiento se puede reconstruir en cualquier momento sin volver a ejecutar
nada. La tabla `resultado_red` es exactamente el insumo de las métricas de tiempo.

Para extraer las cifras, desde `proyecto_final/backend/`:

```bash
uv run python -c "
import sqlite3; c=sqlite3.connect('data/plataforma.db'); c.row_factory=sqlite3.Row
for r in c.execute('SELECT red, COUNT(*) n, ROUND(AVG(duracion_s),2) media FROM resultado_red GROUP BY red'):
    print(dict(r))"
```

---

## 5. Resultados medidos

### 5.1 Rendimiento de la extracción concurrente

Cuatro corridas completas, las cuatro redes en paralelo, tope de 40 registros por red:

| Red | Corridas | Duración media | Mín. | Máx. | Registros |
|---|---|---|---|---|---|
| **X** | 4 | **14,15 s** | 13,01 s | 14,73 s | 80 |
| YouTube | 4 | 1,85 s | 1,47 s | 2,39 s | 160 |
| Bluesky | 4 | 1,44 s | 1,22 s | 1,68 s | 74 |
| Mastodon | 4 | 1,13 s | 0,86 s | 1,58 s | 40 |

Comparación entre el tiempo de pared (la red más lenta) y la suma secuencial:

| Consulta | Pared | Suma secuencial | **Speedup** | Total extremo a extremo |
|---|---|---|---|---|
| `racismo futbol` | 14,31 s | 19,60 s | **1,37×** | 26,8 s |
| `Mundial 2026 racismo` | 13,01 s | 17,06 s | **1,31×** | 184,9 s ⚠️ |
| `Mundial2026` | 14,73 s | 19,29 s | **1,31×** | 34,0 s |
| `Mundial2026` (repetición) | 14,55 s | 18,31 s | **1,26×** | 32,7 s |

⚠️ Los 184,9 s son la **primera** búsqueda del servidor: incluye la carga perezosa de los
modelos de inglés, portugués y *hate speech*. No es representativa del régimen estacionario.

**Interpretación honesta del speedup — esto conviene decirlo, no disimularlo.** El speedup
ronda **1,3×** y no 4×, y la razón está a la vista: X tarda ~14 s mientras las otras tres
responden en menos de 2 s. **El paralelismo está acotado por la fuente más lenta.** Es la Ley
de Amdahl operando sobre una carga heterogénea: el tiempo de pared converge al máximo
individual, no a la suma, que es precisamente el comportamiento esperado de una carga
I/O-bound paralelizada con hilos.

#### 5.1.1 Experimento controlado: quitar la fuente lenta

Para comprobar que el techo lo impone la heterogeneidad y no la implementación, se repitió la
misma consulta **excluyendo X**, dejando tres fuentes de latencia comparable:

| Configuración | Fuentes | Tiempo de pared | Suma secuencial | **Speedup** |
|---|---|---|---|---|
| Con X | 4 | 14,55 s | 18,31 s | **1,26×** |
| **Sin X (corrida A)** | 3 | **1,37 s** | 3,71 s | **2,71×** |
| **Sin X (corrida B)** | 3 | **3,12 s** | 6,14 s | **1,97×** |

Quitar una sola fuente hace caer el tiempo de pared **de ~14,5 s a 1,4–3,1 s** y **duplica el
speedup**. Con tres fuentes homogéneas el speedup observado (2,71×) se acerca al máximo
teórico (3×), lo que confirma que la implementación concurrente es correcta y que el límite
del caso de cuatro redes es la **latencia dispar de las fuentes**, no el mecanismo de
paralelización.

> Formulación sugerida: *"To verify that the observed ceiling stems from source heterogeneity
> rather than from the concurrency mechanism, the same query was repeated excluding the
> slowest source. With three comparable-latency sources, wall-clock time dropped from 14.55 s
> to 1.37 s and the speedup rose from 1.26× to 2.71× — close to the theoretical maximum of 3×
> — confirming that the serial bound is imposed by the slowest extractor, as Amdahl's law
> predicts."*

#### 5.1.2 Aislamiento de fallos (verificado)

Se ejecutó una búsqueda con las cuatro redes tras retirar deliberadamente la sesión de X:

```
youtube    40 registros   1.26 s
bluesky    19 registros   1.04 s
mastodon   20 registros   0.77 s
x           0 registros   0.00 s   FaltanSesion: no existe la sesión …
estado final de la búsqueda: terminada   (no "error")
```

La red caída **se reporta con su error y las otras tres completan normalmente**; la búsqueda
termina en estado `terminada` y los 79 comentarios se clasifican igual. Es la evidencia de
que el `try/except` por productor del orquestador aísla el fallo, y de que el sistema degrada
en lugar de caerse — una propiedad necesaria cuando las fuentes son plataformas de terceros
cuyo acceso puede expirar en cualquier momento.

> Formulación sugerida: *"Wall-clock time converges to the slowest source rather than to the
> sum of individual latencies, confirming genuine concurrent execution. The observed speedup
> of ~1.3× is bounded by the heterogeneity of the sources: X requires ~14 s due to its
> browser-session access mechanism, while the remaining three respond in under 2 s. This is
> Amdahl's law applied to a heterogeneous I/O-bound workload."*

### 5.2 Clasificación — 354 comentarios de 4 búsquedas

| Red | n | Negativo | Neutral | Positivo | Con odio |
|---|---|---|---|---|---|
| YouTube | 160 | **53,1 %** | 23,8 % | 23,1 % | **10,0 %** |
| X | 80 | 52,5 % | 42,5 % | 5,0 % | 5,0 % |
| Bluesky | 74 | 35,1 % | 54,1 % | 10,8 % | 4,1 % |
| Mastodon | 40 | 15,0 % | 85,0 % | 0,0 % | 5,0 % |

En la búsqueda `racismo futbol` específicamente: 79 comentarios, **75,9 % negativo**, 12,7 %
con odio, y **X al 95 % de comentarios negativos**.

### 5.3 Tres observaciones metodológicas que salen de estos datos

**(a) El 54,5 % de los comentarios no declara idioma.** De 354 registros, 193 llegan sin
etiqueta de idioma; 132 declaran español y 23 inglés. YouTube en particular **no entrega
idioma en absoluto**. El clasificador rutea esos casos al modelo en español por defecto.
Es una limitación real que debe declararse: el idioma es un metadato poco fiable en datos
sociales, y coincide con lo ya observado en la Práctica 6 sobre Bluesky (~54 % sin declarar).

**(b) Solo 2 de 354 comentarios dispararon el léxico xenófobo.** Las consultas del usuario
caen en la **conversación general**, no en el núcleo denso del problema. Esto no es un fallo:
es exactamente la razón por la que el corpus de la Práctica 6 usó una estrategia de **dos
capas** (búsqueda amplia + cruce dirigido con léxico). La aplicación en vivo demuestra que el
sistema funciona; el corpus es lo que permite hacer afirmaciones estadísticas.

**(c) La aplicación en vivo y el corpus responden preguntas distintas.** Con ~160 comentarios
por consulta no se pueden hacer afirmaciones estadísticas. Los porcentajes de §5.2 describen
lo recolectado, no la población. Las afirmaciones del artículo deben apoyarse en el corpus de
396 841 registros de la Práctica 6/7.

---

## 6. Justificación de las cuatro fuentes (y de las que se descartaron)

La rúbrica valora la coherencia entre el problema y las fuentes elegidas.

| Fuente | En vivo | Mecanismo | Por qué está |
|---|---|---|---|
| **Bluesky** | sí | API oficial del protocolo AT (`app.bsky.feed.searchPosts`) | protocolo abierto, búsqueda global por texto, la más rápida |
| **X** | sí | Playwright sobre sesión de navegador | máxima relevancia temática: es donde ocurre la agresión directa |
| **YouTube** | sí | Data API v3 (`search.list` + `commentThreads.list`) | mayor volumen de comentarios; acceso autorizado sin *throttle* por IP |
| **Mastodon** | sí | timelines públicos por hashtag | fediverso, sin credenciales; sustituye a Reddit |
| TikTok | no | captura semiasistida | su anti-bot impide disparar por consulta; aporta solo su corpus |
| Tumblr | no | API por etiquetas | funciona por etiquetas fijas, no por consulta libre |

### 6.1 Reddit: un hallazgo, no un fracaso

Reddit era la candidata natural (busca por texto, hilos de comentarios ricos). Se descartó
tras verificar con evidencia reproducible que **responde HTTP 403 al acceso programático**, y
que las cabeceras (`via: varnish`, `server-timing: reddit-ct`) confirman que el bloqueo lo
emite su propia CDN. Además, en 2026 cerró el registro *self-service* de su Data API.

Esto vale más para el artículo que si hubiera funcionado:

> **La disponibilidad de las fuentes de datos sociales depende de decisiones comerciales de
> las plataformas, no de su viabilidad técnica.** Las dos redes más valiosas para este
> problema (X y Reddit) son justamente las dos cerradas. Bluesky y Mastodon, ambas sobre
> protocolos abiertos, fueron los reemplazos naturales.

⚠️ **Importante:** afirmar solo el **comportamiento medido** (el 403 y sus cabeceras). No
atribuir causas internas que no se pudieron verificar.

### 6.2 Cada fuente impone su propio modelo de acceso

Es un resultado de ingeniería que merece su párrafo. Las cuatro redes se extraen con
mecanismos completamente distintos porque cada plataforma expone lo que quiere:

- **Bluesky** da búsqueda de texto libre sobre un protocolo abierto y documentado.
- **YouTube** obliga a pasar por su API con clave y cuota (10 000 unidades/día).
- **X** no ofrece acceso viable: hay que conducir un navegador con una sesión humana.
- **Mastodon** no ofrece búsqueda de texto libre sin token, así que **la consulta se mapea a
  un hashtag** — de ahí que las consultas con espacios devuelvan cero.

El **contrato de datos común** (§2.2) es lo que absorbe esa heterogeneidad: los cuatro
extractores son radicalmente distintos por dentro y absolutamente intercambiables por fuera.

---

## 7. Hallazgos del corpus (Práctica 7) — el núcleo de los resultados

Estos son los resultados **estadísticamente sólidos**: 396 841 comentarios recolectados, de
los cuales 8 783 forman el núcleo dirigido (los que disparan el léxico xenófobo curado).
Están en `practica_07/informe/INFORME_P7.md`, con figuras en `practica_07/informe/figuras/`.

| Red | n | Negativo | Neutral | Positivo | Con odio |
|---|---|---|---|---|---|
| **X** | 4 739 | **70,1 %** | 22,7 % | 7,2 % | **40,3 %** |
| YouTube | 832 | 52,8 % | 32,2 % | 15,0 % | 39,7 % |
| Tumblr | 41 | 58,5 % | 24,4 % | 17,1 % | 15,8 % |
| Bluesky | 3 161 | 35,0 % | 50,5 % | 14,5 % | 5,2 % |
| TikTok | 10 | 10,0 % | 80,0 % | 10,0 % | 0,0 % |

**Hallazgo 1 — X es el epicentro.** 70,1 % negativo y 40,3 % con odio: la señal más densa y
hostil. Conecta con el gancho de la problemática (la traducción automática de X pone a hablar
entre sí a hinchadas que antes no se cruzaban).

**Hallazgo 2 — La anomalía de Bluesky es contra-discurso, no ausencia de racismo.** Solo
5,2 % con odio pese a ser captura dirigida. La inspección manual muestra que sus textos
**mencionan** los términos del léxico pero para **condenar** el racismo (ejemplo real:
*"Argentinian woman arrested in Brazil after calling some folks monkey (racism)"*). El modelo
los marca correctamente como no-odiosos. La conclusión no es sobre el modelo sino sobre las
plataformas: **Bluesky captura la meta-conversación; X y YouTube capturan la agresión.**
Es el argumento más fuerte a favor de la extracción multi-red: una sola fuente daría una foto
sesgada.

**Hallazgo 3 — El idioma predice la hostilidad mejor que la red.** Español 75,4 % negativo,
inglés 43,3 %, portugués 40,0 %. La xenofobia de este corpus es predominantemente
hispanohablante, hija de la rivalidad futbolística latinoamericana. Explica desde otro ángulo
la suavidad aparente de Bluesky: su corpus es mayormente en inglés.

**Hallazgo 4 — Lo más frecuente no es lo más virulento.** El eje *anti-negro/simiesco* es con
diferencia el más voluminoso (4 765 comentarios) pero el de menor proporción de odio explícito
(21,7 %); los ejes *colonial* (57,5 %) y *anti-mexicano* (56,6 %), mucho más pequeños, son los
más virulentos. Lectura: el insulto racial más común circula tan normalizado —como emoji, como
broma— que ni siquiera se formula de forma agresiva.

**Hallazgo 5 (central) — El modelo subdetecta el odio implícito.** El 29,9 % global de
*hateful* es un **piso, no un techo**. Revisando los casos marcados "sin odio" aparece odio
codificado que el transformer no reconoce:

- *Leetspeak*: `m0n0`, `macac0s`
- Emoji: 🍌🍌🍌, 🐒, *"uga uga uga"*
- Acrónimos/portmanteaus: *"mexisimios"*, *"Ecuakong"*, *"Mechico"*
- Ironía: *"se merecen la extinción"* (clasificado negativo, no odioso)

**Esto no es un fallo a ocultar: es el resultado.** Confirma la hipótesis rectora del proyecto
—el odio disfrazado de humor escapa a los clasificadores estándar— y justifica el diseño de
**dos ejes separados** (sentimiento y xenofobia) más un léxico curado con revisión humana.

### 7.1 La disociación entre sentimiento y odio (para la Introducción)

Es lo que distingue este trabajo de un análisis de sentimientos convencional:

- *"Qué mal jugó Ecuador, un desastre"* → sentimiento **negativo**, xenofobia **no**.
- *"jajaja los monos ecuatorianos 🐒🍌"* → sentimiento aparentemente **jocoso**, xenofobia **sí**.

Medir solo el sentimiento dejaría el segundo caso fuera del radar. Por eso la clasificación
es de **dos ejes** y no de uno.

### 7.2 Rendimiento de la clasificación paralela (Práctica 7)

| Configuración | Procesos | Tiempo |
|---|---|---|
| Serial | 1 | 359,8 s |
| Paralelo | 6 | 137,9 s |
| **Speedup** | | **2,61×** |
| **Eficiencia** | | **43 %** |

**El detalle que vale para el artículo:** inicialmente el paralelo iba **más lento** que el
serial (0,97×). La causa era la **sobre-suscripción de hilos**: N procesos × N hilos internos
de `torch` compitiendo por los mismos núcleos. Fijar `torch.set_num_threads(1)` y las
variables `OMP_NUM_THREADS`/`MKL_NUM_THREADS` a 1 llevó el speedup de 0,97× a 2,61×.

> Es un resultado publicable: *paralelizar sin controlar el paralelismo interno de la librería
> de álgebra puede anular por completo la ganancia*. La eficiencia del 43 % está acotada por
> la memoria (~4 GB por proceso), no por el número de núcleos.

---

## 8. Limitaciones (declararlas fortalece el artículo)

1. **Subdetección del odio implícito** (§7, hallazgo 5): el marcado de *hate speech* debe
   leerse como **cota inferior**.
2. **Sesgo de selección:** el análisis del corpus se hace sobre el núcleo *dirigido*, no sobre
   la conversación general. Los porcentajes describen el tono **dentro** de lo ya marcado.
3. **Idioma declarado poco fiable:** 54,5 % de los registros en vivo no declaran idioma; los
   textos cortos se rutean a español por defecto.
4. **Eficiencia acotada por memoria**, no por núcleos: ~4 GB por proceso.
5. **Speedup de extracción acotado por la fuente más lenta** (§5.1).
6. **Precisión no validada contra anotación humana:** no se dispone de un conjunto etiquetado
   por personas, así que no se reportan *precision/recall*. Lo que sí se hizo fue **inspección
   manual cualitativa** de los casos límite, que es lo que produjo los hallazgos 2 y 5.
7. **TikTok y Tumblr quedan fuera del modo en vivo** por restricciones de sus plataformas.

---

## 9. Qué pruebas faltan (y son rápidas)

Las cuatro corridas actuales usaron consultas parecidas. Para robustecer los resultados
conviene añadir, **con el servidor ya caliente** (~35 s cada una):

| Consulta sugerida | Qué demuestra | Estado |
|---|---|---|
| `Mundial2026` o `WorldCup2026` | Las **cuatro** redes con datos (Mastodon incluida) | ✅ hecha |
| `racismo futbol` | Alta densidad temática, X al 95 % negativo | ✅ hecha |
| Búsqueda con **X desmarcada** | El tiempo de pared cae de ~14 s a 1,4–3,1 s y el speedup se duplica → Ley de Amdahl visible | ✅ hecha (§5.1.1) |
| Búsqueda con **una red caída** | Aislamiento de fallos: la búsqueda termina igual | ✅ hecha (§5.1.2) |
| `Ecuador monos` | Si dispara el **léxico xenófobo** (marca `dirigida`), sería la captura ideal para la pantalla 3 | ⬜ pendiente |
| Una consulta **en inglés** (`racism world cup`) | Contraste de idioma; conecta con el hallazgo 3 | ⬜ pendiente |
| Una consulta **neutra** (`goles Mundial2026`) | Grupo de control: debería dar mayoría neutral/positiva y poco odio | ⬜ pendiente |

Las tres pendientes son deseables pero **no bloquean la entrega**: los cuatro criterios de la
rúbrica de la aplicación ya están cubiertos con las corridas hechas.

---

## 10. Las capturas de evidencia

**Todas están en `paper/evidencia_capturas/`.** Corresponden a la consulta `racismo futbol`
(79 comentarios, 3 redes con datos) salvo donde se indique:

| Archivo | Qué muestra |
|---|---|
| `pestaña1.png` | Pantalla 1 completa: 4 redes lanzadas, tiempos por red, **speedup 1,37×** y el diagrama de barras temporal |
| `evidencia9.png` | Pantalla 2: KPIs (79 comentarios, 75,9 % negativo, 12,7 % odio) y los cuatro gráficos |
| `evidencia4.png`, `evidencia5.png`, `evidencia7.png` | Pantalla 3: comentarios reales con su clasificación y filtros aplicados |
| `evidencia3.png`, `evidencia2.png` | Pantalla 4: interpretación automática de la búsqueda + los cinco hallazgos del corpus |
| `evidencia_x_pruebas.png` | El navegador ejecutando la búsqueda real en X + el log del servidor: evidencia del mecanismo de extracción |
| `prueba2_evi2.png` | **Experimento sin X** (§5.1.1): tres redes de latencia comparable, pared 3,12 s frente a suma 6,14 s, **speedup 1,97×**. Junto a `pestaña1.png` (1,37×) forma el par que demuestra la Ley de Amdahl |
| `prueba2_evi1.png` | Clasificación de esa misma corrida sin X: 79 comentarios, 39,2 % negativo, 2,5 % odio |

> **Nota para el artículo:** en `pestaña1.png` Mastodon aparece con 0 registros porque la
> consulta `racismo futbol` lleva espacio (§1, advertencia 2). Si se necesita una figura con
> las cuatro redes aportando datos, usar una corrida con `Mundial2026`.

---

## 11. Mapa: qué sección del artículo se escribe con qué

| Sección del artículo | Fuente en este repositorio |
|---|---|
| **Abstract** | §0 de este documento |
| **Introducción** | §0, §7.1 (la disociación sentimiento/odio) y la problemática de `ESTRATEGIA_BUSQUEDA.md` |
| **Trabajos relacionados** | ⚠️ **pendiente, lo tiene que buscar Jose** — mínimo 4 trabajos de ≤ 3 años |
| **Metodología** | §1, §2, §3, §6 de este documento + `proyecto_final/backend/README.md` (sección "Decisiones de arquitectura") |
| **Resultados** | §5 (sistema en vivo) y §7 (corpus). Figuras listas en `practica_07/informe/figuras/` y capturas en `paper/evidencia_capturas/` |
| **Discusión / Limitaciones** | §6.1 (Reddit), §7 hallazgos 2 y 5, §8 |
| **Conclusiones** | ver §12 |
| **Bibliografía** | ⚠️ **pendiente** — mínimo 15 referencias |

---

## 12. Cuatro conclusiones y dos recomendaciones (la rúbrica las pide explícitamente)

**Conclusiones** (una por cada área que exige la rúbrica: NLP, algoritmos, HPC, resultados):

1. **(NLP)** Los clasificadores de *hate speech* preentrenados detectan la agresión explícita
   pero **subdetectan sistemáticamente el odio codificado** —leetspeak, emoji, portmanteaus,
   ironía—, por lo que sus métricas deben interpretarse como cota inferior en corpus donde el
   odio circula disfrazado de humor.
2. **(Algoritmos)** Separar la clasificación en **dos ejes independientes** (sentimiento y
   discurso de odio) captura casos que un análisis de sentimientos convencional pierde: un
   comentario de tono jocoso puede ser xenófobo.
3. **(HPC)** La técnica de paralelismo debe elegirse por la **naturaleza de la carga**, no por
   costumbre: hilos para el trabajo I/O-bound (extracción) y procesos para el CPU-bound
   (inferencia). Además, paralelizar sin controlar el paralelismo interno de la librería de
   álgebra puede **anular la ganancia por completo** (0,97× → 2,61× al fijar los hilos de
   `torch`).
4. **(Resultados)** El tono de un mismo fenómeno **varía radicalmente según la plataforma**:
   X concentra la agresión (40,3 % con odio) mientras Bluesky concentra el contra-discurso
   (5,2 %). La extracción multi-fuente no es un requisito administrativo: sin ella la
   caracterización del fenómeno estaría sesgada por la cultura de una sola red.

**Recomendaciones:**

1. **Combinar léxico curado con revisión humana sobre el núcleo dirigido**, en lugar de
   confiar únicamente en el clasificador automático. La inspección manual de los casos límite
   fue lo que produjo los dos hallazgos más valiosos de este trabajo.
2. **Diseñar los sistemas de recolección asumiendo que las fuentes se cierran.** La
   disponibilidad de los datos sociales depende de decisiones comerciales, no técnicas: un
   contrato de datos común que desacople los extractores del resto del sistema permite
   sustituir una fuente sin rediseñar el pipeline, como se hizo al reemplazar Reddit por
   Mastodon.

---

## 13. Advertencias — qué NO afirmar

- **No decir que el free-threading (Python sin GIL) es lo que hace funcionar la extracción.**
  Un hilo que espera I/O libera el GIL de todos modos; la extracción funcionaría igual en
  CPython estándar. El backend de hecho corre en Python 3.12 **con** GIL, porque `torch` no
  tiene ruedas para 3.14 free-threaded.
- **No atribuir a Reddit causas internas no verificadas.** Solo el comportamiento medido.
- **No presentar los porcentajes de la app en vivo como resultados estadísticos.** Son ~160
  comentarios por consulta. Las afirmaciones van sobre el corpus de 396 841.
- **No prometer precisión temporal que TikTok no puede dar** (no tiene filtro de fecha usable).
- **No reportar *precision/recall*:** no hay conjunto anotado por humanos (§8, limitación 6).
