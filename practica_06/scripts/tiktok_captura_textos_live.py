"""Captura asistida en vivo de textos visibles de TikTok.

Uso:
    uv run --env-file .env python scripts/tiktok_captura_textos_live.py
    uv run --env-file .env python scripts/tiktok_captura_textos_live.py --buscar "vinicius mono"

La persona navega, abre videos/comentarios y hace scroll. El script toma
snapshots periódicos del DOM visible y guarda textos candidatos en el dataset.
No resuelve captchas ni simula interacción humana.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from extractor_mundial.almacenamiento import Almacen
from extractor_mundial.config import DIR_DATA
from extractor_mundial.contrato import Registro
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
    "company",
    "program",
    "terms & policies",
    "comments",
    "you may like",
    "log in",
    "follow",
    "following",
    "reply",
    "share",
    "copy link",
    "report",
    "see translation",
    "original sound",
}

UI_CONTIENE = (
    "drag the slider",
    "maximum number of attempts",
    "try again later",
    "keyboard shortcuts",
    "privacy policy",
    "terms of service",
)

USUARIO_RE = re.compile(r"^@?[A-Za-z0-9_.]{3,32}$")
METRICA_RE = re.compile(r"^[\d\s.,]+[KMBkmb]?$")
FECHA_RE = re.compile(r"^(\d+[smhdw]|[A-Za-z]{3,9} \d{1,2}|yesterday)$")


def _ruta_local(valor: str) -> Path:
    ruta = Path(valor).expanduser()
    if not ruta.is_absolute():
        ruta = Path.cwd() / ruta
    return ruta


def _cookie_playwright(item: dict) -> dict | None:
    nombre = item.get("name")
    valor = item.get("value")
    if not nombre or valor is None:
        return None

    cookie = {
        "name": str(nombre),
        "value": str(valor),
        "path": str(item.get("path") or "/"),
    }
    if str(nombre).startswith("__Host-"):
        cookie["url"] = "https://www.tiktok.com"
    else:
        domain = str(item.get("domain") or ".tiktok.com")
        if "tiktok.com" not in domain:
            return None
        cookie["domain"] = domain

    if "expirationDate" in item:
        cookie["expires"] = float(item["expirationDate"])
    elif "expires" in item and item["expires"] not in (-1, None):
        cookie["expires"] = float(item["expires"])
    if "httpOnly" in item:
        cookie["httpOnly"] = bool(item["httpOnly"])
    if "secure" in item:
        cookie["secure"] = bool(item["secure"])
    return cookie


def _cargar_cookies() -> list[dict]:
    ruta = os.environ.get("TIKTOK_COOKIES_FILE", "").strip()
    if not ruta:
        return []
    archivo = _ruta_local(ruta)
    if not archivo.exists():
        return []
    data = json.loads(archivo.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [
            {"name": nombre, "value": valor, "domain": ".tiktok.com", "path": "/"}
            for nombre, valor in data.items()
        ]
    if not isinstance(data, list):
        return []
    return [
        cookie
        for item in data
        if isinstance(item, dict)
        for cookie in [_cookie_playwright(item)]
        if cookie is not None
    ]


async def _agregar_cookies(context, cookies: list[dict]) -> None:
    agregadas = 0
    for cookie in cookies:
        try:
            await context.add_cookies([cookie])
            agregadas += 1
        except Exception:
            continue
    if cookies:
        print(f"Cookies TikTok cargadas: {agregadas}/{len(cookies)}")


def _normalizar_texto(texto: str) -> str:
    return " ".join(texto.replace("\u00a0", " ").split())


def _es_ruido(texto: str, con_lexico: bool, min_len: int) -> bool:
    t = _normalizar_texto(texto)
    if not t:
        return True
    low = t.lower()
    if low in UI_EXACTO:
        return True
    if any(p in low for p in UI_CONTIENE):
        return True
    if METRICA_RE.match(t) or FECHA_RE.match(low):
        return True
    if len(t) < min_len and not con_lexico:
        return True
    if USUARIO_RE.match(t) and not con_lexico:
        return True
    if t.startswith("http"):
        return True
    return False


async def _extraer_textos_visibles(page) -> list[str]:
    return await page.evaluate(
        """() => {
            const selectors = [
              '[data-e2e*="comment"]',
              '[class*="Comment"]',
              '[class*="comment"]',
              '[data-e2e*="description"]',
              '[data-e2e*="video-desc"]',
              '[data-e2e*="browse-video-desc"]',
              'div[dir="auto"]',
              'span[dir="auto"]',
              'p',
              'h1',
              'h2'
            ];
            const seen = new Set();
            const out = [];
            const visible = (el) => {
              const r = el.getBoundingClientRect();
              const style = window.getComputedStyle(el);
              return r.width > 0 && r.height > 0 &&
                r.bottom >= 0 && r.top <= window.innerHeight &&
                style.visibility !== 'hidden' && style.display !== 'none';
            };
            for (const el of document.querySelectorAll(selectors.join(','))) {
              if (!visible(el)) continue;
              const text = (el.innerText || el.textContent || '').trim();
              if (!text || seen.has(text)) continue;
              seen.add(text);
              out.push(text);
            }
            return out;
        }"""
    )


def _argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--buscar", help="abre una búsqueda inicial en TikTok")
    p.add_argument("--url", help="abre una URL inicial específica")
    p.add_argument("--criterio", default="captura_manual_tiktok")
    p.add_argument("--intervalo", type=float, default=2.0)
    p.add_argument("--min-len", type=int, default=12)
    p.add_argument(
        "--solo-dirigida",
        action="store_true",
        help="guarda solo textos que disparan el léxico xenófobo",
    )
    return p.parse_args()


async def main() -> None:
    args = _argumentos()
    browser = os.environ.get("TIKTOK_BROWSER", "chromium").strip() or "chromium"
    profile_dir = os.environ.get("TIKTOK_PROFILE_DIR", ".playwright/tiktok-profile")
    profile_path = _ruta_local(profile_dir)
    profile_path.mkdir(parents=True, exist_ok=True)

    lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")
    almacen = Almacen(DIR_DATA)
    vistos: set[str] = set()
    nuevos = 0
    capturas = 0
    detener = asyncio.Event()

    if args.url:
        inicial = args.url
    elif args.buscar:
        inicial = f"https://www.tiktok.com/search?q={quote_plus(args.buscar)}"
    else:
        inicial = "https://www.tiktok.com"

    async with async_playwright() as p:
        context = await getattr(p, browser).launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=False,
        )
        await _agregar_cookies(context, _cargar_cookies())
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            await page.goto(inicial, wait_until="domcontentloaded", timeout=90_000)
        except PlaywrightTimeoutError:
            print("TikTok tardo en cargar; continua manualmente.")

        async def capturar_loop() -> None:
            nonlocal nuevos, capturas
            while not detener.is_set():
                capturas += 1
                try:
                    textos = await _extraer_textos_visibles(page)
                except Exception:
                    await asyncio.sleep(args.intervalo)
                    continue

                agregados = 0
                for bruto in textos:
                    texto = _normalizar_texto(bruto)
                    con_lexico = lexico.es_dirigida(texto)
                    if _es_ruido(texto, con_lexico, args.min_len):
                        continue
                    if args.solo_dirigida and not con_lexico:
                        continue

                    url_actual = page.url
                    clave = hashlib.sha1(
                        f"{url_actual}|{texto}".encode("utf-8")
                    ).hexdigest()[:20]
                    if clave in vistos:
                        continue
                    vistos.add(clave)

                    estrategia = "dirigida" if con_lexico else "amplia"
                    if almacen.agregar(
                        Registro(
                            id=f"visible-{clave}",
                            red="tiktok",
                            estrategia=estrategia,
                            criterio_busqueda=args.criterio,
                            texto=texto,
                            idioma=None,
                            autor=None,
                            fecha_publicacion=None,
                            url=url_actual,
                            metricas={"captura": "visible_live"},
                            fecha_extraccion=datetime.now(timezone.utc).isoformat(),
                        )
                    ):
                        nuevos += 1
                        agregados += 1

                if agregados:
                    print(
                        f"captura {capturas}: +{agregados} textos "
                        f"(total nuevos: {nuevos})"
                    )
                await asyncio.sleep(args.intervalo)

        tarea = asyncio.create_task(capturar_loop())
        print("\nCaptura en vivo iniciada.")
        print("Abre videos, abre comentarios, busca términos y haz scroll manualmente.")
        print("Presiona Enter en esta terminal para detener y guardar.")
        await asyncio.to_thread(input)
        detener.set()
        await tarea

        for ruta in almacen.volcar():
            print(f"  - {ruta}")
        almacen.cerrar()
        await context.close()

    print(f"\nCapturas tomadas: {capturas}")
    print(f"Nuevos textos TikTok guardados: {nuevos}")


if __name__ == "__main__":
    asyncio.run(main())
