/* Resultados del corpus histórico, medidos en la Práctica 7.
 *
 * NO son datos inventados ni de ejemplo: salen de `practica_07/informe/INFORME_P7.md`,
 * que documenta la clasificación de 8 783 comentarios del núcleo dirigido sobre un
 * corpus total de 396 841 registros recolectados en la Práctica 6.
 *
 * Van en un archivo .js y no .json a propósito: así la página también funciona
 * abriéndola directamente (file://), sin necesidad de servir el frontend.
 *
 * Si se re-ejecuta la clasificación del corpus, se actualizan estas cifras aquí.
 */

const CORPUS = {

  fuente: 'Práctica 7 — clasificación con pysentimiento (RoBERTuito / BERTweet)',

  totales: {
    corpus_completo: 396841,
    corpus_dirigido: 8783,
    redes: 5,
    hateful_global_pct: 29.9,
  },

  /* §8.1 y §8.2 del informe */
  por_red: [
    { red: 'x',        n: 4739, negativo: 70.1, neutral: 22.7, positivo: 7.2,  hateful: 40.3 },
    { red: 'youtube',  n: 832,  negativo: 52.8, neutral: 32.2, positivo: 15.0, hateful: 39.7 },
    { red: 'tumblr',   n: 41,   negativo: 58.5, neutral: 24.4, positivo: 17.1, hateful: 15.8 },
    { red: 'bluesky',  n: 3161, negativo: 35.0, neutral: 50.5, positivo: 14.5, hateful: 5.2 },
    { red: 'tiktok',   n: 10,   negativo: 10.0, neutral: 80.0, positivo: 10.0, hateful: 0.0 },
  ],

  /* §8.3 */
  por_idioma: [
    { idioma: 'Español',    n: 3654, negativo: 75.4 },
    { idioma: 'Inglés',     n: 3947, negativo: 43.3 },
    { idioma: 'Portugués',  n: 940,  negativo: 40.0 },
  ],

  /* §8.4 — volumen y virulencia no coinciden */
  por_eje: [
    { eje: 'Colonial / autenticidad', n: 211,  hateful: 57.5 },
    { eje: 'Anti-mexicano / migrante', n: 893, hateful: 56.6 },
    { eje: 'Sudamericano / regional',  n: 1605, hateful: 35.0 },
    { eje: 'Otros / genérico',         n: 36,   hateful: 30.6 },
    { eje: 'Anti-asiático',            n: 19,   hateful: 27.8 },
    { eje: 'Anti-negro / simiesco',    n: 4765, hateful: 21.7 },
  ],

  /* §6 — rendimiento del pipeline de clasificación */
  rendimiento: {
    serial_s: 359.8,
    paralelo_s: 137.9,
    procesos: 6,
    speedup: 2.61,
    eficiencia_pct: 43,
  },

  /* §8.5 — el hallazgo central: lo que el modelo NO ve */
  odio_codificado: {
    leetspeak: ['m0n0', 'macac0s'],
    emoji: ['🍌🍌🍌', '🐒', 'uga uga uga'],
    portmanteaus: ['mexisimios', 'Ecuakong', 'Mechico'],
    ironia: ['se merecen la extinción'],
  },

  cita_bluesky: 'Argentinian woman arrested in Brazil after calling some folks monkey (racism)',
};
