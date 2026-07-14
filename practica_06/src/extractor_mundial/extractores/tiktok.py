"""Extractor de TikTok - comentarios de videos encontrados por hashtag.

TikTok no ofrece una API publica simple para busqueda abierta. Para la practica
se usa `TikTokApi`, una libreria no oficial basada en Playwright. La extraccion
sigue el mismo contrato que las demas fuentes: el extractor solo produce
`Registro`s; el orquestador decide hilos, cola y persistencia.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from datetime import datetime, timezone

from ..config import DIR_CONFIG
from ..contrato import Registro
from ..lexico import cargar as cargar_lexico
from .base import ExtractorBase


class TikTokNoDisponible(RuntimeError):
    """Faltan dependencias o credenciales para consultar TikTok."""


def _normalizar_hashtag(valor: str) -> str:
    return valor.strip().lstrip("#").replace(" ", "")


def _iso_desde_timestamp(valor) -> str | None:
    try:
        if valor is None:
            return None
        return datetime.fromtimestamp(int(valor), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


class ExtractorTikTok(ExtractorBase):
    red = "tiktok"

    def __init__(self, config) -> None:
        super().__init__(config)
        self._lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")

    def extraer(self) -> Iterator[Registro]:
        try:
            registros = asyncio.run(self._extraer_async())
        except ImportError as e:
            raise TikTokNoDisponible(
                "falta TikTokApi/playwright. Ejecuta `uv sync` y luego "
                "`python -m playwright install chromium`."
            ) from e
        for registro in registros:
            yield registro

    async def _extraer_async(self) -> list[Registro]:
        from TikTokApi import TikTokApi

        ms_token = (
            os.environ.get("TIKTOK_MS_TOKEN")
            or os.environ.get("ms_token")
            or ""
        ).strip()
        if not ms_token:
            raise TikTokNoDisponible(
                "falta TIKTOK_MS_TOKEN en .env. Copialo desde la cookie msToken "
                "de una sesion abierta en tiktok.com."
            )

        hashtags = self._hashtags_objetivo()
        if not hashtags:
            return []

        browser = os.environ.get("TIKTOK_BROWSER", "chromium")
        registros: list[Registro] = []
        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[ms_token],
                num_sessions=1,
                sleep_after=3,
                browser=browser,
            )
            for hashtag in hashtags:
                if len(registros) >= self.config.max_total_por_red:
                    break
                nuevos = await self._extraer_hashtag(api, hashtag)
                registros.extend(nuevos)
        return registros[: self.config.max_total_por_red]

    def _hashtags_objetivo(self) -> list[str]:
        """Hashtags viables para TikTok.

        TikTokApi soporta videos por hashtag. Se usan los hashtags explicitos de
        la configuracion y, ademas, selecciones/jugadores normalizados como
        hashtags porque en TikTok suelen aparecer sin espacios.
        """
        candidatos = [
            *self.config.hashtags_torneo,
            *self.config.hashtags_partido,
            *self.config.selecciones,
            *self.config.jugadores,
        ]
        vistos: set[str] = set()
        salida: list[str] = []
        for valor in candidatos:
            hashtag = _normalizar_hashtag(valor)
            if not hashtag:
                continue
            clave = hashtag.lower()
            if clave in vistos:
                continue
            vistos.add(clave)
            salida.append(hashtag)
        return salida

    async def _extraer_hashtag(self, api, hashtag: str) -> list[Registro]:
        registros: list[Registro] = []
        videos_revisados = 0
        criterio = f"#{hashtag}"
        async for video in api.hashtag(name=hashtag).videos(count=self.config.max_videos):
            if len(registros) >= self.config.max_por_criterio:
                break
            if videos_revisados >= self.config.max_videos:
                break
            videos_revisados += 1
            restantes = self.config.max_por_criterio - len(registros)
            registros.extend(await self._comentarios_video(video, criterio, restantes))
        return registros

    async def _comentarios_video(
        self, video, criterio: str, restantes: int
    ) -> list[Registro]:
        registros: list[Registro] = []
        video_data = getattr(video, "as_dict", {}) or {}
        video_id = str(getattr(video, "id", "") or video_data.get("id") or "")
        video_url = getattr(video, "url", None) or (
            f"https://www.tiktok.com/@/video/{video_id}" if video_id else None
        )

        async for comentario in video.comments(count=restantes):
            d = getattr(comentario, "as_dict", {}) or {}
            texto = (
                getattr(comentario, "text", None)
                or d.get("text")
                or d.get("comment")
                or ""
            ).strip()
            if not texto:
                continue

            comentario_id = str(
                getattr(comentario, "id", "") or d.get("cid") or d.get("id") or ""
            )
            if not comentario_id:
                comentario_id = f"{video_id}:{len(registros)}"

            autor = self._autor_comentario(comentario, d)
            con_lexico = self._lexico.es_dirigida(texto)
            stats = video_data.get("stats") or {}
            registros.append(
                Registro(
                    id=comentario_id,
                    red=self.red,
                    estrategia="dirigida" if con_lexico else "amplia",
                    criterio_busqueda=criterio,
                    texto=texto,
                    idioma=None,
                    autor=autor,
                    fecha_publicacion=_iso_desde_timestamp(d.get("create_time")),
                    url=video_url,
                    metricas={
                        "likes": getattr(comentario, "likes_count", None)
                        or d.get("digg_count"),
                        "video_id": video_id,
                        "video_likes": stats.get("diggCount"),
                        "video_comentarios": stats.get("commentCount"),
                        "video_compartidos": stats.get("shareCount"),
                    },
                )
            )
            if len(registros) >= restantes:
                break
        return registros

    @staticmethod
    def _autor_comentario(comentario, data: dict) -> str | None:
        autor = getattr(comentario, "author", None)
        if autor is not None:
            username = getattr(autor, "username", None)
            if username:
                return username
        user = data.get("user") or {}
        return user.get("unique_id") or user.get("nickname")
