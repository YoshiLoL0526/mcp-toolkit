"""
mcp-toolkit — servidor MCP de propósito general para agentes de IA.
Expone herramientas de búsqueda web, memoria persistente y ejecución de código.
"""

import argparse
import shutil
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP

from mcp_toolkit.tools.memory import (
    memory_clear,
    memory_delete,
    memory_get,
    memory_list,
    memory_set,
)
from mcp_toolkit.tools.run_js import run_js
from mcp_toolkit.tools.run_python import run_python
from mcp_toolkit.tools.web_search import web_search
from mcp_toolkit.utils.browser import shutdown_browser


@asynccontextmanager
async def _lifespan(app: FastMCP) -> AsyncIterator[None]:
    yield
    await shutdown_browser()


mcp = FastMCP(
    name="mcp-toolkit",
    instructions=(
        "Servidor de herramientas de propósito general. "
        "Usa 'web_search' para buscar y leer páginas web con Playwright. "
        "Usa 'memory_*' para guardar y recuperar información entre conversaciones. "
        "Usa 'run_python' o 'run_js' para ejecutar código en un sandbox."
    ),
    lifespan=_lifespan,
)

# ── Registro de herramientas ──────────────────────────────────────────────────

mcp.tool()(web_search)

mcp.tool()(memory_get)
mcp.tool()(memory_set)
mcp.tool()(memory_delete)
mcp.tool()(memory_list)
mcp.tool()(memory_clear)

mcp.tool()(run_python)
mcp.tool()(run_js)


# ── Entry point ───────────────────────────────────────────────────────────────


def _check_dependencies() -> None:
    """Verifica dependencias del sistema en el startup."""
    # Node.js es necesario solo para run_js
    if shutil.which("node") is None:
        print(
            "[mcp-toolkit] AVISO: 'node' no encontrado en PATH. "
            "La herramienta 'run_js' no estará disponible.",
            file=sys.stderr,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-toolkit",
        description="Servidor MCP de propósito general para agentes de IA.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Protocolo de transporte (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host para el servidor SSE (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto para el servidor SSE (default: 8080)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    _check_dependencies()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
