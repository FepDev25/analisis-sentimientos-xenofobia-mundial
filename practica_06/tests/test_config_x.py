from pathlib import Path

from extractor_mundial.config import cargar_config


def test_x_defaults_cuando_no_hay_seccion(tmp_path):
    toml = tmp_path / "b.toml"
    toml.write_text("[ventana]\nselecciones = ['Brasil']\n", encoding="utf-8")
    lex = tmp_path / "lex.txt"
    lex.write_text("monos\n", encoding="utf-8")

    cfg = cargar_config(ruta_toml=toml, ruta_lexico=lex)

    assert cfg.x_sesion == "data/x_session.json"
    assert cfg.x_headless is False
    assert cfg.x_scrolls_sin_avance == 5
    assert cfg.x_pausa == 2.0


def test_x_lee_la_seccion(tmp_path):
    toml = tmp_path / "b.toml"
    toml.write_text(
        "[ventana]\nselecciones = ['Brasil']\n"
        "[x]\nsesion = 'data/otra.json'\nheadless = true\n"
        "scrolls_sin_avance = 8\npausa = 3.5\n",
        encoding="utf-8",
    )
    lex = tmp_path / "lex.txt"
    lex.write_text("monos\n", encoding="utf-8")

    cfg = cargar_config(ruta_toml=toml, ruta_lexico=lex)

    assert cfg.x_sesion == "data/otra.json"
    assert cfg.x_headless is True
    assert cfg.x_scrolls_sin_avance == 8
    assert cfg.x_pausa == 3.5
