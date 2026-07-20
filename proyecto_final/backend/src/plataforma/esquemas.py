# Modelos de la API. Son el contrato con el frontend: FastAPI los publica en
# /docs (OpenAPI), asi que el equipo de frontend trabaja contra esto.

from __future__ import annotations

from pydantic import BaseModel, Field

from . import config


class BusquedaNueva(BaseModel):
    query: str = Field(min_length=2, max_length=200, examples=["Brasil monos"])
    redes: list[str] | None = Field(
        default=None,
        description=f"Subconjunto de {list(config.REDES_EN_VIVO)}. None = todas.",
    )


class Busqueda(BaseModel):
    id: int
    query: str
    estado: str
    creada_en: str
    terminada_en: str | None = None


class Registro(BaseModel):
    id: int
    red: str
    id_externo: str
    estrategia: str
    texto: str
    idioma: str | None = None
    autor: str | None = None
    fecha_publicacion: str | None = None
    url: str | None = None
    metricas: dict = {}
    sentimiento: str | None = None
    sent_score: float | None = None
    odio: bool | None = None
    odio_score: float | None = None


# Espeja `orquestador.ResultadoRed`. `duracion_s` por red es la evidencia de que
# las redes corren en paralelo: el total es el maximo, no la suma.
class ResultadoRed(BaseModel):
    red: str
    total: int
    error: str | None = None
    duracion_s: float | None = None


class Resumen(BaseModel):
    busqueda_id: int
    global_: dict[str, int] = Field(alias="global")
    por_red: dict[str, dict[str, int]]
    odio_por_red: dict[str, int]
    redes: list[ResultadoRed]

    model_config = {"populate_by_name": True}
