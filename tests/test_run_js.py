import shutil
import pytest
from mcp_toolkit.tools.run_js import run_js, MAX_CODE_LINES


@pytest.mark.asyncio
async def test_node_not_found(monkeypatch):
    monkeypatch.setattr("mcp_toolkit.tools.run_js._node_executable", lambda: None)
    result = await run_js("console.log(1)")
    assert "Node.js no está instalado" in result


@pytest.mark.asyncio
async def test_line_limit(monkeypatch):
    if shutil.which("node") is None and shutil.which("nodejs") is None:
        monkeypatch.setattr(
            "mcp_toolkit.tools.run_js._node_executable",
            lambda: "/fake/node",
        )
    code = "// x\n" * (MAX_CODE_LINES + 1)
    result = await run_js(code)
    assert "límite" in result


@pytest.mark.asyncio
async def test_basic_execution():
    if shutil.which("node") is None:
        pytest.skip("node not available")
    result = await run_js("console.log(2+2)")
    assert "4" in result
