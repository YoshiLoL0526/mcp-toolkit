import pytest
from mcp_toolkit.utils.sandbox import SandboxResult, _truncate, MAX_OUTPUT_CHARS


def test_to_text_normal():
    r = SandboxResult(stdout="hello", stderr="warn", exit_code=0)
    text = r.to_text()
    assert "hello" in text
    assert "warn" in text
    assert "exit_code: 0" in text


def test_to_text_timeout():
    r = SandboxResult(stdout="", stderr="", exit_code=-1, timed_out=True)
    text = r.to_text()
    assert "agotado" in text


def test_to_text_empty():
    r = SandboxResult(stdout="", stderr="", exit_code=0)
    text = r.to_text()
    assert "(sin output)" in text


def test_truncate_short():
    text = "short text"
    assert _truncate(text) == text


def test_truncate_long():
    text = "x" * (MAX_OUTPUT_CHARS + 1000)
    result = _truncate(text)
    assert len(result) < len(text)
    assert "truncado" in result
