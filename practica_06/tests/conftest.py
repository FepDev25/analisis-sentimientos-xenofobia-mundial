"""Fixtures compartidas para los tests (navegador Playwright sin red)."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def navegador():
    """Un Chromium headless para toda la sesión de tests (sin red)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def pagina(navegador):
    """Una página en blanco por test; se llena con `set_content` (HTML local)."""
    contexto = navegador.new_context()
    page = contexto.new_page()
    yield page
    contexto.close()
