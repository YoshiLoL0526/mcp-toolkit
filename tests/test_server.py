import pytest
from unittest.mock import patch, AsyncMock
from mcp_toolkit.server import _lifespan, _parse_args, mcp


def test_default_transport():
    args = _parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8080
    assert args.path == "/mcp"


def test_http_transport():
    args = _parse_args(["--transport", "http"])
    assert args.transport == "http"


def test_http_custom_host_port_path():
    args = _parse_args(["--transport", "http", "--host", "0.0.0.0", "--port", "9000", "--path", "/api"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000
    assert args.path == "/api"


def test_sse_transport():
    args = _parse_args(["--transport", "sse"])
    assert args.transport == "sse"


def test_invalid_transport():
    with pytest.raises(SystemExit):
        _parse_args(["--transport", "grpc"])


@pytest.mark.asyncio
async def test_registered_tools_contract():
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}

    assert {
        "web_search",
        "fetch_url",
        "memory_get",
        "memory_set",
        "memory_delete",
        "memory_list",
        "memory_clear",
        "memory_search",
        "run_python",
        "run_js",
    } <= names


@pytest.mark.asyncio
async def test_lifespan_shutdowns_browser(monkeypatch):
    shutdown = AsyncMock()
    monkeypatch.setattr("mcp_toolkit.server.shutdown_browser", shutdown)

    async with _lifespan(mcp):
        shutdown.assert_not_awaited()

    shutdown.assert_awaited_once()


def test_main_calls_streamable_http(monkeypatch):
    calls = {}

    def fake_run(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(mcp, "run", fake_run)
    monkeypatch.setattr("mcp_toolkit.server._parse_args", lambda: type("A", (), {
        "transport": "http", "host": "0.0.0.0", "port": "8080", "path": "/mcp"
    })())

    from mcp_toolkit.server import main
    main()

    assert calls["transport"] == "streamable-http"
    assert calls["path"] == "/mcp"


def test_main_calls_stdio(monkeypatch):
    calls = {}

    def fake_run(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(mcp, "run", fake_run)
    monkeypatch.setattr("mcp_toolkit.server._parse_args", lambda: type("A", (), {
        "transport": "stdio", "host": "127.0.0.1", "port": 8080, "path": "/mcp"
    })())

    from mcp_toolkit.server import main
    main()

    assert calls["transport"] == "stdio"
