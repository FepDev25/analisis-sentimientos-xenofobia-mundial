# Configuracion por variables de entorno.

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_DATA = RAIZ / "data"

RUTA_BD = Path(os.getenv("PLATAFORMA_BD", str(DIR_DATA / "plataforma.db")))

# TikTok queda fuera: su captura es semi-manual, no sirve disparada por un query.
REDES_EN_VIVO = ("bluesky", "x", "youtube", "tumblr")

# Limites de la busqueda EN VIVO, agresivos a proposito: tiene que responder en
# decenas de segundos, no en la media hora de una corrida batch. X marca el techo
# (~17 s por criterio, medido en P6).
MAX_POR_RED = int(os.getenv("PLATAFORMA_MAX_POR_RED", "40"))
MAX_POR_CRITERIO = int(os.getenv("PLATAFORMA_MAX_POR_CRITERIO", "20"))

# Cada worker carga ~4 GB de pysentimiento y queda residente mientras viva el
# servidor (no solo durante una corrida, como en P7). De ahi que el defecto sea
# mas bajo que el techo de 6 que se midio alli.
N_WORKERS = int(os.getenv("PLATAFORMA_N_WORKERS", "2"))
TAMANO_BLOQUE = int(os.getenv("PLATAFORMA_TAMANO_BLOQUE", "32"))

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
