# Frontend — Plataforma de análisis de xenofobia

Interfaz web de la plataforma. Recibe la consulta del usuario, muestra la extracción
concurrente mientras ocurre, y presenta la clasificación de sentimientos, los comentarios
uno a uno y la interpretación de los resultados.

Consume la API de `../backend` (FastAPI). No comparte código con ella: se comunican por HTTP.

## Cómo se ejecuta

No hay que compilar ni instalar nada: son archivos estáticos.

```bash
# desde proyecto_final/frontend/
python3 -m http.server 5173
# abrir http://127.0.0.1:5173
```

También funciona abriendo `index.html` directamente en el navegador (`file://`), porque
no usa módulos ES ni `fetch` de archivos locales.

El backend debe estar corriendo en `http://127.0.0.1:8000`. Si está en otro puerto o en
otra máquina, se cambia con el botón ⚙ de la cabecera (queda guardado en el navegador).

### Probar sin el backend real

El backend carga ~4 GB de modelos al arrancar y necesita credenciales de cuatro redes.
Para desarrollar la interfaz hay un servidor de prueba que imita la misma API con datos
inventados y retardos parecidos a los reales:

```bash
python3 mock/servidor_mock.py     # escucha en el 8000, solo librería estándar
```

No forma parte del sistema entregable: la demo se hace contra el backend real.

## Las cuatro pantallas

Cada pestaña corresponde a un criterio de la rúbrica de la aplicación web.

| Pestaña | Qué muestra |
|---|---|
| **1 · Búsqueda en vivo** | La consulta, el avance de cada red y la evidencia de que corren en paralelo |
| **2 · Clasificación** | Sentimiento global y por red social, más el eje independiente de discurso de odio |
| **3 · Explorador** | Cada comentario con su red, idioma, sentimiento y marca de odio, filtrable |
| **4 · Interpretación** | Lectura cualitativa de la búsqueda actual y los cinco hallazgos del corpus |

### Cómo se muestra la concurrencia

El backend no empuja eventos: `POST /busquedas` responde 202 al instante y la búsqueda
sigue en segundo plano. El frontend sondea `GET /busquedas/{id}` y deduce en qué fase está
sin que el servidor se lo diga:

- si la búsqueda sigue **en curso** y el resumen aún no tiene filas por red → **extrayendo**
  (los hilos siguen esperando a las redes);
- si ya hay filas por red pero la búsqueda **no ha terminado** → **clasificando**
  (la extracción acabó y el pool de procesos está infiriendo);
- cuando el estado deja de ser `en_curso` → **terminada**.

Esas dos fases son los dos regímenes de paralelismo del proyecto: hilos para esperar red
(I/O) y procesos para inferir (CPU).

Al terminar se contrasta la duración de cada red contra la suma de todas: como arrancan a
la vez, el total lo marca la más lenta, no la acumulación. Ese cociente es el speedup de la
extracción y se muestra en pantalla.

## Estructura

```
frontend/
├── index.html            estructura de las cuatro vistas
├── css/estilos.css       toda la presentación
├── js/
│   ├── api.js            cliente HTTP: lo único que sabe que existe el backend
│   ├── graficos.js       colores, formato, envoltorio de Chart.js y estado compartido
│   ├── datos_corpus.js   resultados del corpus medidos en la Práctica 7
│   ├── vista_busqueda.js pantalla 1
│   ├── vista_dashboard.js pantalla 2
│   ├── vista_explorador.js pantalla 3
│   ├── vista_historia.js pantalla 4
│   └── app.js            pestañas, estado del servidor y arranque
├── vendor/chart.umd.js   Chart.js 4.4.3 (copia local, sin CDN)
└── mock/servidor_mock.py servidor de prueba para desarrollo
```

## Decisiones

### Por qué HTML y JavaScript planos, sin framework

No es una simplificación por falta de tiempo: es que **ninguna de las razones por las que
existe un framework aplica a esta interfaz**.

React, Vue o Angular resuelven tres problemas concretos: sincronizar estado complejo entre
muchos componentes, reutilizar componentes en aplicaciones grandes, y evitar redibujar el
DOM entero en interfaces que cambian constantemente. Aquí:

- **El estado es uno solo y cambia una vez por búsqueda.** Todas las vistas leen del mismo
  objeto (`Estado`) y se redibujan cuando cambia. Eso son 8 líneas de código, no una
  librería de 40 KB con su propio modelo mental.
- **Son cuatro pantallas fijas**, no un catálogo de componentes reutilizables.
- **El volumen es pequeño**: ≤ 160 registros por búsqueda. Redibujar la tabla entera cuesta
  milisegundos; la optimización que ofrece un DOM virtual no tiene nada que optimizar.

A cambio, un framework habría traído costos reales para este proyecto:

- Un paso de compilación (`npm install`, `npm run build`) que es un punto de fallo más
  justo antes de una entrega, y que depende de descargar cientos de paquetes.
- Código que **no se puede leer directamente**: lo que se entrega compilado no se parece a
  lo que se escribió, lo que dificulta explicarlo y defenderlo.
- Un tamaño desproporcionado respecto a lo que hace la interfaz.

El resultado es que **el frontend completo son ocho archivos que se pueden leer de arriba a
abajo**, y que funcionan abriendo `index.html` sin instalar absolutamente nada. Para un
proyecto que hay que explicar, revisar y defender, esa transparencia vale más que las
comodidades de un framework.

**Chart.js con copia local.** Es la única dependencia, y está vendorizada en `vendor/`.
Un CDN implicaría que la demo depende de que haya internet en el aula.

### La paleta de datos (no se eligió a ojo)

Los colores de los gráficos se validaron con un comprobador de contraste y de separación
perceptual para daltonismo. De ahí salieron dos reglas que el código respeta:

**1. Los colores con significado están reservados.** Rojo = negativo, azul = positivo,
gris = neutral, naranja = discurso de odio. Las redes sociales usan **otros cuatro tonos**
(violeta, ámbar, magenta, verde), de modo que un mismo color nunca significa dos cosas
distintas en pantallas contiguas.

**2. La escala de sentimiento es rojo↔azul, no rojo↔verde.** Es la decisión menos obvia y
la más importante: rojo y verde son prácticamente **indistinguibles para la deuteranopia**
(separación perceptual ΔE 4,1, muy por debajo del mínimo de 8), mientras que rojo y azul dan
ΔE 19,2. Como el sentimiento es el dato central de la aplicación, no puede depender de una
distinción que una parte de los lectores no percibe. El gris del medio es el punto neutro de
una escala divergente.

Además, el color nunca es la única señal: las cuatro redes llevan siempre su nombre escrito
al lado, las barras apiladas mantienen un orden fijo (negativo → neutral → positivo) y todos
los gráficos tienen leyenda y valores en el tooltip.

**Sin gráficos de doble eje.** Cuando hay que comparar dos magnitudes de escala distinta
(volumen de comentarios frente a porcentaje de odio, en la pestaña 4) se usan **dos gráficos
apilados que comparten el orden de categorías**, no dos escalas en un mismo par de ejes: eso
último invita a leer cruces entre curvas que no significan nada.

### Por qué no se despliega en un servidor

La aplicación **corre en local a propósito**, y no por falta de recursos. Hay tres razones,
en orden de peso:

1. **El modelo de clasificación vive en memoria del servidor.** Cada proceso del pool carga
   ~4 GB de `pysentimiento`, y el pool se mantiene caliente mientras viva el proceso. Los
   planes gratuitos de hosting (Render: 512 MB; Fly.io: 256 MB; Firebase Hosting: solo
   archivos estáticos, no ejecuta Python) están **uno o dos órdenes de magnitud por debajo**
   de lo que el sistema necesita. No es un problema de configuración: no cabe.
2. **Una de las fuentes exige una sesión de navegador real.** X se lee con las cookies de
   una sesión iniciada manualmente, que caduca y ocasionalmente pide un captcha resuelto por
   una persona. Eso no puede vivir en un servidor sin intervención humana.
3. **La inferencia local es una decisión metodológica, no un parche.** El corpus es discurso
   de odio recolectado de personas reales: procesarlo en la máquina evita enviarlo a un
   tercero, no genera costo por token, y hace el experimento reproducible sin depender de que
   un servicio externo siga existiendo o mantenga sus precios.

La rúbrica pide *"una aplicación web"*, es decir que la interfaz sea web y corra en el
navegador — no que esté publicada en internet. El sistema se demuestra ejecutándolo, y el
procedimiento completo está documentado en este README para que cualquiera lo reproduzca.

**Los filtros se aplican en el navegador.** Una búsqueda en vivo trae como máximo 40
registros por red (tope del backend), así que el conjunto completo cabe en memoria. Filtrar
en el cliente es instantáneo; ir al servidor en cada tecla solo añadiría latencia.

**Los textos se escapan siempre.** Los comentarios vienen de redes sociales y pueden traer
HTML: nunca se insertan sin pasar por `UI.escapar`.

**Los datos del corpus están versionados en `datos_corpus.js`.** La pantalla de
interpretación necesita las cifras de la Práctica 7, pero `data/` está fuera del control de
versiones y pesa cientos de MB. Se guardan solo los agregados ya calculados, con su origen
documentado en el archivo.
