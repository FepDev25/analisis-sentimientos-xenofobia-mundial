"""Registro de extractores disponibles."""

from .base import ExtractorBase
from .bluesky import ExtractorBluesky
from .reddit import ExtractorReddit
from .tiktok import ExtractorTikTok
from .x import ExtractorX
from .youtube import ExtractorYouTube

# Las 3 fuentes que se lanzan en paralelo (una por integrante del grupo).
# Bluesky entró en lugar de Reddit (403 al acceso programático desde jul-2026).
# X queda disponible pero fuera del trío: API de pago + anti-bot agresivo.
EXTRACTORES_POR_DEFECTO = (ExtractorYouTube, ExtractorBluesky, ExtractorTikTok)

__all__ = [
    "ExtractorBase",
    "ExtractorX",
    "ExtractorTikTok",
    "ExtractorYouTube",
    "ExtractorBluesky",
    "ExtractorReddit",
    "EXTRACTORES_POR_DEFECTO",
]
