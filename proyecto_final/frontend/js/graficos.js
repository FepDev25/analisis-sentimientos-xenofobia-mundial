/* Utilidades de presentación: colores, formato y envoltorio de Chart.js.
 *
 * Todo lo visual compartido vive aquí para que las cuatro vistas se vean como
 * una sola aplicación: el mismo rojo significa "negativo" en todas partes.
 */

const UI = (function () {

  /* Un color por red, estable en toda la app (gráficos, carriles y tabla). */
  const COLOR_RED = {
    bluesky:  '#4f8cff',
    x:        '#9aa4b8',
    youtube:  '#ff4d4d',
    mastodon: '#a78bfa',
    tumblr:   '#38bdf8',
    tiktok:   '#2dd4bf',
    reddit:   '#fb923c',
  };
  const COLOR_POR_DEFECTO = '#6b7280';

  const COLOR_SENTIMIENTO = {
    negativo: '#e5484d',
    neutral:  '#8b8d98',
    positivo: '#30a46c',
  };

  const ORDEN_SENTIMIENTO = ['negativo', 'neutral', 'positivo'];

  const NOMBRE_RED = {
    bluesky: 'Bluesky', x: 'X', youtube: 'YouTube',
    mastodon: 'Mastodon', tumblr: 'Tumblr', tiktok: 'TikTok', reddit: 'Reddit',
  };

  const colorRed  = (red) => COLOR_RED[red] || COLOR_POR_DEFECTO;
  const nombreRed = (red) => NOMBRE_RED[red] || red;

  /* ── Formato ────────────────────────────────────────── */

  const numero = (n) => (n == null ? '—' : n.toLocaleString('es-EC'));
  const segundos = (s) => (s == null ? '—' : `${s.toFixed(2)} s`);
  const porcentaje = (parte, total) => (!total ? '0 %' : `${((parte / total) * 100).toFixed(1)} %`);

  /* Inserta texto sin interpretarlo como HTML. Los comentarios vienen de redes
   * sociales: nunca se concatenan en innerHTML. */
  function escapar(txt) {
    const d = document.createElement('div');
    d.textContent = txt == null ? '' : String(txt);
    return d.innerHTML;
  }

  /* ── Chart.js ───────────────────────────────────────── */

  Chart.defaults.color = '#98a1b3';
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  Chart.defaults.font.size = 11;
  Chart.defaults.animation.duration = 450;

  const REJILLA = { color: 'rgba(255,255,255,.06)' };

  /* Chart.js no permite dos gráficos sobre el mismo canvas: se guarda la
   * instancia por id y se destruye antes de redibujar. */
  const instancias = {};

  function dibujar(idCanvas, config) {
    const lienzo = document.getElementById(idCanvas);
    if (!lienzo) return null;
    if (instancias[idCanvas]) instancias[idCanvas].destroy();
    instancias[idCanvas] = new Chart(lienzo, config);
    return instancias[idCanvas];
  }

  function limpiar(idCanvas) {
    if (instancias[idCanvas]) { instancias[idCanvas].destroy(); delete instancias[idCanvas]; }
  }

  return {
    COLOR_RED, COLOR_SENTIMIENTO, ORDEN_SENTIMIENTO, REJILLA,
    colorRed, nombreRed, numero, segundos, porcentaje, escapar, dibujar, limpiar,
  };
})();


/* Estado compartido: el resultado de la última búsqueda.
 *
 * Las cuatro vistas leen de aquí en lugar de volver a pedir los datos al
 * servidor. Con los topes en vivo del backend (≤ 40 registros por red) todo
 * cabe holgadamente en memoria, así que los filtros del explorador se aplican
 * en el navegador y son instantáneos.
 */
const Estado = {
  busqueda: null,   // { id, query, estado, ... }
  resumen: null,    // { global, por_red, odio_por_red, redes[] }
  registros: [],    // lista completa de comentarios ya clasificados
  oyentes: [],

  publicar(datos) {
    Object.assign(this, datos);
    this.oyentes.forEach((f) => f(this));
  },
  alCambiar(f) { this.oyentes.push(f); },
};
