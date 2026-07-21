/* Utilidades de presentación: colores, formato y envoltorio de Chart.js.
 *
 * Todo lo visual compartido vive aquí para que las cuatro vistas se vean como
 * una sola aplicación: el mismo rojo significa "negativo" en todas partes.
 */

const UI = (function () {

  /* Los colores viven en el CSS (`:root`) y se leen de ahí: una sola fuente de
   * verdad para la interfaz y los gráficos.
   *
   * La paleta no se eligió a ojo. Se validó con un comprobador de contraste y de
   * separación para daltonismo, y de ahí salen dos reglas:
   *
   *  1. Rojo, azul, gris y naranja están RESERVADOS para el significado
   *     (negativo, positivo, neutral, odio). Las redes usan otros cuatro tonos,
   *     así que un color nunca significa dos cosas distintas.
   *  2. La escala de sentimiento es divergente rojo↔azul y NO rojo↔verde:
   *     rojo/verde es prácticamente indistinguible para la deuteranopia
   *     (ΔE 4.1, bajo el mínimo de 8), mientras que rojo/azul da ΔE 19.2.
   */
  const _css = (nombre, respaldo) => {
    const v = getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
    return v || respaldo;
  };

  const COLOR_RED = {
    bluesky:  _css('--red-bluesky',  '#9085e9'),
    x:        _css('--red-x',        '#c98500'),
    youtube:  _css('--red-youtube',  '#d55181'),
    mastodon: _css('--red-mastodon', '#008300'),
    tumblr:   '#1baf7a',
    tiktok:   '#b06ab0',
    reddit:   '#8a6d3b',
  };
  const COLOR_POR_DEFECTO = '#6d7c93';

  const COLOR_SENTIMIENTO = {
    negativo: _css('--negativo', '#e66767'),
    neutral:  _css('--neutral',  '#8b93a3'),
    positivo: _css('--positivo', '#4d8df0'),
  };
  const COLOR_ODIO = _css('--odio', '#d95926');

  // Orden fijo: negativo → neutral → positivo. En las barras apiladas esa
  // posición es codificación secundaria (la identidad no depende solo del color).
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

  Chart.defaults.color = _css('--texto-suave', '#9dabc0');
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  Chart.defaults.font.size = 12;
  Chart.defaults.animation.duration = 450;
  Chart.defaults.plugins.legend.labels.boxWidth = 11;
  Chart.defaults.plugins.legend.labels.boxHeight = 11;
  Chart.defaults.plugins.legend.labels.padding = 14;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.pointStyle = 'circle';
  Chart.defaults.plugins.tooltip.backgroundColor = '#1b2431';
  Chart.defaults.plugins.tooltip.borderColor = '#2b3646';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.titleColor = '#eef2f8';
  Chart.defaults.plugins.tooltip.bodyColor = '#eef2f8';
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  // Marcas finas: con pocas categorías, una barra a ancho completo se lee como
  // un bloque de color y no como un dato.
  Chart.defaults.datasets.bar.maxBarThickness = 58;

  // Rejilla discreta: la cuadrícula orienta, no compite con los datos.
  const REJILLA = { color: 'rgba(255,255,255,.055)', drawTicks: false };

  // Separación de 2 px entre segmentos apilados y entre barras contiguas: el
  // borde del color de la superficie evita que dos colores se toquen.
  const SEPARADOR = { borderColor: '#141a24', borderWidth: 2, borderRadius: 4 };

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
    COLOR_RED, COLOR_SENTIMIENTO, COLOR_ODIO, ORDEN_SENTIMIENTO, REJILLA, SEPARADOR,
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
