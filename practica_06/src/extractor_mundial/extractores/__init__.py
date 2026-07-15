"""Registro de extractores disponibles."""

from .base import ExtractorBase
from .bluesky import ExtractorBluesky
from .reddit import ExtractorReddit
from .tiktok import ExtractorTikTok
from .x import ExtractorX
from .youtube import ExtractorYouTube

# TODOS los extractores registrados. De aquí toma `--redes` sus opciones, así se puede
# componer cualquier trío para la corrida de evidencia (p. ej. youtube + x + bluesky).
EXTRACTORES = (
    ExtractorYouTube,
    ExtractorBluesky,
    ExtractorTikTok,
    ExtractorX,
    ExtractorReddit,
)

# Las 3 fuentes que se lanzan en paralelo por defecto (una por integrante del grupo).
# Bluesky entró en lugar de Reddit (403 al acceso programático desde jul-2026).
# X queda disponible (seleccionable con --redes) pero fuera del trío por defecto:
# API de pago + anti-bot agresivo, así que se usa como fuente opcional-rica.
EXTRACTORES_POR_DEFECTO = (ExtractorYouTube, ExtractorBluesky, ExtractorTikTok)

__all__ = [
    "ExtractorBase",
    "ExtractorX",
    "ExtractorTikTok",
    "ExtractorYouTube",
    "ExtractorBluesky",
    "ExtractorReddit",
    "EXTRACTORES",
    "EXTRACTORES_POR_DEFECTO",
]
