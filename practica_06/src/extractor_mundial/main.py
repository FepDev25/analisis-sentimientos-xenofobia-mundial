"""Punto de entrada: lanza la extracción paralela y consolida el dataset.

Uso:
    uv run extractor-mundial
"""

from __future__ import annotations

from .almacenamiento import Almacen
from .config import DIR_DATA, cargar_config
from .extractores import EXTRACTORES_POR_DEFECTO
from .orquestador import ResultadoRed, ejecutar


def _reporte(resultados: list[ResultadoRed], guardados: int) -> None:
    print("\n=== Resultado de la extracción paralela ===")
    for r in resultados:
        estado = f"{r.total} registros" if not r.error else f"⚠ {r.error}"
        print(f"  [{r.red:>8}] {estado}")
    if resultados:
        print(f"\nTiempo total (los {len(resultados)} en paralelo): "
              f"{resultados[0].duracion_s:.2f}s")
    print(f"Guardados (sin duplicados): {guardados}")


def main() -> None:
    config = cargar_config()
    extractores = [Extractor(config) for Extractor in EXTRACTORES_POR_DEFECTO]

    almacen = Almacen(DIR_DATA)
    resultados = ejecutar(extractores, consumir=almacen.agregar)

    rutas = almacen.volcar()
    _reporte(resultados, almacen.total)
    print("\nArchivos generados:")
    for ruta in rutas:
        print(f"  - {ruta}")


if __name__ == "__main__":
    main()
