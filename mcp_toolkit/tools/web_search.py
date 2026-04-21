"""
Herramienta web_search: busca en DuckDuckGo vía httpx y,
opcionalmente, extrae el contenido completo con trafilatura
(fallback a Playwright para SPAs con JS).
"""

from __future__ import annotations

import asyncio
import re
from urllib.parse import quote_plus, urlparse, unquote

import httpx
import trafilatura
from bs4 import BeautifulSoup

from mcp_toolkit.utils.browser import get_context
from mcp_toolkit.utils.logging import get_logger

logger = get_logger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"
MAX_RESULTS = 10
MAX_CONTENT_CHARS = 8_000
PAGE_TIMEOUT_MS = 25_000

DDG_RESULT_SEL = "div.result"
DDG_TITLE_SEL = "a.result__a"
DDG_SNIPPET_SEL = "a.result__snippet"

HTTPX_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clean_url(url: str) -> str:
    """Extrae la URL real de los redirects de DuckDuckGo."""
    match = re.search(r"uddg=([^&]+)", url)
    if match:
        return unquote(match.group(1))
    if url.startswith("//"):
        return "https:" + url
    return url


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/y.js"):
            return False
        return True
    except Exception:
        return False


def _is_ad_result(item) -> bool:
    """Detecta bloques de anuncios en el HTML de DuckDuckGo."""
    classes = set(item.get("class", []))
    if classes & {"result--ad", "result--ads", "result-sponsored"}:
        return True

    badge_text = item.get_text(" ", strip=True).lower()
    return " sponsored " in f" {badge_text} " or " anuncio " in f" {badge_text} "


def _parse_ddg_results(html: str, max_results: int) -> list[dict]:
    """Parsea los resultados del HTML de DuckDuckGo."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []

    seen_urls: set[str] = set()

    for item in soup.select(DDG_RESULT_SEL):
        if len(results) >= max_results:
            break
        if _is_ad_result(item):
            continue

        title_el = item.select_one(DDG_TITLE_SEL)
        snippet_el = item.select_one(DDG_SNIPPET_SEL)

        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        raw_url = title_el.get("href", "")
        url = _clean_url(str(raw_url))
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        if not _is_valid_url(url) or url in seen_urls:
            continue

        seen_urls.add(url)
        results.append({"title": title, "url": url, "snippet": snippet})

    return results


def _extract_with_trafilatura(html: str) -> str | None:
    """Extrae contenido principal usando trafilatura."""
    text = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=False,
        include_images=False,
        include_tables=True,
        no_fallback=False,
        favor_precision=False,
    )
    return text


def _truncate(text: str) -> str:
    if len(text) > MAX_CONTENT_CHARS:
        return text[:MAX_CONTENT_CHARS] + "\n\n… [contenido truncado]"
    return text


# ── Búsqueda DDG via httpx ────────────────────────────────────────────────────


async def _search_ddg(query: str, max_results: int, language: str) -> list[dict]:
    """Obtiene resultados de DuckDuckGo usando httpx (sin browser)."""
    search_url = SEARCH_URL.format(query=quote_plus(query))
    headers = {**HTTPX_HEADERS, "Accept-Language": f"{language},en;q=0.9"}

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.get(search_url, headers=headers)
        resp.raise_for_status()

    return _parse_ddg_results(resp.text, max_results)


# ── Extracción de contenido ───────────────────────────────────────────────────


async def _fetch_content(url: str) -> str:
    """
    Extrae contenido de una URL.
    1. Intenta con httpx + trafilatura (rápido, sin browser).
    2. Si trafilatura no extrae suficiente contenido, usa Playwright como fallback.
    """
    html: str | None = None

    # Paso 1: httpx
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(url, headers=HTTPX_HEADERS)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        logger.debug("httpx falló para %s: %s — usando Playwright", url, exc)

    if html:
        content = _extract_with_trafilatura(html)
        if content and len(content.strip()) >= 200:
            return _truncate(content)

    # Paso 2: Playwright fallback (SPAs / contenido detrás de JS)
    logger.debug("Trafilatura insuficiente para %s — usando Playwright", url)
    try:
        async with get_context(timeout_ms=PAGE_TIMEOUT_MS) as ctx:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=5_000)
            except Exception:
                logger.debug("La página no llegó a networkidle para %s; usando HTML actual", url)
            html = await page.content()
            await page.close()
    except Exception as exc:
        logger.warning("Playwright también falló para %s: %s", url, exc)
        return f"[Error al cargar la página: {exc}]"

    content = _extract_with_trafilatura(html)
    if not content:
        return "[No se pudo extraer contenido de la página]"
    return _truncate(content)


# ── Tool principal ────────────────────────────────────────────────────────────


async def web_search(
    query: str,
    max_results: int = 5,
    deep: bool = False,
    language: str = "es-ES",
) -> str:
    """
    Busca en internet usando DuckDuckGo.

    Args:
        query:       Texto a buscar.
        max_results: Número de resultados a devolver (máximo 10).
        deep:        Si es True, extrae el contenido completo de cada página.
        language:    Código de idioma para las cabeceras HTTP (ej: "es-ES", "en-US").

    Returns:
        Resultados formateados en Markdown con título, URL, snippet
        y (si deep=True) el contenido completo de cada página.
    """
    max_results = min(max_results, MAX_RESULTS)

    try:
        results = await _search_ddg(query, max_results, language)
    except Exception as exc:
        logger.error("Error en búsqueda DDG '%s': %s", query, exc)
        return f"Error al realizar la búsqueda: {exc}"

    if not results:
        return "No se encontraron resultados para la búsqueda."

    if deep:
        async def _enrich(result: dict) -> None:
            result["content"] = await _fetch_content(result["url"])

        await asyncio.gather(*[_enrich(r) for r in results])

    # ── Formatear salida ──────────────────────────────────────────────────────
    lines: list[str] = [
        f'## Resultados para: "{query}"\n',
        f"*{len(results)} resultado(s) encontrado(s)*\n",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['title']}")
        lines.append(f"**URL:** {r['url']}")
        if r["snippet"]:
            lines.append(f"**Resumen:** {r['snippet']}")
        if deep and r.get("content"):
            lines.append("\n**Contenido:**\n")
            lines.append(r["content"])
        lines.append("")

    return "\n".join(lines)
