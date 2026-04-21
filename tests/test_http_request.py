import httpx
import pytest

from mcp_toolkit.tools.http_request import (
    MAX_BODY_CHARS,
    _truncate_body,
    http_request,
)


class FakeAsyncClient:
    calls = []
    response = httpx.Response(
        200,
        json={"ok": True},
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://example.com/api"),
    )

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def request(self, method, url, headers=None, content=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "content": content,
                "client_kwargs": self.kwargs,
            }
        )
        return self.response


@pytest.mark.asyncio
async def test_http_request_rejects_invalid_method():
    result = await http_request("TRACE", "https://example.com")

    assert "método HTTP no soportado" in result


@pytest.mark.asyncio
async def test_http_request_rejects_invalid_url():
    result = await http_request("GET", "not-a-url")

    assert "URL debe ser absoluta" in result


@pytest.mark.asyncio
async def test_http_request_sends_request_and_formats_json(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr("mcp_toolkit.tools.http_request.httpx.AsyncClient", FakeAsyncClient)

    result = await http_request(
        "post",
        "https://example.com/api",
        headers={"X-Test": 123},
        body="payload",
        timeout=120,
    )

    assert FakeAsyncClient.calls[0]["method"] == "POST"
    assert FakeAsyncClient.calls[0]["headers"] == {"X-Test": "123"}
    assert FakeAsyncClient.calls[0]["content"] == b"payload"
    assert FakeAsyncClient.calls[0]["client_kwargs"]["timeout"] == 60
    assert "**Status:** 200 OK" in result
    assert '"ok": true' in result


@pytest.mark.asyncio
async def test_http_request_handles_timeout(monkeypatch):
    class TimeoutClient(FakeAsyncClient):
        async def request(self, method, url, headers=None, content=None):
            raise httpx.TimeoutException("too slow")

    monkeypatch.setattr("mcp_toolkit.tools.http_request.httpx.AsyncClient", TimeoutClient)

    result = await http_request("GET", "https://example.com", timeout=1)

    assert "timeout de 1s" in result


def test_truncate_body():
    result = _truncate_body("x" * (MAX_BODY_CHARS + 10))

    assert "truncado 10 caracteres" in result
    assert len(result) > MAX_BODY_CHARS
