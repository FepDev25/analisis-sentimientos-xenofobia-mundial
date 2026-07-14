"""Extractor de X (Twitter) con Playwright — posts por query (búsqueda global)

X exige sesión iniciada para ver la búsqueda. Se usa un navegador Chromium real
(Playwright) con una sesión reutilizada (`storage_state.json`), capturada una vez
con `scripts/recoleccion_x.py --login`. Se raspa el DOM anclando en `data-testid`
(no en clases CSS, que cambian) y se mapea al contrato común.
"""

from __future__ import annotations

import re
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote

from ..config import Criterio
from ..contrato import Registro
from .base import ExtractorBase

_RE_STATUS = re.compile(r"/status/(\d+)")
_RE_HANDLE = re.compile(r"@\w+")


class FaltanSesion(RuntimeError):
    """No existe el storage_state; hay que capturarlo con --login."""


def _num_de_aria(etiqueta: str | None) -> int | None:
    """Primer número de un aria-label ('100 Likes. Like' -> 100)."""
    if not etiqueta:
        return None
    m = re.search(r"\d[\d.,]*", etiqueta)
    if not m:
        return None
    return int(re.sub(r"\D", "", m.group()))


def _marcar(texto: str, estrategia_criterio: str, lexico: list[str]) -> str:
    """Marcado de 2 capas: 'dirigida' si hay término del léxico; si no, hereda."""
    bajo = texto.lower()
    if any(t in bajo for t in lexico):
        return "dirigida"
    return estrategia_criterio


def _parsear_tweet(articulo, criterio: Criterio, lexico: list[str]) -> Registro | None:
    """Mapea un nodo article[data-testid=tweet] al contrato. None si es inservible.

    `articulo` es un playwright.sync_api.Locator (se anota en string para no importar
    Playwright a nivel de módulo).
    """
    textos = articulo.locator('[data-testid="tweetText"]')
    if textos.count() == 0:
        return None
    texto = textos.first.inner_text().strip()
    if not texto:
        return None

    enlace = articulo.locator("a:has(time)").first
    href = enlace.get_attribute("href") or ""
    m = _RE_STATUS.search(href)
    if not m:
        return None
    tid = m.group(1)

    idioma = textos.first.get_attribute("lang")
    nombre = articulo.locator('[data-testid="User-Name"]').first.inner_text()
    mh = _RE_HANDLE.search(nombre)
    autor = mh.group() if mh else None
    fecha = articulo.locator("time").first.get_attribute("datetime")

    def _metrica(testid: str) -> int | None:
        loc = articulo.locator(f'[data-testid="{testid}"]')
        if loc.count() == 0:
            return None
        return _num_de_aria(loc.first.get_attribute("aria-label"))

    url = (
        f"https://x.com/{autor.lstrip('@')}/status/{tid}"
        if autor
        else f"https://x.com/i/status/{tid}"
    )

    return Registro(
        id=tid,
        red="x",
        estrategia=_marcar(texto, criterio.estrategia, lexico),
        criterio_busqueda=criterio.query,
        texto=texto,
        idioma=idioma,
        autor=autor,
        fecha_publicacion=fecha,
        url=url,
        metricas={
            "likes": _metrica("like"),
            "reposts": _metrica("retweet"),
            "respuestas": _metrica("reply"),
        },
    )


class ExtractorX(ExtractorBase):
    red = "x"

    _TIMEOUT_MS = 30_000       # espera máxima por navegación / selector
    _SCROLL_PX = 3_000         # cuánto baja cada scroll
    _ESPERA_SCROLL_MS = 1_500  # espera tras cada scroll para que rendericen tweets

    def __init__(self, config) -> None:
        super().__init__(config)
        self._lexico = [t.lower() for t in config.lexico]

    # navegación / scroll
    def _esperar_timeline(self, pagina) -> None:
        """Espera el primer tweet; si no llega, asume pared (login/rate-limit/captcha)."""
        from playwright.sync_api import TimeoutError as PWTimeout

        try:
            pagina.wait_for_selector(
                'article[data-testid="tweet"]', timeout=self._TIMEOUT_MS
            )
        except PWTimeout as e:
            raise RuntimeError(
                "no cargó el timeline (login wall / rate-limit / captcha)"
            ) from e

    def _buscar(self, pagina, criterio: Criterio, limite: int) -> Iterator[Registro]:
        """Navega a la query (pestaña Latest), scrollea y va emitiendo Registros."""
        url = (
            f"https://x.com/search?q={quote(criterio.query)}"
            "&src=typed_query&f=live"
        )
        pagina.goto(url, timeout=self._TIMEOUT_MS, wait_until="domcontentloaded")
        self._esperar_timeline(pagina)

        vistos: set[str] = set()
        sin_avance = 0
        while len(vistos) < limite and sin_avance < self.config.x_scrolls_sin_avance:
            articulos = pagina.locator('article[data-testid="tweet"]')
            nuevos = 0
            for i in range(articulos.count()):
                reg = _parsear_tweet(articulos.nth(i), criterio, self._lexico)
                if reg is None or reg.id in vistos:
                    continue
                vistos.add(reg.id)
                nuevos += 1
                yield reg
                if len(vistos) >= limite:
                    return
            sin_avance = sin_avance + 1 if nuevos == 0 else 0
            pagina.mouse.wheel(0, self._SCROLL_PX)
            pagina.wait_for_timeout(self._ESPERA_SCROLL_MS)

    # interfaz del orquestador
    def extraer(self) -> Iterator[Registro]:
        ruta = Path(self.config.x_sesion)
        if not ruta.exists():
            raise FaltanSesion(
                f"no existe la sesión {ruta}. Captúrala una vez con:\n"
                "  uv run --group x python scripts/recoleccion_x.py --login"
            )

        from playwright.sync_api import sync_playwright

        total = 0
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=self.config.x_headless)
            contexto = navegador.new_context(storage_state=str(ruta))
            pagina = contexto.new_page()
            try:
                for criterio in self.config.todos_los_criterios():
                    if total >= self.config.max_total_por_red:
                        break
                    restante = self.config.max_total_por_red - total
                    limite = min(self.config.max_por_criterio, restante)
                    try:
                        for registro in self._buscar(pagina, criterio, limite):
                            yield registro
                            total += 1
                    except Exception as e:
                        # una query caída no debe tumbar las demás
                        print(
                            f"[x] consulta {criterio.query!r} omitida "
                            f"({type(e).__name__}: {e})",
                            file=sys.stderr,
                        )
                        continue
                    time.sleep(self.config.x_pausa)
            finally:
                contexto.close()
                navegador.close()
