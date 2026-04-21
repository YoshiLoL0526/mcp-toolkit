"""
Singleton de Playwright: una única instancia de Chromium compartida
por todas las llamadas a web_search para evitar overhead de inicio.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from mcp_toolkit.utils.logging import get_logger

logger = get_logger(__name__)

_playwright: Playwright | None = None
_browser: Browser | None = None
_lock = asyncio.Lock()


async def _get_browser() -> Browser:
    global _playwright, _browser

    async with _lock:
        if _browser is None or not _browser.is_connected():
            if _playwright is None:
                _playwright = await async_playwright().start()

            logger.info("Lanzando browser Chromium")
            try:
                _browser = await _playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                )
            except Exception:
                logger.exception("Error al lanzar Chromium")
                raise

    return _browser


@asynccontextmanager
async def get_context(
    *,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    timeout_ms: int = 30_000,
) -> AsyncIterator[BrowserContext]:
    """
    Context manager que devuelve un BrowserContext limpio y lo cierra al salir.
    Cada llamada a web_search obtiene su propio contexto aislado.
    """
    browser = await _get_browser()
    context = await browser.new_context(
        viewport={"width": viewport_width, "height": viewport_height},
        java_script_enabled=True,
        ignore_https_errors=True,
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    )
    context.set_default_timeout(timeout_ms)
    try:
        yield context
    finally:
        await context.close()


async def shutdown_browser() -> None:
    """Cierra el browser y Playwright de forma limpia al apagar el servidor."""
    global _playwright, _browser

    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            logger.exception("Error al cerrar el browser")
        _browser = None

    if _playwright is not None:
        try:
            await _playwright.stop()
        except Exception:
            logger.exception("Error al detener Playwright")
        _playwright = None
