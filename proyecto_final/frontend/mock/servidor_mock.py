"""Servidor de prueba que imita la API del backend.

Para qué sirve
--------------
El backend real carga ~4 GB de modelos al arrancar y necesita credenciales de
cuatro redes. Eso está bien para la demo final, pero bloquea el desarrollo del
frontend: cada recarga costaría minutos.

Este servidor responde exactamente los mismos endpoints con datos inventados y
con retardos parecidos a los reales (X lenta, Bluesky rápida), para poder
maquetar, probar los filtros y ver los gráficos sin depender de nada.

NO forma parte del sistema entregable: es una herramienta de desarrollo. La
demo se hace contra `plataforma.main:app`.

Uso
---
    python3 mock/servidor_mock.py            # escucha en el 8000

Solo usa la librería estándar de Python: no hay que instalar nada.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO = 8000

REDES = ["bluesky", "x", "youtube", "mastodon"]

# Latencias parecidas a las medidas en la práctica: X es la que marca el techo.
LATENCIA = {"bluesky": (1.2, 2.4), "youtube": (1.0, 2.0), "mastodon": (0.9, 1.8), "x": (7.0, 10.0)}

# Textos de muestra. Mezclan los tres casos que aparecen en el corpus real:
# agresión directa, denuncia del racismo (contra-discurso) y comentario
# futbolístico neutro. Así los filtros y los gráficos muestran algo con sentido.
MUESTRAS = [
    ("negativo", True,  "amplia",   "es", "otra vez los mismos de siempre arruinando el partido, que se regresen a su pais"),
    ("negativo", True,  "dirigida", "es", "jajaja los monos ecuatorianos no saben jugar 🐒"),
    ("negativo", False, "amplia",   "es", "que mal jugo la seleccion hoy, un desastre total"),
    ("neutral",  False, "amplia",   "es", "alguien sabe a que hora es el partido de manana?"),
    ("positivo", False, "amplia",   "es", "que golazo de mbappe, tremendo jugador"),
    ("negativo", False, "dirigida", "en", "Brazilian woman arrested after racist chant against the ecuadorian squad (racism)"),
    ("neutral",  False, "dirigida", "en", "reminder that calling players monkeys is racism, not banter"),
    ("negativo", True,  "dirigida", "pt", "esses macacos nao deviam estar na copa"),
    ("neutral",  False, "amplia",   "en", "world cup 2026 group stage predictions thread"),
    ("positivo", False, "amplia",   "pt", "que jogo incrivel, melhor partida do mundial ate agora"),
    ("negativo", False, "amplia",   "es", "el arbitro nos robo descaradamente, verguenza"),
    ("neutral",  False, "amplia",   "es", "buen partido de ambos equipos, se vio futbol de verdad"),
    ("negativo", True,  "dirigida", "es", "sudacas por todos lados en el estadio, insoportable"),
    ("positivo", False, "dirigida", "en", "great to see the federation punish the racist chants, long overdue"),
    ("neutral",  False, "amplia",   "en", "anyone streaming the match tonight?"),
]

_bd: dict[int, dict] = {}
_siguiente_id = 1
_candado = threading.Lock()


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fabricar_registros(busqueda_id: int, query: str, redes: list[str]) -> list[dict]:
    """Un puñado de registros por red, con sentimiento y odio ya asignados."""
    salida = []
    ident = 1
    for red in redes:
        for _ in range(random.randint(6, 14)):
            sentimiento, odio, estrategia, idioma, texto = random.choice(MUESTRAS)
            salida.append({
                "id": ident,
                "red": red,
                "id_externo": f"{red}-{ident:05d}",
                "estrategia": estrategia,
                "texto": texto,
                "idioma": idioma,
                "autor": f"usuario_{random.randint(100, 999)}",
                "fecha_publicacion": _ahora(),
                "url": f"https://ejemplo.invalid/{red}/{ident}",
                "metricas": {"likes": random.randint(0, 400)},
                "sentimiento": sentimiento,
                "sent_score": round(random.uniform(0.55, 0.99), 3),
                "odio": odio,
                "odio_score": round(random.uniform(0.6, 0.97), 3) if odio else round(random.uniform(0.01, 0.3), 3),
            })
            ident += 1
    return salida


def _correr_busqueda(busqueda_id: int, query: str, redes: list[str]) -> None:
    """Imita el pipeline: extracción concurrente y luego clasificación.

    Las redes se simulan en hilos, igual que el orquestador real, para que el
    tiempo total sea el de la más lenta y no la suma.
    """
    duraciones: dict[str, float] = {}

    def extraer(red: str) -> None:
        t0 = time.perf_counter()
        time.sleep(random.uniform(*LATENCIA[red]))
        duraciones[red] = time.perf_counter() - t0

    hilos = [threading.Thread(target=extraer, args=(r,)) for r in redes]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    registros = _fabricar_registros(busqueda_id, query, redes)

    with _candado:
        _bd[busqueda_id]["registros"] = registros
        _bd[busqueda_id]["redes"] = [
            {
                "red": red,
                "total": sum(1 for r in registros if r["red"] == red),
                "error": None,
                "duracion_s": round(duraciones.get(red, 0.0), 2),
            }
            for red in redes
        ]

    # La clasificación ocurre después de extraer: mientras dura, el frontend
    # muestra la fase "clasificando".
    time.sleep(random.uniform(1.5, 3.0))

    with _candado:
        _bd[busqueda_id]["estado"] = "terminada"
        _bd[busqueda_id]["terminada_en"] = _ahora()


def _resumen(busqueda: dict) -> dict:
    global_, por_red, odio_por_red = {}, {}, {}
    for r in busqueda.get("registros", []):
        s = r["sentimiento"]
        global_[s] = global_.get(s, 0) + 1
        por_red.setdefault(r["red"], {})
        por_red[r["red"]][s] = por_red[r["red"]].get(s, 0) + 1
        if r["odio"]:
            odio_por_red[r["red"]] = odio_por_red.get(r["red"], 0) + 1

    return {
        "busqueda_id": busqueda["id"],
        "global": global_,
        "por_red": por_red,
        "odio_por_red": odio_por_red,
        "redes": busqueda.get("redes", []),
    }


def _publico(busqueda: dict) -> dict:
    return {k: busqueda[k] for k in ("id", "query", "estado", "creada_en", "terminada_en")}


class Manejador(BaseHTTPRequestHandler):

    def _responder(self, codigo: int, cuerpo) -> None:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_OPTIONS(self):  # noqa: N802 (nombre impuesto por la librería)
        self._responder(204, {})

    def do_GET(self):  # noqa: N802
        ruta = self.path.split("?")[0]

        if ruta == "/redes":
            return self._responder(200, REDES)

        m = re.fullmatch(r"/busquedas/(\d+)(/registros|/resumen)?", ruta)
        if not m:
            return self._responder(404, {"detail": "ruta desconocida"})

        with _candado:
            busqueda = _bd.get(int(m.group(1)))
        if busqueda is None:
            return self._responder(404, {"detail": "no existe esa busqueda"})

        cola = m.group(2)
        if cola == "/registros":
            return self._responder(200, busqueda.get("registros", []))
        if cola == "/resumen":
            return self._responder(200, _resumen(busqueda))
        return self._responder(200, _publico(busqueda))

    def do_POST(self):  # noqa: N802
        global _siguiente_id
        if self.path != "/busquedas":
            return self._responder(404, {"detail": "ruta desconocida"})

        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = json.loads(self.rfile.read(largo) or "{}")
        query = (cuerpo.get("query") or "").strip()
        redes = cuerpo.get("redes") or REDES

        if len(query) < 2:
            return self._responder(422, {"detail": "el query necesita al menos 2 caracteres"})

        with _candado:
            bid = _siguiente_id
            _siguiente_id += 1
            _bd[bid] = {
                "id": bid, "query": query, "estado": "en_curso",
                "creada_en": _ahora(), "terminada_en": None,
                "registros": [], "redes": [],
            }

        threading.Thread(target=_correr_busqueda, args=(bid, query, redes), daemon=True).start()
        with _candado:
            return self._responder(202, _publico(_bd[bid]))

    def log_message(self, formato, *args):
        print(f"  {self.command} {self.path}")


if __name__ == "__main__":
    print(f"Servidor de PRUEBA (datos falsos) en http://127.0.0.1:{PUERTO}")
    print("Ctrl-C para parar.\n")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()
