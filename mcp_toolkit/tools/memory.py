"""
Herramienta memory: almacén clave-valor persistente usando SQLite.
Los datos sobreviven entre reinicios del servidor.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

# Base de datos en el directorio de datos del usuario
_DB_PATH = Path.home() / ".local" / "share" / "mcp-toolkit" / "memory.db"
DEFAULT_NAMESPACE = "default"
MAX_SEARCH_RESULTS = 20
FTS_TABLE = "memory_fts"


def _fts_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (FTS_TABLE,),
    ).fetchone()
    return row is not None


def _ensure_fts_schema(conn: sqlite3.Connection) -> None:
    fts_exists = _fts_table_exists(conn)
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            namespace UNINDEXED,
            key,
            value,
            content='memory',
            content_rowid='rowid'
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS memory_fts_insert
        AFTER INSERT ON memory
        BEGIN
            INSERT INTO memory_fts(rowid, namespace, key, value)
            VALUES (NEW.rowid, NEW.namespace, NEW.key, NEW.value);
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS memory_fts_delete
        AFTER DELETE ON memory
        BEGIN
            INSERT INTO memory_fts(memory_fts, rowid, namespace, key, value)
            VALUES ('delete', OLD.rowid, OLD.namespace, OLD.key, OLD.value);
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS memory_fts_update
        AFTER UPDATE ON memory
        BEGIN
            INSERT INTO memory_fts(memory_fts, rowid, namespace, key, value)
            VALUES ('delete', OLD.rowid, OLD.namespace, OLD.key, OLD.value);
            INSERT INTO memory_fts(rowid, namespace, key, value)
            VALUES (NEW.rowid, NEW.namespace, NEW.key, NEW.value);
        END
        """
    )
    if not fts_exists:
        conn.execute("INSERT INTO memory_fts(memory_fts) VALUES ('rebuild')")


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory (
            namespace  TEXT NOT NULL DEFAULT 'default',
            key        TEXT NOT NULL,
            value      TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (namespace, key)
        )
    """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS memory_update_ts
        AFTER UPDATE ON memory
        BEGIN
            UPDATE memory
            SET updated_at = datetime('now')
            WHERE namespace = NEW.namespace AND key = NEW.key;
        END
    """
    )
    _ensure_fts_schema(conn)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(memory)").fetchall()
    if not columns:
        _create_schema(conn)
        return

    column_names = {row[1] for row in columns}
    if "namespace" in column_names:
        _create_schema(conn)
        return

    conn.execute("DROP TRIGGER IF EXISTS memory_update_ts")
    conn.execute("ALTER TABLE memory RENAME TO memory_legacy")
    _create_schema(conn)
    conn.execute(
        """
        INSERT INTO memory (namespace, key, value, created_at, updated_at)
        SELECT ?, key, value, created_at, updated_at FROM memory_legacy
        """,
        (DEFAULT_NAMESPACE,),
    )
    conn.execute("DROP TABLE memory_legacy")


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    _ensure_schema(conn)
    conn.commit()
    return conn


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _deserialize(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _normalize_namespace(namespace: str) -> str:
    namespace = namespace.strip()
    return namespace or DEFAULT_NAMESPACE


def _format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _snippet(raw: str, max_chars: int = 240) -> str:
    value = _deserialize(raw)
    text = _format_value(value).replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _build_fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    return " AND ".join(f'"{token}"*' for token in tokens)


# ── Herramientas ──────────────────────────────────────────────────────────────


def memory_set(key: str, value: Any, namespace: str = DEFAULT_NAMESPACE) -> str:
    """
    Guarda un valor en memoria persistente bajo una clave.

    Args:
        key:       Nombre único de la clave (ej: "usuario_preferencias").
        value:     Valor a guardar. Puede ser texto, número, lista u objeto JSON.
        namespace: Espacio de nombres lógico para separar memorias.

    Returns:
        Confirmación del guardado.
    """
    namespace = _normalize_namespace(namespace)
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO memory (namespace, key, value) VALUES (?, ?, ?)
            ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value
            """,
            (namespace, key, _serialize(value)),
        )
        conn.commit()
        return f"✓ Guardado: '{namespace}:{key}'"
    finally:
        conn.close()


def memory_get(key: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """
    Recupera el valor almacenado bajo una clave.

    Args:
        key:       Nombre de la clave a recuperar.
        namespace: Espacio de nombres lógico donde buscar.

    Returns:
        El valor guardado, o un mensaje indicando que no existe.
    """
    namespace = _normalize_namespace(namespace)
    conn = _get_conn()
    try:
        row = conn.execute(
            """
            SELECT value, updated_at
            FROM memory
            WHERE namespace = ? AND key = ?
            """,
            (namespace, key),
        ).fetchone()
        if row is None:
            return f"No existe ningún valor para la clave '{key}' en '{namespace}'."
        value = _deserialize(row[0])
        return f"**{namespace}:{key}** (actualizado: {row[1]})\n\n{_format_value(value)}"
    finally:
        conn.close()


def memory_delete(key: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """
    Elimina una clave de la memoria persistente.

    Args:
        key:       Nombre de la clave a eliminar.
        namespace: Espacio de nombres lógico donde eliminar.

    Returns:
        Confirmación o mensaje de que no existía.
    """
    namespace = _normalize_namespace(namespace)
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM memory WHERE namespace = ? AND key = ?", (namespace, key)
        )
        conn.commit()
        if cursor.rowcount == 0:
            return f"La clave '{key}' no existe en '{namespace}'."
        return f"✓ Eliminado: '{namespace}:{key}'"
    finally:
        conn.close()


def memory_list(prefix: str = "", namespace: str = DEFAULT_NAMESPACE) -> str:
    """
    Lista todas las claves almacenadas, con filtro opcional por prefijo.

    Args:
        prefix:    Filtrar claves que comiencen con este texto (vacío = todas).
        namespace: Espacio de nombres lógico a listar.

    Returns:
        Lista de claves con sus fechas de actualización.
    """
    namespace = _normalize_namespace(namespace)
    conn = _get_conn()
    try:
        if prefix:
            rows = conn.execute(
                """
                SELECT key, updated_at
                FROM memory
                WHERE namespace = ? AND substr(key, 1, ?) = ?
                ORDER BY key
                """,
                (namespace, len(prefix), prefix),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT key, updated_at
                FROM memory
                WHERE namespace = ?
                ORDER BY key
                """,
                (namespace,),
            ).fetchall()

        if not rows:
            msg = (
                f"La memoria '{namespace}' está vacía."
                if not prefix
                else f"No hay claves con prefijo '{prefix}' en '{namespace}'."
            )
            return msg

        lines = [f"**{len(rows)} clave(s) en memoria '{namespace}':**\n"]
        for key, updated_at in rows:
            lines.append(f"- `{key}` — actualizado: {updated_at}")
        return "\n".join(lines)
    finally:
        conn.close()


def memory_clear(namespace: str = DEFAULT_NAMESPACE) -> str:
    """
    Elimina todas las claves de un espacio de nombres.
    Usar con precaución: esta acción no se puede deshacer.

    Returns:
        Número de entradas eliminadas.
    """
    namespace = _normalize_namespace(namespace)
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM memory WHERE namespace = ?", (namespace,))
        conn.commit()
        count = cursor.rowcount
        return f"✓ Memoria '{namespace}' limpiada. {count} entrada(s) eliminada(s)."
    finally:
        conn.close()


def memory_search(
    query: str,
    namespace: str = DEFAULT_NAMESPACE,
    limit: int = 10,
) -> str:
    """
    Busca texto en claves y valores de la memoria persistente.

    Args:
        query:     Texto a buscar en claves o valores.
        namespace: Espacio de nombres lógico donde buscar.
        limit:     Número máximo de resultados (máximo 20).

    Returns:
        Lista de coincidencias con fragmentos de valor.
    """
    query = query.strip()
    if not query:
        return "Error: query no puede estar vacío."

    namespace = _normalize_namespace(namespace)
    limit = max(1, min(limit, MAX_SEARCH_RESULTS))
    fts_query = _build_fts_query(query)
    if not fts_query:
        return "Error: query debe contener texto buscable."

    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT memory.key, memory.value, memory.updated_at, bm25(memory_fts) AS rank
            FROM memory_fts
            JOIN memory ON memory.rowid = memory_fts.rowid
            WHERE memory_fts MATCH ?
              AND memory.namespace = ?
            ORDER BY rank, memory.updated_at DESC, memory.key
            LIMIT ?
            """,
            (fts_query, namespace, limit),
        ).fetchall()

        if not rows:
            return f"No hay coincidencias para '{query}' en '{namespace}'."

        lines = [f"**{len(rows)} resultado(s) para '{query}' en '{namespace}':**\n"]
        for key, raw_value, updated_at, _rank in rows:
            lines.append(f"- `{key}` — actualizado: {updated_at}\n  {_snippet(raw_value)}")
        return "\n".join(lines)
    finally:
        conn.close()
