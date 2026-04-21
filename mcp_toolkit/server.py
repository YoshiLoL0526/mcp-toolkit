"""
mcp-toolkit — servidor MCP de propósito general para agentes de IA.
Expone herramientas de búsqueda web, memoria persistente y ejecución de código.
"""

import argparse
import shutil
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP

from mcp_toolkit.utils.logging import get_logger
from mcp_toolkit.tools.http_request import http_request
from mcp_toolkit.tools.memory import (
    memory_clear,
    memory_delete,
    memory_get,
    memory_list,
    memory_search,
    memory_set,
)
from mcp_toolkit.tools.fetch_url import fetch_url
from mcp_toolkit.tools.run_js import run_js
from mcp_toolkit.tools.run_python import run_python
from mcp_toolkit.tools.web_search import web_search
from mcp_toolkit.utils.browser import shutdown_browser

logger = get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastMCP) -> AsyncIterator[None]:
    logger.info("mcp-toolkit arrancando")
    try:
        yield
    finally:
        logger.info("mcp-toolkit apagándose")
        await shutdown_browser()


mcp = FastMCP(
    name="mcp-toolkit",
    instructions=(
        "Servidor de herramientas de propósito general. "
        "Usa 'web_search' para buscar y leer páginas web con Playwright. "
        "Usa 'fetch_url' para extraer el contenido de una URL directa. "
        "Usa 'http_request' para realizar peticiones HTTP sin browser. "
        "Usa 'memory_*' para guardar y recuperar información entre conversaciones. "
        "Usa 'run_python' o 'run_js' para ejecutar código en un sandbox."
    ),
    lifespan=_lifespan,
)

# ── Registro de herramientas ──────────────────────────────────────────────────

mcp.tool()(web_search)
mcp.tool()(fetch_url)
mcp.tool()(http_request)

mcp.tool()(memory_get)
mcp.tool()(memory_set)
mcp.tool()(memory_delete)
mcp.tool()(memory_list)
mcp.tool()(memory_clear)
mcp.tool()(memory_search)

mcp.tool()(run_python)
mcp.tool()(run_js)


# ── Entry point ───────────────────────────────────────────────────────────────


def _check_dependencies() -> None:
    """Verifica dependencias del sistema en el startup."""
    if shutil.which("node") is None:
        logger.warning(
            "'node' no encontrado en PATH — la herramienta 'run_js' no estará disponible"
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-toolkit",
        description="Servidor MCP de propósito general para agentes de IA.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Protocolo de transporte (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host para el servidor HTTP (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto para el servidor HTTP (default: 8080)",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="Ruta del endpoint HTTP (default: /mcp)",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args()
    _check_dependencies()

    if args.transport == "http":
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path,
        )
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
