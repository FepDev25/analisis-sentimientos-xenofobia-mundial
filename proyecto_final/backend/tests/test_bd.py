# Tests de la capa de datos. Solo usan `sqlite3` (stdlib): corren sin instalar
# nada y sin P6 (los `Registro` entran por duck-typing).

from __future__ import annotations

from types import SimpleNamespace

import pytest

from plataforma import bd


def registro(red="x", id="1", texto="Brasil monos", estrategia="dirigida", idioma="es"):
    return SimpleNamespace(
        red=red,
        id=id,
        estrategia=estrategia,
        criterio_busqueda="Brasil monos",
        texto=texto,
        idioma=idioma,
        autor="@alguien",
        fecha_publicacion="2026-07-01T00:00:00+00:00",
        url="https://x.com/alguien/status/1",
        metricas={"likes": 5},
        fecha_extraccion="2026-07-16T00:00:00+00:00",
    )


@pytest.fixture
def con(tmp_path):
    c = bd.conectar(tmp_path / "test.db")
    yield c
    c.close()


def test_conectar_crea_esquema_y_activa_wal(con):
    tablas = {
        f["name"]
        for f in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"busqueda", "registro", "sentimiento", "resultado_red"} <= tablas
    assert con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_ciclo_de_vida_de_busqueda(con):
    bid = bd.crear_busqueda(con, "Brasil monos")
    assert bd.obtener_busqueda(con, bid)["estado"] == "en_curso"

    bd.terminar_busqueda(con, bid)
    b = bd.obtener_busqueda(con, bid)
    assert b["estado"] == "terminada"
    assert b["terminada_en"] is not None


def test_estado_invalido_es_rechazado(con):
    bid = bd.crear_busqueda(con, "q")
    with pytest.raises(ValueError):
        bd.terminar_busqueda(con, bid, "inventado")


def test_guardar_registro_deduplica_dentro_de_la_busqueda(con):
    bid = bd.crear_busqueda(con, "q")
    assert bd.guardar_registro(con, bid, registro()) is not None
    assert bd.guardar_registro(con, bid, registro()) is None  # mismo (red, id)


def test_el_mismo_post_se_repite_en_otra_busqueda(con):
    # La dedup es POR busqueda: dos busquedas distintas ven el mismo tweet.
    b1 = bd.crear_busqueda(con, "q1")
    b2 = bd.crear_busqueda(con, "q2")
    assert bd.guardar_registro(con, b1, registro()) is not None
    assert bd.guardar_registro(con, b2, registro()) is not None


def test_registros_de_filtra_por_red_y_deserializa_metricas(con):
    bid = bd.crear_busqueda(con, "q")
    bd.guardar_registro(con, bid, registro(red="x", id="1"))
    bd.guardar_registro(con, bid, registro(red="bluesky", id="2"))
    con.commit()

    assert len(bd.registros_de(con, bid)) == 2
    solo_x = bd.registros_de(con, bid, red="x")
    assert len(solo_x) == 1
    assert solo_x[0]["metricas"] == {"likes": 5}  # vuelve como dict, no string
    assert solo_x[0]["sentimiento"] is None  # aun sin clasificar


def test_registros_sin_clasificar_solo_trae_pendientes(con):
    bid = bd.crear_busqueda(con, "q")
    rid1 = bd.guardar_registro(con, bid, registro(id="1"))
    bd.guardar_registro(con, bid, registro(id="2"))
    con.commit()

    assert len(bd.registros_sin_clasificar(con, bid)) == 2
    bd.guardar_sentimientos(
        con, [{"registro_id": rid1, "sentimiento": "negativo", "sent_score": 0.9}]
    )
    pendientes = bd.registros_sin_clasificar(con, bid)
    assert len(pendientes) == 1
    assert pendientes[0]["id"] != rid1


def test_guardar_sentimientos_es_idempotente(con):
    bid = bd.crear_busqueda(con, "q")
    rid = bd.guardar_registro(con, bid, registro())
    con.commit()

    bd.guardar_sentimientos(
        con, [{"registro_id": rid, "sentimiento": "neutral", "sent_score": 0.5}]
    )
    bd.guardar_sentimientos(
        con,
        [{"registro_id": rid, "sentimiento": "negativo", "sent_score": 0.9, "odio": True,
          "odio_score": 0.8}],
    )
    fila = bd.registros_de(con, bid)[0]
    assert fila["sentimiento"] == "negativo"  # el segundo pisa al primero
    assert fila["odio"] is True  # vuelve como bool, no como 0/1


def test_resumen_da_global_y_por_red(con):
    bid = bd.crear_busqueda(con, "q")
    r1 = bd.guardar_registro(con, bid, registro(red="x", id="1"))
    r2 = bd.guardar_registro(con, bid, registro(red="x", id="2"))
    r3 = bd.guardar_registro(con, bid, registro(red="bluesky", id="3"))
    con.commit()

    bd.guardar_sentimientos(
        con,
        [
            {"registro_id": r1, "sentimiento": "negativo", "odio": True},
            {"registro_id": r2, "sentimiento": "negativo", "odio": False},
            {"registro_id": r3, "sentimiento": "neutral", "odio": False},
        ],
    )

    res = bd.resumen(con, bid)
    assert res["global"] == {"negativo": 2, "neutral": 1}
    assert res["por_red"]["x"] == {"negativo": 2}
    assert res["por_red"]["bluesky"] == {"neutral": 1}
    assert res["odio_por_red"]["x"] == 1


def test_resultado_red_se_actualiza_en_conflicto(con):
    bid = bd.crear_busqueda(con, "q")
    bd.guardar_resultado_red(con, bid, "x", 0, "throttle", 1.0)
    bd.guardar_resultado_red(con, bid, "x", 15, None, 17.37)

    redes = bd.resumen(con, bid)["redes"]
    assert len(redes) == 1
    assert redes[0]["total"] == 15
    assert redes[0]["error"] is None


def test_borrar_busqueda_arrastra_sus_registros(con):
    bid = bd.crear_busqueda(con, "q")
    rid = bd.guardar_registro(con, bid, registro())
    bd.guardar_sentimientos(con, [{"registro_id": rid, "sentimiento": "negativo"}])
    con.commit()

    con.execute("DELETE FROM busqueda WHERE id = ?", (bid,))
    con.commit()
    assert con.execute("SELECT COUNT(*) FROM registro").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM sentimiento").fetchone()[0] == 0
