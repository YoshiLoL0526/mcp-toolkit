"""
Herramienta memory: almacén clave-valor persistente usando SQLite.
Los datos sobreviven entre reinicios del servidor.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

# Base de datos en el directorio de datos del usuario
_DB_PATH = Path.home() / ".local" / "share" / "mcp-toolkit" / "memory.db"


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS memory_update_ts
        AFTER UPDATE ON memory
        BEGIN
            UPDATE memory SET updated_at = datetime('now') WHERE key = NEW.key;
        END
    """
    )
    conn.commit()
    return conn


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _deserialize(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


# ── Herramientas ──────────────────────────────────────────────────────────────


def memory_set(key: str, value: Any) -> str:
    """
    Guarda un valor en memoria persistente bajo una clave.

    Args:
        key:   Nombre único de la clave (ej: "usuario_preferencias").
        value: Valor a guardar. Puede ser texto, número, lista u objeto JSON.

    Returns:
        Confirmación del guardado.
    """
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO memory (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, _serialize(value)),
        )
        conn.commit()
        return f"✓ Guardado: '{key}'"
    finally:
        conn.close()


def memory_get(key: str) -> str:
    """
    Recupera el valor almacenado bajo una clave.

    Args:
        key: Nombre de la clave a recuperar.

    Returns:
        El valor guardado, o un mensaje indicando que no existe.
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value, updated_at FROM memory WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return f"No existe ningún valor para la clave '{key}'."
        value = _deserialize(row[0])
        return f"**{key}** (actualizado: {row[1]})\n\n{json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else str(value)}"
    finally:
        conn.close()


def memory_delete(key: str) -> str:
    """
    Elimina una clave de la memoria persistente.

    Args:
        key: Nombre de la clave a eliminar.

    Returns:
        Confirmación o mensaje de que no existía.
    """
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM memory WHERE key = ?", (key,))
        conn.commit()
        if cursor.rowcount == 0:
            return f"La clave '{key}' no existe."
        return f"✓ Eliminado: '{key}'"
    finally:
        conn.close()


def memory_list(prefix: str = "") -> str:
    """
    Lista todas las claves almacenadas, con filtro opcional por prefijo.

    Args:
        prefix: Filtrar claves que comiencen con este texto (vacío = todas).

    Returns:
        Lista de claves con sus fechas de actualización.
    """
    conn = _get_conn()
    try:
        if prefix:
            rows = conn.execute(
                "SELECT key, updated_at FROM memory WHERE key LIKE ? ORDER BY key",
                (f"{prefix}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, updated_at FROM memory ORDER BY key"
            ).fetchall()

        if not rows:
            msg = (
                "La memoria está vacía."
                if not prefix
                else f"No hay claves con prefijo '{prefix}'."
            )
            return msg

        lines = [f"**{len(rows)} clave(s) en memoria:**\n"]
        for key, updated_at in rows:
            lines.append(f"- `{key}` — actualizado: {updated_at}")
        return "\n".join(lines)
    finally:
        conn.close()


def memory_clear() -> str:
    """
    Elimina TODAS las claves de la memoria persistente.
    Usar con precaución: esta acción no se puede deshacer.

    Returns:
        Número de entradas eliminadas.
    """
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM memory")
        conn.commit()
        count = cursor.rowcount
        return f"✓ Memoria limpiada. {count} entrada(s) eliminada(s)."
    finally:
        conn.close()
