"""Extractor de YouTube — comentarios por query (Data API v3, con API key)

Segundo régimen de YouTube, complementario al scraper de `youtube.py`:

  - `youtube.py` (raspado sin key): ideal para BATCH offline. Sin cuota, volumen
    ilimitado, pero itera videos FIJOS (playlists/canales del TOML), no acepta un
    query, y Google lo throttlea por IP si se abusa.
  - este módulo (Data API v3): ideal EN VIVO. Acepta el query del usuario
    (`search.list`), no lo throttlea por IP, pero gasta cuota (10k unidades/día).

Ambos conviven: la app web usa este; la recolección masiva usa el otro.

Mecanismo: HTTP directo contra la API pública (sin `google-api-python-client`,
igual que Bluesky, para que el protocolo quede a la vista y no depender de un
wrapper pesado):
  - `search.list`         → query → videos del evento.
  - `commentThreads.list` → comentarios de nivel superior de cada video.

Estrategia de 2 capas (la misma que YouTube batch y Bluesky): los comentarios se
recolectan como `amplia` y se re-marcan como `dirigida` si su texto trae un
término del léxico xenófobo.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator

import requests

from ..config import Criterio, DIR_CONFIG
from ..contrato import Registro
from ..lexico import Lexico, cargar as cargar_lexico
from .base import ExtractorBase

API = "https://www.googleapis.com/youtube/v3"


class FaltaApiKey(RuntimeError):
    """El .env no tiene YOUTUBE_API_KEY."""


class _CuotaAgotada(RuntimeError):
    """La API respondió 403 por cuota diaria agotada: cortar YouTube por hoy."""


class _ComentariosDeshabilitados(RuntimeError):
    """El video tiene los comentarios cerrados: se salta, no es error de la corrida."""


# Mapea un item de commentThreads.list al contrato. None si hay que descartarlo.
# Función pura (sin red) para poder testear el mapeo contra un fixture.
def _a_registro(item: dict, criterio: Criterio, lexico: Lexico) -> Registro | None:
    hilo = item.get("snippet") or {}
    comentario = (hilo.get("topLevelComment") or {}).get("snippet") or {}
    texto = (comentario.get("textOriginal") or "").strip()
    if not texto:
        return None

    # Una búsqueda 'amplia' puede traer igualmente un comentario con carga
    # xenófoba: se re-marca como 'dirigida' (misma regla que Bluesky/YouTube batch).
    estrategia = "dirigida" if lexico.es_dirigida(texto) else criterio.estrategia

    comentario_id = (hilo.get("topLevelComment") or {}).get("id", "")
    video_id = hilo.get("videoId")

    return Registro(
        id=comentario_id,
        red="youtube",
        estrategia=estrategia,
        criterio_busqueda=criterio.query,
        texto=texto,
        idioma=None,  # se detecta en la Práctica 7
        autor=comentario.get("authorDisplayName"),
        fecha_publicacion=comentario.get("publishedAt"),  # ya viene en ISO 8601
        url=f"https://www.youtube.com/watch?v={video_id}&lc={comentario_id}",
        metricas={
            "likes": comentario.get("likeCount"),
            "respuestas": hilo.get("totalReplyCount"),
        },
    )


class ExtractorYouTubeApi(ExtractorBase):
    red = "youtube"

    # Videos que se piden por query. search.list cuesta 100 unidades sin importar
    # cuántos devuelva, así que se piden de una: el corte real lo da max_total_por_red.
    _MAX_VIDEOS = 15
    # Tope de la API por página de comentarios.
    _POR_PAGINA = 100
    _TIMEOUT = 20

    def __init__(self, config) -> None:
        super().__init__(config)
        self._lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")
        self._sesion = requests.Session()

    def _clave(self) -> str:
        clave = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if not clave:
            raise FaltaApiKey(
                "falta YOUTUBE_API_KEY. Crea una API key gratuita en Google Cloud "
                "Console (habilita 'YouTube Data API v3'), ponla en .env y ejecuta "
                "con `uv run --env-file .env ...`"
            )
        return clave

    # Traduce un 403 de la API a la excepción específica según su `reason`.
    @staticmethod
    def _mapear_403(resp: requests.Response) -> None:
        try:
            errores = resp.json().get("error", {}).get("errors", [])
            razon = errores[0].get("reason", "") if errores else ""
        except ValueError:
            razon = ""
        if razon in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
            raise _CuotaAgotada(
                "cuota diaria de la YouTube Data API agotada (10k unidades). "
                "Reintenta mañana o usa otra API key / proyecto de GCP."
            )
        if razon == "commentsDisabled":
            raise _ComentariosDeshabilitados(razon)
        resp.raise_for_status()

    def _get(self, recurso: str, params: dict) -> dict:
        params = {**params, "key": self._clave()}
        r = self._sesion.get(f"{API}/{recurso}", params=params, timeout=self._TIMEOUT)
        if r.status_code == 403:
            self._mapear_403(r)
        r.raise_for_status()
        return r.json()

    # query → lista de video_id (los más relevantes del evento).
    def _buscar_videos(self, query: str, limite: int) -> list[str]:
        datos = self._get(
            "search",
            {
                "part": "id",
                "q": query,
                "type": "video",
                "maxResults": min(limite, 50),
                "order": "relevance",
            },
        )
        ids = []
        for item in datos.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            if vid:
                ids.append(vid)
        return ids

    # Itera los items crudos de commentThreads.list de UN video, paginando.
    def _items_de_video(self, video_id: str, limite: int) -> Iterator[dict]:
        token: str | None = None
        emitidos = 0
        while emitidos < limite:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(self._POR_PAGINA, limite - emitidos),
                "order": "relevance",
                "textFormat": "plainText",
            }
            if token:
                params["pageToken"] = token
            datos = self._get("commentThreads", params)
            items = datos.get("items", [])
            if not items:
                return
            for item in items:
                if emitidos >= limite:
                    return
                yield item
                emitidos += 1
            token = datos.get("nextPageToken")
            if not token:
                return

    # ------------------------------------------------ interfaz del orquestador
    def extraer(self) -> Iterator[Registro]:
        self._clave()  # falla claro y temprano si no hay API key
        total = 0
        for criterio in self.config.todos_los_criterios():
            if total >= self.config.max_total_por_red:
                break
            try:
                videos = self._buscar_videos(criterio.query, self._MAX_VIDEOS)
            except requests.RequestException as e:
                print(
                    f"[youtube-api] búsqueda {criterio.query!r} omitida "
                    f"({type(e).__name__}: {e})",
                    file=sys.stderr,
                )
                continue

            for video_id in videos:
                if total >= self.config.max_total_por_red:
                    break
                restante = self.config.max_total_por_red - total
                limite = min(self.config.max_por_criterio, restante)
                try:
                    for item in self._items_de_video(video_id, limite):
                        registro = _a_registro(item, criterio, self._lexico)
                        if registro is None:
                            continue
                        yield registro
                        total += 1
                except _ComentariosDeshabilitados:
                    continue  # video sin comentarios: se salta sin ruido
                except requests.RequestException as e:
                    # Un video caído no debe tumbar la query ni las demás redes.
                    print(
                        f"[youtube-api] video {video_id} omitido "
                        f"({type(e).__name__}: {e})",
                        file=sys.stderr,
                    )
                    continue
