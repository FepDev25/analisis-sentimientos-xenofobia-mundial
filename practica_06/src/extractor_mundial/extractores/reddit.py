"""Extractor de Reddit — comentarios por subreddit (RESPALDO de X)"""

from __future__ import annotations

from collections.abc import Iterator

from ..contrato import Registro
from .base import ExtractorBase


class ExtractorReddit(ExtractorBase):
    red = "reddit"

    def extraer(self) -> Iterator[Registro]:
        raise NotImplementedError("Extractor de Reddit (respaldo) pendiente.")
        yield
