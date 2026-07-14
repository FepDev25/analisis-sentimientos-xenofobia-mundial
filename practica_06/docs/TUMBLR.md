# Extractor de Tumblr

> Fuente a cargo de **José Abad**. Práctica 6 - Computación Paralela.

Código: `src/extractor_mundial/extractores/tumblr.py`

## 1. Selección de la fuente

Tumblr se utilizó como fuente digital adicional porque dispone de una API oficial y permite consultar publicaciones públicas relacionadas con el Mundial de la FIFA 2026. La plataforma aporta contenido textual con identificador, autor, fecha, etiquetas y URL original.

## 2. Mecanismo de extracción

El extractor realiza solicitudes HTTP a la API oficial de Tumblr. La autenticación utiliza la variable `TUMBLR_API_KEY`, almacenada en el archivo `.env` y excluida del repositorio.

Las consultas emplean etiquetas relacionadas con el Mundial, selecciones, jugadores y términos futbolísticos. También se valida que cada publicación mantenga relación con el contexto del torneo.

## 3. Procesamiento

Antes de guardar los registros se aplican las siguientes operaciones:

- normalización del contenido textual;
- eliminación de publicaciones sin texto;
- eliminación de duplicados;
- validación de la ventana temporal;
- comprobación del contexto futbolístico;
- conservación de etiquetas, autor, fecha y URL;
- clasificación de la estrategia como amplia o dirigida.

## 4. Mapeo al contrato

| Campo | Origen |
|---|---|
| `id` | Identificador de la publicación |
| `red` | `tumblr` |
| `estrategia` | `amplia` o `dirigida` |
| `criterio_busqueda` | Etiqueta utilizada |
| `texto` | Contenido textual normalizado |
| `autor` | Nombre del blog |
| `fecha_publicacion` | Fecha de la publicación |
| `url` | URL original |
| `metricas` | Etiquetas y metadatos disponibles |

## 5. Ejecución

Para ejecutar únicamente esta fuente:

    uv run --env-file .env extractor-mundial --redes tumblr

## 6. Resultados

La extracción produjo 3 770 publicaciones únicas.

| Estrategia | Registros |
|---|---:|
| Amplia | 3 745 |
| Dirigida | 25 |
| Total | 3 770 |

La evidencia se encuentra en `evidencia/corrida_tumblr.log`.

## 7. Limitaciones

Tumblr contiene publicaciones de comunidades diversas. Por ello se aplicó un filtro de contexto para reducir resultados no relacionados con fútbol. La clasificación definitiva de xenofobia se realizará en las etapas posteriores del proyecto, donde podrá analizarse el significado contextual de cada publicación.
