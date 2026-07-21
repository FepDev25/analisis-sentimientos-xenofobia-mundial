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

**Sin framework ni compilación.** El proyecto se entrega y se defiende en una sola sesión:
un `npm install` añade un punto de fallo (versiones, red, build) sin aportar nada que estas
cuatro pantallas necesiten. Se abre el archivo y funciona.

**Chart.js con copia local.** Un CDN implica que la demo depende de que haya internet en el
aula. La librería vive en `vendor/`.

**Los filtros se aplican en el navegador.** Una búsqueda en vivo trae como máximo 40
registros por red (tope del backend), así que el conjunto completo cabe en memoria. Filtrar
en el cliente es instantáneo; ir al servidor en cada tecla solo añadiría latencia.

**Los textos se escapan siempre.** Los comentarios vienen de redes sociales y pueden traer
HTML: nunca se insertan sin pasar por `UI.escapar`.

**Los datos del corpus están versionados en `datos_corpus.js`.** La pantalla de
interpretación necesita las cifras de la Práctica 7, pero `data/` está fuera del control de
versiones y pesa cientos de MB. Se guardan solo los agregados ya calculados, con su origen
documentado en el archivo.
