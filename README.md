# Análisis de sentimientos sobre xenofobia en el Mundial FIFA 2026

Proyecto de **Computación Paralela** para recolectar, procesar y analizar publicaciones de redes
sociales relacionadas con expresiones xenófobas durante la Copa Mundial de la FIFA 2026.

El proyecto se divide en tres entregas:

| Entrega | Objetivo |
|---|---|
| Práctica 6 | Extracción concurrente de datos desde al menos tres redes sociales. |
| Práctica 7 | Análisis de sentimientos y detección de xenofobia sobre el dataset recolectado. |
| Proyecto final | Aplicación web con extracción, clasificación, visualización, storytelling y artículo académico. |

## Problemática

Durante el Mundial, la rivalidad deportiva puede convertirse en ataques xenófobos entre países,
especialmente mediante insultos raciales, burlas sobre origen nacional, color de piel, cultura o
comentarios presentados como humor. El objetivo es construir un dataset textual que permita analizar
esa conversación y clasificarla posteriormente con técnicas de procesamiento de lenguaje natural.

## Práctica 6

La implementación actual está en [`practica_06/`](practica_06/).

Fuentes activas:

| Fuente | Estado | Mecanismo |
|---|---|---|
| YouTube | Implementado | `yt-dlp` + `youtube-comment-downloader` |
| Bluesky | Implementado | API oficial del protocolo AT |
| TikTok | Experimental | `TikTokApi` + Playwright + `ms_token` |

Reddit fue descartado porque respondió HTTP 403 al acceso programático. X queda fuera de la práctica
por costo de API y restricciones anti-bot.

## Paralelismo

La extracción usa un patrón **productor-consumidor**:

```text
Hilo YouTube ──┐
Hilo Bluesky ──┼── queue.Queue ── controlador ── dataset.jsonl / CSV / JSON
Hilo TikTok  ──┘
```

Se usa `threading.Thread` porque la extracción es principalmente **I/O-bound**: cada extractor pasa
la mayor parte del tiempo esperando respuestas de red. La comunicación se hace mediante
`queue.Queue`, que es segura entre hilos, y un único consumidor escribe en disco para evitar
condiciones de carrera.

## Estructura

```text
.
├── CONTRATO.md              # Esquema común de datos
├── ESTRATEGIA_BUSQUEDA.md   # Problemática, fuentes y criterios de búsqueda
├── rubricas/                # Rúbricas de prácticas y proyecto final
└── practica_06/
    ├── config/              # Búsqueda y léxico xenófobo
    ├── src/                 # Extractores, orquestador y almacenamiento
    ├── data/                # Salida local ignorada por Git
    └── evidencia/           # Logs versionables para la entrega
```

## Uso básico

```bash
cd practica_06
uv sync
cp .env.example .env        # rellenar credenciales de Bluesky y TikTok
uv run --env-file .env extractor-mundial --max-por-criterio 50
```

Para recolectar una sola fuente:

```bash
uv run --env-file .env extractor-mundial --redes bluesky
```

Para recalcular la marca `amplia`/`dirigida` después de editar el léxico:

```bash
uv run extractor-mundial --remarcar
```
