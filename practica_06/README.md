# Práctica 6 — Extracción paralela de datos sobre xenofobia en el Mundial FIFA 2026

Materia: **Computación Paralela** · Entregable de la Práctica de laboratorio 06.

Sistema que extrae, **de forma concurrente**, comentarios y publicaciones de varias redes sociales para analizar la **xenofobia durante el Mundial FIFA 2026**.

## Problemática y diseño

- **Problemática y estrategia de búsqueda:** ver [`../ESTRATEGIA_BUSQUEDA.md`](../ESTRATEGIA_BUSQUEDA.md)
- **Contrato de datos (esquema común):** ver [`../CONTRATO.md`](../CONTRATO.md)

## Fuentes

| Fuente | Alcance | Mecanismo | Estado |
|--------|---------|-----------|--------|
| YouTube | Comentarios de videos/playlists de resúmenes | `yt-dlp` + `youtube-comment-downloader` (sin API key) | ✅ |
| Bluesky | Búsqueda global por query | API oficial del protocolo AT (app password) | ✅ |
| TikTok | Comentarios de videos por hashtag | `TikTokApi` + Playwright + `ms_token` | 🧪 |
| ~~Reddit~~ | ~~Por subreddit~~ | **Descartado**: responde 403 al acceso programático | ❌ |
| ~~X~~ | ~~Búsqueda global por query~~ | Fuera del trío: API de pago + anti-bot | ⏳ |

> **YouTube:** se usan librerías que leen la API interna (sin API key ni cuota), justificado por la rúbrica ("librerías de terceros u otros mecanismos justificados") y mejor para grandes volúmenes. Marcado de 2 capas: los comentarios que contienen términos del léxico se etiquetan `dirigida`, el resto `amplia`.

> **Bluesky** sustituye a Reddit, descartado tras confirmar que bloquea el acceso programático (403 desde su propia CDN) y que su registro de apps ya no emite credenciales. Bluesky corre sobre un **protocolo abierto (AT)**: API pública y credencial inmediata. Detalle completo, resultados y hallazgos en [`docs/BLUESKY.md`](docs/BLUESKY.md).

## Paralelismo

Los extractores se lanzan **en paralelo con hilos (`threading`)** y se comunican con un controlador central mediante una **cola (`queue.Queue`)**. El scraping es I/O-bound (dominado por la espera de red), por lo que los hilos dan paralelismo real sin el costo de los procesos. Detalle en `src/extractor_mundial/orquestador.py`.

```
   Hilo YouTube ─►┐
   Hilo Bluesky ─►│ queue.Queue ──► controlador ──► CSV/JSON (por red + consolidado)
   Hilo TikTok ──►┘
```

Corre sobre **CPython 3.14 free-threaded** (sin GIL). Para la extracción, que es I/O-bound, el GIL no
sería un obstáculo — los hilos lo liberan mientras esperan a la red. La ventaja aparece en la
Práctica 7, donde la clasificación de sentimientos sí es CPU-bound: los mismos hilos podrán usar
varios núcleos de verdad, sin migrar a procesos. El programa imprime al arrancar el estado del GIL y
el número de núcleos, de modo que la salida de cada corrida documenta el entorno.

## Estructura

```
practica_06/
├── docs/
│   ├── BLUESKY.md           # documentación de la fuente Bluesky (+ hallazgos)
│   └── xenofobia-redes-sociales-mundial-fifa-2026.md
├── config/
│   ├── busqueda.toml        # Capa A: hashtags, selecciones, jugadores, canales, ventana
│   └── lexico.txt           # Capa B: léxico xenófobo semilla
├── src/extractor_mundial/
│   ├── contrato.py          # esquema de datos (dataclass validada)
│   ├── config.py            # carga de config/
│   ├── almacenamiento.py    # CSV por red + consolidado, dedup
│   ├── orquestador.py       # hilos + cola (núcleo del paralelismo)
│   ├── remarcado.py         # recalcula amplia/dirigida sin volver a extraer
│   ├── main.py              # entrypoint
│   └── extractores/         # youtube, bluesky, tiktok, x, reddit (+ base común)
├── data/                    # salida (ignorada por git)
└── evidencia/               # logs de ejecución para la rúbrica
```

## Uso

```bash
# Instalar dependencias / sincronizar entorno
uv sync

# Instalar el navegador que usa TikTokApi
uv run python -m playwright install chromium

# Configurar credenciales
cp .env.example .env        # y rellenar

# Extracción paralela: las 3 redes a la vez
uv run --env-file .env extractor-mundial

# Recolectar SOLO una fuente (cada integrante la suya, sin re-scrapear las ajenas)
uv run --env-file .env extractor-mundial --redes bluesky

# Recalcular la marca amplia/dirigida tras editar config/lexico.txt (sin tocar la red)
uv run extractor-mundial --remarcar
```

> **Dos tipos de corrida, no mezclarlos.** *Recolección*: cada integrante corre su fuente en su
> máquina, por tandas (`data/` está en `.gitignore`, no viaja por git). *Evidencia*: una corrida de
> las 3 redes a la vez con topes bajos (`--max-por-criterio`), cuya salida se guarda en `evidencia/`.
> Los `dataset.jsonl` de cada uno se consolidan concatenándolos: el almacén deduplica por `(red, id)`.

## Estado

Orquestador + contrato + almacenamiento funcionando.

- ✅ **YouTube** — implementado y probado (playlist ESPN Fans, 172 videos).
- ✅ **Bluesky** — implementado y ejecutado: **33 475 posts** en 474 s ([`docs/BLUESKY.md`](docs/BLUESKY.md)).
- 🧪 **TikTok** — extractor implementado con `TikTokApi`; falta prueba real con `TIKTOK_MS_TOKEN`.
- ❌ **Reddit** — descartado (403 al acceso programático).
