"""Recolección de YouTube — maximiza comentarios, pensada para dejar
corriendo horas (toda la noche) sin vigilancia.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from extractor_mundial.almacenamiento import Almacen
from extractor_mundial.config import DIR_DATA, cargar_config
from extractor_mundial.extractores.youtube import ExtractorYouTube

# Playlist extra encontrada (DS Sports, 300+ resúmenes del Mundial).
PLAYLIST_DS_SPORTS = (
    "https://www.youtube.com/playlist?list=PLlDA_e1cBD7n5wCXuj7YXnuIp1s5YJDvd"
)

# Archivos de estado que se respaldan y (opcionalmente) se resetean.
LOGS_ESTADO = ("youtube_videos_hechos.txt", "youtube_videos_fallidos.txt")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recolección nocturna de YouTube.")
    p.add_argument("--horas", type=float, default=10.0,
                   help="presupuesto máximo de tiempo (default 10h).")
    p.add_argument("--por-video", type=int, default=5000,
                   help="tope de comentarios por video (default 5000).")
    p.add_argument("--pausa", type=float, default=8.0,
                   help="segundos de pausa entre videos (default 8).")
    p.add_argument("--cooldown", type=float, default=900.0,
                   help="enfriamiento (s) tras throttle sostenido (default 900 = 15 min).")
    p.add_argument("--continuar", action="store_true",
                   help="NO resetear los logs: reanuda donde quedó en vez de reprocesar todo.")
    p.add_argument("--sin-ds-sports", action="store_true",
                   help="no añadir la playlist extra de DS Sports.")
    return p.parse_args()


def respaldar(dir_data: Path) -> Path:
    """Copia el estado actual a data/backups/<timestamp>/ (red de seguridad)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = dir_data / "backups" / ts
    destino.mkdir(parents=True, exist_ok=True)
    patrones = ["dataset.jsonl", "dataset.csv", "dataset.json", "youtube.csv", *LOGS_ESTADO]
    copiados = 0
    for nombre in patrones:
        origen = dir_data / nombre
        if origen.exists():
            shutil.copy2(origen, destino / nombre)
            copiados += 1
    print(f"[backup] {copiados} archivos respaldados en {destino}")
    return destino


def resetear_logs(dir_data: Path) -> None:
    """Vacía los logs de hechos/fallidos para reprocesar TODOS los videos.

    dataset.jsonl se conserva: el dedup evita duplicar; solo se AÑADEN los
    comentarios nuevos (los que el tope anterior dejó fuera).
    """
    for nombre in LOGS_ESTADO:
        ruta = dir_data / nombre
        if ruta.exists():
            ruta.unlink()
    print("[reset] logs de videos hechos/fallidos vaciados: se reprocesa toda la playlist.")


def configurar(args: argparse.Namespace):
    """Config con topes altos, pausa larga y la playlist extra."""
    config = cargar_config()
    config.max_por_criterio = args.por_video
    config.pausa_youtube = args.pausa
    # Tanda "sin límite" de videos: cada tanda intenta cuantos pueda hasta agotar
    # o hasta throttle sostenido; el bucle exterior se encarga de reintentar.
    config.max_videos = 10_000
    config.max_total_por_red = 100_000_000
    if not args.sin_ds_sports and PLAYLIST_DS_SPORTS not in config.playlists_youtube:
        config.playlists_youtube.append(PLAYLIST_DS_SPORTS)

    # Extractor MÁS PACIENTE para desatender: espera más y tolera más fallos
    # seguidos antes de cortar una tanda, y da más strikes a los videos difíciles.
    ExtractorYouTube._BACKOFF = (15, 45, 120)
    ExtractorYouTube._MAX_FALLOS_SEGUIDOS = 8
    ExtractorYouTube._MAX_STRIKES = 5
    return config


def main() -> None:
    args = parse_args()
    print("=== Recolección nocturna de YouTube ===")
    print(f"  tope/video={args.por_video}  pausa={args.pausa}s  "
          f"cooldown={args.cooldown/60:.0f}min  presupuesto={args.horas}h  "
          f"{'REANUDAR' if args.continuar else 'RESET (reprocesa todo)'}")

    respaldar(DIR_DATA)
    if not args.continuar:
        resetear_logs(DIR_DATA)

    config = configurar(args)
    extractor = ExtractorYouTube(config)

    # Expandimos la lista de videos UNA vez (las playlists no cambian en la noche).
    print("[youtube] expandiendo playlists (puede tardar)...")
    todos = {vid for vid, _ in extractor.videos()}
    print(f"[youtube] {len(todos)} videos en total entre todas las playlists.")

    # Un solo Almacén para toda la corrida (dataset.jsonl es durable por línea).
    almacen = Almacen(DIR_DATA)
    print(f"[almacen] comentarios previos: {almacen.previos:,}")

    t0 = time.monotonic()
    tanda = 0
    try:
        while True:
            hechos = extractor._cargar_hechos()
            strikes = extractor._cargar_fallidos()
            pendientes = [
                v for v in todos
                if v not in hechos and strikes.get(v, 0) < extractor._MAX_STRIKES
            ]
            if not pendientes:
                print("\n✓ No quedan videos pendientes. Recolección COMPLETA.")
                break
            transcurrido = time.monotonic() - t0
            if transcurrido > args.horas * 3600:
                print(f"\n⏱ Presupuesto de {args.horas}h agotado. "
                      f"Quedan {len(pendientes)} videos (reanuda con --continuar).")
                break

            tanda += 1
            antes = almacen.total
            print(f"\n--- Tanda {tanda} | {len(pendientes)} pendientes | "
                  f"{transcurrido/3600:.1f}h transcurridas | "
                  f"{almacen.total:,} comentarios ---")

            for registro in extractor.extraer():
                almacen.agregar(registro)

            almacen.volcar()  # refresca CSV/JSON al cierre de cada tanda
            ganados = almacen.total - antes
            hechos_ahora = extractor._cargar_hechos()
            print(f"[tanda {tanda}] +{ganados:,} comentarios nuevos | "
                  f"videos hechos: {len(hechos_ahora)}/{len(todos)}")

            # Recalcular pendientes tras la tanda.
            strikes = extractor._cargar_fallidos()
            quedan = [
                v for v in todos
                if v not in hechos_ahora and strikes.get(v, 0) < extractor._MAX_STRIKES
            ]
            if not quedan:
                continue  # el while de arriba cerrará como COMPLETA

            # Si la tanda no completó ningún video nuevo, casi seguro fue throttle
            # sostenido: enfriamiento largo antes de reintentar.
            avanzo = len(hechos_ahora) > len(hechos)
            espera = 30 if avanzo else args.cooldown
            print(f"[pausa] {'breve' if avanzo else 'THROTTLE → enfriamiento'}: "
                  f"espero {espera/60:.1f} min antes de la próxima tanda...")
            time.sleep(espera)
    except KeyboardInterrupt:
        print("\n[interrumpido] cortando limpio; dataset.jsonl ya está a salvo.")
    finally:
        rutas = almacen.volcar()
        almacen.cerrar()
        total_final = almacen.total
        print(f"\n=== Fin. {total_final:,} comentarios totales "
              f"(+{total_final - almacen.previos:,} en esta corrida) en {(time.monotonic()-t0)/3600:.1f}h ===")
        for r in rutas:
            print(f"  - {r}")


if __name__ == "__main__":
    sys.exit(main())
