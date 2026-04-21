import pytest
from mcp_toolkit.tools.run_python import run_python, MAX_CODE_LINES
from mcp_toolkit.utils.sandbox import MAX_STDIN_CHARS


@pytest.mark.asyncio
async def test_basic_print():
    result = await run_python("print('hola')")
    assert "hola" in result


@pytest.mark.asyncio
async def test_stderr():
    result = await run_python("import sys; sys.stderr.write('err')")
    assert "err" in result


@pytest.mark.asyncio
async def test_exit_code():
    result = await run_python("raise SystemExit(42)")
    assert "42" in result


@pytest.mark.asyncio
async def test_line_limit():
    code = "# x\n" * (MAX_CODE_LINES + 1)
    result = await run_python(code)
    assert "límite" in result


@pytest.mark.asyncio
async def test_stdin():
    result = await run_python(
        "import sys; print(sys.stdin.read())", stdin="hello"
    )
    assert "hello" in result


@pytest.mark.asyncio
async def test_timeout():
    result = await run_python("import time; time.sleep(5)", timeout=1)
    assert "agotado" in result


@pytest.mark.asyncio
async def test_environment_is_minimal(monkeypatch):
    monkeypatch.setenv("MCP_TOOLKIT_SECRET", "hidden")

    result = await run_python(
        "import os; print(os.environ.get('MCP_TOOLKIT_SECRET', 'missing'))"
    )

    assert "missing" in result
    assert "hidden" not in result


@pytest.mark.asyncio
async def test_runs_in_temporary_working_directory():
    result = await run_python("import os; print(os.getcwd())")

    assert "mcp-toolkit-python-" in result


@pytest.mark.asyncio
async def test_stdin_limit():
    result = await run_python("print('unreachable')", stdin="x" * (MAX_STDIN_CHARS + 1))

    assert "stdin supera el límite" in result
