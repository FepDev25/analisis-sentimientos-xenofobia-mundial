"""Extractor de TikTok — comentarios/posts por hashtag (búsqueda global)"""

from __future__ import annotations

from collections.abc import Iterator

from ..contrato import Registro
from .base import ExtractorBase


class ExtractorTikTok(ExtractorBase):
    red = "tiktok"

    def extraer(self) -> Iterator[Registro]:
        raise NotImplementedError("Extractor de TikTok pendiente.")
        yield
