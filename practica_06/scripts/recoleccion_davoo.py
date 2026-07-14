"""Recolección DIRIGIDA — canal de reacciones de Davoo Xeneize (@DavooXeneizePlusX).

Hipótesis: los canales de REACCIÓN concentran más debate, humor xenófobo y gente
con rabia que los canales de highlights
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from yt_dlp import YoutubeDL

from extractor_mundial.almacenamiento import Almacen
from extractor_mundial.config import DIR_DATA, cargar_config
from extractor_mundial.extractores.youtube import ExtractorYouTube

CANAL = "https://www.youtube.com/@DavooXeneizePlusX/videos"
LOGS_ESTADO = ("youtube_videos_hechos.txt", "youtube_videos_fallidos.txt")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recolección dirigida al canal de Davoo Xeneize.")
    p.add_argument("--videos", type=int, default=75,
                   help="nº de videos MÁS RECIENTES a recolectar (default 75 = los del Mundial).")
    p.add_argument("--por-video", type=int, default=5000,
                   help="tope de comentarios por video (default 5000).")
    p.add_argument("--pausa", type=float, default=8.0,
                   help="segundos de pausa entre videos (default 8).")
    p.add_argument("--horas", type=float, default=8.0,
                   help="presupuesto máximo de tiempo (default 8h).")
    p.add_argument("--cooldown", type=float, default=900.0,
                   help="enfriamiento (s) tras throttle sostenido (default 900 = 15 min).")
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


def ultimos_videos(url: str, n: int) -> list[tuple[str, str]]:
    """(video_id, título) de los N videos más recientes del canal (más nuevo primero)."""
    opts = {
        "extract_flat": True,
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "playlistend": n,          # solo trae metadatos de los primeros N (los recientes)
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False) or {}
    pares: list[tuple[str, str]] = []
    for e in info.get("entries", []) or []:
        if e and e.get("id"):
            pares.append((e["id"], e.get("title") or e["id"]))
    return pares[:n]


def configurar(args: argparse.Namespace):
    """Config acotada SOLO a los videos de Davoo (sin playlists/canales de fondo)."""
    config = cargar_config()
    config.max_por_criterio = args.por_video
    config.pausa_youtube = args.pausa
    config.max_videos = 10_000            # tanda "sin límite" de videos
    config.max_total_por_red = 100_000_000
    # Aislar esta corrida: no arrastrar las playlists ESPN/DS Sports.
    config.playlists_youtube = []
    config.canales_youtube = []
    config.videos_youtube = []
    # Extractor paciente para desatender.
    ExtractorYouTube._BACKOFF = (15, 45, 120)
    ExtractorYouTube._MAX_FALLOS_SEGUIDOS = 8
    ExtractorYouTube._MAX_STRIKES = 5
    return config


def main() -> None:
    args = parse_args()
    print("=== Recolección dirigida: canal Davoo Xeneize (reacciones) ===")
    print(f"  videos={args.videos}  tope/video={args.por_video}  pausa={args.pausa}s  "
          f"cooldown={args.cooldown/60:.0f}min  presupuesto={args.horas}h")

    respaldar(DIR_DATA)

    print(f"[youtube] expandiendo canal (últimos {args.videos} videos)...")
    pares = ultimos_videos(CANAL, args.videos)
    if not pares:
        print("‼ No se obtuvieron videos del canal (¿URL o red?). Aborto.")
        sys.exit(1)
    todos = {vid for vid, _ in pares}
    print(f"[youtube] {len(pares)} videos a recolectar (más reciente: {pares[0][1][:70]!r}).")

    config = configurar(args)
    extractor = ExtractorYouTube(config)
    # La lista de videos es fija: la fijamos una vez y evitamos re-expandir el
    # canal en cada tanda (más rápido y menos throttle).
    extractor.videos = lambda: list(pares)  # type: ignore[method-assign]

    almacen = Almacen(DIR_DATA)
    print(f"[almacen] comentarios previos (todas las redes): {almacen.previos:,}")

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
                print("\n✓ No quedan videos pendientes del canal. Recolección COMPLETA.")
                break
            transcurrido = time.monotonic() - t0
            if transcurrido > args.horas * 3600:
                print(f"\n⏱ Presupuesto de {args.horas}h agotado. "
                      f"Quedan {len(pendientes)} videos (re-ejecuta para reanudar).")
                break

            tanda += 1
            antes = almacen.total
            print(f"\n--- Tanda {tanda} | {len(pendientes)}/{len(todos)} pendientes | "
                  f"{transcurrido/3600:.1f}h | {almacen.total:,} comentarios ---")

            for registro in extractor.extraer():
                almacen.agregar(registro)

            almacen.volcar()  # refresca CSV/JSON al cierre de cada tanda
            ganados = almacen.total - antes
            hechos_ahora = extractor._cargar_hechos()
            hechos_davoo = len(todos & hechos_ahora)
            print(f"[tanda {tanda}] +{ganados:,} comentarios | "
                  f"videos del canal hechos: {hechos_davoo}/{len(todos)}")

            strikes = extractor._cargar_fallidos()
            quedan = [
                v for v in todos
                if v not in hechos_ahora and strikes.get(v, 0) < extractor._MAX_STRIKES
            ]
            if not quedan:
                continue  # el while cerrará como COMPLETA
            # Si la tanda no completó ningún video nuevo → throttle: enfriar largo.
            avanzo = len(todos & hechos_ahora) > len(todos & hechos)
            espera = 30 if avanzo else args.cooldown
            print(f"[pausa] {'breve' if avanzo else 'THROTTLE → enfriamiento'}: "
                  f"espero {espera/60:.1f} min...")
            time.sleep(espera)
    except KeyboardInterrupt:
        print("\n[interrumpido] cortando limpio; dataset.jsonl ya está a salvo.")
    finally:
        rutas = almacen.volcar()
        almacen.cerrar()
        total_final = almacen.total
        print(f"\n=== Fin. {total_final:,} comentarios totales "
              f"(+{total_final - almacen.previos:,} en esta corrida) "
              f"en {(time.monotonic()-t0)/3600:.1f}h ===")
        for r in rutas:
            print(f"  - {r}")


if __name__ == "__main__":
    sys.exit(main())
