import json
import sqlite3
import pytest
from mcp_toolkit.tools.memory import (
    memory_set,
    memory_get,
    memory_delete,
    memory_list,
    memory_clear,
    memory_search,
)


def test_set_and_get(tmp_db):
    memory_set("mykey", "myvalue")
    result = memory_get("mykey")
    assert "mykey" in result
    assert "myvalue" in result


def test_set_overwrites(tmp_db):
    memory_set("mykey", "first")
    memory_set("mykey", "second")
    result = memory_get("mykey")
    assert "second" in result
    assert "first" not in result


def test_get_missing_key(tmp_db):
    result = memory_get("nonexistent")
    assert "No existe" in result


def test_delete_existing(tmp_db):
    memory_set("delme", "value")
    memory_delete("delme")
    result = memory_get("delme")
    assert "No existe" in result


def test_delete_missing(tmp_db):
    result = memory_delete("ghost")
    assert "no existe" in result.lower()


def test_list_empty(tmp_db):
    result = memory_list()
    assert "vacía" in result


def test_list_all(tmp_db):
    memory_set("key1", "v1")
    memory_set("key2", "v2")
    result = memory_list()
    assert "key1" in result
    assert "key2" in result


def test_list_prefix(tmp_db):
    memory_set("a_1", "v1")
    memory_set("a_2", "v2")
    memory_set("b_1", "v3")
    result = memory_list(prefix="a_")
    assert "a_1" in result
    assert "a_2" in result
    assert "b_1" not in result


def test_list_prefix_is_literal(tmp_db):
    memory_set("user_1", "literal underscore")
    memory_set("userA1", "wildcard match")
    memory_set("100%done", "literal percent")
    memory_set("100Xdone", "wildcard match")

    underscore_result = memory_list(prefix="user_")
    assert "user_1" in underscore_result
    assert "userA1" not in underscore_result

    percent_result = memory_list(prefix="100%")
    assert "100%done" in percent_result
    assert "100Xdone" not in percent_result


def test_clear(tmp_db):
    memory_set("k1", "v1")
    memory_set("k2", "v2")
    memory_clear()
    result = memory_list()
    assert "vacía" in result


def test_set_complex_value(tmp_db):
    data = {"name": "Alice", "scores": [1, 2, 3]}
    memory_set("complex", data)
    result = memory_get("complex")
    assert "Alice" in result
    assert "scores" in result


def test_namespaces_are_isolated(tmp_db):
    memory_set("shared", "default value")
    memory_set("shared", "project value", namespace="project")

    default_result = memory_get("shared")
    project_result = memory_get("shared", namespace="project")

    assert "default value" in default_result
    assert "project value" not in default_result
    assert "project value" in project_result
    assert "default value" not in project_result


def test_list_namespace(tmp_db):
    memory_set("default_key", "v")
    memory_set("project_key", "v", namespace="project")

    result = memory_list(namespace="project")

    assert "project_key" in result
    assert "default_key" not in result


def test_clear_namespace_only(tmp_db):
    memory_set("default_key", "v")
    memory_set("project_key", "v", namespace="project")

    memory_clear(namespace="project")

    assert "default_key" in memory_list()
    assert "project_key" not in memory_list(namespace="project")


def test_memory_search_matches_keys_and_values(tmp_db):
    memory_set("profile", {"name": "Alice", "role": "engineer"}, namespace="project")
    memory_set("notes", "meeting agenda", namespace="project")
    memory_set("other", "Alice in default")

    result = memory_search("alice", namespace="project")

    assert "profile" in result
    assert "Alice" in result
    assert "other" not in result


def test_memory_search_orders_by_fts_relevance(tmp_db):
    memory_set("brief", "python")
    memory_set("focused", "python python python")

    result = memory_search("python")

    assert result.index("focused") < result.index("brief")


def test_memory_search_uses_full_text_not_substring_like(tmp_db):
    memory_set("profile", {"name": "Alice", "role": "engineer"})

    result = memory_search("lic")

    assert "No hay coincidencias" in result
    assert "profile" not in result


def test_memory_search_fts_index_tracks_updates_and_deletes(tmp_db):
    memory_set("note", "alpha")
    memory_set("note", "beta")

    old_result = memory_search("alpha")
    new_result = memory_search("beta")

    assert "No hay coincidencias" in old_result
    assert "note" in new_result

    memory_delete("note")

    deleted_result = memory_search("beta")

    assert "No hay coincidencias" in deleted_result


def test_memory_search_rejects_empty_query(tmp_db):
    result = memory_search(" ")

    assert "query no puede estar vacío" in result


def test_legacy_memory_schema_is_migrated(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        """
        CREATE TABLE memory (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute("INSERT INTO memory (key, value) VALUES (?, ?)", ("legacy", '"value"'))
    conn.commit()
    conn.close()

    result = memory_get("legacy")

    assert "default:legacy" in result
    assert "value" in result
