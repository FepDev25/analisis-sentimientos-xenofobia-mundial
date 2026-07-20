# Clasificacion de sentimientos sobre un pool de procesos que se mantiene caliente
# mientras vive el servidor.

from __future__ import annotations

import os

# Pinneo de hilos ANTES de que un proceso hijo importe torch. Sin esto, N procesos
# x N hilos de torch se ahogan entre si: en P7 el paralelo llego a ir mas lento
# que el serial (0.97x) hasta que se fijo esto.
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402

from . import config  # noqa: E402
from .sentimiento_worker import clasificar_bloque  # noqa: E402

_pool: ProcessPoolExecutor | None = None


# Crea el pool. Cada proceso carga los modelos en su primer uso y los cachea
# (`lru_cache` del worker), asi que conviene calentarlo al arrancar el servidor y
# no en la primera busqueda del usuario.
def arrancar(calentar: bool = True) -> None:
    global _pool
    if _pool is not None:
        return
    _pool = ProcessPoolExecutor(max_workers=config.N_WORKERS)
    if calentar:
        bloque = [(0, "hola", "es", True)]
        # Best-effort: no hay forma de garantizar que un submit por worker aterrice
        # en workers distintos, pero con el pool recien creado es lo habitual.
        for fut in [_pool.submit(clasificar_bloque, bloque) for _ in range(config.N_WORKERS)]:
            fut.result()


def apagar() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=True)
        _pool = None


def _partir(items: list, tamano: int) -> list[list]:
    return [items[i : i + tamano] for i in range(0, len(items), tamano)]


# `registros`: dicts con `id`, `texto`, `idioma` (lo que devuelve
# `bd.registros_sin_clasificar`). Devuelve filas listas para `bd.guardar_sentimientos`.
def clasificar(registros: list[dict], con_odio: bool = True) -> list[dict]:
    if not registros:
        return []
    if _pool is None:
        raise RuntimeError("el pool no esta arrancado: llama a arrancar() primero")

    bloques = _partir(
        [(r["id"], r["texto"], r.get("idioma"), con_odio) for r in registros],
        config.TAMANO_BLOQUE,
    )

    filas: list[dict] = []
    futuros = [_pool.submit(clasificar_bloque, b) for b in bloques]
    for fut in as_completed(futuros):
        try:
            resultado = fut.result()
        except Exception:
            continue  # un bloque caido no invalida los demas (criterio de P7)
        for fila in resultado:
            # El worker indexa por `indice`; aca ese indice ES el id del registro.
            fila["registro_id"] = fila.pop("indice")
            filas.append(fila)
    return filas
