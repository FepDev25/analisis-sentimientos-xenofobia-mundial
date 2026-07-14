# Contrato de datos común a los 3 extractores

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# Valores permitidos.
# `reddit` se conserva por trazabilidad histórica: se descartó como fuente en
# jul-2026 al confirmar que su API responde 403 al acceso programático.
REDES = ("x", "tiktok", "youtube", "reddit", "bluesky", "tumblr", "twitch")
ESTRATEGIAS = ("amplia", "dirigida")

# Orden de columnas para el CSV.
CAMPOS = (
    "id",
    "red",
    "estrategia",
    "criterio_busqueda",
    "texto",
    "idioma",
    "autor",
    "fecha_publicacion",
    "url",
    "metricas",
    "fecha_extraccion",
)

# Timestamp actual en ISO 8601 (UTC)
def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Un comentario/post extraído. Mismo esquema para todas las redes
@dataclass
class Registro:
    id: str
    red: str
    estrategia: str
    criterio_busqueda: str
    texto: str
    idioma: str | None = None
    autor: str | None = None
    fecha_publicacion: str | None = None
    url: str | None = None
    metricas: dict = field(default_factory=dict)
    fecha_extraccion: str = field(default_factory=_ahora_iso)

    def __post_init__(self) -> None:
        # validación de esquema
        if self.red not in REDES:
            raise ValueError(f"red inválida: {self.red!r} (permitidas: {REDES})")
        if self.estrategia not in ESTRATEGIAS:
            raise ValueError(
                f"estrategia inválida: {self.estrategia!r} (permitidas: {ESTRATEGIAS})"
            )
        if not self.id:
            raise ValueError("el registro necesita un 'id' no vacío para deduplicar")
        if not self.texto or not self.texto.strip():
            raise ValueError("el registro necesita 'texto' no vacío (dato central)")

    # Clave de unicidad global: (red, id)
    @property
    def clave(self) -> tuple[str, str]:
        return (self.red, self.id)

    # Dict con `metricas` como objeto anidado (para JSON)
    def a_dict(self) -> dict:
        return asdict(self)

    # Dict con `metricas` serializada a JSON string (para CSV)
    def a_fila_csv(self) -> dict:
        d = asdict(self)
        d["metricas"] = json.dumps(self.metricas, ensure_ascii=False)
        return d
