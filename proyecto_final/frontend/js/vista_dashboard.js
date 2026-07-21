/* Vista 2 — Clasificación de sentimientos, global y por red social.
 *
 * Los conteos los calcula el backend (`GET /busquedas/{id}/resumen`), que es
 * quien tiene el SQL. Aquí solo se dibujan.
 *
 * Nota de lectura: el sentimiento y el odio son EJES DISTINTOS. Un comentario
 * puede ser "positivo" y aun así xenófobo — es justamente el caso del odio
 * disfrazado de broma, que es la hipótesis del proyecto. Por eso el odio tiene
 * su propio gráfico y no es una categoría más del sentimiento.
 */

const VistaDashboard = (function () {

  const $ = (id) => document.getElementById(id);

  /* Si el resumen no llegó, se reconstruye desde los registros: la vista nunca
   * se queda en blanco por un fallo de un endpoint. */
  function resumirDesdeRegistros(registros) {
    const global = {}, porRed = {}, odioPorRed = {};
    registros.forEach((r) => {
      if (!r.sentimiento) return;
      global[r.sentimiento] = (global[r.sentimiento] || 0) + 1;
      porRed[r.red] = porRed[r.red] || {};
      porRed[r.red][r.sentimiento] = (porRed[r.red][r.sentimiento] || 0) + 1;
      if (r.odio) odioPorRed[r.red] = (odioPorRed[r.red] || 0) + 1;
    });
    return { global, por_red: porRed, odio_por_red: odioPorRed, redes: [] };
  }

  function pintarKpis(resumen, registros) {
    const total = registros.length;
    const clasificados = registros.filter((r) => r.sentimiento).length;
    const negativos = registros.filter((r) => r.sentimiento === 'negativo').length;
    const conOdio = registros.filter((r) => r.odio).length;
    const redesConDatos = new Set(registros.map((r) => r.red)).size;

    const tarjetas = [
      ['comentarios', UI.numero(total)],
      ['redes con datos', String(redesConDatos)],
      ['negativos', UI.porcentaje(negativos, clasificados)],
      ['discurso de odio', UI.porcentaje(conOdio, clasificados)],
    ];

    $('kpis').innerHTML = tarjetas.map(([nombre, valor]) => `
      <div class="kpi">
        <div class="kpi-valor">${valor}</div>
        <div class="kpi-nombre">${nombre}</div>
      </div>`).join('');
  }

  function pintarGlobal(global) {
    const etiquetas = UI.ORDEN_SENTIMIENTO.filter((s) => global[s]);
    UI.dibujar('g-global', {
      type: 'doughnut',
      data: {
        labels: etiquetas,
        datasets: [{
          data: etiquetas.map((s) => global[s]),
          backgroundColor: etiquetas.map((s) => UI.COLOR_SENTIMIENTO[s]),
          borderColor: '#141a24',
          borderWidth: 2,
        }],
      },
      options: {
        maintainAspectRatio: false,
        cutout: '58%',
        plugins: {
          legend: { position: 'bottom' },
          tooltip: {
            callbacks: {
              label: (c) => {
                const total = c.dataset.data.reduce((a, b) => a + b, 0);
                return `${c.label}: ${UI.numero(c.raw)} (${UI.porcentaje(c.raw, total)})`;
              },
            },
          },
        },
      },
    });
  }

  /* Barras apiladas al 100 %: compara la MEZCLA de cada red, no su tamaño.
   * Sin normalizar, YouTube taparía a las demás solo por traer más. */
  function pintarPorRed(porRed) {
    const redes = Object.keys(porRed).sort();
    UI.dibujar('g-por-red', {
      type: 'bar',
      data: {
        labels: redes.map(UI.nombreRed),
        datasets: UI.ORDEN_SENTIMIENTO.map((s) => ({
          label: s,
          data: redes.map((red) => {
            const fila = porRed[red] || {};
            const total = Object.values(fila).reduce((a, b) => a + b, 0);
            return total ? ((fila[s] || 0) / total) * 100 : 0;
          }),
          backgroundColor: UI.COLOR_SENTIMIENTO[s],
          ...UI.SEPARADOR,
          conteos: redes.map((red) => (porRed[red] || {})[s] || 0),
        })),
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: {
            callbacks: {
              label: (c) => `${c.dataset.label}: ${c.raw.toFixed(1)} % (${UI.numero(c.dataset.conteos[c.dataIndex])})`,
            },
          },
        },
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, max: 100, grid: UI.REJILLA, ticks: { callback: (v) => `${v} %` } },
        },
      },
    });
  }

  function pintarOdio(porRed, odioPorRed) {
    const redes = Object.keys(porRed).sort();
    const datos = redes.map((red) => {
      const total = Object.values(porRed[red] || {}).reduce((a, b) => a + b, 0);
      return total ? ((odioPorRed[red] || 0) / total) * 100 : 0;
    });

    UI.dibujar('g-odio', {
      type: 'bar',
      data: {
        labels: redes.map(UI.nombreRed),
        datasets: [{
          label: '% con discurso de odio',
          data: datos,
          backgroundColor: redes.map(UI.colorRed),
          borderRadius: 4,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (c) => `${c.raw.toFixed(1)} % (${UI.numero(odioPorRed[redes[c.dataIndex]] || 0)} comentarios)`,
            },
          },
        },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, grid: UI.REJILLA, ticks: { callback: (v) => `${v} %` } },
        },
      },
    });
  }

  function pintarVolumen(registros) {
    const conteo = {};
    registros.forEach((r) => { conteo[r.red] = (conteo[r.red] || 0) + 1; });
    const redes = Object.keys(conteo).sort((a, b) => conteo[b] - conteo[a]);

    UI.dibujar('g-volumen', {
      type: 'bar',
      data: {
        labels: redes.map(UI.nombreRed),
        datasets: [{
          label: 'comentarios',
          data: redes.map((r) => conteo[r]),
          backgroundColor: redes.map(UI.colorRed),
          borderRadius: 4,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: UI.REJILLA } },
      },
    });
  }

  function refrescar(estado) {
    const registros = estado.registros || [];
    if (!registros.length) {
      $('dashboard-vacio').classList.remove('oculto');
      $('dashboard-contenido').classList.add('oculto');
      return;
    }

    let resumen = estado.resumen;
    if (!resumen || !resumen.global || !Object.keys(resumen.global).length) {
      resumen = resumirDesdeRegistros(registros);
    }

    $('dashboard-vacio').classList.add('oculto');
    $('dashboard-contenido').classList.remove('oculto');

    pintarKpis(resumen, registros);
    pintarGlobal(resumen.global || {});
    pintarPorRed(resumen.por_red || {});
    pintarOdio(resumen.por_red || {}, resumen.odio_por_red || {});
    pintarVolumen(registros);
  }

  function iniciar() { Estado.alCambiar(refrescar); }

  return { iniciar, refrescar };
})();
