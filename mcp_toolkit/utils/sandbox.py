"""
Utilidades para el sandbox de ejecución de código:
timeouts, captura de output y restricciones de seguridad.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

# Límites del sandbox
MAX_OUTPUT_CHARS = 10_000  # truncar stdout/stderr largo
MAX_MEMORY_MB = 256  # límite de memoria RSS (solo Linux)
DEFAULT_TIMEOUT = 10  # segundos por defecto


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False

    def to_text(self) -> str:
        parts: list[str] = []

        if self.timed_out:
            parts.append("⚠️  Tiempo de ejecución agotado.")

        if self.stdout:
            parts.append(f"stdout:\n{self.stdout}")

        if self.stderr:
            parts.append(f"stderr:\n{self.stderr}")

        if not self.stdout and not self.stderr and not self.timed_out:
            parts.append("(sin output)")

        parts.append(f"exit_code: {self.exit_code}")
        return "\n\n".join(parts)


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    half = MAX_OUTPUT_CHARS // 2
    return (
        text[:half]
        + f"\n... [truncado {len(text) - MAX_OUTPUT_CHARS} caracteres] ...\n"
        + text[-half:]
    )


def _set_resource_limits() -> None:
    """
    Aplica límites de recursos al proceso hijo (solo Linux/macOS).
    Se ejecuta como preexec_fn en subprocess, por eso es síncrono.
    """
    try:
        import resource

        mem_bytes = MAX_MEMORY_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except (ImportError, ValueError, OSError):
        pass


async def run_subprocess(
    cmd: list[str],
    *,
    input_text: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
) -> SandboxResult:
    """
    Ejecuta un subproceso de forma asíncrona con timeout y captura de output.
    """
    import os

    # Heredar entorno del sistema y añadir/sobreescribir con env
    full_env = os.environ.copy()

    # Bloquear acceso a red en el proceso hijo vía variables de entorno
    full_env.update(
        {
            "no_proxy": "*",
            "NO_PROXY": "*",
            "http_proxy": "",
            "https_proxy": "",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
        }
    )

    if env:
        full_env.update(env)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if input_text else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
            preexec_fn=_set_resource_limits if sys.platform != "win32" else None,
        )

        stdin_bytes = input_text.encode() if input_text else None

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=timeout,
            )
            return SandboxResult(
                stdout=_truncate(stdout_bytes.decode(errors="replace")),
                stderr=_truncate(stderr_bytes.decode(errors="replace")),
                exit_code=proc.returncode or 0,
            )

        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return SandboxResult(
                stdout="",
                stderr="",
                exit_code=-1,
                timed_out=True,
            )

    except FileNotFoundError as exc:
        return SandboxResult(
            stdout="",
            stderr=f"Ejecutable no encontrado: {exc}",
            exit_code=127,
        )
