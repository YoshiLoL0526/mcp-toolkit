"""
Herramienta run_python: ejecuta código Python en un subproceso aislado
con timeout y sin acceso a red.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from mcp_toolkit.utils.sandbox import DEFAULT_TIMEOUT, run_subprocess

# Máximo de líneas de código aceptadas
MAX_CODE_LINES = 500


async def run_python(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
    stdin: str = "",
) -> str:
    """
    Ejecuta un fragmento de código Python y devuelve su salida.

    El código corre en un subproceso separado con:
    - Timeout configurable (por defecto 10 segundos).
    - Sin acceso a red (variables de entorno anuladas).
    - Límite de memoria de 256 MB en Linux.
    - El módulo sys.exit() termina el proceso sin errores.

    Args:
        code:    Código Python a ejecutar.
        timeout: Tiempo máximo de ejecución en segundos (máximo 60).
        stdin:   Texto a pasar como entrada estándar al programa.

    Returns:
        Stdout, stderr y código de salida del proceso.

    Ejemplo:
        run_python("print(sum(range(100)))")
        run_python("import math\\nprint(math.pi)")
    """
    if len(code.splitlines()) > MAX_CODE_LINES:
        return f"Error: el código supera el límite de {MAX_CODE_LINES} líneas."

    timeout = min(timeout, 60)

    # Escribir el código a un archivo temporal para evitar problemas
    # con comillas y caracteres especiales en la línea de comandos
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = await run_subprocess(
            [sys.executable, tmp_path],
            input_text=stdin or None,
            timeout=timeout,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return result.to_text()
