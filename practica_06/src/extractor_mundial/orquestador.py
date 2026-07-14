"""
Orquestador

Los hilos dan paralelismo real de espera, se usa además una cola compartida como canal productor - consumidor,
cada extractor (productor) mete sus `Registro` en la cola desde su propio hilo, y un único controlador (consumidor)
los recoge y los persiste.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterable

from .contrato import Registro
from .extractores.base import ExtractorBase

# Sentinela que un productor pone en la cola para avisar que terminó.
_FIN = object()

# Resumen de lo que produjo un extractor (para el reporte final)
class ResultadoRed:
    def __init__(self, red: str) -> None:
        self.red = red
        self.total = 0
        self.error: str | None = None
        self.duracion_s = 0.0

# Corre en su propio hilo: extrae y encola cada registro
def _productor(
    extractor: ExtractorBase,
    cola: "queue.Queue",
    resultado: ResultadoRed,
) -> None:
    inicio = time.perf_counter()
    try:
        for registro in extractor.extraer():
            cola.put(registro)
            resultado.total += 1
    except NotImplementedError as e:
        resultado.error = f"pendiente: {e}"
    except Exception as e:  # robustez: un extractor caído no tumba a los demás
        resultado.error = f"{type(e).__name__}: {e}"
    finally:
        resultado.duracion_s = time.perf_counter() - inicio
        cola.put(_FIN)  # avisa al controlador que este productor acabó

# Lanza todos los extractores en paralelo y consume sus registros
def ejecutar(
    extractores: Iterable[ExtractorBase],
    consumir: Callable[[Registro], None],
) -> list[ResultadoRed]:
    """
    Args:
        extractores: instancias ya construidas (una por red).
        consumir: función que recibe cada Registro (p. ej. lo guarda).

    Returns:
        Un ResultadoRed por extractor, con total y posible error.
    """
    extractores = list(extractores)
    cola: "queue.Queue" = queue.Queue()
    resultados = [ResultadoRed(e.red) for e in extractores]

    # Lanzar los hilos productores, TODOS arrancan antes de consumir
    hilos = []
    for extractor, resultado in zip(extractores, resultados):
        h = threading.Thread(
            target=_productor,
            args=(extractor, cola, resultado),
            name=f"extractor-{extractor.red}",
            daemon=True,
        )
        h.start()
        hilos.append(h)

    # Controlador central, consume de la cola hasta que todos terminen.
    productores_activos = len(hilos)
    while productores_activos > 0:
        item = cola.get()
        if item is _FIN:
            productores_activos -= 1
        else:
            consumir(item)
        cola.task_done()

    for h in hilos:
        h.join()

    return resultados
