"""
Herramienta run_js: ejecuta código JavaScript con Node.js en un
subproceso aislado con timeout y sin acceso a red.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from mcp_toolkit.utils.sandbox import DEFAULT_TIMEOUT, run_subprocess

MAX_CODE_LINES = 500


def _node_executable() -> str | None:
    return shutil.which("node") or shutil.which("nodejs")


async def run_js(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
    stdin: str = "",
) -> str:
    """
    Ejecuta un fragmento de código JavaScript con Node.js y devuelve su salida.

    El código corre en un subproceso separado con:
    - Timeout configurable (por defecto 10 segundos).
    - Sin acceso a red (variables de entorno anuladas).
    - Node.js debe estar instalado en el sistema.

    Args:
        code:    Código JavaScript a ejecutar.
        timeout: Tiempo máximo de ejecución en segundos (máximo 60).
        stdin:   Texto a pasar como entrada estándar al programa.

    Returns:
        Stdout, stderr y código de salida del proceso.

    Ejemplo:
        run_js("console.log([1,2,3].reduce((a,b) => a+b, 0))")
        run_js("const fs = require('fs'); console.log(Object.keys(process.env).length)")
    """
    node = _node_executable()
    if node is None:
        return (
            "Error: Node.js no está instalado o no se encuentra en PATH.\n"
            "Instálalo desde https://nodejs.org o con tu gestor de paquetes."
        )

    if len(code.splitlines()) > MAX_CODE_LINES:
        return f"Error: el código supera el límite de {MAX_CODE_LINES} líneas."

    timeout = min(timeout, 60)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".mjs",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = await run_subprocess(
            [node, tmp_path],
            input_text=stdin or None,
            timeout=timeout,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return result.to_text()
