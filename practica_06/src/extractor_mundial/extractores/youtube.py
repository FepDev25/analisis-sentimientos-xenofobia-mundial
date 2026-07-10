"""Extractor de YouTube — comentarios de videos de resúmenes de goles"""

from __future__ import annotations

from collections.abc import Iterator

from ..contrato import Registro
from .base import ExtractorBase


class ExtractorYouTube(ExtractorBase):
    red = "youtube"

    def extraer(self) -> Iterator[Registro]:
        raise NotImplementedError(
            "Extractor de YouTube pendiente (siguiente paso: API oficial Data v3)."
        )
        yield  # marca la función como generador
