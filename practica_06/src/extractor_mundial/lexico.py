"""Marcado del léxico xenófobo — fuente única compartida por el extractor y el AED"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Encabezado que fija el eje vigente: "# EJE: anti-negro / simiesco"
_RE_EJE = re.compile(r"#\s*EJE:\s*(.+?)\s*$", re.IGNORECASE)
# Menciones @usuario: se descartan antes de marcar (no son contenido).
_RE_MENCION = re.compile(r"@\w+")


@dataclass(frozen=True)
class Entrada:
    termino: str  # término tal cual (para mostrar/agrupar)
    eje: str      # eje temático del odio (heredado de la sección)
    exacto: bool  # True → match por límite de palabra


def _parsear(ruta: Path) -> list[Entrada]:
    entradas: list[Entrada] = []
    eje = "sin-clasificar"
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        cruda = linea.strip()
        if not cruda:
            continue
        if cruda.startswith("#"):
            m = _RE_EJE.match(cruda)
            if m:
                # Nombre corto del eje: se descarta el paréntesis descriptivo.
                eje = m.group(1).split("(")[0].strip()
            continue
        cuerpo, _, flags = cruda.partition("#")
        termino = cuerpo.strip()
        if not termino:
            continue
        exacto = "exacto" in flags.lower() or "palabra" in flags.lower()
        entradas.append(Entrada(termino, eje, exacto))
    return entradas


class Lexico:
    """Léxico cargado y listo para marcar. Precompila los matchers una sola vez."""

    def __init__(self, entradas: list[Entrada]) -> None:
        self.entradas = entradas
        # (entrada, término_lower) para los de substring
        self._subs: list[tuple[Entrada, str]] = []
        # (entrada, regex.search) para los de límite de palabra
        self._exactos: list[tuple[Entrada, object]] = []
        for e in entradas:
            t = e.termino.lower()
            if e.exacto:
                pat = re.compile(rf"\b{re.escape(t)}\b")
                self._exactos.append((e, pat.search))
            else:
                self._subs.append((e, t))

    @staticmethod
    def _preparar(texto: str) -> str:
        return _RE_MENCION.sub(" ", str(texto).lower())

    def disparos(self, texto: str) -> list[Entrada]:
        """Entradas del léxico que dispara este texto (mismo criterio en todos lados)."""
        t = self._preparar(texto)
        out = [e for e, buscar in self._exactos if buscar(t)]
        out += [e for e, sub in self._subs if sub in t]
        return out

    def es_dirigida(self, texto: str) -> bool:
        t = self._preparar(texto)
        return (any(buscar(t) for _, buscar in self._exactos)
                or any(sub in t for _, sub in self._subs))

    @property
    def terminos(self) -> list[str]:
        return [e.termino for e in self.entradas]


def cargar(ruta: Path) -> Lexico:
    """Carga el léxico desde `lexico.txt` y devuelve un `Lexico` listo para marcar."""
    return Lexico(_parsear(ruta))
