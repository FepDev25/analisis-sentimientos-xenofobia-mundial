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

## Fuentes seleccionadas (3 + respaldo)

| Fuente | Relevancia | Dificultad scraping (2026) | Alcance |
|--------|-----------|----------------------------|---------|
| **YouTube** | Alta (comentarios en resúmenes de goles) | 🟢 Fácil — API oficial | Por canal/video |
| **TikTok** | Muy alta | 🟡 Media — librerías no oficiales | Búsqueda global por hashtag |
| **X** | Máxima (+ ángulo traducción) | 🔴 Difícil — API cara, anti-bot | Búsqueda global por query |
| **Reddit** *(respaldo)* | Alta | 🟢 Fácil | Por subreddit |

**Plan de riesgo:** X es la fuente más valiosa pero la más frágil. Si el extractor de X se cae antes del cierre (15-jul-2026), se reemplaza por **Reddit** (`r/soccer`, `r/worldcup`, subs de selecciones) para no perder la práctica.

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
> - YouTube / Reddit: timestamp por comentario → filtrado limpio del lado cliente.
> - X: operadores `since:`/`until:` existen pero limitados por anti-bot.
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

- **YouTube** → por **canal/video**: canales oficiales de resúmenes (FIFA, ESPN, federaciones, medios deportivos). La API entrega los comentarios del video.
- **X** → **búsqueda global** por query (hashtag + término). El contenido vive en tuiteros independientes, no en cuentas oficiales.
- **TikTok** → **búsqueda global** por hashtag/keyword (misma lógica que X).
- **Reddit** (respaldo) → por **subreddit** (`r/soccer`, `r/worldcup`, subs de selecciones), buscando dentro de ellos.

## Resumen en una línea (para el informe)

> Ventana temporal de 3 capas (previa / torneo / histórica), búsqueda de dos capas (evento × léxico xenófobo) con etiquetado de origen, alcance por canal en YouTube y búsqueda global por hashtag/término en X y TikTok (Reddit por subreddit como respaldo).
