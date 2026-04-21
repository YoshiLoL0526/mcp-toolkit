import json
import pytest
from mcp_toolkit.tools.memory import (
    memory_set,
    memory_get,
    memory_delete,
    memory_list,
    memory_clear,
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
