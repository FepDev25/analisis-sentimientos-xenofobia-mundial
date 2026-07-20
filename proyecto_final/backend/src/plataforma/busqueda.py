# Orquestacion de una busqueda: query -> extractores concurrentes -> BD -> clasificacion.
#
# Reutiliza el orquestador de P6 sin tocarlo: sus extractores son generadores y
# `ejecutar()` recibe el consumidor, asi que basta pasarle uno que escriba en la BD.

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from extractor_mundial import orquestador
from extractor_mundial.config import DIR_DATA, Config, Criterio, cargar_config
from extractor_mundial.extractores.base import ExtractorBase
from extractor_mundial.extractores.bluesky import ExtractorBluesky
from extractor_mundial.extractores.mastodon import ExtractorMastodon
from extractor_mundial.extractores.x import ExtractorX
from extractor_mundial.extractores.youtube_api import ExtractorYouTubeApi

from . import bd, config, sentimiento


# El query del usuario reemplaza al cruce evento x lexico del TOML. El resto de la
# config (lexico para el marcado, sesion de X, idiomas) se sigue leyendo de P6.
@dataclass
class ConfigBusqueda(Config):
    query: str = ""

    def todos_los_criterios(self) -> list[Criterio]:
        # `amplia` es el punto de partida: los extractores promueven a `dirigida`
        # via `_marcar()` si el texto trae un termino del lexico.
        return [Criterio(self.query, "amplia")]


# Extractor que declara una red aun no migrada al modo query. El orquestador
# captura NotImplementedError y lo reporta como "pendiente: ..." sin tumbar la
# busqueda ni las demas redes.
class _Pendiente(ExtractorBase):
    def __init__(self, cfg: Config, red: str, motivo: str) -> None:
        super().__init__(cfg)
        self.red = red
        self._motivo = motivo

    def extraer(self):
        raise NotImplementedError(self._motivo)


_PENDIENTES = {
    "tumblr": "Tumblr aun itera las etiquetas fijas del TOML. Falta mapear el "
              "query del usuario a un tag.",
}


def _config_para(query: str) -> ConfigBusqueda:
    base = cargar_config()
    cfg = ConfigBusqueda(**asdict(base), query=query)
    cfg.max_por_criterio = config.MAX_POR_CRITERIO
    cfg.max_total_por_red = config.MAX_POR_RED
    # La sesion de X vive en practica_06/data; sin ruta absoluta el extractor la
    # buscaria relativa al cwd del backend (FaltanSesion).
    cfg.x_sesion = str(DIR_DATA / "x_session.json")
    return cfg


def _extractores(cfg: ConfigBusqueda, redes: list[str]) -> list[ExtractorBase]:
    clases = {
        "bluesky": ExtractorBluesky,
        "x": ExtractorX,
        "youtube": ExtractorYouTubeApi,
        "mastodon": ExtractorMastodon,
    }
    salida: list[ExtractorBase] = []
    for red in redes:
        if red in clases:
            salida.append(clases[red](cfg))
        elif red in _PENDIENTES:
            salida.append(_Pendiente(cfg, red, _PENDIENTES[red]))
        else:
            raise ValueError(f"red no soportada en vivo: {red!r}")
    return salida


# Corre la busqueda completa. Bloquea hasta terminar (~decenas de segundos), asi
# que se lanza en segundo plano desde la API.
def ejecutar(
    con: sqlite3.Connection, busqueda_id: int, query: str, redes: list[str] | None = None
) -> None:
    redes = list(redes or config.REDES_EN_VIVO)
    cfg = _config_para(query)

    try:
        resultados = orquestador.ejecutar(
            _extractores(cfg, redes),
            lambda registro: bd.guardar_registro(con, busqueda_id, registro),
        )
        con.commit()  # el consumidor no confirma por registro

        for r in resultados:
            bd.guardar_resultado_red(
                con, busqueda_id, r.red, r.total, r.error, r.duracion_s
            )

        pendientes = bd.registros_sin_clasificar(con, busqueda_id)
        bd.guardar_sentimientos(con, sentimiento.clasificar(pendientes))
        bd.terminar_busqueda(con, busqueda_id)
    except Exception:
        bd.terminar_busqueda(con, busqueda_id, "error")
        raise
