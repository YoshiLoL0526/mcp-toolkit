"""
Logging centralizado para mcp-toolkit.

Configura un logger jerárquico bajo 'mcp_toolkit.*' con:
- Handler a stderr (siempre activo; seguro con transporte stdio).
- Handler a archivo rotativo opcional (MCP_LOG_FILE, por defecto en
  ~/.local/share/mcp-toolkit/mcp-toolkit.log).
- Nivel controlable via MCP_LOG_LEVEL (default: WARNING).

Uso en cada módulo:
    from mcp_toolkit.utils.logging import get_logger
    logger = get_logger(__name__)
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

_DEFAULT_LOG_FILE = Path.home() / ".local" / "share" / "mcp-toolkit" / "mcp-toolkit.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB por archivo
_BACKUP_COUNT = 3

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    level_name = os.environ.get("MCP_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    root = logging.getLogger("mcp_toolkit")
    root.setLevel(level)
    root.propagate = False  # no contaminar el logger raíz de la aplicación host

    # ── stderr ────────────────────────────────────────────────────────────────
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)

    # ── archivo rotativo ──────────────────────────────────────────────────────
    log_file_env = os.environ.get("MCP_LOG_FILE", "")
    log_path = Path(log_file_env) if log_file_env else _DEFAULT_LOG_FILE

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as exc:
        root.warning("No se pudo crear el log de archivo en %s: %s", log_path, exc)


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger bajo el namespace 'mcp_toolkit'."""
    _configure()
    return logging.getLogger(name)
