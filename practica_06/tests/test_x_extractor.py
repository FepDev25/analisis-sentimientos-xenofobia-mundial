import pytest

from extractor_mundial.config import cargar_config
from extractor_mundial.extractores.x import ExtractorX, FaltanSesion


def test_extraer_sin_sesion_avisa_claro(tmp_path):
    cfg = cargar_config()
    cfg.x_sesion = str(tmp_path / "no_existe.json")  # sesión ausente a propósito
    ext = ExtractorX(cfg)

    with pytest.raises(FaltanSesion):
        next(ext.extraer())  # debe fallar ANTES de abrir navegador
