/* Vista 3 — Explorador de comentarios.
 *
 * Muestra cada comentario con la red de la que salió y cómo lo clasificó el
 * modelo. Es la parte "auditable" del sistema: la rúbrica pide poder ver los
 * comentarios y su clasificación, no solo los agregados.
 *
 * Los filtros se aplican en el navegador, no en el servidor. Una búsqueda en
 * vivo trae como máximo 40 registros por red (tope del backend), así que el
 * conjunto completo ya está en memoria y filtrar es instantáneo — pedir al
 * servidor en cada tecla solo añadiría latencia.
 */

const VistaExplorador = (function () {

  const $ = (id) => document.getElementById(id);
  const CAMPOS = ['f-red', 'f-sentimiento', 'f-odio', 'f-estrategia', 'f-texto'];

  function poblarRedes(registros) {
    const redes = [...new Set(registros.map((r) => r.red))].sort();
    $('f-red').innerHTML =
      '<option value="">todas</option>' +
      redes.map((r) => `<option value="${UI.escapar(r)}">${UI.escapar(UI.nombreRed(r))}</option>`).join('');
  }

  function filtrar(registros) {
    const red = $('f-red').value;
    const sent = $('f-sentimiento').value;
    const odio = $('f-odio').value;
    const estrategia = $('f-estrategia').value;
    const texto = $('f-texto').value.trim().toLowerCase();

    return registros.filter((r) => {
      if (red && r.red !== red) return false;
      if (sent && r.sentimiento !== sent) return false;
      if (odio === 'si' && !r.odio) return false;
      if (odio === 'no' && r.odio) return false;
      if (estrategia && r.estrategia !== estrategia) return false;
      if (texto && !(r.texto || '').toLowerCase().includes(texto)) return false;
      return true;
    });
  }

  function etiquetaSentimiento(r) {
    if (!r.sentimiento) return '<span class="etiqueta et-vacia">sin clasificar</span>';
    const score = r.sent_score != null ? ` ${(r.sent_score * 100).toFixed(0)}%` : '';
    return `<span class="etiqueta et-${r.sentimiento}" title="confianza del modelo">${r.sentimiento}${score}</span>`;
  }

  function etiquetaOdio(r) {
    if (r.odio == null) return '<span class="etiqueta et-vacia">—</span>';
    if (!r.odio) return '<span class="etiqueta et-vacia">no</span>';
    const score = r.odio_score != null ? ` ${(r.odio_score * 100).toFixed(0)}%` : '';
    return `<span class="etiqueta et-odio">odio${score}</span>`;
  }

  function fila(r) {
    // El texto va escapado: viene de redes sociales y puede traer HTML.
    const autor = r.autor ? `<span class="autor">@${UI.escapar(r.autor)}</span>` : '';
    const marca = r.estrategia === 'dirigida'
      ? ' <span class="etiqueta et-dirigida" title="el texto contiene un término del léxico xenófobo">léxico</span>'
      : '';
    const enlace = r.url
      ? `<a href="${UI.escapar(r.url)}" target="_blank" rel="noopener noreferrer">ver ↗</a>`
      : '<span class="et-vacia">—</span>';

    return `
      <tr>
        <td><span class="pastilla-red"><span class="punto-red" style="background:${UI.colorRed(r.red)}"></span>${UI.escapar(UI.nombreRed(r.red))}</span></td>
        <td class="celda-texto">${UI.escapar(r.texto)}${marca}${autor}</td>
        <td>${UI.escapar(r.idioma || '—')}</td>
        <td>${etiquetaSentimiento(r)}</td>
        <td>${etiquetaOdio(r)}</td>
        <td>${enlace}</td>
      </tr>`;
  }

  function pintar() {
    const todos = Estado.registros || [];
    const visibles = filtrar(todos);

    $('contador-filtro').textContent =
      visibles.length === todos.length
        ? `${UI.numero(todos.length)} comentarios`
        : `${UI.numero(visibles.length)} de ${UI.numero(todos.length)} comentarios`;

    // Se pinta de una sola vez: mil concatenaciones al DOM son mil reflows.
    $('cuerpo-tabla').innerHTML = visibles.map(fila).join('');
    $('sin-resultados').classList.toggle('oculto', visibles.length > 0);
  }

  function refrescar(estado) {
    const registros = estado.registros || [];
    if (!registros.length) {
      $('explorador-vacio').classList.remove('oculto');
      $('explorador-contenido').classList.add('oculto');
      return;
    }
    $('explorador-vacio').classList.add('oculto');
    $('explorador-contenido').classList.remove('oculto');
    poblarRedes(registros);
    pintar();
  }

  function limpiar() {
    CAMPOS.forEach((id) => { $(id).value = ''; });
    pintar();
  }

  function iniciar() {
    CAMPOS.forEach((id) => {
      const el = $(id);
      el.addEventListener(id === 'f-texto' ? 'input' : 'change', pintar);
    });
    $('btn-limpiar').addEventListener('click', limpiar);
    Estado.alCambiar(refrescar);
  }

  return { iniciar, refrescar };
})();
