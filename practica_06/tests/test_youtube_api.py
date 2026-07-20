import pytest
import requests

from extractor_mundial.config import Criterio, cargar_config
from extractor_mundial.lexico import Entrada, Lexico
from extractor_mundial.extractores.youtube_api import (
    ExtractorYouTubeApi,
    FaltaApiKey,
    _ComentariosDeshabilitados,
    _a_registro,
)

# Léxico mínimo para el marcado de 2 capas (substring, sin límite de palabra).
_LEXICO = Lexico([Entrada("monos", "anti-negro", False)])

# Item tal como lo devuelve commentThreads.list (part=snippet).
_ITEM = {
    "id": "UgxThreadId123",
    "snippet": {
        "videoId": "vid789",
        "totalReplyCount": 3,
        "topLevelComment": {
            "id": "UgxComentario456",
            "snippet": {
                "textOriginal": "Gran partido de Brasil",
                "authorDisplayName": "Hincha Neutral",
                "likeCount": 42,
                "publishedAt": "2026-06-28T21:15:00Z",
            },
        },
    },
}


def test_a_registro_mapea_todos_los_campos():
    reg = _a_registro(_ITEM, Criterio("Brasil", "amplia"), _LEXICO)

    assert reg is not None
    assert reg.id == "UgxComentario456"
    assert reg.red == "youtube"
    assert reg.estrategia == "amplia"  # sin término del léxico
    assert reg.criterio_busqueda == "Brasil"
    assert reg.texto == "Gran partido de Brasil"
    assert reg.idioma is None  # se detecta en la Práctica 7
    assert reg.autor == "Hincha Neutral"
    assert reg.fecha_publicacion == "2026-06-28T21:15:00Z"
    assert reg.url == "https://www.youtube.com/watch?v=vid789&lc=UgxComentario456"
    assert reg.metricas == {"likes": 42, "respuestas": 3}


def test_a_registro_remarca_dirigida_por_lexico():
    item = {
        "id": "t",
        "snippet": {
            "videoId": "v",
            "totalReplyCount": 0,
            "topLevelComment": {
                "id": "c",
                "snippet": {
                    "textOriginal": "Brasil son unos MONOS",
                    "authorDisplayName": "x",
                    "likeCount": 0,
                    "publishedAt": "2026-06-28T00:00:00Z",
                },
            },
        },
    }
    # Vino de una búsqueda amplia pero el léxico lo promueve a dirigida.
    reg = _a_registro(item, Criterio("Brasil", "amplia"), _LEXICO)
    assert reg is not None
    assert reg.estrategia == "dirigida"


def test_a_registro_sin_texto_devuelve_none():
    item = {
        "id": "t",
        "snippet": {
            "videoId": "v",
            "totalReplyCount": 0,
            "topLevelComment": {
                "id": "c",
                "snippet": {
                    "textOriginal": "   ",
                    "authorDisplayName": "x",
                    "likeCount": 0,
                    "publishedAt": "2026-06-28T00:00:00Z",
                },
            },
        },
    }
    assert _a_registro(item, Criterio("Brasil", "amplia"), _LEXICO) is None


def _item(cid: str, texto: str) -> dict:
    return {
        "id": cid,
        "snippet": {
            "videoId": "v",
            "totalReplyCount": 0,
            "topLevelComment": {
                "id": cid,
                "snippet": {
                    "textOriginal": texto,
                    "authorDisplayName": "x",
                    "likeCount": 0,
                    "publishedAt": "2026-06-28T00:00:00Z",
                },
            },
        },
    }


# Extractor con la capa de red sustituida por datos en memoria: prueba el loop
# (topes / aislamiento) sin tocar la API.
class _FakeYT(ExtractorYouTubeApi):
    def __init__(self, cfg, videos, comentarios):
        super().__init__(cfg)
        self._videos = videos
        self._comentarios = comentarios  # video_id -> list[item] | Exception

    def _buscar_videos(self, query, limite):
        return self._videos

    def _items_de_video(self, video_id, limite):
        r = self._comentarios[video_id]
        if isinstance(r, Exception):
            raise r
        for i, it in enumerate(r):
            if i >= limite:
                return
            yield it


def _cfg_una_query(monkeypatch, tope):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test")
    cfg = cargar_config()
    cfg.todos_los_criterios = lambda: [Criterio("Brasil", "amplia")]
    cfg.max_total_por_red = tope
    cfg.max_por_criterio = 100
    return cfg


def test_extraer_corta_en_el_tope_por_red(monkeypatch):
    cfg = _cfg_una_query(monkeypatch, tope=3)
    ext = _FakeYT(
        cfg,
        ["v1", "v2"],
        {
            "v1": [_item("c1", "a"), _item("c2", "b")],
            "v2": [_item("c3", "c"), _item("c4", "d")],
        },
    )
    regs = list(ext.extraer())
    assert [r.id for r in regs] == ["c1", "c2", "c3"]  # corta al llegar a 3


def test_extraer_aisla_video_fallido(monkeypatch):
    cfg = _cfg_una_query(monkeypatch, tope=10)
    ext = _FakeYT(
        cfg,
        ["v1", "v2", "v3"],
        {
            "v1": [_item("c1", "a")],
            "v2": _ComentariosDeshabilitados("cerrados"),  # se salta sin ruido
            "v3": requests.ConnectionError("caido"),       # se salta con aviso
        },
    )
    regs = list(ext.extraer())
    assert [r.id for r in regs] == ["c1"]  # v2 y v3 no tumban la corrida


def test_extraer_sin_api_key_avisa_claro(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    cfg = cargar_config()
    cfg.todos_los_criterios = lambda: [Criterio("Brasil", "amplia")]
    ext = ExtractorYouTubeApi(cfg)
    with pytest.raises(FaltaApiKey):
        next(ext.extraer())  # falla antes de cualquier llamada de red
