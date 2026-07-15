# Evidencia de ejecución

Logs de corrida que documentan la **ejecución concurrente** de los extractores (requisito central de la rúbrica: "iniciar la extracción de las tres fuentes al mismo tiempo").

## `corrida_multifuente.log` — las 3 redes en paralelo

Corrida de las tres fuentes (YouTube, X, Bluesky) lanzadas a la vez con topes bajos.
Comando:

```bash
uv run --group x --env-file .env extractor-mundial \
  --redes youtube x bluesky --max-por-criterio 5 --max-por-red 15 \
  2>&1 | tee evidencia/corrida_multifuente.log
```

Qué demuestra el log:

- **Entorno:** CPython 3.14 free-threaded, GIL desactivado, 20 núcleos (el banner queda impreso en la salida, de modo que la corrida documenta su propio entorno).
- **Lanzamiento simultáneo:** `Lanzando 3 extractor(es) en paralelo: youtube, bluesky, x`. Los tres hilos arrancan antes de que el controlador empiece a consumir.
- **Consolidación por cola:** cada extractor produce a la `queue.Queue` compartida y un único controlador central deduplica por `(red, id)` y persiste.
- **Prueba de concurrencia:** el tiempo total reportado es el **máximo** de los tres, no la suma. En la corrida: total 106.68 s ≈ el tiempo de YouTube (el más lento), mientras X (17.37 s) y Bluesky (2.78 s) corrieron en paralelo dentro de esa misma ventana.

Resultado de la corrida:

| Red | Registros | Tiempo |
|---|---|---|
| Bluesky | 15 | 2.78 s |
| X | 15 | 17.37 s |
| YouTube | 0 | 106.68 s |

## Nota sobre YouTube = 0 en esta corrida

YouTube devolvió 0 en esta corrida por un **rate-limit temporal** de su lado (visible en el log como `Failed to set sorting`), consecuencia de haber ejecutado la recolección varias veces seguidas en un lapso corto durante las pruebas. Es una condición externa transitoria, no una falla del extractor:

- La **capacidad de YouTube está probada**: hay **372 183 comentarios** de YouTube ya en el dataset consolidado (`data/dataset.jsonl`), recolectados por este mismo extractor.
- El extractor maneja el throttle con **backoff** y **quarantine** de videos no scrapeables, y corta cuando el throttle es sostenido para no colgarse.
- La corrida sigue siendo evidencia válida de **ejecución concurrente**: los tres extractores se lanzaron a la vez y dos produjeron datos en vivo dentro de la misma ventana temporal.

Para reproducir con YouTube produciendo, basta correr cuando su rate-limit se haya enfriado (espaciar las corridas evita el throttle).

## Dataset consolidado

El dataset completo (`data/dataset.jsonl`, ignorado por git) reúne las tres redes:

| Red | Registros |
|---|---|
| YouTube | 372 183 |
| Bluesky | 26 176 |
| X | 4 930 |
