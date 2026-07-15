"""Extractor de Twitch a partir de chats de VOD descargados en JSON.

Los archivos de entrada se obtienen con TwitchDownloaderCLI y deben guardarse
en data/ con el patrón:

    twitch_raw_<video_id>.json

Cada mensaje del chat se convierte al contrato común del proyecto.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from ..config import DIR_DATA
from ..contrato import Registro
from .base import ExtractorBase


_RE_ESPACIOS = re.compile(r"\s+")
_RE_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_RE_COMANDO = re.compile(r"^![a-zA-Z0-9_]+(?:\s|$)")

_BOTS_CONOCIDOS = {
    "streamelements",
    "nightbot",
    "moobot",
    "fossabot",
    "wizebot",
    "streamlabs",
}


def _normalizar_texto(texto: str) -> str:
    """Elimina saltos y espacios repetidos sin alterar el contenido."""
    return _RE_ESPACIOS.sub(" ", texto).strip()


def _texto_del_mensaje(mensaje: dict) -> str:
    """Reconstruye el texto ignorando fragmentos que sean emotes de Twitch."""
    fragmentos = mensaje.get("fragments") or []

    if fragmentos:
        partes: list[str] = []

        for fragmento in fragmentos:
            if fragmento.get("emoticon") is None:
                partes.append(str(fragmento.get("text") or ""))

        texto = "".join(partes)
    else:
        texto = str(mensaje.get("body") or "")

    return _normalizar_texto(texto)


def _badges(mensaje: dict) -> list[str]:
    """Devuelve los identificadores de badges del usuario."""
    resultado: list[str] = []

    for badge in mensaje.get("user_badges") or []:
        identificador = badge.get("_id")
        if identificador:
            resultado.append(str(identificador))

    return resultado


def _es_bot(comentario: dict) -> bool:
    """Detecta cuentas automatizadas mediante badge y nombre conocido."""
    mensaje = comentario.get("message") or {}
    badges = set(_badges(mensaje))

    comentarista = comentario.get("commenter") or {}
    nombre = str(
        comentarista.get("name")
        or comentarista.get("display_name")
        or ""
    ).casefold()

    return "bot-badge" in badges or nombre in _BOTS_CONOCIDOS


def _texto_util(texto: str) -> bool:
    """Conserva únicamente mensajes con contenido lingüístico mínimo."""
    if not texto:
        return False

    if _RE_COMANDO.match(texto):
        return False

    # Un enlace por sí solo no aporta texto para el análisis.
    texto_sin_urls = _RE_URL.sub(" ", texto)

    # Exige al menos tres caracteres alfabéticos.
    return sum(caracter.isalpha() for caracter in texto_sin_urls) >= 3


def _en_ventana(fecha: str, inicio: str, fin: str) -> bool:
    """Comprueba la fecha ISO contra la ventana configurada."""
    if not fecha:
        return False

    dia = fecha[:10]

    if inicio and dia < inicio:
        return False

    if fin and dia > fin:
        return False

    return True


def _url_vod(video_id: str, segundos: int) -> str:
    """Genera la URL del VOD posicionada en el instante del mensaje."""
    segundos = max(0, int(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)

    return (
        f"https://www.twitch.tv/videos/{video_id}"
        f"?t={horas}h{minutos}m{segundos}s"
    )


class ExtractorTwitch(ExtractorBase):
    """Procesa chats históricos de Twitch descargados previamente."""

    red = "twitch"
    patron_archivos = "twitch_raw_*.json"

    def archivos(self) -> list[Path]:
        """Lista los chats disponibles de forma determinista."""
        return sorted(DIR_DATA.glob(self.patron_archivos))

    def extraer(self) -> Iterator[Registro]:
        archivos = self.archivos()

        if not archivos:
            raise FileNotFoundError(
                f"No existen archivos {self.patron_archivos!r} "
                f"dentro de {DIR_DATA}"
            )

        total = 0

        # Evita spam inmediato: mismo usuario + mismo texto en 30 segundos.
        ultimo_mensaje: dict[tuple[str, str], int] = {}

        for ruta in archivos:
            if total >= self.config.max_total_por_red:
                break

            with ruta.open(encoding="utf-8") as archivo:
                datos = json.load(archivo)

            video = datos.get("video") or {}
            streamer = datos.get("streamer") or {}

            video_id = str(video.get("id") or ruta.stem.removeprefix("twitch_raw_"))
            titulo = str(video.get("title") or video_id)
            canal = str(
                streamer.get("login")
                or streamer.get("name")
                or streamer.get("id")
                or ""
            )

            criterio = f"{canal}: {titulo}" if canal else titulo

            for comentario in datos.get("comments") or []:
                if total >= self.config.max_total_por_red:
                    break

                identificador = str(comentario.get("_id") or "").strip()
                fecha = str(comentario.get("created_at") or "").strip()

                if not identificador:
                    continue

                if not _en_ventana(
                    fecha,
                    self.config.inicio,
                    self.config.fin,
                ):
                    continue

                if _es_bot(comentario):
                    continue

                mensaje = comentario.get("message") or {}
                texto = _texto_del_mensaje(mensaje)

                if not _texto_util(texto):
                    continue

                comentarista = comentario.get("commenter") or {}
                autor_id = str(comentarista.get("_id") or "")
                autor = str(
                    comentarista.get("display_name")
                    or comentarista.get("name")
                    or autor_id
                    or ""
                )

                offset = int(comentario.get("content_offset_seconds") or 0)

                clave_spam = (autor_id, texto.casefold())
                offset_anterior = ultimo_mensaje.get(clave_spam)

                if (
                    offset_anterior is not None
                    and 0 <= offset - offset_anterior <= 30
                ):
                    continue

                ultimo_mensaje[clave_spam] = offset

                badges = _badges(mensaje)
                emotes = mensaje.get("emoticons") or []

                yield Registro(
                    id=identificador,
                    red=self.red,
                    estrategia="amplia",
                    criterio_busqueda=criterio,
                    texto=texto,
                    idioma=None,
                    autor=autor or None,
                    fecha_publicacion=fecha or None,
                    url=_url_vod(video_id, offset),
                    metricas={
                        "video_id": video_id,
                        "canal_id": str(
                            comentario.get("channel_id")
                            or streamer.get("id")
                            or ""
                        ),
                        "streamer": canal,
                        "titulo_video": titulo,
                        "segundo_video": offset,
                        "visualizaciones_video": video.get("viewCount"),
                        "categoria": video.get("game"),
                        "bits_gastados": mensaje.get("bits_spent", 0),
                        "badges": badges,
                        "cantidad_emotes": len(emotes),
                        "archivo_origen": ruta.name,
                    },
                )

                total += 1
