# Interfaz común a todos los extractores.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..config import Config
from ..contrato import Registro


class ExtractorBase(ABC):
    #: Nombre de la red; debe ser uno de contrato.REDES.
    red: str = ""

    def __init__(self, config: Config) -> None:
        self.config = config

    # Produce los registros de esta red según la configuración.
    @abstractmethod
    def extraer(self) -> Iterator[Registro]:
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Extractor {self.red}>"
