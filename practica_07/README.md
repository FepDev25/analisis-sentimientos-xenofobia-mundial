# Práctica 7 — Análisis paralelo de sentimientos sobre datos de redes sociales

Materia: **Computación Paralela** · Entregable de la Práctica de laboratorio 07.

Toma el corpus extraído en la Práctica 6 y realiza un **análisis de sentimientos paralelo**: clasifica cada texto en positivo / negativo / neutral y marca discurso de odio (*hate speech*), para cuantificar el tono del discurso xenófobo durante el Mundial FIFA 2026 por red social, idioma y eje temático.

El **informe técnico completo** (con figuras, tablas y análisis de resultados listo para Overleaf) está en [`informe/INFORME_P7.md`](informe/INFORME_P7.md).

## Núcleo del trabajo: clasificación en paralelo por procesos

La clasificación se paraleliza **por procesos** (`ProcessPoolExecutor`). El corpus se parte en bloques; cada bloque va a un proceso que carga los modelos una sola vez y clasifica su lote:

```
   corpus_dirigida.jsonl ─► bloques ─► ProcessPoolExecutor ─► [proc 1] [proc 2] ... [proc k]
                                                                    │       │           │
                                                                    └───────┴─── checkpoint ─► sentimiento_dirigida.csv/.jsonl
```

**Por qué procesos y no hilos.** La inferencia del transformer es **CPU-bound** (cómputo puro, sin espera de red). El GIL serializa hilos en trabajo de CPU, así que el paralelismo real lo dan los **procesos**. Es un contraste deliberado con la Práctica 6, que era I/O-bound y por eso usó hilos + cola. Misma problemática, técnica adaptada a la naturaleza del trabajo.

Evidencia medida (muestra de 600 textos, 6 procesos): serial 359.8 s, paralelo 137.9 s, **speedup 2.61x**. La eficiencia sub-lineal se explica por el costo fijo de carga de modelos por proceso (detalle en el informe, seccion 6).

## Modelo

`pysentimiento` — modelos *transformer* preentrenados, ejecutados **localmente**. Entrenado sobre tweets (texto corto e informal), multiidioma (español, inglés, portugués, italiano) y con un modelo de *hate speech* integrado que encaja con la problemática de xenofobia. Local y reproducible, sin API de pago. Justificación completa en el informe, seccion 3.

## Datos

Lee el corpus **curado** de la Práctica 6 (inmutable) y escribe en `practica_07/data/`. Se trabaja en dos capas:

| Capa | Registros | Uso |
|---|---|---|
| `corpus_completo` | 396 841 | Todo lo recolectado (5 redes). |
| `corpus_dirigida` | 8 783 | Núcleo denso xenófobo, auditable. Es sobre el que corre el análisis. |

## Estructura

```
practica_07/
├── curacion_datos.ipynb       # P6 -> P7: perfila, normaliza, deduplica, re-marca léxico
├── analisis_sentimiento.ipynb # carga, clasificación paralela, speedup, export, gráficos
├── sentimiento_worker.py       # unidad de trabajo por proceso (importable por el pool)
├── pyproject.toml / uv.lock    # entorno propio (Python 3.11–3.13 + torch/pysentimiento)
├── ENTORNO.md                  # receta de instalación
├── informe/                    # informe técnico + figuras para el artículo
└── data/                       # corpus curado + resultados (ignorado por git)
```

## Uso

### Entorno propio

La Práctica 7 usa un entorno **distinto** al de la Práctica 6: Python 3.11–3.13 (no el 3.14 free-threaded de P6, porque `torch` no publica ruedas para ese build). Desde `practica_07/`:

```bash
uv python install 3.12
uv sync --python 3.12    # baja torch + pysentimiento (~2–3 GB la primera vez)
```

### 1. Curación (P6 -> P7)

Genera el corpus curado en `data/` a partir del dataset de la Práctica 6. Corre con el entorno de P6 (grupo `analisis`), porque lee de `../practica_06/data/`:

```bash
cd ../practica_06
uv run --group analisis jupyter nbconvert --to notebook --execute --inplace \
  ../practica_07/curacion_datos.ipynb
```

### 2. Análisis de sentimientos (paralelo)

Desde `practica_07/`, con su entorno propio:

```bash
uv run jupyter nbconvert --to notebook --execute --inplace analisis_sentimiento.ipynb
```

Config editable en la primera celda del notebook:

- `CORPUS` — `dirigida` (rápido) | `completo` (lento).
- `N_WORKERS` — número de procesos. Limitado por memoria: cada proceso carga ~4 GB de
  modelos, por eso se topa en un valor que entre en la RAM disponible.
- `ANALIZAR_ODIO` — añade el modelo de hate speech.
- `TAMANO_BLOQUE` — filas por bloque enviado a cada proceso.

Salida: `data/sentimiento_<capa>.csv` y `.jsonl`, cada texto ligado a su sentimiento, su score, su red de origen y su marcado xenófobo previo.

## Robustez

La clasificación tiene **checkpoint incremental**: cada bloque terminado se persiste al vuelo, así un corte no pierde lo ya procesado y al re-ejecutar se reanuda saltando lo hecho (mismo patrón que la recolección de la Práctica 6). Un bloque que falla se aísla y el resto del pool continúa.

## Resultados (resumen)

Sobre el núcleo dirigido (8 783 textos): 55.7 % negativo, 33.7 % neutral, 10.6 % positivo. X es la red más hostil (70 % negativo, 40 % hateful); el contenido en español es marcadamente más negativo que en inglés o portugués; los ejes más virulentos son el colonial y el anti-mexicano. El análisis completo, con figuras y limitaciones (incluida la subdetección del odio implícito), está en [`informe/INFORME_P7.md`](informe/INFORME_P7.md).
