"""Genera una vista curada de los textos capturados desde TikTok.

No modifica `data/tiktok.csv` ni `dataset.jsonl`. Produce:
  - data/tiktok_curado.csv
  - data/tiktok_curado.json
  - data/tiktok_curado_resumen.txt
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

from extractor_mundial.config import DIR_DATA
from extractor_mundial.contrato import CAMPOS
from extractor_mundial.lexico import cargar as cargar_lexico


DIR_CONFIG = Path(__file__).resolve().parents[1] / "config"

UI_EXACTO = {
    "tiktok",
    "search",
    "for you",
    "explore",
    "following",
    "friends",
    "live",
    "messages",
    "activity",
    "upload",
    "profile",
    "more",
    "comments",
    "you may like",
    "add comment...",
    "follow",
    "reply",
    "share",
    "copy link",
    "see translation",
    "original sound",
}

UI_PREFIJOS = (
    "view all results for",
    "related searches",
)

USUARIO_RE = re.compile(r"^@?[A-Za-z0-9_.]{3,32}$")
METRICA_RE = re.compile(r"^[\d\s.,]+[KMBkmb]?$")


def _normalizar(texto: str) -> str:
    texto = texto.replace("\u00a0", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _limpiar_tiktok(texto: str) -> str:
    texto = _normalizar(texto)
    texto = re.sub(r"^\d+\s+comments?\s+", "", texto, flags=re.I)
    texto = re.sub(r"\s+View\s+\d+\s+repl(?:y|ies)\b.*$", "", texto, flags=re.I)
    texto = re.sub(r"\s+\d+[smhdw]\s+ago\s+Reply\b.*$", "", texto, flags=re.I)
    texto = re.sub(r"\s+\d{1,2}-\d{1,2}\s+Reply\b.*$", "", texto, flags=re.I)
    texto = re.sub(r"\s+\d{1,2}/\d{1,2}\s+Reply\b.*$", "", texto, flags=re.I)
    texto = re.sub(r"\s+Reply\s+\d+.*$", "", texto, flags=re.I)
    texto = re.sub(r"\s+Reply\b.*$", "", texto, flags=re.I)
    return _normalizar(texto)


def _captura_visible(fila: dict) -> bool:
    try:
        return json.loads(fila.get("metricas") or "{}").get("captura") == "visible_live"
    except json.JSONDecodeError:
        return False


def _ruido(texto: str, dirigida: bool) -> str | None:
    low = texto.lower()
    if not texto:
        return "vacio"
    if low in UI_EXACTO or low.startswith(UI_PREFIJOS):
        return "ui"
    if "drag the slider" in low or "maximum number of attempts" in low:
        return "captcha"
    if METRICA_RE.match(texto):
        return "metrica"
    if USUARIO_RE.match(texto) and not dirigida:
        return "usuario"
    if "[Sticker]" in texto and not dirigida:
        return "sticker"
    if len(texto) < 25 and not dirigida:
        return "muy_corto"
    if len(texto) > 320:
        return "bloque_largo"
    return None


def main() -> None:
    origen = DIR_DATA / "tiktok.csv"
    if not origen.exists():
        raise SystemExit("No existe data/tiktok.csv")

    lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")
    filas = list(csv.DictReader(origen.open(encoding="utf-8")))
    salidas: list[dict] = []
    vistos: set[str] = set()
    descartes: Counter[str] = Counter()

    for fila in filas:
        if not _captura_visible(fila):
            descartes["captura_grilla"] += 1
            continue

        texto = _limpiar_tiktok(fila.get("texto") or "")
        dirigida = lexico.es_dirigida(texto)
        razon = _ruido(texto, dirigida)
        if razon:
            descartes[razon] += 1
            continue

        clave = texto.lower()
        if clave in vistos:
            descartes["duplicado_texto"] += 1
            continue
        vistos.add(clave)

        nueva = dict(fila)
        nueva["texto"] = texto
        nueva["estrategia"] = "dirigida" if dirigida else "amplia"
        salidas.append(nueva)

    # TikTok suele renderizar el mismo comentario dos veces: una variante incluye
    # el usuario y otra solo el texto. Para análisis conviene conservar la más
    # limpia, que normalmente es la más corta y aparece como sufijo de la otra.
    por_url: dict[str, list[dict]] = {}
    for fila in salidas:
        por_url.setdefault(fila.get("url") or "", []).append(fila)

    dedupe_suffix: list[dict] = []
    descartes_suffix = 0
    for _, grupo in por_url.items():
        mantenidas: list[dict] = []
        for fila in sorted(grupo, key=lambda f: len(f.get("texto") or "")):
            texto = (fila.get("texto") or "").lower()
            if any(
                texto.endswith((m.get("texto") or "").lower())
                and len(texto) > len(m.get("texto") or "")
                and len(texto) - len(m.get("texto") or "") <= 65
                for m in mantenidas
            ):
                descartes_suffix += 1
                continue
            mantenidas.append(fila)
        dedupe_suffix.extend(mantenidas)

    salidas = dedupe_suffix
    if descartes_suffix:
        descartes["duplicado_con_usuario"] += descartes_suffix

    csv_out = DIR_DATA / "tiktok_curado.csv"
    with csv_out.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        for fila in salidas:
            escritor.writerow({k: fila.get(k) for k in CAMPOS})

    json_out = DIR_DATA / "tiktok_curado.json"
    json_out.write_text(
        json.dumps(salidas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    resumen = [
        f"origen_total: {len(filas)}",
        f"curado_total: {len(salidas)}",
        f"estrategia: {dict(Counter(f['estrategia'] for f in salidas))}",
        f"descartes: {dict(descartes)}",
    ]
    resumen_out = DIR_DATA / "tiktok_curado_resumen.txt"
    resumen_out.write_text("\n".join(resumen) + "\n", encoding="utf-8")

    print("\n".join(resumen))
    print(f"- {csv_out}")
    print(f"- {json_out}")
    print(f"- {resumen_out}")


if __name__ == "__main__":
    main()
