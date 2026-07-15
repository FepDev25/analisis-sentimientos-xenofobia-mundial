# Análisis de sentimientos sobre xenofobia en el Mundial FIFA 2026

Proyecto de **Computación Paralela**: recolectar, procesar y analizar publicaciones de redes sociales relacionadas con expresiones xenófobas durante la Copa Mundial de la FIFA 2026, aplicando técnicas de paralelismo en cada etapa.

El trabajo se divide en tres entregas encadenadas sobre un mismo hilo conductor:

| Entrega | Objetivo | Estado |
|---|---|---|
| Práctica 6 | Extracción **concurrente** de datos desde al menos tres redes sociales. | Implementada |
| Práctica 7 | **Análisis de sentimientos paralelo** y detección de xenofobia sobre el dataset. | Implementada |
| Proyecto final | Aplicación web con visualización, storytelling y artículo académico. | Pendiente |

Cada práctica tiene su propio README con el detalle: [`practica_06/README.md`](practica_06/README.md) y [`practica_07/README.md`](practica_07/README.md).

## Problemática

Durante el Mundial, la rivalidad deportiva puede convertirse en ataques xenófobos entre países: insultos raciales, burlas sobre el origen nacional o el color de piel, y comentarios presentados como humor. El objetivo es construir un dataset textual de esa conversación y clasificarla para medir su tono y su carga de odio. El detalle de la problemática, las fuentes y los criterios de búsqueda está en [`ESTRATEGIA_BUSQUEDA.md`](ESTRATEGIA_BUSQUEDA.md).

## Las dos etapas, dos formas de paralelismo

El eje del proyecto es que **cada etapa usa la técnica de paralelismo adecuada a la
naturaleza de su trabajo**:

- **Práctica 6 — extracción (I/O-bound).** El scraping pasa la mayor parte del tiempo esperando la red, así que se usan **hilos (`threading`) con una cola (`queue.Queue`)**: los extractores producen a la cola y un controlador central consolida. El GIL se libera durante la espera, de modo que los hilos dan paralelismo real sin el costo de procesos.

- **Práctica 7 — clasificación (CPU-bound).** La inferencia del modelo es cómputo puro, y ahí el GIL sí serializaría a los hilos, así que se usan **procesos** (`ProcessPoolExecutor`): el corpus se parte en bloques y cada proceso clasifica el suyo.

Misma problemática, técnica adaptada al tipo de carga. Ese contraste es un resultado en sí
mismo.

## Práctica 6 — Extracción paralela

Lanza tres extractores en paralelo, cada uno en su hilo, y consolida por una cola compartida.

Fuentes con datos reales:

| Fuente | Mecanismo |
|---|---|
| YouTube | `yt-dlp` + `youtube-comment-downloader` (sin API key) |
| X (Twitter) | Playwright con sesión de navegador logueado |
| Bluesky | API oficial del protocolo abierto AT |

Reddit se descartó (HTTP 403 al acceso programático) y Bluesky lo reemplazó. TikTok quedó implementado pero sin corrida verificada.

Dataset consolidado: **403 mil registros** (YouTube 372 mil, Bluesky 26 mil, X 5 mil), etiquetados en dos capas de búsqueda: `amplia` (términos de evento) y `dirigida` (evento cruzado con un léxico xenófobo de 104 términos en 6 ejes).

## Práctica 7 — Análisis de sentimientos paralelo

Toma el dataset de la Práctica 6, lo cura, y clasifica cada texto en positivo / negativo / neutral marcando además discurso de odio, usando el modelo local **pysentimiento** paralelizado por procesos.

Resultados sobre el núcleo dirigido (8.783 comentarios): 56 por ciento negativo, X como la red más hostil, el español como el idioma más agresivo, y la constatación de que el modelo subdetecta el odio implícito (leet, emojis, juegos de palabras). Aceleración medida: **speedup 2.61x** (serial vs. paralelo). El informe técnico completo, con figuras, está en [`practica_07/informe/INFORME_P7.md`](practica_07/informe/INFORME_P7.md).

## Estructura

```text
.
├── CONTRATO.md              # Esquema de datos común a todas las redes
├── ESTRATEGIA_BUSQUEDA.md   # Problemática, fuentes y criterios de búsqueda
├── rubricas/                # Rúbricas de las prácticas y del proyecto final
├── practica_06/             # Extracción paralela (hilos + cola)
│   ├── config/              # Términos de búsqueda y léxico xenófobo
│   ├── src/                 # Extractores, orquestador y almacenamiento
│   └── evidencia/           # Logs de ejecución para la entrega
└── practica_07/             # Análisis de sentimientos paralelo (procesos)
    ├── curacion_datos.ipynb
    ├── analisis_sentimiento.ipynb
    └── informe/             # Informe técnico + figuras
```

## Inicio rápido

Cada práctica tiene su propio entorno (`uv`) y su README con los comandos exactos. En resumen:

```bash
# Práctica 6 — extracción (las 3 redes en paralelo)
cd practica_06
uv sync
cp .env.example .env        # rellenar credenciales (Bluesky, etc.)
uv run --group x --env-file .env extractor-mundial \
  --redes youtube x bluesky --max-por-criterio 5 --max-por-red 15

# Práctica 7 — análisis de sentimientos (entorno propio)
cd ../practica_07
uv python install 3.12
uv sync --python 3.12
uv run jupyter nbconvert --to notebook --execute --inplace analisis_sentimiento.ipynb
```
