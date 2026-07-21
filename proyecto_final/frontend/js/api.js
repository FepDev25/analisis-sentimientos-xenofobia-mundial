/* Cliente de la API del backend.
 *
 * Es la ÚNICA parte del frontend que sabe que existe HTTP. Las vistas piden
 * datos aquí y reciben objetos ya listos; si el backend cambia de forma, se
 * cambia solo este archivo.
 *
 * El backend no empuja eventos (no hay websockets ni SSE): `POST /busquedas`
 * responde 202 al instante y la búsqueda sigue en segundo plano. Por eso el
 * seguimiento en vivo se hace por sondeo (`seguir`).
 */

const API = (function () {

  const CLAVE_BASE = 'plataforma_api_base';
  let base = localStorage.getItem(CLAVE_BASE) || 'http://127.0.0.1:8000';

  function urlBase() { return base; }

  function fijarBase(nueva) {
    base = nueva.replace(/\/+$/, '');
    localStorage.setItem(CLAVE_BASE, base);
  }

  async function pedir(ruta, opciones = {}) {
    let respuesta;
    try {
      respuesta = await fetch(base + ruta, {
        headers: { 'Content-Type': 'application/json' },
        ...opciones,
      });
    } catch (e) {
      // fetch solo lanza si no hubo respuesta: servidor caído o CORS.
      throw new Error(`No se pudo contactar al servidor en ${base}. ¿Está corriendo el backend?`);
    }
    if (!respuesta.ok) {
      let detalle = respuesta.statusText;
      try {
        const cuerpo = await respuesta.json();
        if (cuerpo && cuerpo.detail) detalle = JSON.stringify(cuerpo.detail);
      } catch (_) { /* el cuerpo no era JSON */ }
      throw new Error(`El servidor respondió ${respuesta.status}: ${detalle}`);
    }
    return respuesta.json();
  }

  /* ── Endpoints ──────────────────────────────────────── */

  const redes            = ()        => pedir('/redes');
  const obtenerBusqueda  = (id)      => pedir(`/busquedas/${id}`);
  const resumen          = (id)      => pedir(`/busquedas/${id}/resumen`);
  const registros        = (id, lim) => pedir(`/busquedas/${id}/registros?limite=${lim || 1000}`);

  const crearBusqueda = (query, redesElegidas) =>
    pedir('/busquedas', {
      method: 'POST',
      body: JSON.stringify({ query, redes: redesElegidas && redesElegidas.length ? redesElegidas : null }),
    });

  /* ── Seguimiento en vivo ────────────────────────────── */

  /* Sondea una búsqueda hasta que el backend la da por terminada.
   *
   * En cada vuelta entrega el estado y el resumen. El resumen es lo que
   * permite distinguir las dos fases del pipeline sin que el backend las
   * anuncie: las filas de `redes` se escriben cuando la extracción concurrente
   * termina, así que si ya hay filas pero la búsqueda sigue "en_curso", lo que
   * está corriendo es la clasificación en el pool de procesos.
   *
   * `alLatir` recibe { busqueda, resumen, fase, segundos }.
   */
  async function seguir(id, alLatir, intervaloMs = 900) {
    const inicio = performance.now();

    for (;;) {
      const busqueda = await obtenerBusqueda(id);

      let datos = null;
      try {
        datos = await resumen(id);
      } catch (_) { /* aún no hay nada que resumir */ }

      const hayRedes = !!(datos && datos.redes && datos.redes.length);
      let fase;
      if (busqueda.estado === 'error')        fase = 'error';
      else if (busqueda.estado !== 'en_curso') fase = 'terminada';
      else if (hayRedes)                       fase = 'clasificando';
      else                                     fase = 'extrayendo';

      alLatir({
        busqueda,
        resumen: datos,
        fase,
        segundos: (performance.now() - inicio) / 1000,
      });

      if (fase === 'terminada' || fase === 'error') return { busqueda, resumen: datos, fase };

      await new Promise((r) => setTimeout(r, intervaloMs));
    }
  }

  /* ¿Responde el backend? Se usa para el semáforo de la cabecera. */
  async function vivo() {
    try { await redes(); return true; } catch (_) { return false; }
  }

  return { urlBase, fijarBase, redes, crearBusqueda, obtenerBusqueda, resumen, registros, seguir, vivo };
})();
