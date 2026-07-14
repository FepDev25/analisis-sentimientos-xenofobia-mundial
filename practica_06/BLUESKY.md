# Extractor de Bluesky

> Fuente a cargo de **Sami Suquilanda**. Práctica 6 — Computación Paralela.
> Contrato de datos común: [`../CONTRATO.md`](../CONTRATO.md) · Estrategia: [`../ESTRATEGIA_BUSQUEDA.md`](../ESTRATEGIA_BUSQUEDA.md)

Código: [`src/extractor_mundial/extractores/bluesky.py`](src/extractor_mundial/extractores/bluesky.py)

---

## 1. Por qué Bluesky (y no Reddit)

La fuente asignada originalmente era **Reddit**, como respaldo de X. **Se descartó el 13-jul-2026**
tras comprobar que ya no es accesible de forma programática:

| Comprobación | Resultado |
|---|---|
| `GET www.reddit.com/r/soccer/hot.json` | **HTTP 403** |
| `GET old.reddit.com/r/soccer/hot.json` | **HTTP 403** |
| Con User-Agent de navegador | **HTTP 403** |
| Registro de app en `reddit.com/prefs/apps` | El formulario rebota sin emitir credenciales |

Las cabeceras de la respuesta (`via: varnish`, `server-timing: reddit-ct`) confirman que **el bloqueo
lo emite la CDN de Reddit**, no un intermediario de red local. Sin `client_id` ni `client_secret`, y
con el acceso anónimo bloqueado, no hay vía de extracción viable.

> No se afirma aquí *por qué* Reddit tomó esa decisión — solo se documenta el **comportamiento
> medido y reproducible**.

**Bluesky es el reemplazo natural** porque invierte exactamente el problema:

- Corre sobre el **protocolo abierto AT** (*Authenticated Transfer*), con una API pública documentada.
- La credencial se obtiene **al instante** (cuenta gratuita + *app password*), sin aprobación manual.
- Tiene **conversación orgánica** sobre fútbol y es **multiidioma**, que es justo lo que el estudio
  necesita.

Se evaluaron y **rechazaron** dos alternativas más:
- **Mastodon** — la API es abierta y no pide credenciales, pero el contenido resultó pobre: bots,
  spam y noticias puenteadas automáticamente, con poca conversación real. Queda como plan B.
- **Hacker News** — API abierta, pero es un foro de tecnología. **No hay xenofobia futbolera ahí.**
  Incluirlo rompería la coherencia entre la problemática, la búsqueda y las fuentes.

### Lo que esto aporta al estudio

Las dos fuentes con más valor para el tema (**X** y **Reddit**) son precisamente las dos cerradas.
La conclusión no es anecdótica:

> **La disponibilidad de las fuentes de datos sociales depende de decisiones comerciales de las
> plataformas, no de su viabilidad técnica.** Un diseño de investigación que dependa de una API
> propietaria es frágil por construcción; apoyarse en un **protocolo abierto** es una decisión de
> arquitectura, no solo de conveniencia.

---

## 2. Mecanismo

**HTTP directo con `requests` contra dos endpoints XRPC.** Se descartó a propósito usar una librería
envoltorio (`atproto`): menos dependencias que se rompan, y **el protocolo queda a la vista en el
código**, que es lo que hay que poder explicar.

| Endpoint | Para qué |
|---|---|
| `com.atproto.server.createSession` | Canjea `handle` + **app password** por un JWT (~2 h de vida) |
| `app.bsky.feed.searchPosts` | Búsqueda global de texto, paginada por `cursor` (100 por página) |

**Credenciales** (en `.env`, que está en `.gitignore`):

```
BLUESKY_HANDLE=usuario.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

Se usa un **app password**, no la contraseña de la cuenta: es revocable y de permisos limitados. Si
se filtrara, se revoca y la cuenta no cae.

**Resiliencia:** reintentos con espera creciente (5 s / 15 s / 40 s) ante un `429` (rate limit), y una
consulta caída **no tumba las demás** — se anota en el log y se continúa. En la corrida real, la
consulta `Ecuador gorila` recibió un `502` del servidor de Bluesky y la extracción siguió sin
interrupción.

---

## 3. Estrategia de búsqueda (2 capas)

Se replica **la misma lógica que el extractor de YouTube**, para que las dos redes sean comparables
en el análisis posterior:

| Capa | Cómo se construye | Etiqueta |
|---|---|---|
| **Amplia** | Términos de evento (hashtags, selecciones, jugadores) | `amplia` |
| **Dirigida** | Evento × término del léxico xenófobo | `dirigida` |

Además, **cualquier post cuyo texto contenga un término del léxico se re-marca como `dirigida`**,
aunque haya venido de una búsqueda amplia. Así el campo `estrategia` habilita la estadística clave
del proyecto: *"de N posts recogidos, un X % presenta carga xenófoba"*.

### Decisión medida: los hashtags NO sirven en la capa dirigida

| Consulta | Resultados |
|---|---|
| `#WorldCup2026 monos` | **0** |
| `Brasil monos` | sí devuelve |

La búsqueda de Bluesky exige que **todos** los términos aparezcan en el post, y **nadie escribe un
insulto racista y encima le pone el hashtag oficial del torneo**. Cruzar hashtags con el léxico solo
malgasta presupuesto de consultas.

→ El cruce dirigido se construye solo con **selecciones + jugadores** (`Config.terminos_dirigida`).
Con el mismo tope de 120 consultas se pasó de cubrir **5 términos** del léxico a cubrir **8**.

### Recorrido intercalado

El producto cartesiano completo son miles de consultas. Al recortarlo, **el orden importa**: si se
recorriera evento por evento, el recorte cubriría solo las primeras selecciones. Se recorre
**intercalando por término del léxico**, de modo que el recorte sigue cubriendo **todas** las
selecciones.

---

## 4. Mapeo al contrato

Bluesky **declara el idioma de cada post** (`record.langs`), así que el campo `idioma` del contrato
—que en YouTube va `null`— aquí sí se puede llenar.

| Campo del contrato | Origen en Bluesky |
|---|---|
| `id` | `post.uri` (`at://<did>/app.bsky.feed.post/<rkey>`) — único y estable |
| `red` | `"bluesky"` |
| `estrategia` | `dirigida` si el texto trae léxico **o** vino de consulta dirigida |
| `criterio_busqueda` | La query exacta usada |
| `texto` | `record.text` |
| `idioma` | `record.langs[0]` |
| `autor` | `author.handle` |
| `fecha_publicacion` | `record.createdAt` (ya viene en ISO 8601) |
| `url` | `https://bsky.app/profile/{handle}/post/{rkey}` |
| `metricas` | `likes`, `reposts`, `respuestas`, `citas` |

---

## 5. Uso

```bash
# Recolección (solo esta fuente, sin re-scrapear las de los compañeros)
uv run --env-file .env extractor-mundial --redes bluesky

# Recalcular la marca amplia/dirigida tras editar config/lexico.txt (sin red)
uv run extractor-mundial --remarcar
```

---

## 6. Resultados de la ejecución

Corrida del **13-jul-2026** (log completo en [`evidencia/corrida_bluesky.log`](evidencia/corrida_bluesky.log)):

| Métrica | Valor |
|---|---|
| Consultas lanzadas | 144 (24 amplias + 120 dirigidas) |
| Posts producidos | 37 591 |
| **Posts únicos (tras deduplicar)** | **33 475** |
| Duplicados descartados | 4 116 (consultas que se solapan) |
| Tiempo | **474 s (~8 min)** |

**Por estrategia:**

| Estrategia | Posts | % |
|---|---|---|
| `amplia` | 28 030 | 83.7 % |
| `dirigida` | **5 445** | **16.3 %** |

**Por idioma:**

| Idioma | Posts | % |
|---|---|---|
| `en` | 15 377 | 45.9 % |
| *(no declarado)* | 8 850 | 26.4 % |
| `es` | 5 480 | 16.4 % |
| `pt` | 3 772 | 11.3 % |

> **El 26.4 % de los posts no declara idioma.** Se **conservan** en lugar de descartarlos: filtrar
> estrictamente tiraría más de un cuarto del corpus. El idioma se detectará en la Práctica 7.

---

## 7. Hallazgos sobre la calidad del léxico

La extracción sirvió además para **validar empíricamente el léxico**, y encontró dos problemas reales.

### 7.1 El emoji 🍉 estaba mal calibrado → retirado

Figuraba como "emoji en clave racista". Pero en 2026 la sandía es, de forma abrumadora, el **símbolo
de solidaridad con Palestina**. En el corpus marcaba como xenófobos posts sobre el genocidio en Gaza
(uno de ellos, sobre unas declaraciones de Javier Bardem), que no tienen ninguna relación con la
xenofobia futbolera.

No es un término *ambiguo*: en este contexto es sencillamente **incorrecto**, y contaminaba la
métrica con contenido político no relacionado. **Se movió a la sección APARCADOS del léxico**, con la
justificación documentada.

### 7.2 El término `monkey` produce falsos positivos → se conserva a propósito

`monkey` es el término que más marcas dispara (2 341 de 5 445). Y pesca de todo:

| Post | ¿Xenofobia? |
|---|---|
| *"But in Brazil the people live in trees with monkeys."* | ✅ Sí |
| *"Different than Brazil or **12 Monkeys**…"* | ❌ No — es la película de Terry Gilliam |
| *"**Monkey D. Luffy** is now Samurai Blue"* | ❌ No — es el personaje de One Piece |

**Se conserva deliberadamente.** Este es el caso que **justifica la Práctica 7**: un léxico plano no
puede distinguir *"viven en árboles con monos"* de *"12 Monkeys"*, porque la diferencia **no está en
las palabras, está en el contexto**. Es la evidencia empírica de que el análisis de sentimientos
necesita un modelo con comprensión semántica, no reglas.

Esto confirma con datos la intuición ya recogida en la sección **APARCADOS** del léxico, donde se
habían aparcado a mano los términos *substring-inseguros* (`mono` dentro de "demonio") y los
*ambiguos semánticos* (`negro` como color).

### 7.3 Consecuencia de diseño: el re-marcado

Corregir el léxico **no puede exigir volver a extraer 33 000 posts**. Como el texto ya está guardado,
la marca `amplia`/`dirigida` se recalcula sobre el dataset existente, sin tocar la red
(`--remarcar`, en [`src/extractor_mundial/remarcado.py`](src/extractor_mundial/remarcado.py)).

Esto importa porque el léxico es **un artefacto vivo**: los tres integrantes lo nutren con lo que
observan en campo.

---

## 8. Bug corregido en el almacenamiento

Al implementar el re-marcado se detectó una **pérdida silenciosa de registros** en
`almacenamiento.py::_leer_jsonl` — código común a todas las fuentes, no solo a Bluesky.

`str.splitlines()` de Python no corta únicamente por `\n`: corta **también** por `U+2028`
(LINE SEPARATOR), `U+2029` (PARAGRAPH SEPARATOR) y `U+0085` (NEXT LINE). Esos caracteres son
**legales dentro de un string JSON**, y `json.dumps(..., ensure_ascii=False)` los escribe **sin
escapar**. Un post que los contenga (son frecuentes en texto copiado de redes sociales) **se parte en
dos trozos**, ninguno de los dos es JSON válido, y el `except json.JSONDecodeError: continue` los
descarta **sin avisar**.

- **Medido:** 4 registros perdidos de 33 479 en una sola pasada, y el efecto **se acumula** en cada
  lectura del `jsonl`.
- **Reproducido:** un registro sintético con `U+2028` entra al archivo y salen **cero**.
- **Corregido:** se parte por `"\n"` de forma explícita. Tras el arreglo el re-marcado es
  **idempotente** (33 475 → 33 475, 0 cambios).
