"""Extractor de Bluesky — posts por query (búsqueda global)

Sustituye a Reddit, descartado el 13-jul-2026 tras confirmar que responde 403 al
acceso programático desde su propia CDN y que su registro de apps ya no emite
credenciales. Bluesky corre sobre el protocolo abierto AT: la API es pública y
documentada, y la cuenta + app password se obtienen al instante, sin aprobación.

Mecanismo: HTTP directo contra dos endpoints XRPC (sin librería intermedia, para
no depender de un wrapper que se rompa y para que el protocolo quede a la vista):
  - `com.atproto.server.createSession` → canjea handle + app password por un JWT.
  - `app.bsky.feed.searchPosts`        → búsqueda global de texto, paginada.

Estrategia de 2 capas (la misma que YouTube, para que las redes sean comparables):
se lanzan las consultas `amplia` (solo evento) y `dirigida` (evento × léxico), y
además CUALQUIER post cuyo texto contenga un término del léxico se re-marca como
`dirigida` aunque haya venido de una búsqueda amplia.

A diferencia de YouTube, Bluesky sí declara el idioma de cada post (`record.langs`),
así que el campo `idioma` del contrato se puede llenar.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator

import requests

from ..config import Criterio, DIR_CONFIG
from ..contrato import Registro
from ..lexico import cargar as cargar_lexico
from .base import ExtractorBase

API = "https://bsky.social/xrpc"


class FaltanCredenciales(RuntimeError):
    """El .env no tiene las credenciales de Bluesky."""


class ExtractorBluesky(ExtractorBase):
    red = "bluesky"

    # Tope de la API por página.
    _POR_PAGINA = 100
    # Esperas (s) ante un 429 (rate limit) antes de reintentar la misma página.
    _BACKOFF = (5, 15, 40)
    # Pausa entre consultas: la API tolera bastante, pero no hay por qué abusar.
    _PAUSA = 0.3
    _TIMEOUT = 20

    def __init__(self, config) -> None:
        super().__init__(config)
        self._lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")
        self._idiomas = set(config.idiomas_bluesky)
        self._sesion = requests.Session()
        self._jwt: str | None = None

    # ------------------------------------------------------------------ sesión
    def _autenticar(self) -> None:
        """Canjea handle + app password por un JWT (dura ~2h; sobra para la corrida)."""
        handle = os.environ.get("BLUESKY_HANDLE", "").strip()
        password = os.environ.get("BLUESKY_APP_PASSWORD", "").strip()
        if not handle or not password:
            raise FaltanCredenciales(
                "faltan BLUESKY_HANDLE / BLUESKY_APP_PASSWORD. "
                "Copia .env.example a .env, rellénalo y ejecuta con "
                "`uv run --env-file .env extractor-mundial`"
            )
        r = self._sesion.post(
            f"{API}/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
            timeout=self._TIMEOUT,
        )
        if r.status_code == 401:
            raise FaltanCredenciales(
                "Bluesky rechazó las credenciales (401). Revisa el handle y que la "
                "clave sea un APP PASSWORD (Settings > App Passwords), no la de la cuenta."
            )
        r.raise_for_status()
        self._jwt = r.json()["accessJwt"]

    @property
    def _cabeceras(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._jwt}"}

    # --------------------------------------------------------------- búsqueda
    def _pagina(self, query: str, cursor: str | None) -> dict:
        """Una página de resultados, con reintentos ante rate limit (429)."""
        params = {"q": query, "limit": self._POR_PAGINA}
        if cursor:
            params["cursor"] = cursor

        for espera in (0, *self._BACKOFF):
            if espera:
                print(f"[bluesky] rate limit; espero {espera}s", file=sys.stderr)
                time.sleep(espera)
            r = self._sesion.get(
                f"{API}/app.bsky.feed.searchPosts",
                params=params,
                headers=self._cabeceras,
                timeout=self._TIMEOUT,
            )
            if r.status_code == 429:
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("rate limit sostenido de Bluesky tras agotar los reintentos")

    def _buscar(self, query: str, limite: int) -> Iterator[dict]:
        """Itera los posts crudos de una consulta, paginando con el cursor."""
        cursor: str | None = None
        emitidos = 0
        while emitidos < limite:
            datos = self._pagina(query, cursor)
            posts = datos.get("posts") or []
            if not posts:
                return  # la consulta se agotó
            for post in posts:
                if emitidos >= limite:
                    return
                yield post
                emitidos += 1
            cursor = datos.get("cursor")
            if not cursor:
                return  # no hay más páginas
            time.sleep(self._PAUSA)

    # ------------------------------------------------------- mapeo al contrato
    def _a_registro(self, post: dict, criterio: Criterio) -> Registro | None:
        """Mapea un post de Bluesky al contrato común. None si hay que descartarlo."""
        record = post.get("record") or {}
        texto = (record.get("text") or "").strip()
        if not texto:
            return None

        # Bluesky declara el idioma del post. Se filtra localmente (mismo patrón que
        # el resto de redes): si no declara idioma, se conserva por si acaso.
        langs = record.get("langs") or []
        idioma = langs[0] if langs else None
        if self._idiomas and idioma and idioma not in self._idiomas:
            return None

        # Una búsqueda 'amplia' puede traer igualmente un post con carga xenófoba:
        # se re-marca como 'dirigida' (misma regla que YouTube).
        con_lexico = self._lexico.es_dirigida(texto)
        estrategia = "dirigida" if con_lexico else criterio.estrategia

        autor = (post.get("author") or {}).get("handle")
        # El `uri` es at://<did>/app.bsky.feed.post/<rkey>; el rkey arma el permalink.
        uri = post["uri"]
        rkey = uri.rsplit("/", 1)[-1]

        return Registro(
            id=uri,  # único y estable en toda la red
            red=self.red,
            estrategia=estrategia,
            criterio_busqueda=criterio.query,
            texto=texto,
            idioma=idioma,
            autor=autor,
            fecha_publicacion=record.get("createdAt"),  # ya viene en ISO 8601
            url=f"https://bsky.app/profile/{autor}/post/{rkey}" if autor else None,
            metricas={
                "likes": post.get("likeCount"),
                "reposts": post.get("repostCount"),
                "respuestas": post.get("replyCount"),
                "citas": post.get("quoteCount"),
            },
        )

    # ------------------------------------------------ interfaz del orquestador
    def extraer(self) -> Iterator[Registro]:
        self._autenticar()

        total = 0
        for criterio in self.config.todos_los_criterios():
            if total >= self.config.max_total_por_red:
                break
            restante = self.config.max_total_por_red - total
            limite = min(self.config.max_por_criterio, restante)
            try:
                for post in self._buscar(criterio.query, limite):
                    registro = self._a_registro(post, criterio)
                    if registro is None:
                        continue
                    yield registro
                    total += 1
            except requests.RequestException as e:
                # Una consulta caída no debe tumbar las demás: se anota y se sigue.
                print(
                    f"[bluesky] consulta {criterio.query!r} omitida "
                    f"({type(e).__name__}: {e})",
                    file=sys.stderr,
                )
                continue
