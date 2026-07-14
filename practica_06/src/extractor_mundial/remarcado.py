# Re-marcado del campo `estrategia` SIN volver a extraer.
#
# El léxico es un artefacto vivo: los 3 integrantes lo nutren con lo que observan en
# campo, y un término mal calibrado contamina la métrica ("de N comentarios, X% con
# carga xenófoba"). Como el `texto` ya está guardado en `dataset.jsonl`, la marca
# amplia/dirigida se puede recalcular en segundos, sin volver a pedirle nada a la red.
#
# Se reconstruye EXACTAMENTE la misma regla que aplican los extractores:
#   dirigida  <=>  el texto contiene léxico  O  vino de una consulta dirigida
# (YouTube no busca por query, así que para sus registros solo aplica la 1ª condición:
#  el título del video nunca coincide con una consulta dirigida.)

from __future__ import annotations

import json
from pathlib import Path

from .config import DIR_CONFIG, Config
from .lexico import cargar as cargar_lexico


def remarcar(dir_data: Path, config: Config) -> tuple[int, int, int]:
    """Recalcula `estrategia` en dataset.jsonl. Devuelve (total, dirigida, cambiados)."""
    jsonl = dir_data / "dataset.jsonl"
    if not jsonl.exists():
        return (0, 0, 0)

    lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")
    queries_dirigidas = {c.query for c in config.criterios_dirigida()}

    registros: list[dict] = []
    cambiados = 0
    dirigidas = 0
    # Se parte por "\n", NO con splitlines(): ver la nota en almacenamiento._leer_jsonl.
    # splitlines() corta también por U+2028/U+2029/U+0085, que van sin escapar dentro
    # del JSON y partirían el registro en dos, perdiéndolo en silencio.
    for linea in jsonl.read_text(encoding="utf-8").split("\n"):
        linea = linea.strip()
        if not linea:
            continue
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue  # línea truncada por un corte previo

        con_lexico = lexico.es_dirigida(d["texto"])
        de_consulta_dirigida = d["criterio_busqueda"] in queries_dirigidas
        nueva = "dirigida" if (con_lexico or de_consulta_dirigida) else "amplia"

        if nueva != d["estrategia"]:
            cambiados += 1
            d["estrategia"] = nueva
        if nueva == "dirigida":
            dirigidas += 1
        registros.append(d)

    # Escritura atómica: si esto se corta, el dataset original sigue intacto.
    tmp = jsonl.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for d in registros:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    tmp.replace(jsonl)

    return (len(registros), dirigidas, cambiados)
