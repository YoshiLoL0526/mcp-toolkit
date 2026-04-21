"""
Utilidades para el sandbox de ejecución de código:
timeouts, captura de output y restricciones de seguridad.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from mcp_toolkit.utils.logging import get_logger

logger = get_logger(__name__)

# Límites del sandbox
MAX_OUTPUT_CHARS = 10_000  # truncar stdout/stderr largo
MAX_MEMORY_MB = 256  # límite de memoria RSS (solo Linux)
DEFAULT_TIMEOUT = 10  # segundos por defecto
MAX_STDIN_CHARS = 100_000

_BASE_ENV_KEYS = (
    "PATH",
    "SystemRoot",
    "WINDIR",
    "TEMP",
    "TMP",
    "HOME",
    "USERPROFILE",
)


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


def _sandbox_env(extra_env: dict[str, str] | None = None) -> dict[str, str]:
    """Construye un entorno mínimo para no exponer secretos del proceso host."""
    full_env = {key: os.environ[key] for key in _BASE_ENV_KEYS if key in os.environ}
    full_env.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "no_proxy": "*",
            "NO_PROXY": "*",
            "http_proxy": "",
            "https_proxy": "",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
        }
    )

    if extra_env:
        full_env.update(extra_env)

    return full_env


async def run_subprocess(
    cmd: list[str],
    *,
    input_text: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> SandboxResult:
    """
    Ejecuta un subproceso de forma asíncrona con timeout y captura de output.
    """
    if input_text and len(input_text) > MAX_STDIN_CHARS:
        return SandboxResult(
            stdout="",
            stderr=f"stdin supera el límite de {MAX_STDIN_CHARS} caracteres",
            exit_code=1,
        )

    full_env = _sandbox_env(env)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if input_text else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
            cwd=str(cwd) if cwd else None,
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
            logger.warning("Subproceso %s superó timeout de %ss", cmd[0], timeout)
            return SandboxResult(
                stdout="",
                stderr="",
                exit_code=-1,
                timed_out=True,
            )

    except FileNotFoundError as exc:
        logger.error("Ejecutable no encontrado: %s", exc)
        return SandboxResult(
            stdout="",
            stderr=f"Ejecutable no encontrado: {exc}",
            exit_code=127,
        )
