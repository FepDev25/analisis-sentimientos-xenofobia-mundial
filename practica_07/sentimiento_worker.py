"""Clasificador de sentimientos por bloques — unidad de trabajo del pool de procesos

Cada proceso carga los modelos de pysentimiento UNA vez (cache por `lru_cache`) 
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "TOKENIZERS_PARALLELISM"):
    os.environ.setdefault(_v, "1" if _v != "TOKENIZERS_PARALLELISM" else "false")

from functools import lru_cache

# pysentimiento trae modelos de sentimiento en estos idiomas; el resto se rutea a
# español (idioma dominante del corpus).
IDIOMAS_SOPORTADOS = {"es", "en", "it", "pt"}
# hate_speech solo existe para es/en en pysentimiento.
IDIOMAS_ODIO = {"es", "en"}

# Mapeo de la etiqueta cruda de pysentimiento al contrato del proyecto.
_MAPA_SENTIMIENTO = {"POS": "positivo", "NEG": "negativo", "NEU": "neutral"}


def idioma_modelo(idioma: str | None) -> str:
    """Idioma efectivo para elegir modelo: soportado tal cual, o `es` por defecto."""
    return idioma if idioma in IDIOMAS_SOPORTADOS else "es"


@lru_cache(maxsize=None)
def _analizador(tarea: str, idioma: str):
    """Crea (y cachea por proceso) un analizador de pysentimiento.

    Import lazy: pysentimiento/torch solo se cargan dentro del worker, nunca
    en el proceso padre (evita problemas de `fork` tras inicializar torch).
    """
    import torch
    from pysentimiento import create_analyzer

    # Refuerzo en runtime del pinneo de hilos (las env vars de arriba cubren el
    # arranque; esto asegura que torch no re-expanda a N núcleos por proceso).
    torch.set_num_threads(1)

    return create_analyzer(task=tarea, lang=idioma)


def clasificar_bloque(bloque):
    """Clasifica un bloque de textos. Devuelve filas alineadas por índice global.

    `bloque` = lista de tuplas ``(indice_global, texto, idioma, con_odio)``.
    Devuelve lista de dicts: ``indice``, ``sentimiento``, ``sent_score``,
    ``odio`` (bool|None), ``odio_score`` (float|None).
    """
    if not bloque:
        return []

    con_odio = bool(bloque[0][3])

    # Agrupar índices por idioma de modelo.
    por_idioma: dict[str, list[tuple[int, str]]] = {}
    for indice, texto, idioma, _ in bloque:
        lm = idioma_modelo(idioma)
        por_idioma.setdefault(lm, []).append((indice, str(texto)))

    salida: dict[int, dict] = {}
    for lm, items in por_idioma.items():
        indices = [i for i, _ in items]
        textos = [t for _, t in items]

        preds = _analizador("sentiment", lm).predict(textos)
        for indice, pred in zip(indices, preds):
            probas = getattr(pred, "probas", {}) or {}
            if probas:
                etiqueta = max(probas, key=probas.get)
                score = probas[etiqueta]
            else:
                etiqueta, score = None, None
            # `.upper()`: algún modelo de idioma minoritario devuelve la etiqueta en
            # minúscula (`pos`/`neg`), que no matcheaba las claves POS/NEG/NEU.
            clave = etiqueta.upper() if isinstance(etiqueta, str) else etiqueta
            salida[indice] = {
                "indice": indice,
                "sentimiento": _MAPA_SENTIMIENTO.get(clave, etiqueta),
                "sent_score": score,
                "odio": None,
                "odio_score": None,
            }

        # Análisis de odio opcional, solo en idiomas donde el modelo existe.
        if con_odio and lm in IDIOMAS_ODIO:
            preds_o = _analizador("hate_speech", lm).predict(textos)
            for indice, pred in zip(indices, preds_o):
                # hate_speech es multi-etiqueta: output es una lista de etiquetas.
                etiquetas = pred.output if isinstance(pred.output, (list, tuple, set)) else [pred.output]
                probas = getattr(pred, "probas", {}) or {}
                salida[indice]["odio"] = "hateful" in etiquetas
                salida[indice]["odio_score"] = probas.get("hateful")

    return [salida[i] for i in sorted(salida)]
