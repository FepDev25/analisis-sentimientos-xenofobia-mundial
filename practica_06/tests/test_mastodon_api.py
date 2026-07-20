import pytest
import requests

from extractor_mundial.config import Criterio, cargar_config
from extractor_mundial.lexico import Entrada, Lexico
from extractor_mundial.extractores.mastodon import (
    ExtractorMastodon,
    _a_hashtag,
    _a_registro,
)

_LEXICO = Lexico([Entrada("monos", "anti-negro", False)])

# Status tal como lo devuelve /api/v1/timelines/tag/:tag (content es HTML).
_STATUS = {
    "id": "111222333",
    "uri": "https://mastodon.social/users/hincha/statuses/111222333",
    "url": "https://mastodon.social/@hincha/111222333",
    "content": '<p>Gran partido de <a href="/tags/brasil">#Brasil</a> hoy 🇧🇷</p>',
    "created_at": "2026-06-28T21:15:00.000Z",
    "language": "es",
    "account": {"acct": "hincha", "username": "hincha"},
    "favourites_count": 12,
    "reblogs_count": 3,
    "replies_count": 1,
}


def test_a_hashtag_une_palabras_y_normaliza():
    assert _a_hashtag("World Cup 2026") == "worldcup2026"
    assert _a_hashtag("Ecuador") == "ecuador"
    assert _a_hashtag("#Mundial 2026") == "mundial2026"
    assert _a_hashtag("Brasil Móns") == "brasilmóns"  # conserva acentos


def test_a_registro_mapea_y_limpia_html():
    reg = _a_registro(_STATUS, Criterio("Brasil", "amplia"), _LEXICO)

    assert reg is not None
    assert reg.id == "https://mastodon.social/users/hincha/statuses/111222333"
    assert reg.red == "mastodon"
    assert reg.estrategia == "amplia"  # sin término del léxico
    assert reg.criterio_busqueda == "Brasil"
    assert reg.texto == "Gran partido de #Brasil hoy 🇧🇷"  # HTML quitado
    assert reg.idioma == "es"
    assert reg.autor == "hincha"
    assert reg.fecha_publicacion == "2026-06-28T21:15:00.000Z"
    assert reg.url == "https://mastodon.social/@hincha/111222333"
    assert reg.metricas == {"likes": 12, "reposts": 3, "respuestas": 1}


def test_a_registro_remarca_dirigida_por_lexico():
    status = {**_STATUS, "content": "<p>Brasil son unos MONOS</p>"}
    reg = _a_registro(status, Criterio("Brasil", "amplia"), _LEXICO)
    assert reg is not None
    assert reg.estrategia == "dirigida"


def test_a_registro_reblog_sin_contenido_devuelve_none():
    # Un boost llega con content vacío: se descarta (evita duplicar el original).
    status = {**_STATUS, "content": "<p></p>"}
    assert _a_registro(status, Criterio("Brasil", "amplia"), _LEXICO) is None


# Extractor con la capa de red sustituida por datos en memoria: prueba el loop
# (topes / aislamiento) sin tocar la red.
class _FakeMasto(ExtractorMastodon):
    def __init__(self, cfg, por_tag):
        super().__init__(cfg)
        self._por_tag = por_tag  # tag -> list[status] | Exception

    def _timeline_tag(self, tag, limite):
        r = self._por_tag[tag]
        if isinstance(r, Exception):
            raise r
        for i, s in enumerate(r):
            if i >= limite:
                return
            yield s


def _status(sid: str, texto: str) -> dict:
    return {**_STATUS, "id": sid, "uri": f"tag:{sid}", "content": f"<p>{texto}</p>"}


def _cfg_una_query(tope):
    cfg = cargar_config()
    cfg.todos_los_criterios = lambda: [Criterio("Mundial 2026", "amplia")]
    cfg.max_total_por_red = tope
    cfg.max_por_criterio = 100
    return cfg


def test_extraer_corta_en_el_tope_por_red():
    cfg = _cfg_una_query(tope=2)
    ext = _FakeMasto(cfg, {"mundial2026": [_status("a", "x"), _status("b", "y"), _status("c", "z")]})
    regs = list(ext.extraer())
    assert [r.id for r in regs] == ["tag:a", "tag:b"]


def test_extraer_aisla_query_fallida():
    cfg = cargar_config()
    cfg.todos_los_criterios = lambda: [
        Criterio("Ecuador", "amplia"),
        Criterio("Brasil", "amplia"),
    ]
    cfg.max_total_por_red = 10
    cfg.max_por_criterio = 100
    ext = _FakeMasto(
        cfg,
        {
            "ecuador": requests.ConnectionError("caido"),  # se salta con aviso
            "brasil": [_status("b1", "hola")],
        },
    )
    regs = list(ext.extraer())
    assert [r.id for r in regs] == ["tag:b1"]  # Ecuador no tumba la corrida
