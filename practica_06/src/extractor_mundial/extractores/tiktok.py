"""Extractor de TikTok - comentarios de videos encontrados por hashtag.

TikTok no ofrece una API publica simple para busqueda abierta. Para la practica
se usa `TikTokApi`, una libreria no oficial basada en Playwright. La extraccion
sigue el mismo contrato que las demas fuentes: el extractor solo produce
`Registro`s; el orquestador decide hilos, cola y persistencia.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from ..config import DIR_CONFIG
from ..contrato import Registro
from ..lexico import cargar as cargar_lexico
from .base import ExtractorBase


class TikTokNoDisponible(RuntimeError):
    """Faltan dependencias o credenciales para consultar TikTok."""


def _normalizar_hashtag(valor: str) -> str:
    return valor.strip().lstrip("#").replace(" ", "")


def _iso_desde_timestamp(valor) -> str | None:
    try:
        if valor is None:
            return None
        return datetime.fromtimestamp(int(valor), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _env_bool(nombre: str, default: bool) -> bool:
    valor = os.environ.get(nombre)
    if valor is None:
        return default
    return valor.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(nombre: str, default: int) -> int:
    valor = os.environ.get(nombre)
    if valor is None:
        return default
    try:
        return int(valor)
    except ValueError:
        return default


def _ruta_local(valor: str) -> Path:
    ruta = Path(valor).expanduser()
    if not ruta.is_absolute():
        ruta = Path.cwd() / ruta
    return ruta


def _cargar_cookies() -> dict[str, str] | None:
    ruta = os.environ.get("TIKTOK_COOKIES_FILE", "").strip()
    if not ruta:
        return None
    archivo = _ruta_local(ruta)
    if not archivo.exists():
        raise TikTokNoDisponible(f"no existe TIKTOK_COOKIES_FILE: {archivo}")

    data = json.loads(archivo.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items() if v is not None}

    if isinstance(data, list):
        cookies: dict[str, str] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            domain = str(item.get("domain") or "")
            if domain and "tiktok.com" not in domain:
                continue
            nombre = item.get("name")
            valor = item.get("value")
            if nombre and valor is not None:
                cookies[str(nombre)] = str(valor)
        return cookies

    raise TikTokNoDisponible(
        "TIKTOK_COOKIES_FILE debe ser un JSON objeto o una lista exportada "
        "desde el navegador."
    )


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
        raise TikTokNoDisponible(f"no existe TIKTOK_COOKIES_FILE: {archivo}")

    data = json.loads(archivo.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [
            {"name": nombre, "value": valor, "domain": ".tiktok.com", "path": "/"}
            for nombre, valor in data.items()
        ]
    if not isinstance(data, list):
        raise TikTokNoDisponible(
            "TIKTOK_COOKIES_FILE debe ser un JSON objeto o una lista exportada "
            "desde el navegador."
        )

    return [
        cookie
        for item in data
        if isinstance(item, dict)
        for cookie in [_cookie_playwright(item)]
        if cookie is not None
    ]


async def _agregar_cookies_contexto(context, cookies: list[dict]) -> None:
    for cookie in cookies:
        try:
            await context.add_cookies([cookie])
        except Exception:
            continue


class ExtractorTikTok(ExtractorBase):
    red = "tiktok"

    def __init__(self, config) -> None:
        super().__init__(config)
        self._lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")

    def extraer(self) -> Iterator[Registro]:
        try:
            registros = asyncio.run(self._extraer_async())
        except ImportError as e:
            raise TikTokNoDisponible(
                "falta TikTokApi/playwright. Ejecuta `uv sync` y luego "
                "`python -m playwright install chromium`."
            ) from e
        for registro in registros:
            yield registro

    async def _extraer_async(self) -> list[Registro]:
        modo = os.environ.get("TIKTOK_MODE", "api").strip().lower()
        if modo == "playwright":
            return await self._extraer_playwright()

        from TikTokApi import TikTokApi

        cookies = _cargar_cookies()
        ms_token = (
            os.environ.get("TIKTOK_MS_TOKEN")
            or os.environ.get("ms_token")
            or (cookies or {}).get("msToken")
            or ""
        ).strip()
        if not ms_token:
            raise TikTokNoDisponible(
                "falta TIKTOK_MS_TOKEN o un TIKTOK_COOKIES_FILE con msToken."
            )

        hashtags = self._hashtags_objetivo()
        if not hashtags:
            return []

        browser = os.environ.get("TIKTOK_BROWSER", "chromium")
        headless = _env_bool("TIKTOK_HEADLESS", True)
        timeout_ms = _env_int("TIKTOK_TIMEOUT_MS", 90_000)
        profile_dir = os.environ.get("TIKTOK_PROFILE_DIR", "").strip()
        browser_context_factory = None
        if profile_dir:
            profile_path = _ruta_local(profile_dir)
            profile_path.mkdir(parents=True, exist_ok=True)

            async def _contexto_persistente(playwright):
                browser_type = getattr(playwright, browser)
                return await browser_type.launch_persistent_context(
                    user_data_dir=str(profile_path),
                    headless=headless,
                )

            browser_context_factory = _contexto_persistente

        registros: list[Registro] = []
        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[ms_token],
                num_sessions=1,
                sleep_after=3,
                browser=browser,
                headless=headless,
                browser_context_factory=browser_context_factory,
                cookies=[cookies] if cookies else None,
                timeout=timeout_ms,
            )
            for hashtag in hashtags:
                if len(registros) >= self.config.max_total_por_red:
                    break
                nuevos = await self._extraer_hashtag(api, hashtag)
                registros.extend(nuevos)
        return registros[: self.config.max_total_por_red]

    async def _extraer_playwright(self) -> list[Registro]:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright

        browser = os.environ.get("TIKTOK_BROWSER", "chromium")
        headless = _env_bool("TIKTOK_HEADLESS", False)
        timeout_ms = _env_int("TIKTOK_TIMEOUT_MS", 90_000)
        profile_dir = os.environ.get("TIKTOK_PROFILE_DIR", "").strip()
        if not profile_dir:
            raise TikTokNoDisponible(
                "TIKTOK_MODE=playwright requiere TIKTOK_PROFILE_DIR para reutilizar "
                "la sesion/cookies del navegador."
            )

        profile_path = _ruta_local(profile_dir)
        profile_path.mkdir(parents=True, exist_ok=True)

        registros: list[Registro] = []
        vistos: set[str] = set()
        async with async_playwright() as p:
            browser_type = getattr(p, browser)
            context = await browser_type.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=headless,
            )
            await _agregar_cookies_contexto(context, _cargar_cookies_playwright())
            page = context.pages[0] if context.pages else await context.new_page()
            page.set_default_timeout(timeout_ms)
            try:
                for hashtag in self._hashtags_objetivo():
                    if len(registros) >= self.config.max_total_por_red:
                        break
                    nuevos = await self._extraer_hashtag_playwright(
                        page, hashtag, vistos
                    )
                    registros.extend(nuevos)
                    if len(registros) >= self.config.max_total_por_red:
                        break
            finally:
                await context.close()

        return registros[: self.config.max_total_por_red]

    async def _extraer_hashtag_playwright(
        self, page, hashtag: str, vistos: set[str]
    ) -> list[Registro]:
        criterio = f"#{hashtag}"
        url = f"https://www.tiktok.com/tag/{hashtag}"
        try:
            await page.goto(url, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            pass

        await page.wait_for_timeout(5_000)
        body = await page.locator("body").inner_text(timeout=10_000)
        if "Drag the slider" in body or "Maximum number of attempts" in body:
            raise TikTokNoDisponible(
                "TikTok pide verificacion manual/captcha en la ventana de Playwright. "
                "Ejecuta `python scripts/tiktok_login.py`, resuelve la validacion, "
                "presiona Enter y vuelve a correr."
            )

        for _ in range(3):
            await page.mouse.wheel(0, 1800)
            await page.wait_for_timeout(1_500)

        items = await page.locator('a[href*="/video/"]').evaluate_all(
            """els => els.map(a => ({
                href: a.href,
                text: (a.innerText || a.getAttribute("title") || "").trim()
            }))"""
        )

        registros: list[Registro] = []
        for item in items:
            if len(registros) >= self.config.max_por_criterio:
                break
            href = str(item.get("href") or "")
            if not href or href in vistos:
                continue
            vistos.add(href)
            texto = " ".join(str(item.get("text") or criterio).split())
            con_lexico = self._lexico.es_dirigida(texto)
            registros.append(
                Registro(
                    id=href.rstrip("/").split("/")[-1],
                    red=self.red,
                    estrategia="dirigida" if con_lexico else "amplia",
                    criterio_busqueda=criterio,
                    texto=texto,
                    idioma=None,
                    autor=None,
                    fecha_publicacion=None,
                    url=href,
                    metricas={},
                    fecha_extraccion=datetime.now(timezone.utc).isoformat(),
                )
            )
        return registros

    def _hashtags_objetivo(self) -> list[str]:
        """Hashtags viables para TikTok.

        TikTokApi soporta videos por hashtag. Se usan los hashtags explicitos de
        la configuracion y, ademas, selecciones/jugadores normalizados como
        hashtags porque en TikTok suelen aparecer sin espacios.
        """
        candidatos = [
            *self.config.hashtags_torneo,
            *self.config.hashtags_partido,
            *self.config.selecciones,
            *self.config.jugadores,
        ]
        vistos: set[str] = set()
        salida: list[str] = []
        for valor in candidatos:
            hashtag = _normalizar_hashtag(valor)
            if not hashtag:
                continue
            clave = hashtag.lower()
            if clave in vistos:
                continue
            vistos.add(clave)
            salida.append(hashtag)
        return salida

    async def _extraer_hashtag(self, api, hashtag: str) -> list[Registro]:
        registros: list[Registro] = []
        videos_revisados = 0
        criterio = f"#{hashtag}"
        async for video in api.hashtag(name=hashtag).videos(count=self.config.max_videos):
            if len(registros) >= self.config.max_por_criterio:
                break
            if videos_revisados >= self.config.max_videos:
                break
            videos_revisados += 1
            restantes = self.config.max_por_criterio - len(registros)
            registros.extend(await self._comentarios_video(video, criterio, restantes))
        return registros

    async def _comentarios_video(
        self, video, criterio: str, restantes: int
    ) -> list[Registro]:
        registros: list[Registro] = []
        video_data = getattr(video, "as_dict", {}) or {}
        video_id = str(getattr(video, "id", "") or video_data.get("id") or "")
        video_url = getattr(video, "url", None) or (
            f"https://www.tiktok.com/@/video/{video_id}" if video_id else None
        )

        async for comentario in video.comments(count=restantes):
            d = getattr(comentario, "as_dict", {}) or {}
            texto = (
                getattr(comentario, "text", None)
                or d.get("text")
                or d.get("comment")
                or ""
            ).strip()
            if not texto:
                continue

            comentario_id = str(
                getattr(comentario, "id", "") or d.get("cid") or d.get("id") or ""
            )
            if not comentario_id:
                comentario_id = f"{video_id}:{len(registros)}"

            autor = self._autor_comentario(comentario, d)
            con_lexico = self._lexico.es_dirigida(texto)
            stats = video_data.get("stats") or {}
            registros.append(
                Registro(
                    id=comentario_id,
                    red=self.red,
                    estrategia="dirigida" if con_lexico else "amplia",
                    criterio_busqueda=criterio,
                    texto=texto,
                    idioma=None,
                    autor=autor,
                    fecha_publicacion=_iso_desde_timestamp(d.get("create_time")),
                    url=video_url,
                    metricas={
                        "likes": getattr(comentario, "likes_count", None)
                        or d.get("digg_count"),
                        "video_id": video_id,
                        "video_likes": stats.get("diggCount"),
                        "video_comentarios": stats.get("commentCount"),
                        "video_compartidos": stats.get("shareCount"),
                    },
                )
            )
            if len(registros) >= restantes:
                break
        return registros

    @staticmethod
    def _autor_comentario(comentario, data: dict) -> str | None:
        autor = getattr(comentario, "author", None)
        if autor is not None:
            username = getattr(autor, "username", None)
            if username:
                return username
        user = data.get("user") or {}
        return user.get("unique_id") or user.get("nickname")
