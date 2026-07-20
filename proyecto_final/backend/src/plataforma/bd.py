# Persistencia en SQLite. El esquema vive en `esquema.sql`.

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    # En runtime los `Registro` entran por duck-typing: la capa de datos no
    # necesita a P6 instalado para probarse.
    from extractor_mundial.contrato import Registro

ESTADOS = ("en_curso", "terminada", "error")

_ESQUEMA = Path(__file__).with_name("esquema.sql")


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Abre la conexion y deja la BD lista para usar.
#
# `check_same_thread=False`: el hilo consumidor del orquestador escribe mientras
# el hilo de la peticion HTTP lee. Es seguro porque hay UN solo escritor.
def conectar(ruta: Path | str) -> sqlite3.Connection:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(ruta), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")  # lecturas sin bloquear al escritor
    con.execute("PRAGMA synchronous = NORMAL")
    con.execute("PRAGMA foreign_keys = ON")
    crear_esquema(con)
    return con


def crear_esquema(con: sqlite3.Connection) -> None:
    con.executescript(_ESQUEMA.read_text(encoding="utf-8"))
    con.commit()


# Escritura


def crear_busqueda(con: sqlite3.Connection, query: str) -> int:
    cur = con.execute(
        "INSERT INTO busqueda (query, estado, creada_en) VALUES (?, 'en_curso', ?)",
        (query, _ahora_iso()),
    )
    con.commit()
    return int(cur.lastrowid)


def terminar_busqueda(
    con: sqlite3.Connection, busqueda_id: int, estado: str = "terminada"
) -> None:
    if estado not in ESTADOS:
        raise ValueError(f"estado invalido: {estado!r} (permitidos: {ESTADOS})")
    con.execute(
        "UPDATE busqueda SET estado = ?, terminada_en = ? WHERE id = ?",
        (estado, _ahora_iso(), busqueda_id),
    )
    con.commit()


# Devuelve el id nuevo, o None si era duplicado.
#
# No hace commit: lo llama el consumidor una vez por registro y confirmar en cada
# uno mataria el rendimiento. El llamador confirma por lotes.
def guardar_registro(
    con: sqlite3.Connection, busqueda_id: int, registro: "Registro"
) -> int | None:
    try:
        cur = con.execute(
            """
            INSERT INTO registro (
                busqueda_id, red, id_externo, estrategia, criterio_busqueda,
                texto, idioma, autor, fecha_publicacion, url, metricas,
                fecha_extraccion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                busqueda_id,
                registro.red,
                registro.id,
                registro.estrategia,
                registro.criterio_busqueda,
                registro.texto,
                registro.idioma,
                registro.autor,
                registro.fecha_publicacion,
                registro.url,
                json.dumps(registro.metricas or {}, ensure_ascii=False),
                registro.fecha_extraccion,
            ),
        )
    except sqlite3.IntegrityError:
        return None
    return int(cur.lastrowid)


def guardar_resultado_red(
    con: sqlite3.Connection,
    busqueda_id: int,
    red: str,
    total: int,
    error: str | None,
    duracion_s: float,
) -> None:
    con.execute(
        """
        INSERT INTO resultado_red (busqueda_id, red, total, error, duracion_s)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (busqueda_id, red) DO UPDATE SET
            total = excluded.total,
            error = excluded.error,
            duracion_s = excluded.duracion_s
        """,
        (busqueda_id, red, total, error, duracion_s),
    )
    con.commit()


# `filas`: lo que devuelve `sentimiento_worker.clasificar_bloque`, con
# `registro_id` en lugar de `indice`.
def guardar_sentimientos(con: sqlite3.Connection, filas: Iterable[dict]) -> int:
    datos = [
        (
            f["registro_id"],
            f.get("sentimiento"),
            f.get("sent_score"),
            None if f.get("odio") is None else int(bool(f["odio"])),
            f.get("odio_score"),
        )
        for f in filas
    ]
    if not datos:
        return 0
    con.executemany(
        """
        INSERT INTO sentimiento (registro_id, sentimiento, sent_score, odio, odio_score)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (registro_id) DO UPDATE SET
            sentimiento = excluded.sentimiento,
            sent_score  = excluded.sent_score,
            odio        = excluded.odio,
            odio_score  = excluded.odio_score
        """,
        datos,
    )
    con.commit()
    return len(datos)


# Lectura


def obtener_busqueda(con: sqlite3.Connection, busqueda_id: int) -> dict | None:
    fila = con.execute("SELECT * FROM busqueda WHERE id = ?", (busqueda_id,)).fetchone()
    return dict(fila) if fila else None


def registros_de(
    con: sqlite3.Connection,
    busqueda_id: int,
    red: str | None = None,
    limite: int = 200,
    desplazamiento: int = 0,
) -> list[dict]:
    sql = """
        SELECT r.id, r.red, r.id_externo, r.estrategia, r.texto, r.idioma,
               r.autor, r.fecha_publicacion, r.url, r.metricas,
               s.sentimiento, s.sent_score, s.odio, s.odio_score
        FROM registro r
        LEFT JOIN sentimiento s ON s.registro_id = r.id
        WHERE r.busqueda_id = ?
    """
    params: list[Any] = [busqueda_id]
    if red:
        sql += " AND r.red = ?"
        params.append(red)
    sql += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend([limite, desplazamiento])

    filas = []
    for f in con.execute(sql, params):
        d = dict(f)
        d["metricas"] = json.loads(d["metricas"]) if d["metricas"] else {}
        d["odio"] = None if d["odio"] is None else bool(d["odio"])
        filas.append(d)
    return filas


def registros_sin_clasificar(con: sqlite3.Connection, busqueda_id: int) -> list[dict]:
    sql = """
        SELECT r.id, r.texto, r.idioma
        FROM registro r
        LEFT JOIN sentimiento s ON s.registro_id = r.id
        WHERE r.busqueda_id = ? AND s.registro_id IS NULL
        ORDER BY r.id
    """
    return [dict(f) for f in con.execute(sql, (busqueda_id,))]


# Conteos de sentimiento global y por red: las dos vistas que pide la rubrica.
def resumen(con: sqlite3.Connection, busqueda_id: int) -> dict:
    global_ = con.execute(
        """
        SELECT s.sentimiento, COUNT(*) AS n
        FROM registro r JOIN sentimiento s ON s.registro_id = r.id
        WHERE r.busqueda_id = ?
        GROUP BY s.sentimiento
        """,
        (busqueda_id,),
    ).fetchall()

    por_red = con.execute(
        """
        SELECT r.red, s.sentimiento, COUNT(*) AS n,
               SUM(CASE WHEN s.odio = 1 THEN 1 ELSE 0 END) AS odiosos
        FROM registro r JOIN sentimiento s ON s.registro_id = r.id
        WHERE r.busqueda_id = ?
        GROUP BY r.red, s.sentimiento
        """,
        (busqueda_id,),
    ).fetchall()

    redes = con.execute(
        "SELECT red, total, error, duracion_s FROM resultado_red WHERE busqueda_id = ?",
        (busqueda_id,),
    ).fetchall()

    conteo_red: dict[str, dict[str, int]] = {}
    odio_red: dict[str, int] = {}
    for f in por_red:
        conteo_red.setdefault(f["red"], {})[f["sentimiento"]] = f["n"]
        odio_red[f["red"]] = odio_red.get(f["red"], 0) + (f["odiosos"] or 0)

    return {
        "busqueda_id": busqueda_id,
        "global": {f["sentimiento"]: f["n"] for f in global_},
        "por_red": conteo_red,
        "odio_por_red": odio_red,
        "redes": [dict(f) for f in redes],
    }
