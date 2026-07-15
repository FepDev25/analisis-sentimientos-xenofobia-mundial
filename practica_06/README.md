# Práctica 6 — Extracción paralela de datos sobre xenofobia en el Mundial FIFA 2026

Materia: **Computación Paralela** · Entregable de la Práctica de laboratorio 06.

Sistema que extrae, **de forma concurrente**, comentarios y publicaciones de varias redes sociales para analizar la **xenofobia durante el Mundial FIFA 2026**.

## Problemática y diseño

- **Problemática y estrategia de búsqueda:** ver [`../ESTRATEGIA_BUSQUEDA.md`](../ESTRATEGIA_BUSQUEDA.md)
- **Contrato de datos (esquema común a todas las redes):** ver [`../CONTRATO.md`](../CONTRATO.md)

## Núcleo del trabajo: lanzar las 3 redes a la vez

El corazón de la práctica es la **ejecución concurrente**. Un único comando manda a buscar los mismos términos y **lanza los 3 extractores en paralelo**; cada uno corre en su propio hilo, produce a una cola compartida, y un controlador central consolida:

```bash
uv run --group x --env-file .env extractor-mundial \
  --redes youtube x bluesky --max-por-criterio 5 --max-por-red 15
```

```
   Hilo YouTube ─►┐
   Hilo X ───────►│  queue.Queue  ──►  controlador  ──►  dataset.jsonl + CSV/JSON
   Hilo Bluesky ─►┘                     (dedup por (red, id))
```

Los 3 hilos arrancan a la vez, cumpliendo el requisito de "iniciar la extracción de las tres fuentes al mismo tiempo". El programa imprime al arrancar el estado del GIL y el número de núcleos, de modo que la salida de cada corrida documenta el entorno. Un log de esa corrida queda en [`evidencia/`](evidencia/).

## Qué se manda a buscar (los términos)

Los términos viven en **dos archivos de configuración editables sin tocar código**:

| Archivo | Define | Ejemplos |
|---|---|---|
| `config/busqueda.toml` | Términos de **evento**: hashtags, selecciones, jugadores, ventana temporal, playlists de YouTube | `Brasil`, `#WorldCup2026`, `Mbappé` |
| `config/lexico.txt` | Léxico **xenófobo** (104 términos en 6 ejes) | `monos`, `macaco`, `saltamuros` |

`config.py` los combina en dos capas de búsqueda (`todos_los_criterios()`):

- **Capa amplia** (baseline de volumen): solo evento -> `#WorldCup2026`, `Brasil`, ...
- **Capa dirigida** (la aguja xenófoba): evento x léxico -> `Brasil monos`, `México macaco`, ...

Cada registro se etiqueta con la capa de la que proviene (`amplia` | `dirigida`), lo que permite trabajar el subconjunto denso en la Práctica 7.

## Fuentes

| Fuente | Alcance | Mecanismo | Estado |
|---|---|---|---|
| YouTube | Comentarios de videos/playlists de resúmenes y canales de reacción | `yt-dlp` + `youtube-comment-downloader` (sin API key) | Con datos |
| Bluesky | Búsqueda global por query | API oficial del protocolo abierto AT (app password) | Con datos |
| X (Twitter) | Búsqueda global por query, capa dirigida | Playwright con sesión de navegador logueado | Con datos |
| TikTok | Comentarios de videos por hashtag | `TikTokApi` + Playwright + `ms_token` | Implementado, sin corrida verificada |
| Reddit | Por subreddit | Descartado: responde 403 al acceso programático desde jul-2026 | Descartado |

Notas de justificación:

- **YouTube** usa librerías que leen la API interna (sin API key ni cuota), justificado por la rúbrica ("librerías de terceros u otros mecanismos justificados") y mejor para grandes volúmenes. No busca por texto (su buscador da ruido): usa las playlists como *dónde mirar* y el léxico como *cómo etiquetar* (marcado de 2 capas).
- **Bluesky** sustituye a Reddit (403 al acceso programático + su registro de apps ya no emite credenciales). Corre sobre un protocolo abierto (AT): API pública y credencial inmediata. Detalle en [`docs/BLUESKY.md`](docs/BLUESKY.md).
- **X** es fuente opcional-rica: se recolecta en modo dirigido (busca el patrón xenófobo exacto). Requiere una sesión de navegador capturada una sola vez.
- Cada red adapta los mismos términos a su modelo de acceso: es la decisión "adaptamos la recolección al modelo de acceso de cada red".

## Paralelismo: por qué hilos + cola

Los extractores se lanzan **en paralelo con hilos (`threading`)** y se comunican con un controlador central mediante una **cola (`queue.Queue`)**. El scraping es **I/O-bound** (dominado por la espera de red), por lo que los hilos dan paralelismo real de espera sin el costo de los procesos; la cola es el canal productor-consumidor entre los extractores y el controlador (patrón que la rúbrica lista de forma explícita). Detalle en `src/extractor_mundial/orquestador.py`.

Corre sobre CPython 3.14 free-threaded (sin GIL). Para la extracción I/O-bound el GIL no sería un obstáculo (los hilos lo liberan al esperar la red); la técnica se elige por la naturaleza del trabajo, no por el build. El contraste con la Práctica 7 (CPU-bound -> procesos) es deliberado.

## Estructura

```
practica_06/
├── docs/
│   ├── BLUESKY.md            # documentación de la fuente Bluesky (+ hallazgos)
│   └── xenofobia-redes-sociales-mundial-fifa-2026.md
├── config/
│   ├── busqueda.toml         # términos de evento + playlists + ventana + límites
│   └── lexico.txt            # léxico xenófobo (104 términos, 6 ejes)
├── src/extractor_mundial/
│   ├── contrato.py           # esquema de datos (dataclass validada)
│   ├── config.py             # carga de config/ y armado de criterios de búsqueda
│   ├── almacenamiento.py     # dataset.jsonl durable + CSV por red + consolidado, dedup
│   ├── orquestador.py        # hilos + cola (núcleo del paralelismo)
│   ├── remarcado.py          # recalcula amplia/dirigida sin volver a extraer
│   ├── main.py               # entrypoint (CLI)
│   └── extractores/          # youtube, bluesky, x, tiktok, reddit (+ base común)
├── scripts/                  # recolección por tandas (X, nocturna, canal de reacción)
├── tests/                    # pruebas del extractor y el parser de X
├── data/                     # salida (ignorada por git)
└── evidencia/                # logs de ejecución para la rúbrica
```

## Uso

### Instalación

```bash
uv sync                                   # entorno + dependencias
uv run --group x playwright install chromium   # navegador para X (y TikTok)
cp .env.example .env                      # y rellenar credenciales
```

Credenciales en `.env` (según las redes que se usen):
`BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` (app password de bsky.app), y para TikTok
`TIKTOK_MS_TOKEN`. YouTube no necesita clave.

### Corrida de EVIDENCIA (las 3 redes en paralelo, topes bajos)

```bash
uv run --group x --env-file .env extractor-mundial \
  --redes youtube x bluesky --max-por-criterio 5 --max-por-red 15 \
  2>&1 | tee evidencia/corrida_multifuente.log
```

`--max-por-red N` es el limitador universal: las 3 redes cortan al alcanzar N registros, para una evidencia corta y finita. `--redes` acepta cualquier combinación de las redes registradas.

### Recolección por integrante (una fuente a la vez)

```bash
# Cada integrante corre SU fuente en su máquina, por tandas.
uv run --env-file .env extractor-mundial --redes bluesky
uv run --env-file .env extractor-mundial --redes youtube
```

Los `dataset.jsonl` de cada uno se consolidan concatenándolos: el almacén deduplica por `(red, id)`, así que juntarlos es pegar los archivos.

### Sesión de X (una sola vez)

```bash
# Abrir el Chromium real logueado con puerto de depuración y exportar cookies vivas:
chromium --remote-debugging-port=9222 --profile-directory=Default
uv run --group x python scripts/recoleccion_x.py --conectar-cdp
```

### Otros

```bash
# Recalcular la marca amplia/dirigida tras editar config/lexico.txt (sin tocar la red):
uv run extractor-mundial --remarcar
```

> **Dos tipos de corrida, no mezclarlos.** *Recolección*: cada integrante corre su fuente en su máquina, por tandas (`data/` está en `.gitignore`, no viaja por git). *Evidencia*: una corrida de las 3 redes a la vez con topes bajos, cuya salida se guarda en `evidencia/`.

## Estado actual

Orquestador, contrato y almacenamiento funcionando de punta a punta.

Dataset consolidado (`data/dataset.jsonl`): **403 289 registros** de 3 redes reales.

| Red | Registros |
|---|---|
| YouTube | 372 183 |
| Bluesky | 26 176 |
| X | 4 930 |

Capas: `amplia` 394 631 · `dirigida` 8 658.

- **YouTube** — implementado y probado; playlists de resúmenes (ESPN, DS Sports) y canal de reacción (Davoo Xeneize). Recolección robusta: guardado incremental, reanudación por tandas, backoff y quarantine de videos no scrapeables.
- **Bluesky** — implementado y ejecutado (protocolo AT, `searchPosts` paginado, marcado de 2 capas). Detalle en [`docs/BLUESKY.md`](docs/BLUESKY.md).
- **X** — implementado y probado en vivo (Playwright, sesión por CDP, recolección dirigida). Cubierto por 7 pruebas (`tests/`).
- **TikTok** — extractor implementado con `TikTokApi`; falta prueba real con `TIKTOK_MS_TOKEN`.
- **Reddit** — descartado (403 al acceso programático).

## Continuidad

El dataset generado alimenta la **Práctica 7** (análisis de sentimientos paralelo) y el proyecto final (dashboard + artículo). Ver `../practica_07/`.
