/* Vista 1 — Consulta y ejecución concurrente.
 *
 * Es la pantalla que demuestra la concurrencia. El backend no emite eventos,
 * así que se sondea (`API.seguir`) y se muestran las dos fases del pipeline:
 *
 *   fase 1  extracción     N hilos, uno por red        (espera de red, I/O)
 *   fase 2  clasificación  pool de procesos            (inferencia, CPU)
 *
 * Al terminar se contrasta el tiempo de la extracción concurrente contra lo que
 * habría costado hacerla red por red: esa comparación es la evidencia.
 */

const VistaBusqueda = (function () {

  let redesDisponibles = [];
  let buscando = false;
  let temporizador = null;

  const $ = (id) => document.getElementById(id);

  /* ── Selector de redes ──────────────────────────────── */

  async function cargarRedes() {
    const caja = $('selector-redes');
    try {
      redesDisponibles = await API.redes();
    } catch (e) {
      caja.innerHTML = '<span class="ayuda">No se pudo leer la lista de redes del servidor.</span>';
      return;
    }
    caja.innerHTML = redesDisponibles.map((red) => `
      <label class="red-check">
        <input type="checkbox" value="${UI.escapar(red)}" checked>
        <span class="punto-red" style="background:${UI.colorRed(red)}"></span>
        ${UI.escapar(UI.nombreRed(red))}
      </label>`).join('');
  }

  const redesElegidas = () =>
    Array.from(document.querySelectorAll('#selector-redes input:checked')).map((c) => c.value);

  /* ── Carriles (una barra por red) ───────────────────── */

  function pintarCarriles(redes, estados) {
    $('carriles').innerHTML = redes.map((red) => {
      const e = estados[red] || {};
      const trabajando = e.estado === 'trabajando';
      const anchoMax = Math.max(1, ...redes.map((r) => (estados[r] && estados[r].total) || 0));
      const ancho = trabajando ? 100 : Math.round(((e.total || 0) / anchoMax) * 100);

      let dato;
      if (trabajando)      dato = 'extrayendo…';
      else if (e.error)    dato = UI.escapar(e.error.slice(0, 40));
      else                 dato = `${UI.numero(e.total || 0)} · ${UI.segundos(e.duracion_s)}`;

      return `
        <div class="carril">
          <span class="carril-nombre">
            <span class="punto-red" style="background:${UI.colorRed(red)}"></span>
            ${UI.escapar(UI.nombreRed(red))}
          </span>
          <div class="carril-barra">
            <div class="carril-relleno ${trabajando ? 'trabajando' : ''}"
                 style="width:${ancho}%; background:${UI.colorRed(red)}"></div>
          </div>
          <span class="carril-dato ${e.error ? 'error' : ''}">${dato}</span>
        </div>`;
    }).join('');
  }

  /* ── Fases ──────────────────────────────────────────── */

  const TEXTO_FASE = {
    extrayendo:   'extrayendo (hilos)',
    clasificando: 'clasificando (procesos)',
    terminada:    'terminada',
    error:        'error',
  };

  function marcarFase(fase) {
    const etiqueta = $('fase-actual');
    etiqueta.textContent = TEXTO_FASE[fase] || fase;
    etiqueta.className = 'etiqueta-fase ' +
      (fase === 'terminada' ? 'lista' : fase === 'error' ? 'mala' : 'viva');

    const avance = { extrayendo: 1, clasificando: 2, terminada: 3, error: 3 }[fase] || 0;
    [1, 2, 3].forEach((n) => {
      const li = $(`paso-${n}`);
      li.className = 'paso' + (n < avance ? ' hecho' : n === avance ? ' activo' : '');
    });
  }

  /* ── Evidencia de paralelismo ───────────────────────── */

  function pintarEvidencia(filasRed) {
    const conTiempo = filasRed.filter((f) => f.duracion_s != null);
    if (!conTiempo.length) return;

    // Todas las redes arrancan a la vez: la extracción dura lo que la más lenta.
    // Secuencialmente habría durado la suma.
    const pared = Math.max(...conTiempo.map((f) => f.duracion_s));
    const suma  = conTiempo.reduce((a, f) => a + f.duracion_s, 0);

    $('m-pared').textContent  = UI.segundos(pared);
    $('m-suma').textContent   = UI.segundos(suma);
    $('m-ahorro').textContent = `${(suma / pared).toFixed(2)}×`;

    const ordenadas = [...conTiempo].sort((a, b) => b.duracion_s - a.duracion_s);
    UI.dibujar('g-gantt', {
      type: 'bar',
      data: {
        labels: ordenadas.map((f) => UI.nombreRed(f.red)),
        datasets: [{
          label: 'duración (s)',
          data: ordenadas.map((f) => f.duracion_s),
          backgroundColor: ordenadas.map((f) => UI.colorRed(f.red)),
          borderRadius: 4,
        }],
      },
      options: {
        indexAxis: 'y',
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (c) => {
                const f = ordenadas[c.dataIndex];
                return `${f.duracion_s.toFixed(2)} s · ${UI.numero(f.total)} registros`;
              },
            },
          },
          title: {
            display: true,
            text: 'Todas las redes arrancan en el segundo 0 (un hilo cada una)',
            color: '#98a1b3', font: { size: 11, weight: 'normal' },
          },
        },
        scales: {
          x: { grid: UI.REJILLA, title: { display: true, text: 'segundos' } },
          y: { grid: { display: false } },
        },
      },
    });

    $('bloque-evidencia').classList.remove('oculto');
  }

  /* ── Ciclo de una búsqueda ──────────────────────────── */

  function arrancarCronometro() {
    const t0 = performance.now();
    temporizador = setInterval(() => {
      $('cronometro').textContent = `${((performance.now() - t0) / 1000).toFixed(1)} s`;
    }, 100);
  }

  function pararCronometro() { clearInterval(temporizador); temporizador = null; }

  function aviso(mensaje, tipo = 'error') {
    const caja = $('aviso-busqueda');
    caja.className = `aviso ${tipo === 'info' ? 'info' : ''}`;
    caja.textContent = mensaje;
  }

  function ocultarAviso() { $('aviso-busqueda').classList.add('oculto'); }

  async function buscar(evento) {
    evento.preventDefault();
    if (buscando) return;

    const query = $('campo-query').value.trim();
    const redes = redesElegidas();
    if (query.length < 2) return aviso('Escribe al menos 2 caracteres.');
    if (!redes.length)    return aviso('Selecciona al menos una red.');

    buscando = true;
    ocultarAviso();
    $('btn-buscar').disabled = true;
    $('btn-buscar').textContent = 'Buscando…';
    $('panel-progreso').classList.remove('oculto');
    $('bloque-evidencia').classList.add('oculto');
    UI.limpiar('g-gantt');

    // Todas las redes empiezan a trabajar al mismo tiempo: así se pintan.
    const estados = {};
    redes.forEach((r) => { estados[r] = { estado: 'trabajando' }; });
    pintarCarriles(redes, estados);
    marcarFase('extrayendo');
    arrancarCronometro();

    try {
      const creada = await API.crearBusqueda(query, redes);

      const fin = await API.seguir(creada.id, ({ resumen, fase }) => {
        marcarFase(fase);
        if (resumen && resumen.redes && resumen.redes.length) {
          resumen.redes.forEach((f) => {
            estados[f.red] = { estado: 'listo', total: f.total, error: f.error, duracion_s: f.duracion_s };
          });
          pintarCarriles(redes, estados);
        }
      });

      pararCronometro();

      if (fin.fase === 'error') {
        aviso('La búsqueda falló en el servidor. Revisa la consola del backend.');
        $('aviso-busqueda').classList.remove('oculto');
      }

      const registros = await API.registros(fin.busqueda.id, 1000);
      const resumen = fin.resumen || await API.resumen(fin.busqueda.id);

      if (resumen && resumen.redes) pintarEvidencia(resumen.redes);

      Estado.publicar({ busqueda: fin.busqueda, resumen, registros });

      if (!registros.length) {
        aviso('La búsqueda terminó sin registros. Prueba otro término o revisa las credenciales de las redes.', 'info');
        $('aviso-busqueda').classList.remove('oculto');
      }
    } catch (e) {
      pararCronometro();
      marcarFase('error');
      aviso(e.message);
      $('aviso-busqueda').classList.remove('oculto');
    } finally {
      buscando = false;
      $('btn-buscar').disabled = false;
      $('btn-buscar').textContent = 'Buscar';
    }
  }

  /* ── Arranque ───────────────────────────────────────── */

  function iniciar() {
    $('form-busqueda').addEventListener('submit', buscar);
    document.querySelectorAll('.chip').forEach((chip) => {
      chip.addEventListener('click', () => { $('campo-query').value = chip.dataset.q; });
    });
    cargarRedes();
  }

  /* Repinta el panel a partir de un resumen ya terminado, sin volver a
   * extraer. Sirve para restaurar la pantalla y para probarla con una búsqueda
   * guardada en la base. */
  function mostrarResultado(resumen) {
    if (!resumen || !resumen.redes || !resumen.redes.length) return;
    const estados = {};
    const redes = resumen.redes.map((f) => f.red);
    resumen.redes.forEach((f) => {
      estados[f.red] = { estado: 'listo', total: f.total, error: f.error, duracion_s: f.duracion_s };
    });
    $('panel-progreso').classList.remove('oculto');
    pintarCarriles(redes, estados);
    marcarFase('terminada');
    pintarEvidencia(resumen.redes);
  }

  return { iniciar, recargarRedes: cargarRedes, mostrarResultado };
})();
