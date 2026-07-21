/* Vista 4 — Interpretación (storytelling).
 *
 * La rúbrica no pide más gráficos: pide EXPLICAR lo que los números significan.
 * Así que la vista tiene dos mitades:
 *
 *   1. Lectura de la búsqueda que el usuario acaba de hacer (se redacta sola a
 *      partir de los resultados en pantalla).
 *   2. Los cinco hallazgos del corpus completo, medidos en la Práctica 7.
 *
 * La segunda mitad se muestra siempre: da contexto aunque nadie haya buscado
 * todavía, y es la parte que sostiene el artículo académico.
 */

const VistaHistoria = (function () {

  const $ = (id) => document.getElementById(id);
  const pct = (v) => `${v.toFixed(1)} %`;

  /* ── Mitad 1: lectura automática de la búsqueda actual ── */

  function narrarBusqueda(estado) {
    const registros = estado.registros || [];
    if (!registros.length) {
      return `
        <div class="tarjeta plana">
          <h2>Tu búsqueda</h2>
          <p class="ayuda">
            Cuando lances una consulta en la pestaña <strong>1</strong>, aquí aparecerá
            una lectura de lo que encontró, comparada con el corpus histórico.
          </p>
        </div>`;
    }

    const clasificados = registros.filter((r) => r.sentimiento);
    const negativos = clasificados.filter((r) => r.sentimiento === 'negativo').length;
    const conOdio = clasificados.filter((r) => r.odio).length;
    const conLexico = registros.filter((r) => r.estrategia === 'dirigida').length;

    // Red más hostil de esta búsqueda (con un mínimo de casos para no leer ruido).
    const porRed = {};
    clasificados.forEach((r) => {
      porRed[r.red] = porRed[r.red] || { n: 0, neg: 0, odio: 0 };
      porRed[r.red].n++;
      if (r.sentimiento === 'negativo') porRed[r.red].neg++;
      if (r.odio) porRed[r.red].odio++;
    });
    const candidatas = Object.entries(porRed).filter(([, v]) => v.n >= 3);
    const masHostil = candidatas.sort((a, b) => (b[1].neg / b[1].n) - (a[1].neg / a[1].n))[0];

    const pctNeg = clasificados.length ? (negativos / clasificados.length) * 100 : 0;
    const pctOdio = clasificados.length ? (conOdio / clasificados.length) * 100 : 0;

    // Se contrasta con la referencia del corpus para que el número diga algo.
    const refNeg = 55.0;  // media aproximada del núcleo dirigido
    const comparacion = pctNeg > refNeg
      ? 'por encima de'
      : pctNeg < refNeg - 10 ? 'bastante por debajo de' : 'en línea con';

    const lineaRed = masHostil
      ? `La red más hostil de esta consulta fue <strong>${UI.nombreRed(masHostil[0])}</strong>,
         con ${pct((masHostil[1].neg / masHostil[1].n) * 100)} de comentarios negativos.`
      : 'No hubo suficientes comentarios por red como para comparar redes entre sí.';

    const lineaLexico = conLexico
      ? `<strong>${UI.numero(conLexico)}</strong> comentarios (${UI.porcentaje(conLexico, registros.length)})
         contienen algún término del léxico xenófobo curado, así que la consulta tocó el núcleo del problema.`
      : `Ningún comentario disparó el léxico xenófobo: esta consulta cayó en la conversación general,
         no en el núcleo del problema. Es el denominador que hace falta para poder decir
         "de N comentarios, X % son xenófobos".`;

    return `
      <div class="tarjeta plana">
        <h2>Tu búsqueda: “${UI.escapar(estado.busqueda ? estado.busqueda.query : '')}”</h2>
        <p>
          Se recolectaron <strong>${UI.numero(registros.length)}</strong> comentarios de
          <strong>${new Set(registros.map((r) => r.red)).size}</strong> redes.
          El <strong>${pct(pctNeg)}</strong> es negativo, ${comparacion} lo que muestra el corpus
          histórico, y el <strong>${pct(pctOdio)}</strong> fue marcado como discurso de odio explícito.
        </p>
        <p>${lineaRed}</p>
        <p>${lineaLexico}</p>
        <p class="ayuda">
          Recordatorio de lectura: el porcentaje de odio es una <strong>cota inferior</strong>.
          El modelo detecta el insulto directo; el odio disfrazado de broma se le escapa (hallazgo 5).
        </p>
      </div>`;
  }

  /* ── Mitad 2: hallazgos del corpus ─────────────────── */

  function bloqueHallazgos() {
    const t = CORPUS.totales;
    const r = CORPUS.rendimiento;
    const c = CORPUS.odio_codificado;

    const codigos = [...c.leetspeak, ...c.emoji, ...c.portmanteaus]
      .map((x) => `<code>${UI.escapar(x)}</code>`).join('');

    return `
      <div class="tarjeta plana">
        <h2>Qué encontramos en el corpus completo</h2>
        <p>
          La búsqueda en vivo es una muestra pequeña, pensada para responder en segundos.
          El análisis de fondo se hizo sobre <strong>${UI.numero(t.corpus_completo)}</strong> comentarios
          recolectados de ${t.redes} redes durante el Mundial, de los cuales
          <strong>${UI.numero(t.corpus_dirigido)}</strong> forman el <em>núcleo dirigido</em>:
          los que contienen algún término del léxico xenófobo y son auditables a mano.
        </p>
        <p class="ayuda">
          Clasificar ese núcleo tardó ${r.serial_s} s en secuencial y ${r.paralelo_s} s
          repartido en ${r.procesos} procesos: un <strong>speedup de ${r.speedup}×</strong>
          (${r.eficiencia_pct} % de eficiencia).
        </p>
      </div>

      <div class="rejilla rejilla-2">
        <div class="tarjeta plana hallazgo">
          <span class="numero">Hallazgo 1</span>
          <h3>X es el epicentro de la agresión directa</h3>
          <p>
            X concentra el ${CORPUS.por_red[0].negativo} % de comentarios negativos y el
            ${CORPUS.por_red[0].hateful} % marcados como odio: es la red con la señal más densa
            y más hostil. Confirma el gancho de la problemática — la traducción automática
            de X pone a hablar entre sí a hinchadas que antes no se cruzaban.
          </p>
          <div class="lienzo"><canvas id="g-h-redes"></canvas></div>
        </div>

        <div class="tarjeta plana hallazgo">
          <span class="numero">Hallazgo 2</span>
          <h3>Bluesky no es menos racista: es contra-discurso</h3>
          <p>
            Bluesky aparece con apenas ${CORPUS.por_red[3].hateful} % de odio pese a ser captura
            dirigida. Al revisar los textos a mano se ve por qué: <strong>mencionan</strong> los
            términos del léxico, pero para <strong>denunciar</strong> el racismo.
          </p>
          <p class="cita">“${UI.escapar(CORPUS.cita_bluesky)}”</p>
          <p>
            El modelo los marca bien como no-odiosos. La conclusión no es sobre el modelo sino
            sobre las plataformas: <strong>Bluesky captura la meta-conversación; X y YouTube
            capturan la agresión</strong>.
          </p>
          <div class="metricas">
            <div class="metrica"><span class="metrica-valor" style="color:var(--odio)">${CORPUS.por_red[0].hateful} %</span><span class="metrica-nombre">odio en X</span></div>
            <div class="metrica"><span class="metrica-valor" style="color:var(--positivo)">${CORPUS.por_red[3].hateful} %</span><span class="metrica-nombre">odio en Bluesky</span></div>
            <div class="metrica"><span class="metrica-valor">${(CORPUS.por_red[0].hateful / CORPUS.por_red[3].hateful).toFixed(1)}×</span><span class="metrica-nombre">de diferencia</span></div>
          </div>
          <p class="ayuda">
            Misma consulta, mismo léxico, mismo modelo: lo que cambia es la cultura de la plataforma.
            Por eso la extracción tiene que ser multi-red — una sola fuente daría una foto sesgada.
          </p>
        </div>
      </div>

      <div class="rejilla rejilla-2">
        <div class="tarjeta plana hallazgo">
          <span class="numero">Hallazgo 3</span>
          <h3>El idioma predice la hostilidad mejor que la red</h3>
          <p>
            El contenido en español es marcadamente más hostil (${CORPUS.por_idioma[0].negativo} % negativo)
            que el inglés o el portugués. La xenofobia de este corpus es sobre todo
            <strong>hispanohablante</strong>, hija de la rivalidad futbolística latinoamericana.
            Y explica desde otro ángulo la suavidad aparente de Bluesky: su corpus es mayormente en inglés.
          </p>
          <div class="lienzo"><canvas id="g-h-idioma"></canvas></div>
        </div>

        <div class="tarjeta plana hallazgo">
          <span class="numero">Hallazgo 4</span>
          <h3>Lo más frecuente no es lo más virulento</h3>
          <p>
            El eje <em>anti-negro / simiesco</em> es con diferencia el más voluminoso
            (${UI.numero(CORPUS.por_eje[5].n)} comentarios) pero el de menor proporción de odio explícito
            (${CORPUS.por_eje[5].hateful} %). En cambio los ejes <em>colonial</em> y
            <em>anti-mexicano</em>, mucho más pequeños, superan el 56 %.
          </p>
          <p class="ayuda">
            Traducción: el insulto racial más común circula tan normalizado —como emoji, como broma—
            que ni siquiera se formula de forma agresiva. Justo lo que el hallazgo 5 explica.
          </p>
          <!-- Dos gráficos apilados con el MISMO orden de categorías, en lugar de
               un gráfico de doble eje: dos escalas distintas en un solo par de ejes
               inducen comparaciones falsas. Aquí el contraste se ve alineando las
               dos series verticalmente. -->
          <div class="rotulo" style="margin-top:.9rem">Volumen (comentarios)</div>
          <div class="lienzo-bajo"><canvas id="g-h-ejes-vol"></canvas></div>
          <div class="rotulo" style="margin-top:.9rem">Virulencia (% con odio)</div>
          <div class="lienzo-bajo"><canvas id="g-h-ejes-odio"></canvas></div>
        </div>
      </div>

      <div class="tarjeta plana hallazgo">
        <span class="numero">Hallazgo 5 · central</span>
        <h3>El modelo subdetecta el odio implícito</h3>
        <p>
          El ${t.hateful_global_pct} % global de odio es un <strong>piso, no un techo</strong>.
          Al revisar los comentarios que el clasificador marcó como “sin odio” aparece odio
          <strong>codificado</strong> que el modelo no reconoce:
        </p>
        <div class="lista-codificada">${codigos}</div>
        <p>
          A eso se suma la ironía: <em>“${UI.escapar(CORPUS.odio_codificado.ironia[0])}”</em> se clasifica
          como negativo, pero no como odio.
        </p>
        <div class="remate">
          <p>
            <strong>Esto no es un fallo que ocultar: es el resultado.</strong>
            Confirma la hipótesis con la que arrancó el proyecto — el odio disfrazado de humor
            escapa a los clasificadores estándar — y justifica el diseño de dos ejes separados
            (sentimiento y xenofobia) más un léxico curado con revisión humana.
            Un comentario puede ser jocoso y racista a la vez; medir solo el sentimiento
            lo dejaría fuera del radar.
          </p>
        </div>
      </div>`;
  }

  /* ── Gráficos del corpus ───────────────────────────── */

  function pintarGraficos() {
    const redes = CORPUS.por_red.filter((f) => f.n >= 30);   // TikTok (n=10) es ruido

    UI.dibujar('g-h-redes', {
      type: 'bar',
      data: {
        labels: redes.map((f) => UI.nombreRed(f.red)),
        datasets: [
          { label: '% negativo', data: redes.map((f) => f.negativo), backgroundColor: UI.COLOR_SENTIMIENTO.negativo, ...UI.SEPARADOR },
          { label: '% con odio', data: redes.map((f) => f.hateful),  backgroundColor: UI.COLOR_ODIO, ...UI.SEPARADOR },
        ],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: { callbacks: { afterLabel: (c) => `n = ${UI.numero(redes[c.dataIndex].n)}` } },
        },
        scales: { x: { grid: { display: false } }, y: { beginAtZero: true, max: 100, grid: UI.REJILLA, ticks: { callback: (v) => `${v} %` } } },
      },
    });

    UI.dibujar('g-h-idioma', {
      type: 'bar',
      data: {
        labels: CORPUS.por_idioma.map((f) => f.idioma),
        datasets: [{
          label: '% negativo',
          data: CORPUS.por_idioma.map((f) => f.negativo),
          backgroundColor: ['#e5484d', '#8b8d98', '#8b8d98'],
          borderRadius: 4,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { afterLabel: (c) => `n = ${UI.numero(CORPUS.por_idioma[c.dataIndex].n)}` } },
        },
        scales: { x: { grid: { display: false } }, y: { beginAtZero: true, max: 100, grid: UI.REJILLA, ticks: { callback: (v) => `${v} %` } } },
      },
    });

    // Volumen y virulencia son dos magnitudes con escalas distintas. En vez de
    // meterlas en un mismo par de ejes (dos escalas en un gráfico invitan a leer
    // cruces que no significan nada), se dibujan como dos gráficos apilados que
    // COMPARTEN el orden de categorías: la discrepancia se ve de un vistazo.
    const ejes = [...CORPUS.por_eje].sort((a, b) => b.n - a.n);
    const etiquetasEjes = ejes.map((f) => f.eje);
    const ejeX = {
      grid: { display: false },
      ticks: { maxRotation: 34, minRotation: 34, font: { size: 10 }, autoSkip: false },
    };

    UI.dibujar('g-h-ejes-vol', {
      type: 'bar',
      data: {
        labels: etiquetasEjes,
        datasets: [{
          label: 'comentarios',
          data: ejes.map((f) => f.n),
          backgroundColor: UI.colorRed('bluesky'),
          ...UI.SEPARADOR,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { ...ejeX, ticks: { ...ejeX.ticks, display: false } }, y: { beginAtZero: true, grid: UI.REJILLA } },
      },
    });

    UI.dibujar('g-h-ejes-odio', {
      type: 'bar',
      data: {
        labels: etiquetasEjes,
        datasets: [{
          label: '% con odio',
          data: ejes.map((f) => f.hateful),
          backgroundColor: UI.COLOR_ODIO,
          ...UI.SEPARADOR,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { afterLabel: (c) => `n = ${UI.numero(ejes[c.dataIndex].n)}` } },
        },
        scales: { x: ejeX, y: { beginAtZero: true, max: 100, grid: UI.REJILLA, ticks: { callback: (v) => `${v} %` } } },
      },
    });
  }

  function refrescar(estado) {
    $('contenido-historia').innerHTML = narrarBusqueda(estado || Estado) + bloqueHallazgos();
    pintarGraficos();
  }

  function iniciar() {
    refrescar(Estado);
    Estado.alCambiar(refrescar);
  }

  return { iniciar, refrescar };
})();
