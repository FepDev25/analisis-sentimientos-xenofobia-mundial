# Extractor de Twitch

> Fuente a cargo de **José Abad**. Práctica 6 - Computación Paralela.
> Contrato de datos común: [`../CONTRATO.md`](../CONTRATO.md) · Estrategia: [`../ESTRATEGIA_BUSQUEDA.md`](../ESTRATEGIA_BUSQUEDA.md)

Código: [`../src/extractor_mundial/extractores/twitch.py`](../src/extractor_mundial/extractores/twitch.py)

---

## 1. Selección de la fuente

Twitch se incorporó como fuente adicional debido a la disponibilidad de conversaciones públicas
y de alto volumen relacionadas con partidos del Mundial de la FIFA 2026.

A diferencia de una búsqueda general por palabras clave, el chat de un video bajo demanda mantiene
un contexto temporal y temático definido. Todos los mensajes analizados pertenecen a una transmisión
específica relacionada con el partido Portugal contra Colombia.

La fuente utilizada fue:

| Campo | Valor |
|---|---|
| Canal | `ishowspeed` |
| Video | `2806902010` |
| Título | `irl stream Portugal vs Colombia Ronaldo Last Group Game World Cup Full Match Stream` |
| Fecha de inicio | 27-jun-2026 |
| Duración | 21 851 segundos |
| Visualizaciones registradas | 1 895 657 |
| Mensajes originales | 87 317 |

La fecha del video se encuentra dentro del periodo definido para el estudio.

---

## 2. Mecanismo de extracción

La obtención se realizó en dos etapas:

1. Descarga del chat público del video mediante TwitchDownloaderCLI 1.56.4.
2. Procesamiento local del archivo JSON mediante `ExtractorTwitch`.

El comando utilizado para descargar el chat fue:

```bash
./TwitchDownloaderCLI chatdownload \
  --id 2806902010 \
  --output ../../data/twitch_prueba.json \
  --threads 4


```

## 3. Resultados

La extracción produjo 87 317 mensajes originales. Después de aplicar los filtros de limpieza se conservaron 65 444 registros válidos y únicos.

| Métrica | Valor |
|---|---:|
| Mensajes originales | 87 317 |
| Registros válidos | 65 444 |
| Identificadores únicos | 65 444 |
| Autores distintos | 14 636 |
| Videos procesados | 1 |
| Tiempo de procesamiento | 2.01 segundos |

El log completo se encuentra en `evidencia/twitch_extraccion_2806902010.log`.

## 4. Procesamiento

El extractor elimina mensajes de bots, comandos, enlaces sin texto, mensajes compuestos únicamente por emotes y repeticiones inmediatas del mismo usuario. También valida que la fecha se encuentre dentro del periodo configurado.

Todos los registros se clasifican como `amplia`, porque proceden del chat completo de una transmisión y no de consultas realizadas con términos xenófobos.

## 5. Mapeo al contrato

| Campo | Origen |
|---|---|
| `id` | Identificador del comentario |
| `red` | `twitch` |
| `estrategia` | `amplia` |
| `criterio_busqueda` | Canal y título del video |
| `texto` | Cuerpo textual del mensaje |
| `autor` | Usuario del chat |
| `fecha_publicacion` | Fecha del comentario |
| `url` | Video posicionado en el segundo del mensaje |
| `metricas` | Video, canal, segundo, badges y emotes |

## 6. Ejecución

Para procesar los archivos de chat descargados:

    uv run extractor-mundial --redes twitch

## 7. Limitaciones

El corpus corresponde a una transmisión específica del partido Portugal contra Colombia y no representa todas las conversaciones de Twitch sobre el Mundial.

Los mensajes breves pueden depender del momento de la transmisión. Para mantener la trazabilidad, cada registro conserva el segundo exacto del video y una URL posicionada temporalmente.
