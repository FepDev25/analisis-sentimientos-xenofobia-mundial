"""Abre TikTok en un perfil persistente de Playwright para iniciar sesion.

Uso:
    uv run --env-file .env python scripts/tiktok_login.py

La ventana que se abre usa el mismo perfil que el extractor si `TIKTOK_PROFILE_DIR`
apunta a la misma ruta. No imprime cookies ni credenciales.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright


def _env_bool(nombre: str, default: bool) -> bool:
    valor = os.environ.get(nombre)
    if valor is None:
        return default
    return valor.strip().lower() not in {"0", "false", "no", "off"}


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

    same_site = item.get("sameSite")
    if isinstance(same_site, str):
        mapa = {"no_restriction": "None", "unspecified": "Lax"}
        normalizado = mapa.get(same_site.lower(), same_site.capitalize())
        if normalizado in {"Strict", "Lax", "None"}:
            cookie["sameSite"] = normalizado

    return cookie


def _cargar_cookies_playwright() -> list[dict]:
    ruta = os.environ.get("TIKTOK_COOKIES_FILE", "").strip()
    if not ruta:
        return []
    archivo = _ruta_local(ruta)
    if not archivo.exists():
        print(f"No existe TIKTOK_COOKIES_FILE: {archivo}")
        return []

    data = json.loads(archivo.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [
            {"name": nombre, "value": valor, "domain": ".tiktok.com", "path": "/"}
            for nombre, valor in data.items()
        ]
    if not isinstance(data, list):
        print("TIKTOK_COOKIES_FILE no tiene formato JSON esperado.")
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
        print(f"Cookies TikTok cargadas en Playwright: {agregadas}/{len(cookies)}")


async def main() -> None:
    browser = os.environ.get("TIKTOK_BROWSER", "chromium").strip() or "chromium"
    profile_dir = os.environ.get("TIKTOK_PROFILE_DIR", ".playwright/tiktok-profile")
    profile_path = Path(profile_dir)
    if not profile_path.is_absolute():
        profile_path = Path.cwd() / profile_path
    profile_path.mkdir(parents=True, exist_ok=True)

    headless = _env_bool("TIKTOK_HEADLESS", False)
    if headless:
        print("TIKTOK_HEADLESS=true: cambiando a ventana visible para iniciar sesion.")
        headless = False

    async with async_playwright() as p:
        browser_type = getattr(p, browser)
        context = await browser_type.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=headless,
        )
        await _agregar_cookies(context, _cargar_cookies_playwright())
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.goto(
                "https://www.tiktok.com",
                wait_until="domcontentloaded",
                timeout=90_000,
            )
        except PlaywrightTimeoutError:
            print("TikTok tardo en cargar, pero la ventana queda abierta igual.")
        print("Se abrio TikTok con el perfil persistente:")
        print(f"  {profile_path}")
        print("Inicia sesion en la ventana. Cuando termines, vuelve aqui y presiona Enter.")
        await asyncio.to_thread(input)
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
