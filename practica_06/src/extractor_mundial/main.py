"""Punto de entrada: lanza la extracción paralela y consolida el dataset.

Uso:
    uv run --env-file .env extractor-mundial                    # las 3 redes en paralelo
    uv run --env-file .env extractor-mundial --redes bluesky    # solo una (recolección)
    uv run --env-file .env extractor-mundial --max-por-criterio 50

Hay dos tipos de corrida y conviene no mezclarlos:
  - RECOLECCIÓN: cada integrante corre SU red (`--redes`), en su máquina y por tandas.
    Los `dataset.jsonl` de cada uno se concatenan al final: el almacén deduplica por
    (red, id), así que juntarlos es simplemente pegar los archivos.
  - EVIDENCIA: una corrida de las 3 redes a la vez, con topes bajos, para demostrar
    la ejecución concurrente. Es la que se guarda en `evidencia/`.
"""

from __future__ import annotations

import argparse
import os
import sys

from .almacenamiento import Almacen
from .config import DIR_DATA, cargar_config
from .extractores import EXTRACTORES, EXTRACTORES_POR_DEFECTO
from .orquestador import ResultadoRed, ejecutar
from .remarcado import remarcar


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
        print(f"  [{r.red:>8}] {estado}  ({r.duracion_s:.2f}s)")
    if resultados:
        duracion_total = max(r.duracion_s for r in resultados)
        print(f"\nTiempo total (los {len(resultados)} en paralelo): "
              f"{duracion_total:.2f}s")
    print(
        f"Nuevos en esta corrida: {almacen.nuevos}  |  "
        f"previos: {almacen.previos}  |  total acumulado: {almacen.total}"
    )


def _argumentos() -> argparse.Namespace:
    # Se puede elegir cualquier red registrada; por defecto, el trío del grupo.
    todas = [E.red for E in EXTRACTORES]
    por_defecto = [E.red for E in EXTRACTORES_POR_DEFECTO]
    p = argparse.ArgumentParser(prog="extractor-mundial")
    p.add_argument(
        "--redes",
        nargs="+",
        choices=todas,
        default=por_defecto,
        metavar="RED",
        help=f"redes a extraer (por defecto, el trío en paralelo: "
             f"{', '.join(por_defecto)}). Disponibles: {', '.join(todas)}. "
             f"Para la evidencia multi-fuente: --redes youtube x bluesky",
    )
    p.add_argument(
        "--max-por-criterio",
        type=int,
        metavar="N",
        help="sobrescribe el tope de registros por criterio (config/busqueda.toml). "
             "Útil para la corrida corta de evidencia.",
    )
    p.add_argument(
        "--max-por-red",
        type=int,
        metavar="N",
        help="tope TOTAL de registros por red; las 3 cortan al alcanzarlo. Es el "
             "limitador universal para una corrida de EVIDENCIA corta y finita "
             "(p. ej. --max-por-red 15): a diferencia de --max-por-criterio, también "
             "acota YouTube, que no busca por criterios sino por videos.",
    )
    p.add_argument(
        "--remarcar",
        action="store_true",
        help="recalcula el campo 'estrategia' del dataset ya extraído con el léxico "
             "actual y sale. No pide nada a la red: úsalo tras tocar lexico.txt.",
    )
    return p.parse_args()


def _solo_remarcar(config) -> None:
    almacen = Almacen(DIR_DATA)
    almacen.cerrar()  # el re-marcado reescribe el jsonl: no dejarlo abierto
    total, dirigidas, cambiados = remarcar(DIR_DATA, config)
    if not total:
        print("No hay dataset.jsonl que re-marcar.")
        return
    pct = dirigidas / total * 100
    print(f"Re-marcado con el léxico actual ({len(config.lexico)} términos):")
    print(f"  registros : {total}")
    print(f"  dirigida  : {dirigidas}  ({pct:.1f}%)")
    print(f"  cambiados : {cambiados}")
    # Regenerar las vistas CSV/JSON desde el jsonl ya corregido.
    for ruta in Almacen(DIR_DATA).volcar():
        print(f"  - {ruta.name}")


def main() -> None:
    args = _argumentos()
    _banner_entorno()

    config = cargar_config()
    if args.remarcar:
        _solo_remarcar(config)
        return

    if args.max_por_criterio is not None:
        config.max_por_criterio = args.max_por_criterio
    if args.max_por_red is not None:
        config.max_total_por_red = args.max_por_red

    elegidos = [E for E in EXTRACTORES if E.red in args.redes]
    extractores = [Extractor(config) for Extractor in elegidos]
    print(f"\nLanzando {len(extractores)} extractor(es) en paralelo: "
          f"{', '.join(e.red for e in extractores)}")

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
