import pytest
from mcp_toolkit.tools.run_python import run_python, MAX_CODE_LINES


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
