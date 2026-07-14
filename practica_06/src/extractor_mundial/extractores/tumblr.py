"""Extractor de Tumblr — publicaciones públicas por etiqueta.

Tumblr permite consultar publicaciones públicas mediante el endpoint `/v2/tagged`
usando una OAuth Consumer Key como `api_key`.

La búsqueda de Tumblr funciona por etiquetas, no por texto libre. Por eso cada
criterio del proyecto se normaliza como etiqueta y luego el texto recuperado se
clasifica como amplio o dirigido usando el léxico común.
"""

from __future__ import annotations

import html
import os
import re
import sys
import time
from collections.abc import Iterator
from datetime import datetime, timezone

import requests

from ..config import Criterio, DIR_CONFIG
from ..contrato import Registro
from ..lexico import cargar as cargar_lexico
from .base import ExtractorBase

API = "https://api.tumblr.com/v2/tagged"


class FaltanCredenciales(RuntimeError):
    """El archivo .env no contiene la Consumer Key de Tumblr."""


class ExtractorTumblr(ExtractorBase):
    red = "tumblr"

    _POR_PAGINA = 20
    _TIMEOUT = 30
    _PAUSA = 0.25
    _BACKOFF = (5, 15, 30)

    def __init__(self, config) -> None:
        super().__init__(config)
        self._api_key = os.environ.get("TUMBLR_API_KEY", "").strip()
        self._lexico = cargar_lexico(DIR_CONFIG / "lexico.txt")
        self._sesion = requests.Session()

    def _validar_credenciales(self) -> None:
        if not self._api_key:
            raise FaltanCredenciales(
                "falta TUMBLR_API_KEY. Copia .env.example a .env, agrega la "
                "OAuth Consumer Key y ejecuta con "
                "`uv run --env-file .env extractor-mundial`"
            )

    @staticmethod
    def _normalizar_etiqueta(query: str) -> str:
        """Convierte una consulta del proyecto en una etiqueta válida para Tumblr."""
        etiqueta = query.strip().lstrip("#")
        etiqueta = re.sub(r"\s+", " ", etiqueta)
        return etiqueta[:250]

    @staticmethod
    def _limpiar_html(texto: str) -> str:
        texto = re.sub(r"<[^>]+>", " ", texto or "")
        texto = html.unescape(texto)
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    def _extraer_texto(self, post: dict) -> str:
        """Obtiene texto útil evitando repetir el mismo contenido."""
        candidatos: list[str] = []

        for campo in (
            "summary",
            "caption",
            "body",
            "description",
            "question",
            "answer",
        ):
            valor = post.get(campo)
            if isinstance(valor, str) and valor.strip():
                candidatos.append(valor)

        for elemento in post.get("trail") or []:
            if not isinstance(elemento, dict):
                continue
            contenido = elemento.get("content")
            if isinstance(contenido, str) and contenido.strip():
                candidatos.append(contenido)

        for bloque in post.get("content") or []:
            if not isinstance(bloque, dict):
                continue
            valor = bloque.get("text")
            if isinstance(valor, str) and valor.strip():
                candidatos.append(valor)

        # Tumblr suele repetir el mismo texto en varios campos.
        partes: list[str] = []
        normalizados: set[str] = set()

        for candidato in candidatos:
            limpio = self._limpiar_html(candidato)
            if not limpio:
                continue

            clave = limpio.casefold()
            if clave in normalizados:
                continue

            # Evitar guardar una versión corta cuando ya está contenida
            # completamente dentro de otra más extensa.
            if any(clave in existente or existente in clave for existente in normalizados):
                if any(clave in existente for existente in normalizados):
                    continue

                partes = [
                    parte
                    for parte in partes
                    if parte.casefold() not in clave
                ]
                normalizados = {parte.casefold() for parte in partes}

            partes.append(limpio)
            normalizados.add(clave)

        return " ".join(partes).strip()

    def _pagina(self, etiqueta: str, before: int | None = None) -> list[dict]:
        params = {
            "tag": etiqueta,
            "api_key": self._api_key,
            "limit": self._POR_PAGINA,
            "filter": "text",
        }
        if before is not None:
            params["before"] = before

        for espera in (0, *self._BACKOFF):
            if espera:
                print(f"[tumblr] rate limit; espero {espera}s", file=sys.stderr)
                time.sleep(espera)

            respuesta = self._sesion.get(
                API,
                params=params,
                timeout=self._TIMEOUT,
            )

            if respuesta.status_code == 429:
                continue

            respuesta.raise_for_status()
            return respuesta.json().get("response") or []

        raise RuntimeError("rate limit sostenido de Tumblr tras varios reintentos")

    def _buscar(self, etiqueta: str, limite: int) -> Iterator[dict]:
        emitidos = 0
        before: int | None = None
        ids_vistos: set[str] = set()

        while emitidos < limite:
            posts = self._pagina(etiqueta, before)
            if not posts:
                return

            fechas: list[int] = []

            for post in posts:
                post_id = str(post.get("id") or "")
                if not post_id or post_id in ids_vistos:
                    continue

                ids_vistos.add(post_id)
                yield post
                emitidos += 1

                timestamp = post.get("timestamp")
                if isinstance(timestamp, int):
                    fechas.append(timestamp)

                if emitidos >= limite:
                    return

            if not fechas:
                return

            nuevo_before = min(fechas)
            if before is not None and nuevo_before >= before:
                return

            before = nuevo_before
            time.sleep(self._PAUSA)

    def _dentro_de_ventana(self, timestamp) -> bool:
        """Filtra según config.inicio y config.fin."""
        if not isinstance(timestamp, int):
            return True

        fecha = datetime.fromtimestamp(timestamp, tz=timezone.utc).date()

        try:
            inicio = datetime.fromisoformat(self.config.inicio).date()
            fin = datetime.fromisoformat(self.config.fin).date()
        except (TypeError, ValueError):
            return True

        return inicio <= fecha <= fin

    @staticmethod
    def _fecha_iso(timestamp) -> str | None:
        if not isinstance(timestamp, int):
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    @staticmethod
    def _es_contexto_futbol(texto: str, etiquetas: list[str]) -> bool:
        """Comprueba que la publicación tenga contexto futbolístico explícito."""
        contenido = f"{texto} {' '.join(etiquetas)}".casefold()

        patrones = (
            r"\bf[uú]tbol\b",
            r"\bfootball\b",
            r"\bsoccer\b",
            r"\bfutebol\b",
            r"\bworld cup\b",
            r"\bfifa\b",
            r"\bmundial(?: de f[uú]tbol)?\b",
            r"\bcopa do mundo\b",
            r"\bcopa del mundo\b",
            r"\bfutbolista(?:s)?\b",
            r"\bfootballer(?:s)?\b",
            r"\bjugador(?:es)? de f[uú]tbol\b",
            r"\bselecci[oó]n (?:nacional|de f[uú]tbol)\b",
            r"\bnational football team\b",
            r"\bfootball team\b",
            r"\bfootball club\b",
            r"\bclub de f[uú]tbol\b",
            r"\bfootball fans?\b",
            r"\bafici[oó]n(?:ados?)?\b",
            r"\bfootball stadium\b",
            r"\bestadio de f[uú]tbol\b",
            r"\bfootball referee\b",
            r"\b[aá]rbitro de f[uú]tbol\b",
            r"\bmbapp[eé]\b",
            r"\bmessi\b",
            r"\bvinicius\b",
            r"\blamine yamal\b",
        )

        return any(re.search(patron, contenido) for patron in patrones)


    def _a_registro(self, post: dict, criterio: Criterio) -> Registro | None:
        texto = self._extraer_texto(post)
        if not texto:
            return None

        if not self._dentro_de_ventana(post.get("timestamp")):
            return None

        tags = post.get("tags") or []

        # Tumblr contiene mucho material sobre racismo que no pertenece al fútbol.
        # Se conserva únicamente lo relacionado con el evento o el deporte.
        if not self._es_contexto_futbol(texto, tags):
            return None

        # Las etiquetas temáticas ya expresan una búsqueda dirigida. También se
        # marca como dirigida cualquier publicación que contenga términos del léxico.
        etiquetas_dirigidas = {
            "racismo",
            "racism",
            "xenophobia",
            "xenofobia",
            "football racism",
            "racial abuse",
            "racist football",
            "anti racism",
        }

        estrategia = (
            "dirigida"
            if (
                criterio.query.casefold() in etiquetas_dirigidas
                or self._lexico.es_dirigida(texto)
            )
            else "amplia"
        )

        blog_name = post.get("blog_name")
        post_id = str(post.get("id") or "")
        if not post_id:
            return None

        return Registro(
            id=post_id,
            red=self.red,
            estrategia=estrategia,
            criterio_busqueda=criterio.query,
            texto=texto,
            idioma=None,
            autor=blog_name,
            fecha_publicacion=self._fecha_iso(post.get("timestamp")),
            url=post.get("post_url"),
            metricas={
                "notas": post.get("note_count"),
                "tipo": post.get("type"),
                "etiquetas": tags,
            },
        )

    def extraer(self) -> Iterator[Registro]:
        self._validar_credenciales()

        total = 0
        claves_emitidas: set[tuple[str, str]] = set()

        etiquetas = self.config.etiquetas_tumblr
        if not etiquetas:
            etiquetas = [
                "racismo",
                "racism",
                "xenophobia",
                "football racism",
                "world cup",
                "football",
                "futbol",
                "futebol",
            ]

        for etiqueta_original in etiquetas:
            if total >= self.config.max_total_por_red:
                break

            etiqueta = self._normalizar_etiqueta(etiqueta_original)
            if not etiqueta:
                continue

            restante = self.config.max_total_por_red - total
            limite = min(self.config.max_por_criterio, restante)

            criterio = Criterio(
                query=etiqueta_original,
                estrategia=(
                    "dirigida"
                    if self._lexico.es_dirigida(etiqueta_original)
                    or etiqueta_original.casefold()
                    in {
                        "racismo",
                        "racism",
                        "xenophobia",
                        "xenofobia",
                        "football racism",
                        "racial abuse",
                        "racist football",
                    }
                    else "amplia"
                ),
            )

            try:
                for post in self._buscar(etiqueta, limite):
                    registro = self._a_registro(post, criterio)
                    if registro is None or registro.clave in claves_emitidas:
                        continue

                    claves_emitidas.add(registro.clave)
                    yield registro
                    total += 1

                    if total >= self.config.max_total_por_red:
                        return

            except requests.RequestException as e:
                print(
                    f"[tumblr] etiqueta {etiqueta!r} omitida "
                    f"({type(e).__name__}: {e})",
                    file=sys.stderr,
                )
                continue

