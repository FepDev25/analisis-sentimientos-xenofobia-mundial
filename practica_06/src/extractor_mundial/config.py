# Carga de la configuración de búsqueda (`config/busqueda.toml` + `lexico.txt`)

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Raíz del proyecto: .../practica_06/
RAIZ = Path(__file__).resolve().parents[2]
DIR_CONFIG = RAIZ / "config"
DIR_DATA = RAIZ / "data"

# Una búsqueda concreta, con su etiqueta de origen.
@dataclass
class Criterio:
    query: str
    estrategia: str  # "amplia" | "dirigida"

# Configuración de búsqueda ya cargada y lista para usar
@dataclass
class Config:
    inicio: str
    fin: str
    hashtags_torneo: list[str]
    hashtags_partido: list[str]
    selecciones: list[str]
    jugadores: list[str]
    canales_youtube: list[str]
    videos_youtube: list[str]
    playlists_youtube: list[str]
    subreddits: list[str]
    idiomas_bluesky: list[str]
    max_criterios_dirigida: int   # tope del cruce evento × léxico (son miles)
    lexico: list[str]
    max_por_criterio: int
    max_total_por_red: int
    max_videos: int          # videos por corrida (tandas); evita throttle
    pausa_youtube: float     # segundos de pausa entre videos

    # Términos "evento" combinados
    @property
    def terminos_evento(self) -> list[str]:
        return [
            *self.hashtags_torneo,
            *self.hashtags_partido,
            *self.selecciones,
            *self.jugadores,
        ]

    # Criterios de búsqueda amplia para redes con búsqueda por texto libre.
    def criterios_amplia(self) -> list[Criterio]:
        """baseline de volumen."""
        return [Criterio(q, "amplia") for q in self.terminos_evento]

    # Base del cruce dirigido: SIN hashtags, a propósito.
    # Medido el 13-jul-2026 en Bluesky: `#WorldCup2026 monos` devuelve 0 resultados,
    # mientras que `Brasil monos` sí trae. Tiene sentido — nadie escribe un insulto
    # racista y encima le pone el hashtag oficial del torneo. Cruzar hashtags con el
    # léxico solo quema presupuesto de consultas.
    @property
    def terminos_dirigida(self) -> list[str]:
        return [*self.selecciones, *self.jugadores]

    def criterios_dirigida(self) -> list[Criterio]:
        """subconjunto denso (evento + término peyorativo).

        El producto cartesiano completo son miles de consultas (~15 eventos × ~100
        términos), inviable en una corrida. Se INTERCALA por término del léxico en
        vez de agotar evento por evento: así, al cortar en `max_criterios_dirigida`,
        el recorte sigue cubriendo TODOS los eventos y no solo los primeros.
        """
        criterios = []
        for termino in self.lexico:
            for evento in self.terminos_dirigida:
                criterios.append(Criterio(f"{evento} {termino}", "dirigida"))
        return criterios[: self.max_criterios_dirigida]

    def todos_los_criterios(self) -> list[Criterio]:
        return self.criterios_amplia() + self.criterios_dirigida()

# Lee el léxico ignorando comentarios y líneas vacías. Soporta comentarios de
# línea (# ...) y también INLINE (`termino  # nota`): se corta en el primer '#',
def _cargar_lexico(ruta: Path) -> list[str]:
    if not ruta.exists():
        return []
    entradas = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea:
            entradas.append(linea)
    return entradas


def cargar_config(
    ruta_toml: Path | None = None, ruta_lexico: Path | None = None
) -> Config:
    ruta_toml = ruta_toml or (DIR_CONFIG / "busqueda.toml")
    ruta_lexico = ruta_lexico or (DIR_CONFIG / "lexico.txt")

    with ruta_toml.open("rb") as f:
        d = tomllib.load(f)

    v = d.get("ventana", {})
    yt = d.get("youtube", {})
    rd = d.get("reddit", {})
    bs = d.get("bluesky", {})
    lim = d.get("limites", {})

    return Config(
        inicio=v.get("inicio", ""),
        fin=v.get("fin", ""),
        hashtags_torneo=v.get("hashtags_torneo", []),
        hashtags_partido=v.get("hashtags_partido", []),
        selecciones=v.get("selecciones", []),
        jugadores=v.get("jugadores", []),
        canales_youtube=yt.get("canales", []),
        videos_youtube=yt.get("videos", []),
        playlists_youtube=yt.get("playlists", []),
        subreddits=rd.get("subreddits", []),
        idiomas_bluesky=bs.get("idiomas", []),
        max_criterios_dirigida=bs.get("max_criterios_dirigida", 120),
        lexico=_cargar_lexico(ruta_lexico),
        max_por_criterio=lim.get("max_por_criterio", 200),
        max_total_por_red=lim.get("max_total_por_red", 2000),
        max_videos=lim.get("max_videos", 30),
        pausa_youtube=yt.get("pausa_videos", 2.0),
    )
