Apertura:

jueves, 9 de julio de 2026, 00:00

Cierre:

miércoles, 15 de julio de 2026, 13:59

## OBJETIVOS

- Identificar una problemática real que pueda ser analizada a partir de información publicada en redes sociales.
- Diseñar una estrategia de extracción de datos basada en una consulta, búsqueda, hashtag, palabra clave o criterio definido por los estudiantes.
- Seleccionar al menos tres redes sociales o fuentes digitales relacionadas con la problemática planteada.
- Implementar una solución paralela o concurrente que permita extraer datos desde las tres fuentes de información al mismo tiempo.
- Aplicar los conceptos de computación paralela revisados en la asignatura para justificar el diseño propuesto.
- Generar una base inicial de datos textuales que será utilizada posteriormente en el proyecto final para análisis de sentimientos, visualización y storytelling.

## INSTRUCCIONES

## Extracción paralela de datos desde redes sociales

En esta práctica, cada grupo deberá identificar una problemática real que pueda ser analizada mediante información publicada en redes sociales o fuentes digitales equivalentes.

La problemática puede estar relacionada con temas sociales, educativos, ambientales, políticos, deportivos, culturales, tecnológicos, comerciales o institucionales.

## Ejemplos:

- Percepción ciudadana sobre la seguridad en Cuenca.
- Opiniones sobre el uso de inteligencia artificial en la educación.
- Comentarios sobre el turismo en Ecuador.
- Percepción sobre una marca, producto o servicio.
- Reacciones frente a un evento deportivo, social o político.
- Opiniones de estudiantes sobre una universidad, carrera o servicio académico.

A partir de la problemática seleccionada, el grupo deberá definir una estrategia de búsqueda. Esta estrategia puede estar basada en:

- Palabras clave.
- Hashtags.
- Consultas por tema.
- Búsqueda por usuario, canal o página.
- Búsqueda por fechas.
- Búsqueda por publicaciones relacionadas.

Cada grupo deberá seleccionar al menos tres redes sociales o fuentes digitales desde donde pueda obtener información textual relacionada con la problemática.

## Ejemplo:

- YouTube.
- Reddit.
- X/Twitter.
- Facebook.
- Instagram.
- TikTok.
- LinkedIn.
- Threads
- TripAdvisor.
- Kick
- Snapchat

Debido a las restricciones de acceso de algunas redes sociales, cada grupo deberá proponer e implementar una estrategia de extracción de datos, la cual puede incluir la creación de scrapers, el uso de APIs oficiales, librerías de terceros u otros mecanismos justificados. Lo importante es que exista una relación clara entre la problemática seleccionada, la búsqueda planteada, las fuentes utilizadas y los datos obtenidos.

## REQUERIMIENTO PRINCIPAL DE PARALELISMO

La extracción de datos deberá realizarse de forma paralela o concurrente .

El sistema debe iniciar la extracción desde las tres fuentes de información al mismo tiempo, o mediante una estrategia equivalente que evidencie ejecución concurrente.

Cada grupo deberá proponer y justificar la técnica utilizada con base en los contenidos revisados en la asignatura.

El grupo deberá explicar por qué eligió esa técnica y cómo se relaciona con el problema planteado.

## Por ejemplo:

- Uso de hilos si la extracción depende principalmente de llamadas a APIs o lectura de datos.
- Uso de procesos si se requiere procesamiento adicional durante la extracción.
- Uso de colas si se necesita comunicar datos entre extractores y un controlador central.
- Uso de un pool si se desea administrar automáticamente varias tareas de extracción.

## Almacenamiento y organización de los datos

Cada grupo podrá seleccionar el mecanismo de almacenamiento que considere más adecuado para su solución, de acuerdo con el diseño propuesto. Se podrán utilizar archivos en formato CSV o JSON, bases de datos relacionales, bases de datos NoSQL, archivos independientes por cada red social o fuente de información, u otra alternativa debidamente justificada.

Independientemente del mecanismo seleccionado, el almacenamiento deberá conservar la trazabilidad de los datos. Es decir, cada registro deberá permitir identificar claramente de qué red social o fuente proviene la información, cuál fue la consulta, palabra clave, hashtag o criterio de búsqueda utilizado, y cuál es el contenido textual obtenido. De manera complementaria, se podrán almacenar otros datos disponibles, como fecha de publicación, autor, usuario, canal, número de reacciones, comentarios, visualizaciones u otras métricas de interacción.

## ENTREGABLES

Los estudiantes deberán subir al AVAC:

- Enlace de GitHub

## GUÍA DE EVALUACIÓN

| Criterio                                                         |   Puntos |
|------------------------------------------------------------------|----------|
| Definición clara de la problemática                              |      0.7 |
| Justificación de las tres redes sociales o fuentes seleccionadas |      0.6 |
| Diseño propuesto de la solución y estrategia de búsqueda         |      0.7 |
| Implementación de extracción paralela o concurrente              |      1.2 |
| Uso adecuado y justificación de la técnica de paralelismo        |      0.7 |
| Almacenamiento correcto de los datos extraídos                   |      0.5 |
| Evidencia de ejecución y dataset generado                        |      0.4 |
| Relación clara con el proyecto final                             |      0.2 |
| Total                                                            |      5.0 |

Resumir

Agregar entrega

## Estado de la entrega