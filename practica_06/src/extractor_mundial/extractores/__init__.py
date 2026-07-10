"""Registro de extractores disponibles."""

from .base import ExtractorBase
from .reddit import ExtractorReddit
from .tiktok import ExtractorTikTok
from .x import ExtractorX
from .youtube import ExtractorYouTube

# Extractores que se lanzan en paralelo por defecto (Reddit es respaldo de X).
EXTRACTORES_POR_DEFECTO = (ExtractorX, ExtractorTikTok, ExtractorYouTube)

__all__ = [
    "ExtractorBase",
    "ExtractorX",
    "ExtractorTikTok",
    "ExtractorYouTube",
    "ExtractorReddit",
    "EXTRACTORES_POR_DEFECTO",
]
