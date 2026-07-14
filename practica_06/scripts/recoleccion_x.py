"""Recolección de X (Twitter) con Playwright — spike con caja de tiempo"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from extractor_mundial.almacenamiento import Almacen
from extractor_mundial.config import DIR_DATA, Criterio, cargar_config
from extractor_mundial.extractores.x import ExtractorX
from extractor_mundial.orquestador import ejecutar


# Queries curadas de los ejes que el tope de `criterios_dirigida` NO alcanza (el
# léxico es anti-negro en sus primeros ~40 términos). Palabras REALES buscables en X
# (sin emojis/leet, que rinden poco). Intercaladas por eje para que cada tanda rinda.
QUERIES_OTROS_EJES = [
    # anti-mexicano / migrante
    "Mexico frijolero", "sudacas", "no son franceses de verdad", "Japon ojos rasgados",
    "frijoleros", "Argentina sudaca", "France is not Africa", "francés de mierda",
    # sudamericano / regional
    "Mexico saltamuros", "Ecuador sudaca", "Africa won the World Cup", "japoneses slant eyes",
    "saltamuros", "puto argentino", "Francia colonizado", "europeo de mierda",
    # colonial / autenticidad
    "Mexico muevecoches", "boliviano de mierda", "vuelvan a África", "Japon sin alma asiática",
    "mexicano wetback", "ecuatoriano de mierda", "equipo africano ganó", "latino de mierda",
    "Mexico beaner", "sudamericanos inferiores", "diversidad importada",
    "mexicano de mierda", "argie", "Francia beur", "Brasil sudaca", "mejor equipo de África",
    "estos sudacas", "Africa won",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recolección de X con Playwright.")
    p.add_argument("--login", action="store_true",
                   help="captura la sesión con login manual (headful) y sale.")
    p.add_argument("--desde-perfil", action="store_true",
                   help="exporta la sesión desde un perfil de Chromium YA logueado (sin login).")
    p.add_argument("--perfil", type=str, default="~/.config/chromium",
                   help="user-data-dir del Chromium donde ya iniciaste sesión en X.")
    p.add_argument("--chromium-bin", type=str, default="/usr/bin/chromium",
                   help="binario de Chromium del sistema (el que cifró las cookies).")
    p.add_argument("--conectar-cdp", type=str, nargs="?", const="http://localhost:9222",
                   default=None,
                   help="exporta la sesión desde un Chromium YA ABIERTO con "
                        "--remote-debugging-port (default http://localhost:9222).")
    p.add_argument("--max-queries", type=int, default=None,
                   help="límite de consultas (modo spike; default: todas).")
    p.add_argument("--solo-dirigida", action="store_true",
                   help="usar SOLO las queries dirigida (evento × léxico), sin amplia.")
    p.add_argument("--otros-ejes", action="store_true",
                   help="preset curado de los ejes que el tope no alcanza "
                        "(anti-mexicano/sudamericano/colonial/asiático).")
    p.add_argument("--query", action="append", default=[], metavar="TEXTO",
                   help="query puntual a recolectar como dirigida (repetible). "
                        "Tiene prioridad sobre --solo-dirigida.")
    p.add_argument("--pausa", type=float, default=None,
                   help="segundos de pausa entre queries (default: el de config).")
    p.add_argument("--tanda", type=int, default=None, metavar="N",
                   help="correr en tandas de N queries con enfriamiento entre medio "
                        "(sobrevive al throttle de X). Sin esto, corre todo de una.")
    p.add_argument("--cooldown", type=float, default=10.0, metavar="MIN",
                   help="minutos de enfriamiento cuando una tanda rinde 0 (throttle).")
    p.add_argument("--espera-inicial", type=float, default=0.0, metavar="MIN",
                   help="minutos a esperar ANTES de arrancar (deja enfriar un throttle previo).")
    p.add_argument("--saltar-hechos", action="store_true",
                   help="saltar queries que YA están en el dataset (no re-pegarle a X).")
    p.add_argument("--por-query", type=int, default=None,
                   help="tope de tweets por query (default: el de config).")
    p.add_argument("--headless", action="store_true",
                   help="correr sin ventana (X lo detecta más fácil).")
    return p.parse_args()


def login(ruta: Path) -> None:
    """Abre Chromium visible, espera el login manual y guarda la sesión."""
    from playwright.sync_api import sync_playwright

    ruta.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)
        contexto = navegador.new_context()
        pagina = contexto.new_page()
        pagina.goto("https://x.com/login")
        input("→ Logueate en la ventana y pulsa ENTER aquí cuando estés DENTRO...")
        contexto.storage_state(path=str(ruta))
        navegador.close()
    print(f"[login] sesión guardada en {ruta}")


def exportar_de_perfil(ruta: Path, perfil: Path, ejecutable: str, headless: bool) -> bool:
    """Exporta la sesión de X desde un perfil de Chromium YA logueado.

    No hace login: abre el perfil real con el binario del sistema (mismo que cifró
    las cookies, así se descifran) y vuelca cookies+storage al storage_state.
    Devuelve True si al abrir x.com/home NO fuimos redirigidos al login.
    """
    from playwright.sync_api import sync_playwright

    ruta.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            user_data_dir=str(perfil),
            executable_path=ejecutable,
            headless=headless,
            args=["--disable-blink-features=AutomationControlled",
                  "--password-store=gnome-libsecret"],
        )
        try:
            pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
            pagina.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30_000)
            pagina.wait_for_timeout(3_000)
            url = pagina.url
            logueado = "/login" not in url and "/i/flow/login" not in url
            contexto.storage_state(path=str(ruta))
        finally:
            contexto.close()
    print(f"[perfil] sesión exportada a {ruta} (logueado={logueado}, url={url})")
    return logueado


def exportar_de_cdp(ruta: Path, url_cdp: str) -> bool:
    """Exporta la sesión desde un Chromium YA ABIERTO (por CDP).

    El navegador vivo ya descifró sus cookies; solo se las pedimos. Requiere haber
    lanzado Chromium con --remote-debugging-port=9222. Devuelve True si encontró la
    cookie de sesión de X (auth_token).
    """
    from playwright.sync_api import sync_playwright

    ruta.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.connect_over_cdp(url_cdp)
        if not navegador.contexts:
            navegador.close()
            raise RuntimeError("el navegador conectado no expone contextos/cookies")
        contexto = navegador.contexts[0]
        estado = contexto.storage_state(path=str(ruta))
        navegador.close()

    nombres = {c["name"] for c in estado["cookies"] if "x.com" in c.get("domain", "")}
    tiene_sesion = "auth_token" in nombres
    print(f"[cdp] sesión exportada a {ruta} "
          f"(cookies x.com: {len(nombres)}, auth_token: {tiene_sesion})")
    return tiene_sesion


def respaldar(dir_data: Path) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = dir_data / "backups" / ts
    destino.mkdir(parents=True, exist_ok=True)
    copiados = 0
    for nombre in ("dataset.jsonl", "dataset.csv", "dataset.json"):
        origen = dir_data / nombre
        if origen.exists():
            shutil.copy2(origen, destino / nombre)
            copiados += 1
    print(f"[backup] {copiados} archivos respaldados en {destino}")


def queries_hechas(dir_data: Path, red: str = "x") -> set[str]:
    """Criterios de búsqueda que YA tienen registros de `red` en el dataset."""
    import json

    jsonl = dir_data / "dataset.jsonl"
    hechas: set[str] = set()
    if not jsonl.exists():
        return hechas
    for linea in jsonl.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if d.get("red") == red and d.get("criterio_busqueda"):
            hechas.add(d["criterio_busqueda"])
    return hechas


def recolectar_resiliente(extractor, config, base, almacen, tanda, cooldown_min,
                          pausa, max_rondas=3) -> None:
    """Corre `base` en tandas y REINTENTA las queries que quedaron sin datos.

    Cada tanda se lanza por el orquestador de hilos (X = un hilo I/O-bound). Una query
    que no deja registros (throttle o sin resultados) se junta como "pendiente" y se
    reintenta en la siguiente ronda tras un enfriamiento — así el throttle no nos hace
    perder queries. Aditivo/reanudable: `Almacen` deduplica por (red, id).
    """
    pendientes = list(base)
    for ronda in range(1, max_rondas + 1):
        if not pendientes:
            break
        print(f"\n===== Ronda {ronda}/{max_rondas} | {len(pendientes)} queries pendientes =====")
        fallidas = []
        n_tandas = (len(pendientes) + tanda - 1) // tanda
        for i in range(0, len(pendientes), tanda):
            lote = pendientes[i : i + tanda]
            n = i // tanda + 1
            config.todos_los_criterios = lambda lote=lote: lote  # type: ignore[method-assign]
            antes = almacen.total
            print(f"\n--- Ronda {ronda} · Tanda {n}/{n_tandas} | {len(lote)} queries "
                  f"({lote[0].query!r} … {lote[-1].query!r}) ---")
            ejecutar([extractor], almacen.agregar)
            almacen.volcar()  # durabilidad al cierre de cada tanda
            ganados = almacen.total - antes
            hechas = queries_hechas(DIR_DATA, "x")
            fallidas.extend(c for c in lote if c.query not in hechas)
            print(f"[tanda {n}] +{ganados:,} tweets")
            if i + tanda < len(pendientes):  # no esperar tras la última tanda
                if ganados == 0:
                    print(f"[cooldown] tanda sin datos (throttle) → {cooldown_min:.0f} min...")
                    time.sleep(cooldown_min * 60)
                else:
                    time.sleep(pausa)
        pendientes = fallidas
        if pendientes and ronda < max_rondas:
            print(f"[ronda {ronda}] {len(pendientes)} sin datos → cooldown "
                  f"{cooldown_min:.0f} min y reintento")
            time.sleep(cooldown_min * 60)
    if pendientes:
        print(f"\n⚠ Tras {max_rondas} rondas, {len(pendientes)} queries sin datos "
              f"(throttle persistente o sin resultados reales): "
              f"{[c.query for c in pendientes]}")


def main() -> None:
    args = parse_args()
    config = cargar_config()
    if args.headless:
        config.x_headless = True
    if args.por_query:
        config.max_por_criterio = args.por_query
    if args.pausa is not None:
        config.x_pausa = args.pausa

    ruta = Path(config.x_sesion)
    if args.login:
        login(ruta)
        return

    if args.conectar_cdp:
        ok = exportar_de_cdp(ruta, args.conectar_cdp)
        if not ok:
            print("‼ No apareció auth_token de x.com. Asegurate de estar logueado en X "
                  "en ese Chromium y de haberlo abierto con --remote-debugging-port=9222.")
            sys.exit(1)
        return

    if args.desde_perfil:
        perfil = Path(args.perfil).expanduser()
        if not (perfil / "Default" / "Cookies").exists():
            print(f"‼ No encuentro cookies en {perfil}/Default. ¿Es el perfil correcto?")
            sys.exit(1)
        ok = exportar_de_perfil(ruta, perfil, args.chromium_bin, headless=config.x_headless)
        if not ok:
            print("‼ Al abrir x.com fuimos redirigidos al login: el perfil no tiene "
                  "sesión válida de X. Inicia sesión en ese Chromium y reintenta.")
            sys.exit(1)
        return

    if not ruta.exists():
        print(f"‼ No existe la sesión {ruta}. Corre primero:\n"
              "  uv run --group x python scripts/recoleccion_x.py --login")
        sys.exit(1)

    print("=== Recolección de X (Playwright) — spike ===")
    respaldar(DIR_DATA)

    extractor = ExtractorX(config)
    if args.query:
        base = [Criterio(q, "dirigida") for q in args.query]
    elif args.otros_ejes:
        base = [Criterio(q, "dirigida") for q in QUERIES_OTROS_EJES]
    elif args.solo_dirigida:
        base = config.criterios_dirigida()
    else:
        base = config.todos_los_criterios()
    if args.saltar_hechos:
        hechas = queries_hechas(DIR_DATA, red="x")
        antes = len(base)
        base = [c for c in base if c.query not in hechas]
        print(f"[saltar-hechos] {antes - len(base)} queries ya hechas omitidas; "
              f"quedan {len(base)}")
    if args.max_queries:
        base = base[: args.max_queries]

    if not base:
        print("‼ No quedan queries por recolectar. Nada que hacer.")
        return

    etiqueta = ("query" if args.query else "otros-ejes" if args.otros_ejes
                else "solo-dirigida" if args.solo_dirigida else "todos")
    print(f"[{etiqueta}] {len(base)} queries "
          f"(ej.: {base[0].query!r} … {base[-1].query!r})")

    almacen = Almacen(DIR_DATA)
    previos = almacen.previos
    print(f"[almacen] comentarios previos (todas las redes): {previos:,}")

    if args.espera_inicial:
        print(f"[espera-inicial] enfriando {args.espera_inicial:.0f} min antes de arrancar "
              "(throttle previo)...")
        time.sleep(args.espera_inicial * 60)

    if args.tanda:
        recolectar_resiliente(extractor, config, base, almacen,
                              args.tanda, args.cooldown, config.x_pausa)
    else:
        config.todos_los_criterios = lambda: base  # type: ignore[method-assign]
        ejecutar([extractor], almacen.agregar)

    rutas = almacen.volcar()
    almacen.cerrar()
    print(f"\n=== Fin. {almacen.total:,} comentarios totales "
          f"(+{almacen.total - previos:,} en esta corrida) ===")
    for r in rutas:
        print(f"  - {r}")


if __name__ == "__main__":
    sys.exit(main())
