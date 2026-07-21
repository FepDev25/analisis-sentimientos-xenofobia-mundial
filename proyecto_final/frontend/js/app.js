/* Arranque de la aplicación: pestañas, estado del servidor y configuración.
 *
 * Cada vista se inicializa una vez y luego se redibuja sola cuando cambia el
 * `Estado` compartido.
 */

(function () {

  const $ = (id) => document.getElementById(id);

  /* ── Pestañas ───────────────────────────────────────── */

  // Al mostrar una pestaña se redibuja su contenido. Chart.js mide el canvas
  // cuando lo crea: si estaba oculto (display:none) mediría cero y el gráfico
  // saldría aplastado.
  const REFRESCAR = {
    dashboard:  () => VistaDashboard.refrescar(Estado),
    explorador: () => VistaExplorador.refrescar(Estado),
    historia:   () => VistaHistoria.refrescar(Estado),
  };

  function mostrar(nombre) {
    document.querySelectorAll('.pestana').forEach((b) =>
      b.classList.toggle('activa', b.dataset.vista === nombre));
    document.querySelectorAll('.vista').forEach((v) =>
      v.classList.toggle('activa', v.id === `vista-${nombre}`));
    if (REFRESCAR[nombre]) REFRESCAR[nombre]();
  }

  document.querySelectorAll('.pestana').forEach((b) =>
    b.addEventListener('click', () => mostrar(b.dataset.vista)));

  /* ── Semáforo del servidor ──────────────────────────── */

  async function revisarServidor() {
    const luz = $('luz-api');
    const texto = $('texto-api');
    texto.textContent = 'conectando…';
    luz.className = 'luz luz-gris';

    if (await API.vivo()) {
      luz.className = 'luz luz-verde';
      texto.textContent = API.urlBase().replace(/^https?:\/\//, '');
    } else {
      luz.className = 'luz luz-roja';
      texto.textContent = 'sin conexión';
    }
  }

  /* ── Configuración del servidor ─────────────────────── */

  $('btn-config').addEventListener('click', () => {
    $('campo-base').value = API.urlBase();
    $('modal-config').classList.remove('oculto');
  });

  $('btn-cancelar-config').addEventListener('click', () =>
    $('modal-config').classList.add('oculto'));

  $('btn-guardar-config').addEventListener('click', async () => {
    API.fijarBase($('campo-base').value.trim());
    $('modal-config').classList.add('oculto');
    await revisarServidor();
    VistaBusqueda.recargarRedes();
  });

  /* ── Inicio ─────────────────────────────────────────── */

  VistaBusqueda.iniciar();
  VistaDashboard.iniciar();
  VistaExplorador.iniciar();
  VistaHistoria.iniciar();

  revisarServidor();
  // El backend puede tardar en arrancar (carga los modelos al iniciar):
  // se reintenta en segundo plano para que la luz se ponga verde sola.
  setInterval(revisarServidor, 15000);
})();
