# Persistencia INCREMENTAL y reanudable de los registros.
#
# `dataset.jsonl` es el log durable: cada `agregar()` escribe UNA línea y hace
# flush, así un throttle de la red o un corte (Ctrl-C) no pierde lo ya recolectado.
# Al iniciar se cargan las claves ya presentes para deduplicar ENTRE corridas
# (permite recolectar por tandas). Los CSV por red + los consolidados CSV/JSON son
# vistas que se (re)generan desde el jsonl en `volcar()`.

from __future__ import annotations

import csv
import json
from pathlib import Path

from .contrato import CAMPOS, Registro


class Almacen:
    def __init__(self, dir_data: Path) -> None:
        self.dir_data = dir_data
        self.dir_data.mkdir(parents=True, exist_ok=True)
        self._jsonl = self.dir_data / "dataset.jsonl"
        self._vistos: set[tuple[str, str]] = set()
        self._nuevos = 0
        # Reanudar: claves ya guardadas en corridas previas (para no duplicar).
        self._cargar_existentes()
        self._previos = len(self._vistos)
        # Log durable en modo append.
        self._fh = self._jsonl.open("a", encoding="utf-8")

    # Carga las claves (red, id) ya presentes en el jsonl.
    def _cargar_existentes(self) -> None:
        if not self._jsonl.exists():
            return
        for d in self._leer_jsonl():
            self._vistos.add((d["red"], d["id"]))

    # Guarda un registro si no es duplicado. Devuelve True si se agregó.
    def agregar(self, registro: Registro) -> bool:
        if registro.clave in self._vistos:
            return False
        self._vistos.add(registro.clave)
        self._fh.write(json.dumps(registro.a_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()  # durable de inmediato
        self._nuevos += 1
        return True

    @property
    def total(self) -> int:
        return len(self._vistos)

    @property
    def nuevos(self) -> int:
        return self._nuevos

    @property
    def previos(self) -> int:
        return self._previos

    # (Re)genera los CSV por red + consolidados CSV/JSON desde el jsonl.
    def volcar(self) -> list[Path]:
        self._fh.flush()
        registros = self._leer_jsonl()
        rutas: list[Path] = []

        por_red: dict[str, list[dict]] = {}
        for d in registros:
            por_red.setdefault(d["red"], []).append(d)

        for red, filas in por_red.items():
            ruta = self.dir_data / f"{red}.csv"
            self._escribir_csv(ruta, filas)
            rutas.append(ruta)

        csv_all = self.dir_data / "dataset.csv"
        self._escribir_csv(csv_all, registros)
        rutas.append(csv_all)

        json_all = self.dir_data / "dataset.json"
        json_all.write_text(
            json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rutas.append(json_all)
        return rutas

    def cerrar(self) -> None:
        try:
            self._fh.flush()
            self._fh.close()
        except (ValueError, OSError):
            pass

    # Lee el jsonl tolerando una última línea truncada por un corte previo.
    def _leer_jsonl(self) -> list[dict]:
        if not self._jsonl.exists():
            return []
        out: list[dict] = []
        for linea in self._jsonl.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea:
                continue
            try:
                out.append(json.loads(linea))
            except json.JSONDecodeError:
                continue  # línea a medio escribir: se descarta
        return out

    @staticmethod
    def _escribir_csv(ruta: Path, filas: list[dict]) -> None:
        with ruta.open("w", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=CAMPOS)
            escritor.writeheader()
            for d in filas:
                fila = {k: d.get(k) for k in CAMPOS}
                fila["metricas"] = json.dumps(d.get("metricas", {}), ensure_ascii=False)
                escritor.writerow(fila)
