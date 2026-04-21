"""
Herramienta run_python: ejecuta código Python en un subproceso aislado
con timeout y sin acceso a red.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from mcp_toolkit.utils.sandbox import DEFAULT_TIMEOUT, MAX_STDIN_CHARS, run_subprocess

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
    - Entorno mínimo sin secretos heredados del proceso host.
    - Directorio de trabajo temporal.
    - Límite de memoria de 256 MB en Linux/macOS.
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

    if len(stdin) > MAX_STDIN_CHARS:
        return f"Error: stdin supera el límite de {MAX_STDIN_CHARS} caracteres."

    timeout = max(1, min(timeout, 60))

    with tempfile.TemporaryDirectory(prefix="mcp-toolkit-python-") as sandbox_dir:
        tmp_path = Path(sandbox_dir) / "snippet.py"
        with tmp_path.open(mode="w", encoding="utf-8") as tmp:
            tmp.write(code)

        result = await run_subprocess(
            [sys.executable, "-I", str(tmp_path)],
            input_text=stdin or None,
            timeout=timeout,
            cwd=sandbox_dir,
        )

    return result.to_text()
