Apertura: jueves, 9 de julio de 2026, 00:00 Cierre: miércoles, 22 de julio de 2026, 13:59

## Antecedentes

El proyecto final de la asignatura de Computación Paralela integra las competencias desarrolladas a lo largo de las prácticas de laboratorio, orientadas al diseño, implementación y evaluación de soluciones paralelas. Estas actividades han permitido abordar modelos de programación, arquitecturas de cómputo, concurrencia mediante hilos y procesos, y el uso de tecnologías de alto rendimiento, consolidando una base teórico-práctica sólida.

Las prácticas 6 y 7 constituyen el núcleo aplicado: la primera se enfocó en la extracción concurrente y preprocesamiento de datos de redes sociales, mientras que la segunda incorporó modelos de análisis de sentimientos basados en LLMs, evaluando además el rendimiento del procesamiento paralelo.

Sobre esta base, el proyecto propone el desarrollo de una solución integral para la extracción, procesamiento, análisis y visualización de datos, combinando computación paralela y procesamiento de lenguaje natural. En este contexto, el estudiante aplicará la teoría de ciencias de la computación y los fundamentos de desarrollo de software para identificar y diseñar soluciones adecuadas a problemas complejos, así como implementará dichas soluciones de manera eficiente. El proyecto se estructura en dos componentes: (i) una aplicación web con procesos concurrentes y (ii) un artículo académico que documenta la metodología y los resultados.

En conjunto, el proyecto articula computación paralela, ingeniería de software e inteligencia artificial, evidenciando la capacidad del estudiante para resolver problemas reales mediante el uso eficiente de recursos computacionales.

## Descripción del Problema

En la actualidad, las redes sociales se han convertido en una de las principales fuentes de generación de información a gran escala, reflejando opiniones, percepciones y comportamientos de los usuarios en tiempo real. Plataformas como TikTok, Facebook, X, Instagram y otras permiten acceder a grandes volúmenes de datos no estructurados, los cuales pueden ser analizados para la toma de decisiones en diversos contextos, tales como marketing, análisis político, monitoreo social y estudios de comportamiento.

Sin embargo, el procesamiento de esta información presenta múltiples desafíos. En primer lugar, la alta velocidad y volumen de generación de datos dificultan su recolección y análisis utilizando enfoques secuenciales tradicionales. En segundo lugar, la naturaleza no estructurada del texto requiere la aplicación de técnicas avanzadas de procesamiento de lenguaje natural (NLP) para su limpieza, transformación y análisis. Adicionalmente, la diversidad de fuentes implica la necesidad de integrar información proveniente de distintas plataformas, cada una con características y formatos particulares.

Otro desafío relevante es la identificación automática del sentimiento asociado a los comentarios y publicaciones, lo cual requiere el uso de modelos de aprendizaje automático o modelos de lenguaje de gran escala (LLMs) capaces de interpretar el contexto semántico del texto. Este proceso no solo debe ser preciso, sino también eficiente, considerando la gran cantidad de datos a procesar.

En este contexto, surge la necesidad de diseñar e implementar una solución informática que permita:

- Extraer datos desde múltiples redes sociales de forma concurrente.
- Procesar grandes volúmenes de información textual.
- Clasificar automáticamente el sentimiento de los datos obtenidos.
- Integrar y visualizar los resultados de manera clara y comprensible.

Además, no es suficiente con presentar resultados cuantitativos; es necesario interpretar los patrones identificados , generando un análisis que permita comprender el comportamiento del sentimiento en función de la fuente de información y el contexto de la consulta realizada.

Por tanto, el problema central que aborda este proyecto consiste en:

¿Cómo diseñar e implementar una solución basada en computación paralela que permita extraer, procesar y analizar grandes volúmenes de datos provenientes de redes sociales, clasificando su sentimiento y generando resultados interpretables de manera eficiente, de modo que el estudiante aplique la teoría de ciencias de la computación y los fundamentos de desarrollo de software para identificar y diseñar la solución, así como implemente dicha solución de manera eficiente?

## Componentes del proyecto

## Desarrollo de la aplicación

La solución propuesta consiste en el desarrollo de una aplicación web que integre los procesos de extracción, procesamiento y análisis de datos provenientes de redes sociales, incorporando técnicas de concurrencia y procesamiento de lenguaje natural.

A nivel funcional, la aplicación deberá permitir la definición de una consulta de búsqueda y gestionar la obtención concurrente de información desde múltiples fuentes (al menos cuatro plataformas). Los datos recuperados deberán ser procesados para determinar el sentimiento asociado a cada elemento, generando resultados tanto a nivel global como segmentados por red social.

La solución deberá facilitar la exploración de los datos obtenidos, permitiendo visualizar los comentarios y su clasificación correspondiente, así como presentar una interpretación de los resultados mediante un enfoque de storytelling que dé contexto a los patrones identificados.

A nivel de diseño, cada grupo deberá proponer una arquitectura de software que soporte este flujo de procesamiento, justificando las decisiones relacionadas con almacenamiento, procesamiento concurrente y mecanismos de análisis. En este sentido, se espera que se definan y argumenten los componentes necesarios, incluyendo el tipo de base de datos, la estrategia de paralelismo empleada y los modelos o servicios utilizados para la clasificación de sentimientos.

La propuesta deberá evidenciar coherencia entre los requerimientos funcionales, el diseño planteado y la implementación desarrollada, sirviendo como base para la validación experimental y la documentación formal del proyecto en el artículo académico.

## Artículo académico

Como complemento al desarrollo de la solución propuesta, los estudiantes deberán elaborar un artículo académico en idioma inglés que documente de manera formal la aplicación web desarrollada, la cual integra los procesos de extracción, procesamiento y análisis de datos provenientes de redes sociales mediante técnicas de concurrencia y procesamiento de lenguaje natural, siguiendo la plantilla oficial de Springer.

El artículo deberá presentar de forma estructurada el problema abordado, la propuesta de solución, el diseño de la arquitectura, el desarrollo realizado y los resultados obtenidos. Se espera que el contenido refleje coherencia entre los distintos componentes del proyecto, evidenciando la relación entre el planteamiento del problema, las decisiones de diseño, la implementación y el análisis de resultados.

En cuanto a su estructura, el documento deberá incluir un título conciso, con una extensión máxima de 20 palabras, así como un resumen (abstract) que describa la problemática, la propuesta de solución, los resultados relevantes y las conclusiones generales, con una extensión entre 250 y 300 palabras.

La sección de introducción deberá contextualizar el problema, definir claramente el objetivo del trabajo, presentar la propuesta de solución y describir la organización del documento. Por su parte, la sección de trabajos relacionados deberá incluir al menos cuatro publicaciones recientes, en las cuales se analicen el problema abordado, la metodología utilizada y los resultados obtenidos, estableciendo una relación con la propuesta desarrollada.

En la sección de metodología, los estudiantes deberán presentar la arquitectura de la solución mediante un esquema gráfico, junto con una explicación detallada de sus componentes y del flujo de procesamiento implementado. Asimismo, deberán describir las decisiones técnicas adoptadas durante el desarrollo.

La sección de resultados deberá incluir un análisis del desempeño de la solución, considerando aspectos como la precisión de la clasificación de sentimientos, los resultados obtenidos en los casos de estudio y los tiempos de ejecución asociados al procesamiento de los datos.

Finalmente, la sección de conclusiones deberá sintetizar los principales hallazgos del trabajo, incluyendo al menos cuatro conclusiones relacionadas con el procesamiento de lenguaje natural, los algoritmos utilizados, el uso de computación de alto rendimiento y los resultados obtenidos. Adicionalmente, se deberán plantear al menos dos recomendaciones derivadas del estudio. El documento deberá incluir un mínimo de quince referencias bibliográficas pertinentes y correctamente citadas.

El artículo académico deberá evidenciar rigor científico, claridad en la redacción y consistencia entre los diferentes apartados, constituyéndose como el soporte formal que valida el desarrollo técnico realizado en el proyecto.

## Rúbrica de Valoración de Conocimientos del Proyecto Final

La evaluación del proyecto final se realizará mediante una rúbrica orientada a valorar de manera integral el desarrollo de la aplicación y la calidad del artículo académico. Esta rúbrica tiene un enfoque formativo y permite evaluar tanto los aspectos técnicos como la capacidad de análisis, interpretación y comunicación de resultados.

Cada criterio será evaluado en cuatro niveles de desempeño:

| Nivel                                                     | Descripción                                                                      |
|-----------------------------------------------------------|----------------------------------------------------------------------------------|
| Excelente                                                 | Cumple completamente con los requerimientos y evidencia un alto nivel de dominio |
| Bueno                                                     | Cumple adecuadamente con los requerimientos, con pequeñas limitaciones           |
| Básico                                                    | Cumple parcialmente con los requerimientos                                       |
| InsuficienteNo cumple con los requerimientos establecidos | InsuficienteNo cumple con los requerimientos establecidos                        |

## Implementación de la Aplicación Web (8 puntos)

| Aspecto a evaluar | Excelente | Bueno | Básico | Insuficiente | Puntaje Máx. |
|---|---|---|---|---|---|
| Integración de extracción concurrente de datos | La búsqueda por query y la extracción concurrente desde múltiples redes sociales funciona correctamente y de forma integrada | Funciona con pequeñas limitaciones o inconsistencias | Funciona parcialmente o solo para algunas redes | No funciona o no se evidencia concurrencia | 2 |
| Clasificación de sentimientos | Presenta clasificación general y por red social de forma clara y consistente | Presenta clasificación general pero limitada por red social | Clasificación incompleta o poco clara | No presenta clasificación funcional | 2 |
| Visualización y exploración de resultados | Permite visualizar comentarios por red social y su clasificación de manera organizada | Permite visualización parcial de resultados | Visualización mínima o poco usable | No se visualizan resultados | 2 |
| Storytelling y explicabilidad de resultados | Integra interpretación cualitativa coherente de los resultados cuantitativos | Presenta explicaciones generales con poca profundidad | Explicabilidad superficial o confusa | No presenta storytelling ni explicabilidad | 2 |

## Artículo Académico (12 puntos)

### Resumen (Abstract) - 2 puntos

| Aspecto a evaluar | Excelente | Bueno | Básico | Insuficiente | Puntaje Máx. |
|---|---|---|---|---|---|
| Resumen (Abstract) | Incluye claramente todos los elementos: problemática, objetivo, metodología, resultados y conclusiones, con redacción precisa, coherente y dentro del rango de palabras establecido | Incluye la mayoría de elementos solicitados, con leves omisiones o problemas de claridad/redacción | Incluye algunos elementos, pero con omisiones importantes o redacción poco clara | Presenta un resumen incorrecto, incoherente o fuera de contexto | 2 |

### Secciones Principales - 2 puntos cada una

| Aspecto a evaluar | Excelente | Bueno | Básico | Insuficiente | Puntaje Máx. |
|---|---|---|---|---|---|
| Introducción | Presenta claramente el contexto, define el problema de forma precisa, establece la motivación, describe la propuesta de solución, resume resultados y detalla la organización del documento | Presenta contexto, problema y propuesta, pero omite parcialmente motivación, resultados u organización del documento | Presenta el problema de forma general, con falta de claridad en la propuesta o sin estructura definida | No define claramente el problema o carece de coherencia y estructura | 2 |
| Trabajos relacionados | Analiza al menos 4 trabajos recientes (≤ 3 años), describiendo problema, metodología y resultados, e incorpora comparación crítica con la propuesta | Describe los trabajos relacionados, pero con análisis limitado o sin comparación clara con la propuesta | Presenta trabajos sin análisis profundo o sin conexión clara con la investigación | No cumple con número, actualidad o análisis requerido | 2 |
| Metodología | Presenta una arquitectura clara y bien estructurada, con soporte gráfico, describe componentes, flujo de datos, tecnologías utilizadas (NLP, LLMs, concurrencia) y justifica decisiones técnicas | Presenta arquitectura y componentes, pero con explicación limitada o sin justificar completamente las decisiones | Presenta una descripción parcial de la solución, con falta de claridad en arquitectura o componentes | No presenta una metodología clara o es inconsistente con la solución propuesta | 2 |
| Resultados y conclusiones | Presenta resultados cuantitativos y cualitativos, analiza precisión/desempeño, discute implicaciones, y formula conclusiones coherentes alineadas con los objetivos, incluyendo al menos 2 recomendaciones | Presenta resultados y conclusiones correctas, pero con análisis limitado o sin profundizar en implicaciones | Presenta resultados sin análisis claro o conclusiones débiles/no alineadas | No presenta resultados válidos o conclusiones coherentes | 2 |
| Bibliografía | Incluye al menos 15 referencias relevantes, actualizadas (últimos años), correctamente citadas y alineadas con el problema y la solución propuesta | Incluye la mayoría de referencias requeridas, con leves problemas de relevancia, actualidad o formato de citación | Incluye un número insuficiente de referencias o presenta problemas significativos de calidad o citación | No cumple con el número mínimo de referencias o presenta citación incorrecta o inexistente | 2 |

La calificación final del proyecto se obtiene mediante la suma de los puntajes obtenidos en cada uno de los criterios evaluados, con un máximo de 20 puntos.