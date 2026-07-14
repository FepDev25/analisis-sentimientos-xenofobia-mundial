"""Captura asistida de TikTok desde una ventana visible de Playwright.

Uso:
    uv run --env-file .env python scripts/tiktok_captura_visible.py worldcup2026

El script abre TikTok con el perfil/cookies configurados. La persona resuelve
validaciones manuales y hace scroll; luego presiona Enter y se guardan los videos
visibles en el dataset. No intenta automatizar captchas.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from extractor_mundial.almacenamiento import Almacen
from extractor_mundial.config import DIR_DATA
from extractor_mundial.contrato import Registro
from extractor_mundial.lexico import cargar as cargar_lexico


DIR_CONFIG = Path(__file__).resolve().parents[1] / "config"


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


def _argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "hashtags",
        nargs="*",
        default=["worldcup2026"],
        help="hashtags sin #. Ejemplo: worldcup2026 Mundial2026",
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

    async with async_playwright() as p:
        context = await getattr(p, browser).launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=False,
        )
        await _agregar_cookies(context, _cargar_cookies())
        page = context.pages[0] if context.pages else await context.new_page()

        total_nuevos = 0
        try:
            for hashtag in args.hashtags:
                hashtag = hashtag.strip().lstrip("#")
                if not hashtag:
                    continue
                url = f"https://www.tiktok.com/tag/{hashtag}"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                except PlaywrightTimeoutError:
                    print("TikTok tardo en cargar; puedes continuar manualmente.")

                print(f"\nAbierto: {url}")
                print("Resuelve captcha si aparece y haz scroll para cargar videos.")
                print("Cuando la pagina tenga los videos visibles, presiona Enter aqui.")
                await asyncio.to_thread(input)

                items = await page.locator('a[href*="/video/"]').evaluate_all(
                    """els => els.map(a => ({
                        href: a.href,
                        text: (a.innerText || a.getAttribute("title") || "").trim()
                    }))"""
                )

                nuevos = 0
                vistos: set[str] = set()
                for item in items:
                    href = str(item.get("href") or "")
                    if not href or href in vistos:
                        continue
                    vistos.add(href)
                    texto = " ".join(str(item.get("text") or f"#{hashtag}").split())
                    estrategia = "dirigida" if lexico.es_dirigida(texto) else "amplia"
                    if almacen.agregar(
                        Registro(
                            id=href.rstrip("/").split("/")[-1],
                            red="tiktok",
                            estrategia=estrategia,
                            criterio_busqueda=f"#{hashtag}",
                            texto=texto,
                            idioma=None,
                            autor=None,
                            fecha_publicacion=None,
                            url=href,
                            metricas={},
                            fecha_extraccion=datetime.now(timezone.utc).isoformat(),
                        )
                    ):
                        nuevos += 1
                total_nuevos += nuevos
                print(f"Videos visibles guardados para #{hashtag}: {nuevos}")
        finally:
            for ruta in almacen.volcar():
                print(f"  - {ruta}")
            almacen.cerrar()
            await context.close()

    print(f"\nNuevos registros TikTok: {total_nuevos}")


if __name__ == "__main__":
    asyncio.run(main())
