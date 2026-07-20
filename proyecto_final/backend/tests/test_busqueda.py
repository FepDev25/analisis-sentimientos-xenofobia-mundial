import os

from extractor_mundial.config import DIR_DATA

from plataforma import busqueda


def test_config_para_apunta_sesion_x_a_practica_06():
    # La sesion de X vive en practica_06/data; sin ruta absoluta, el extractor la
    # busca relativa al cwd del backend y no la encuentra (FaltanSesion).
    cfg = busqueda._config_para("Brasil")
    assert os.path.isabs(cfg.x_sesion)
    assert cfg.x_sesion == str(DIR_DATA / "x_session.json")
