from pathlib import Path

from extractor_mundial.config import Criterio
from extractor_mundial.extractores.x import _marcar, _num_de_aria, _parsear_tweet

_FIXTURE = Path(__file__).parent / "fixtures" / "tweet.html"


def test_num_de_aria_extrae_el_primer_numero():
    assert _num_de_aria("100 Likes. Like") == 100
    assert _num_de_aria("1,234 reposts. Repost") == 1234
    assert _num_de_aria("Reply") is None
    assert _num_de_aria(None) is None
    assert _num_de_aria("") is None


def test_marcar_dos_capas():
    # término del léxico presente → dirigida aunque la query fuera amplia
    assert _marcar("Brasil son unos MONOS", "amplia", ["monos"]) == "dirigida"
    # sin término del léxico → hereda la estrategia del criterio
    assert _marcar("Gran partido de Brasil", "amplia", ["monos"]) == "amplia"
    assert _marcar("Gran partido", "dirigida", ["monos"]) == "dirigida"


def test_parsear_tweet_extrae_todos_los_campos(pagina):
    pagina.set_content(_FIXTURE.read_text(encoding="utf-8"))
    articulo = pagina.locator('article[data-testid="tweet"]').first

    reg = _parsear_tweet(articulo, Criterio("Brasil", "amplia"), ["monos"])

    assert reg is not None
    assert reg.id == "1810234567890123456"
    assert reg.red == "x"
    assert reg.criterio_busqueda == "Brasil"
    assert "monos" in reg.texto.lower()
    assert reg.estrategia == "dirigida"  # re-marcado por el léxico
    assert reg.idioma == "es"
    assert reg.autor == "@cuenta_burner"
    assert reg.fecha_publicacion == "2026-06-28T21:15:00.000Z"
    assert reg.url == "https://x.com/cuenta_burner/status/1810234567890123456"
    assert reg.metricas == {"likes": 100, "reposts": 5, "respuestas": 10}


def test_parsear_tweet_sin_texto_devuelve_none(pagina):
    pagina.set_content(
        '<article data-testid="tweet">'
        '<a href="/x/status/123"><time datetime="2026-06-28T00:00:00.000Z">x</time></a>'
        "</article>"
    )
    articulo = pagina.locator('article[data-testid="tweet"]').first
    assert _parsear_tweet(articulo, Criterio("Brasil", "amplia"), ["monos"]) is None
