# Contrato de Datos

> Acuerdo obligatorio entre los 3 extractores. **Regla de oro:** los tres devuelven **exactamente el mismo esquema**, sin importar la red. Campos que una red no provea van como `null`, pero la columna/clave existe siempre.

## Esquema

| Campo | Tipo | Descripción | Obligatorio |
|-------|------|-------------|:-----------:|
| `id` | string | ID único del comentario/post (el que da la red). Evita duplicados. | ✅ |
| `red` | string | Fuente: `"x"` \| `"tiktok"` \| `"youtube"` \| `"reddit"`. **Trazabilidad.** | ✅ |
| `estrategia` | string | Origen de recolección: `"amplia"` \| `"dirigida"`. | ✅ |
| `criterio_busqueda` | string | Query/hashtag exacto usado (`"#ARGMEX"`, `"Brasil monos"`, …). **Trazabilidad.** | ✅ |
| `texto` | string | Contenido textual del comentario/post. **Dato central** + insumo Práctica 7. | ✅ |
| `idioma` | string \| null | Idioma detectado (`"es"`, `"pt"`, `"ja"`, …) o `null`. | ⬜ |
| `autor` | string \| null | Usuario/canal que publicó. | ⬜ |
| `fecha_publicacion` | string (ISO 8601) \| null | Timestamp del comentario/post. | ⬜ |
| `url` | string \| null | Link directo al comentario/post/video. Evidencia. | ⬜ |
| `metricas` | dict/JSON | Interacción según la red: `{likes, respuestas, vistas, reposts, …}`. Flexible. | ⬜ |
| `fecha_extraccion` | string (ISO 8601) | Cuándo se descargó el registro. | ✅ |

### Campos mínimos de trazabilidad (exigidos por la rúbrica)

`red` + `criterio_busqueda` + `texto` → identifican de qué fuente viene, qué se buscó y cuál es el contenido. El resto son datos complementarios que suman puntos.

## Reglas de diseño

1. **Mismo esquema siempre.** Si TikTok no da `idioma`, va `null` — pero la clave existe igual en las tres redes.
2. **`metricas` es un diccionario flexible** porque cada red mide distinto (X: reposts; YouTube: vistas). No se fuerza la unificación de lo no unificable.
3. **`id` único por red** para deduplicar. Al consolidar, la unicidad global se garantiza con la combinación (`red`, `id`).
4. **Fechas en ISO 8601** (`2026-07-10T14:30:00Z`) para poder filtrar y ordenar.

## Ejemplo de registro (JSON)

```json
{
  "id": "1810234567890123456",
  "red": "x",
  "estrategia": "dirigida",
  "criterio_busqueda": "#BRAJPN monos",
  "texto": "…",
  "idioma": "pt",
  "autor": "@usuario_ejemplo",
  "fecha_publicacion": "2026-06-28T21:15:00Z",
  "url": "https://x.com/usuario_ejemplo/status/1810234567890123456",
  "metricas": { "likes": 42, "reposts": 7, "respuestas": 3 },
  "fecha_extraccion": "2026-07-10T14:30:00Z"
}
```

## Formato de salida

- **Un archivo por red:** `data/x.csv`, `data/tiktok.csv`, `data/youtube.csv` (y `data/reddit.csv` si se activa el respaldo) → evidencia clara por fuente.
- **Un consolidado:** `data/dataset.csv` (o `dataset.json`) que el orquestador arma juntando los tres → dataset unificado para la Práctica 7.

> Para el campo `metricas` en CSV se serializa como JSON string; en JSON va como objeto anidado.
