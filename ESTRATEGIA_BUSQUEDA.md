# Estrategia de Búsqueda

> Práctica 6 — Extracción paralela de datos desde redes sociales
> Materia: Computación Paralela

## Problemática

**Xenofobia en redes sociales durante la Copa Mundial de la FIFA 2026.**

Durante el Mundial, las redes sociales se inundan de comentarios xenófobos e insultos entre naciones que sobrepasan la simple rivalidad futbolística. Se observan ataques por aspecto físico, color de piel y cultura, muchas veces disfrazados de "humor" o "broma".

### Ángulos que dan valor al tema

- **Evento gatillo:** el Mundial concentra un pico de xenofobia en poco tiempo, con un antes / durante / después claramente delimitable.
- **Humor como vehículo (hate speech implícito / *veiled hate speech*):** una comunidad grande normaliza comentarios brutales presentándolos como bromas. Es el caso que rompe a los modelos automáticos → hipótesis fuerte para la Práctica 7 y el proyecto final.
- **Traducción automática de X como amplificador:** la función de traducción automática de X, diseñada para conectar culturas, termina facilitando el conflicto interétnico (ej. brasileños ↔ japoneses insultándose vía traducción).

### Ejemplos de campo (material para justificación e informe)

- Senadora de Paraguay a Mbappé (Francia): "criado por chimpancés / no tomó leche sino agua de coco" — xenofobia disfrazada de humor por figura pública.
- Rivalidades México–Argentina, y comentarios hacia Ecuador (referencias a "monos", color de piel).

## Fuentes seleccionadas

| Fuente | Relevancia | Acceso (2026) | Alcance |
|--------|-----------|----------------------------|---------|
| **YouTube** | Alta (comentarios en resúmenes de goles) | 🟢 `yt-dlp` + `youtube-comment-downloader`, sin API key | Por canal/video/playlist |
| **Bluesky** | Alta | 🟢 API oficial del protocolo AT + app password | Búsqueda global por query |
| **TikTok** | Muy alta | 🟡 Media — librerías no oficiales | Búsqueda global por hashtag |

**Fuentes descartadas o fuera del trío:** X tiene máximo valor para el tema, pero queda fuera por API
de pago y restricciones anti-bot. Reddit fue descartado tras responder HTTP 403 al acceso
programático y no emitir credenciales nuevas en su registro de aplicaciones. Bluesky reemplaza a
Reddit porque ofrece búsqueda global sobre un protocolo abierto y acceso inmediato con app password.

### División de trabajo (3 integrantes)

- Cada integrante es **dueño de un extractor** (una red c/u): pelea su fuente.
- Los tres extractores respetan el **mismo contrato de datos** (ver `CONTRATO.md`).
- Se construye un **orquestador común** que lanza los 3 extractores en paralelo (hilos + cola) y consolida. Esto es lo que otorga el puntaje de paralelismo.

## Ventana temporal (3 capas)

| Capa | Rango | Prioridad |
|------|-------|-----------|
| **Núcleo (torneo)** | 11-jun-2026 → hoy | Alta — ~80% del contenido |
| **Previa** | ~11-may → 10-jun-2026 | Media — buildup, sorteos, convocatorias |
| **Histórica** | anterior a mayo | Opcional (*nice to have*) |

> ⚠️ **Realidad técnica:** el filtro por fecha funciona distinto por red.
> - YouTube / Bluesky: timestamp por comentario/post → filtrado posible del lado cliente.
> - TikTok: **sin filtro de fecha usable** → se trae lo disponible y se filtra localmente por el timestamp que venga.
> Patrón real de implementación: *"traer todo lo posible de la búsqueda y filtrar por fecha localmente"*. No prometer en el informe una precisión temporal que TikTok no puede dar.

## Estrategia de keywords — DOS CAPAS + etiquetado de origen

Cada registro se marca con su `estrategia` de origen (`amplia` | `dirigida`). Esto permite estadísticas del tipo *"de N comentarios generales, X% resultaron xenófobos"* para el dashboard del proyecto final.

### Capa A — Evento

- Hashtags de torneo: `#WorldCup2026`, `#FIFAWorldCup`, `#Mundial2026`, `#WC26`
- Hashtags de partido (código FIFA 3 letras): `#ARGMEX`, `#BRAJPN`, `#FRAESP`, …
- Selecciones en varios idiomas: "Brasil/Brazil", "Japón/Japan/日本", etc.
- Jugadores mediáticos: Mbappé, Messi, Vinícius, … (los que más carga generan)

### Capa B — Léxico xenófobo (semilla)

Cruce de *evento × términos peyorativos* para elevar la precisión. Se mantiene en un **archivo de léxico aparte** (`lexico.txt` / similar) que los 3 integrantes nutren con lo observado en campo. Categorías:

- Términos peyorativos / insultos étnicos.
- Marcadores por color de piel y cultura (ej. "monos", "chimpancés").
- Emojis usados en clave racista (🍌, 🐒).
- Multiidioma (es, pt, ja, en, …).

> Documentar el léxico semilla es parte de la **metodología** y conecta directo con la Práctica 7 (clasificación de sentimientos).

### Trade-off elegido: recolectar AMBAS y etiquetar el origen

- **Amplia** (solo capa A): baseline de volumen, más ruido.
- **Dirigida** (capa A × capa B): subconjunto denso en lo relevante.

## Alcance por fuente (resumen)

- **YouTube** → por **canal/video/playlist**: resúmenes y contenido deportivo donde se concentran comentarios.
- **Bluesky** → **búsqueda global** por query: hashtags, selecciones, jugadores y cruces con léxico.
- **TikTok** → **búsqueda global** por hashtag/keyword: plataforma de alto volumen y conversación audiovisual.

## Resumen en una línea (para el informe)

> Ventana temporal de 3 capas (previa / torneo / histórica), búsqueda de dos capas (evento × léxico xenófobo) con etiquetado de origen, alcance por canal/video en YouTube y búsqueda global por query o hashtag en Bluesky y TikTok.
