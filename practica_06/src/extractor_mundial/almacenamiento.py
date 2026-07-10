# Persistencia de los registros: un archivo por red + un consolidado

from __future__ import annotations

import csv
import json
from pathlib import Path

from .contrato import CAMPOS, Registro

# Acumula registros en memoria, deduplica y vuelca a CSV/JSON
class Almacen:
    def __init__(self, dir_data: Path) -> None:
        self.dir_data = dir_data
        self.dir_data.mkdir(parents=True, exist_ok=True)
        self._por_red: dict[str, list[Registro]] = {}
        self._vistos: set[tuple[str, str]] = set()

    # Guarda un registro si no es duplicado. Devuelve True si se agregó
    def agregar(self, registro: Registro) -> bool:
        if registro.clave in self._vistos:
            return False
        self._vistos.add(registro.clave)
        self._por_red.setdefault(registro.red, []).append(registro)
        return True

    @property
    def total(self) -> int:
        return len(self._vistos)

    # Escribe un CSV por red + dataset.csv y dataset.json consolidados
    def volcar(self) -> list[Path]:
        rutas: list[Path] = []

        # Un archivo por red.
        for red, registros in self._por_red.items():
            ruta = self.dir_data / f"{red}.csv"
            self._escribir_csv(ruta, registros)
            rutas.append(ruta)

        # Consolidado.
        todos = [r for registros in self._por_red.values() for r in registros]
        csv_consolidado = self.dir_data / "dataset.csv"
        self._escribir_csv(csv_consolidado, todos)
        rutas.append(csv_consolidado)

        json_consolidado = self.dir_data / "dataset.json"
        json_consolidado.write_text(
            json.dumps([r.a_dict() for r in todos], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rutas.append(json_consolidado)

        return rutas

    @staticmethod
    def _escribir_csv(ruta: Path, registros: list[Registro]) -> None:
        with ruta.open("w", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=CAMPOS)
            escritor.writeheader()
            for r in registros:
                escritor.writerow(r.a_fila_csv())
