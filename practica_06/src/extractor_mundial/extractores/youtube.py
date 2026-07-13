"""Extractor de YouTube — comentarios de videos de resúmenes de goles

Alcance: por canal/video/playlist. Mecanismo: librerías de terceros que leen la
API interna de YouTube (sin API key ni cuota):
  - `yt-dlp` para expandir playlists/canales en la lista de videos.
  - `youtube-comment-downloader` para bajar los comentarios de cada video.

Estrategia de 2 capas aplicada a YouTube: se recolectan todos los comentarios delos videos del evento (`amplia`),
los que contienen algún término del léxico xenófobo se marcan como `dirigida`. Así el campo `estrategia` habilita la
estadística "de N comentarios, X% con carga xenófoba".
"""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from youtube_comment_downloader import (
    SORT_BY_POPULAR,
    SORT_BY_RECENT,
    YoutubeCommentDownloader,
)
from yt_dlp import YoutubeDL

from ..config import DIR_DATA
from ..contrato import Registro
from .base import ExtractorBase


def _iso(ts: float | None) -> str | None:
    """Convierte un timestamp Unix a ISO 8601 (UTC)."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class ExtractorYouTube(ExtractorBase):
    red = "youtube"

    # Orden en que se intenta pedir los comentarios
    _ORDENES = (SORT_BY_RECENT, SORT_BY_POPULAR)

    # Esperas (s) ante un posible throttle antes de reintentar el mismo video.
    _BACKOFF = (8, 20)
    # Si tantos videos NUEVOS seguidos fallan, se asume throttle sostenido y se corta la corrida
    _MAX_FALLOS_SEGUIDOS = 4
    # Tras este nº de fallos ACUMULADOS entre corridas, el video se descarta
    _MAX_STRIKES = 3
    # Logs de estado para reanudar por tandas.
    _ARCHIVO_HECHOS = "youtube_videos_hechos.txt"
    _ARCHIVO_FALLIDOS = "youtube_videos_fallidos.txt"

    def __init__(self, config) -> None:
        super().__init__(config)
        # Léxico en minúsculas para el marcado amplia/dirigida.
        self._lexico = [t.lower() for t in config.lexico]
        self._downloader = YoutubeCommentDownloader()
        self._ruta_hechos = DIR_DATA / self._ARCHIVO_HECHOS
        self._ruta_fallidos = DIR_DATA / self._ARCHIVO_FALLIDOS

    # resolución de videos
    def videos(self) -> list[tuple[str, str]]:
        """Lista de (video_id, título) a partir de videos + playlists + canales."""
        vistos: dict[str, str] = {}

        # Videos explícitos (IDs o URLs).
        for v in self.config.videos_youtube:
            vid = v.rsplit("=", 1)[-1].rsplit("/", 1)[-1]
            vistos.setdefault(vid, vid)

        # Playlists y canales se expanden en plano (solo metadatos, sin descargar).
        for url in [*self.config.playlists_youtube, *self.config.canales_youtube]:
            for vid, titulo in self._expandir(url):
                vistos.setdefault(vid, titulo)

        return list(vistos.items())

    @staticmethod
    def _expandir(url: str) -> Iterator[tuple[str, str]]:
        opts = {
            "extract_flat": True,
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": True,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False) or {}
        for e in info.get("entries", []) or []:
            if e and e.get("id"):
                yield e["id"], (e.get("title") or e["id"])

    # comentarios de un video
    def _bajar_comentarios(self, url: str) -> Iterator[dict]:
        """Itera los comentarios crudos probando cada orden de `_ORDENES`"""
        ultimo_error: RuntimeError | None = None
        for orden in self._ORDENES:
            emitidos = 0
            try:
                for c in self._downloader.get_comments_from_url(url, sort_by=orden):
                    emitidos += 1
                    yield c
                return  # se agotó el hilo sin error
            except RuntimeError as e:
                if emitidos:
                    raise  # ya emitimos; no reintentar para no duplicar
                ultimo_error = e  # falló al fijar el orden → probar el siguiente
        if ultimo_error is not None:
            raise ultimo_error

    def _bajar_con_reintentos(self, url: str) -> Iterator[dict]:
        """Envuelve `_bajar_comentarios` con backoff ante posible throttle.
        Solo reintenta si el fallo ocurre ANTES de emitir comentarios 
        """
        for i, espera in enumerate((0, *self._BACKOFF)):
            if espera:
                print(
                    f"[youtube] posible throttle; espero {espera}s y reintento",
                    file=sys.stderr,
                )
                time.sleep(espera)
            emitidos = 0
            try:
                for c in self._bajar_comentarios(url):
                    emitidos += 1
                    yield c
                return
            except RuntimeError:
                if emitidos or i == len(self._BACKOFF):
                    raise
                continue

    def comentarios_de_video(
        self, video_id: str, titulo: str, limite: int | None = None
    ) -> Iterator[Registro]:
        """Baja los comentarios de UN video y los mapea al contrato."""
        limite = limite if limite is not None else self.config.max_por_criterio
        url = f"https://www.youtube.com/watch?v={video_id}"
        n = 0
        for c in self._bajar_con_reintentos(url):
            if n >= limite:
                break
            texto = (c.get("text") or "").strip()
            if not texto:
                continue
            dirigida = any(t in texto.lower() for t in self._lexico)
            yield Registro(
                id=c["cid"],
                red=self.red,
                estrategia="dirigida" if dirigida else "amplia",
                criterio_busqueda=titulo,
                texto=texto,
                idioma=None,  # se detecta en la Práctica 7
                autor=c.get("author"),
                fecha_publicacion=_iso(c.get("time_parsed")),
                url=f"{url}&lc={c['cid']}",
                metricas={
                    "likes": c.get("votes"),
                    "respuestas": c.get("replies"),
                    "corazon_autor": c.get("heart"),
                },
            )
            n += 1

    # reanudación por tandas--
    @staticmethod
    def _leer_lineas(ruta: Path) -> list[str]:
        if not ruta.exists():
            return []
        return [
            linea.strip()
            for linea in ruta.read_text(encoding="utf-8").splitlines()
            if linea.strip()
        ]

    def _cargar_hechos(self) -> set[str]:
        """IDs de videos ya recolectados por completo en corridas previas."""
        return set(self._leer_lineas(self._ruta_hechos))

    def _cargar_fallidos(self) -> dict[str, int]:
        """IDs fallidos → nº de fallos ACUMULADOS entre corridas (strikes)."""
        strikes: dict[str, int] = {}
        for vid in self._leer_lineas(self._ruta_fallidos):
            strikes[vid] = strikes.get(vid, 0) + 1
        return strikes

    def _marcar_hecho(self, video_id: str) -> None:
        with self._ruta_hechos.open("a", encoding="utf-8") as f:
            f.write(video_id + "\n")

    def _registrar_fallo(self, video_id: str) -> None:
        with self._ruta_fallidos.open("a", encoding="utf-8") as f:
            f.write(video_id + "\n")

    def _pendientes(
        self, hechos: set[str], strikes: dict[str, int]
    ) -> list[tuple[str, str]]:
        """Videos a procesar esta tanda. NUEVOS (nunca intentados) PRIMERO"""
        nuevos: list[tuple[str, str]] = []
        reintentos: list[tuple[str, str]] = []
        for video_id, titulo in self.videos():
            if video_id in hechos:
                continue
            n = strikes.get(video_id, 0)
            if n >= self._MAX_STRIKES:
                continue  # descartado
            (reintentos if n else nuevos).append((video_id, titulo))
        return nuevos + reintentos

    # interfaz del orquestador
    def extraer(self) -> Iterator[Registro]:
        hechos = self._cargar_hechos()
        strikes = self._cargar_fallidos()
        total = 0
        intentos = 0          # videos abordados en esta corrida (tanda)
        fallos_seguidos = 0
        for video_id, titulo in self._pendientes(hechos, strikes):
            if total >= self.config.max_total_por_red:
                break
            if intentos >= self.config.max_videos:
                break
            # Pausa entre videos para no gatillar el throttle de YouTube.
            if intentos > 0 and self.config.pausa_youtube > 0:
                time.sleep(self.config.pausa_youtube)
            intentos += 1
            restante = self.config.max_total_por_red - total
            limite = min(self.config.max_por_criterio, restante)
            try:
                for registro in self.comentarios_de_video(video_id, titulo, limite):
                    yield registro
                    total += 1
                # Completó sin excepción → no reintentar en la próxima tanda.
                self._marcar_hecho(video_id)
                fallos_seguidos = 0
            except Exception as e:
                # Un video problemático NO debe tumbar el resto de la playlist, se registra y se continúa
                self._registrar_fallo(video_id)
                nuevas = strikes.get(video_id, 0) + 1
                descartado = nuevas >= self._MAX_STRIKES
                print(
                    f"[youtube] video {video_id} omitido "
                    f"({type(e).__name__}: {e})"
                    + (f" — descartado tras {nuevas} fallos" if descartado else ""),
                    file=sys.stderr,
                )
                # Un video ya descartado (no-scrapeable) NO cuenta como señal de throttle
                if descartado:
                    fallos_seguidos = 0
                    continue
                fallos_seguidos += 1
                if fallos_seguidos >= self._MAX_FALLOS_SEGUIDOS:
                    print(
                        f"[youtube] {fallos_seguidos} videos fallidos seguidos: "
                        "parece throttle sostenido, corto la extracción de YouTube "
                        "(reintenta en otra tanda más tarde).",
                        file=sys.stderr,
                    )
                    break
                continue
