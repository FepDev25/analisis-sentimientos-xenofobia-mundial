"""Punto de entrada: lanza la extracción paralela y consolida el dataset.

Uso:
    uv run extractor-mundial
"""

from __future__ import annotations

import os
import sys

from .almacenamiento import Almacen
from .config import DIR_DATA, cargar_config
from .extractores import EXTRACTORES_POR_DEFECTO
from .orquestador import ResultadoRed, ejecutar


# Deja constancia EN LA SALIDA de que corremos sin GIL: la captura de la ejecución
# sirve así de evidencia de la técnica de paralelismo, sin tener que probarlo aparte.
# `sys._is_gil_enabled` solo existe en 3.13+; en un build normal se asume GIL activo.
def _banner_entorno() -> None:
    gil = sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else True
    print("=== Entorno ===")
    print(f"  Python : {sys.version.split()[0]}"
          f"{'  (free-threaded)' if not gil else ''}")
    if gil:
        print("  GIL    : ACTIVO — los hilos se turnan la CPU (solo ayudan en I/O)")
    else:
        print("  GIL    : DESACTIVADO — los hilos usan varios núcleos de verdad")
    print(f"  Núcleos: {os.cpu_count()}")


def _reporte(resultados: list[ResultadoRed], almacen: Almacen) -> None:
    print("\n=== Resultado de la extracción paralela ===")
    for r in resultados:
        estado = f"{r.total} registros" if not r.error else f"⚠ {r.error}"
        print(f"  [{r.red:>8}] {estado}")
    if resultados:
        print(f"\nTiempo total (los {len(resultados)} en paralelo): "
              f"{resultados[0].duracion_s:.2f}s")
    print(
        f"Nuevos en esta corrida: {almacen.nuevos}  |  "
        f"previos: {almacen.previos}  |  total acumulado: {almacen.total}"
    )


def main() -> None:
    _banner_entorno()
    config = cargar_config()
    extractores = [Extractor(config) for Extractor in EXTRACTORES_POR_DEFECTO]

    almacen = Almacen(DIR_DATA)
    resultados: list[ResultadoRed] = []
    try:
        resultados = ejecutar(extractores, consumir=almacen.agregar)
    except KeyboardInterrupt:
        print("\n Interrumpido: los datos ya están en dataset.jsonl "
              "regenerando CSV/JSON con lo recolectado...")
    finally:
        # dataset.jsonl ya es durable; aquí se (re)generan las vistas CSV/JSON.
        rutas = almacen.volcar()
        almacen.cerrar()

    _reporte(resultados, almacen)
    print("\nArchivos generados:")
    for ruta in rutas:
        print(f"  - {ruta}")


if __name__ == "__main__":
    main()
