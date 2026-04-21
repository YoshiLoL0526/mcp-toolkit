"""
Herramienta web_search: busca en DuckDuckGo con Playwright y,
opcionalmente, extrae el contenido completo de los resultados.
"""

from __future__ import annotations

import asyncio
import re
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify

from mcp_toolkit.utils.browser import get_context
from mcp_toolkit.utils.logging import get_logger

logger = get_logger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"
MAX_RESULTS = 10
MAX_CONTENT_CHARS = 8_000  # por página en modo deep
PAGE_TIMEOUT_MS = 25_000

# Selectores de DuckDuckGo (versión HTML sin JS)
DDG_RESULT_SEL = "div.result"
DDG_TITLE_SEL = "a.result__a"
DDG_SNIPPET_SEL = "a.result__snippet"

# Etiquetas a eliminar al extraer contenido
NOISE_TAGS = [
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "iframe",
    "form",
    "button",
    "svg",
    "img",
    "advertisement",
    "ads",
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clean_url(url: str) -> str:
    """Extrae la URL real de los redirects de DuckDuckGo."""
    # DDG envuelve links como: //duckduckgo.com/l/?uddg=<encoded_url>
    match = re.search(r"uddg=([^&]+)", url)
    if match:
        from urllib.parse import unquote

        return unquote(match.group(1))
    if url.startswith("//"):
        return "https:" + url
    return url


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _extract_main_content(html: str, base_url: str = "") -> str:
    """
    Extrae el contenido principal de una página HTML y lo convierte a Markdown.
    Intenta encontrar el contenedor más relevante (<main>, <article>, etc.)
    antes de caer al <body> completo.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Eliminar ruido
    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Prioridad de contenedores semánticos
    content_node = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|article", re.I))
        or soup.find(class_=re.compile(r"content|main|article|post", re.I))
        or soup.body
        or soup
    )

    raw_md = markdownify(
        str(content_node),
        heading_style="ATX",
        strip=["a", "img"],
    )

    # Colapsar líneas en blanco excesivas
    cleaned = re.sub(r"\n{3,}", "\n\n", raw_md).strip()

    if len(cleaned) > MAX_CONTENT_CHARS:
        cleaned = cleaned[:MAX_CONTENT_CHARS] + "\n\n… [contenido truncado]"

    return cleaned


# ── Tool principal ────────────────────────────────────────────────────────────


async def web_search(
    query: str,
    max_results: int = 5,
    deep: bool = False,
    language: str = "es-ES",
) -> str:
    """
    Busca en internet usando DuckDuckGo y Playwright.

    Args:
        query:       Texto a buscar.
        max_results: Número de resultados a devolver (máximo 10).
        deep:        Si es True, accede a cada URL y extrae el contenido
                     completo de la página además del snippet.
        language:    Código de idioma para las cabeceras HTTP (ej: "es-ES", "en-US").

    Returns:
        Resultados formateados en Markdown con título, URL, snippet
        y (si deep=True) el contenido completo de cada página.
    """
    max_results = min(max_results, MAX_RESULTS)
    search_url = SEARCH_URL.format(query=quote_plus(query))

    async with get_context(timeout_ms=PAGE_TIMEOUT_MS) as ctx:
        # ── 1. Obtener resultados de DuckDuckGo ──────────────────────────────
        page = await ctx.new_page()

        await page.set_extra_http_headers(
            {
                "Accept-Language": f"{language},en;q=0.9",
            }
        )

        try:
            await page.goto(search_url, wait_until="domcontentloaded")
        except Exception as exc:
            logger.error("Error al cargar búsqueda '%s': %s", query, exc)
            return f"Error al cargar la búsqueda: {exc}"

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        results: list[dict] = []
        for item in soup.select(DDG_RESULT_SEL)[:max_results]:
            title_el = item.select_one(DDG_TITLE_SEL)
            snippet_el = item.select_one(DDG_SNIPPET_SEL)

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            raw_url = title_el.get("href", "")
            url = _clean_url(str(raw_url))
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            if not _is_valid_url(url):
                continue

            results.append({"title": title, "url": url, "snippet": snippet})

        await page.close()

        if not results:
            return "No se encontraron resultados para la búsqueda."

        # ── 2. Modo deep: extraer contenido completo de cada página ──────────
        if deep:

            async def _fetch_page(result: dict) -> None:
                p = await ctx.new_page()
                try:
                    await p.goto(result["url"], wait_until="domcontentloaded")
                    result["content"] = _extract_main_content(await p.content())
                except Exception as exc:
                    logger.warning("Error al cargar página %s: %s", result["url"], exc)
                    result["content"] = f"[Error al cargar la página: {exc}]"
                finally:
                    await p.close()

            await asyncio.gather(*[_fetch_page(r) for r in results])

    # ── 3. Formatear salida ───────────────────────────────────────────────────
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
