"""Extractor de Mastodon — posts públicos por hashtag (fediverso)

Cuarta red en vivo. Se eligió tras descartar Reddit: en 2026 Reddit cerró el
registro self-service de la Data API (ahora requiere aprobación por ticket), y
Mastodon ofrece lo mismo que Bluesky sin fricción de credenciales.

Mecanismo: HTTP directo contra la API pública del protocolo Mastodon (sin token,
igual que se lee un timeline público en la web):
  - `GET /api/v1/timelines/tag/:tag` → posts públicos recientes con ese hashtag.

Por qué hashtag y no búsqueda de texto: el full-text de Mastodon es opt-in por
usuario y exige token + instancia con ElasticSearch, así que su recall es bajo y
poco fiable. El timeline por hashtag es público y estable. El query del usuario se
mapea a un hashtag (`World Cup 2026` → `worldcup2026`), que actúa como capa
`amplia`; el marcado por léxico promueve a `dirigida` la aguja xenófoba.

A diferencia de Bluesky, el contenido llega en HTML (`<p>`, `<a>`), así que se
limpia a texto plano antes de mapear.
"""

from __future__ import annotations

import html
import re
import sys
import time
from collections.abc import Iterator

import requests

from ..config import Criterio, DIR_CONFIG
from ..contrato import Registro
from ..lexico import Lexico, cargar as cargar_lexico
from .base import ExtractorBase

INSTANCIA_POR_DEFECTO = "mastodon.social"

_RE_TAG = re.compile(r"<[^>]+>")
# Caracteres válidos de un hashtag: alfanuméricos (con acentos/ñ). Todo lo demás
# —incluidos los espacios— se elimina, uniendo las palabras del query en un tag.
_RE_NO_TAG = re.compile(r"[^0-9a-záéíóúüñ]+")


def _limpiar_html(bruto: str) -> str:
    """HTML de un post de Mastodon → texto plano."""
    sin_tags = _RE_TAG.sub(" ", bruto)
    return re.sub(r"\s+", " ", html.unescape(sin_tags)).strip()


def _a_hashtag(query: str) -> str:
    """`World Cup 2026` → `worldcup2026`. Une las palabras del query en un tag."""
    return _RE_NO_TAG.sub("", query.lower())


# Mapea un status de Mastodon al contrato. None si hay que descartarlo (p. ej. un
# boost, que llega sin contenido). Función pura (sin red) para testear el mapeo.
def _a_registro(status: dict, criterio: Criterio, lexico: Lexico) -> Registro | None:
    texto = _limpiar_html(status.get("content") or "")
    if not texto:
        return None

    estrategia = "dirigida" if lexico.es_dirigida(texto) else criterio.estrategia
    cuenta = status.get("account") or {}

    return Registro(
        id=status["uri"],  # global y estable en todo el fediverso
        red="mastodon",
        estrategia=estrategia,
        criterio_busqueda=criterio.query,
        texto=texto,
        idioma=status.get("language"),
        autor=cuenta.get("acct"),
        fecha_publicacion=status.get("created_at"),  # ya viene en ISO 8601
        url=status.get("url"),
        metricas={
            "likes": status.get("favourites_count"),
            "reposts": status.get("reblogs_count"),
            "respuestas": status.get("replies_count"),
        },
    )


class ExtractorMastodon(ExtractorBase):
    red = "mastodon"

    # Tope de la API por página de timeline.
    _POR_PAGINA = 40
    # Esperas (s) ante un 429 (rate limit) antes de reintentar la misma página.
    _BACKOFF = (5, 15, 40)
    _PAUSA = 0.3
    _TIMEOUT = 20

    def __init__(self, config) -> None:
        super().__init__(config)
        self._lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")
        self._instancia = getattr(config, "mastodon_instancia", INSTANCIA_POR_DEFECTO)
        self._sesion = requests.Session()

    def _pagina(self, tag: str, limite: int, max_id: str | None) -> list[dict]:
        """Una página del timeline del hashtag, con reintentos ante rate limit (429)."""
        params = {"limit": min(self._POR_PAGINA, limite)}
        if max_id:
            params["max_id"] = max_id
        url = f"https://{self._instancia}/api/v1/timelines/tag/{tag}"

        for espera in (0, *self._BACKOFF):
            if espera:
                print(f"[mastodon] rate limit; espero {espera}s", file=sys.stderr)
                time.sleep(espera)
            r = self._sesion.get(url, params=params, timeout=self._TIMEOUT)
            if r.status_code == 429:
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("rate limit sostenido de Mastodon tras agotar los reintentos")

    def _timeline_tag(self, tag: str, limite: int) -> Iterator[dict]:
        """Itera los status crudos del hashtag, paginando con max_id (más antiguos)."""
        max_id: str | None = None
        emitidos = 0
        while emitidos < limite:
            statuses = self._pagina(tag, limite - emitidos, max_id)
            if not statuses:
                return  # el hashtag se agotó
            for status in statuses:
                if emitidos >= limite:
                    return
                yield status
                emitidos += 1
            max_id = statuses[-1]["id"]  # newest-first → el último es el más viejo
            time.sleep(self._PAUSA)

    # ------------------------------------------------ interfaz del orquestador
    def extraer(self) -> Iterator[Registro]:
        total = 0
        for criterio in self.config.todos_los_criterios():
            if total >= self.config.max_total_por_red:
                break
            tag = _a_hashtag(criterio.query)
            if not tag:
                continue
            restante = self.config.max_total_por_red - total
            limite = min(self.config.max_por_criterio, restante)
            try:
                for status in self._timeline_tag(tag, limite):
                    registro = _a_registro(status, criterio, self._lexico)
                    if registro is None:
                        continue
                    yield registro
                    total += 1
            except requests.RequestException as e:
                # Una consulta caída no debe tumbar las demás: se anota y se sigue.
                print(
                    f"[mastodon] hashtag #{tag} omitido ({type(e).__name__}: {e})",
                    file=sys.stderr,
                )
                continue
