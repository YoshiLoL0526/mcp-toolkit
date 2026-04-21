import pytest
from pathlib import Path


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_memory.db"
    monkeypatch.setattr("mcp_toolkit.tools.memory._DB_PATH", db_path)
    return db_path
