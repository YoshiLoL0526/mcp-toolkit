"""
Herramienta fetch_url: extrae contenido legible de una URL directa.
"""

from __future__ import annotations

from mcp_toolkit.tools.web_search import _fetch_content, _is_valid_url


async def fetch_url(url: str) -> str:
    """
    Extrae el contenido principal de una URL.

    Args:
        url: URL HTTP o HTTPS a leer.

    Returns:
        Contenido formateado en Markdown, o un mensaje de error si la URL no
        es válida o no se pudo extraer texto.
    """
    if not _is_valid_url(url):
        return "Error: la URL debe ser absoluta y usar http o https."

    content = await _fetch_content(url)
    return "\n".join(
        [
            "## Contenido extraído",
            "",
            f"**URL:** {url}",
            "",
            content,
        ]
    )
