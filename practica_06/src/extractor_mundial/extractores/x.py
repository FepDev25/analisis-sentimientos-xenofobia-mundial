"""Extractor de X — posts por query (búsqueda global)"""

from __future__ import annotations

from collections.abc import Iterator

from ..contrato import Registro
from .base import ExtractorBase


class ExtractorX(ExtractorBase):
    red = "x"

    def extraer(self) -> Iterator[Registro]:
        raise NotImplementedError("Extractor de X pendiente.")
        yield
