import pytest

from mcp_toolkit.tools.fetch_url import fetch_url


@pytest.mark.asyncio
async def test_fetch_url_rejects_invalid_url():
    result = await fetch_url("not-a-url")

    assert "URL debe ser absoluta" in result


@pytest.mark.asyncio
async def test_fetch_url_returns_extracted_content(monkeypatch):
    async def fake_fetch_content(url: str) -> str:
        return f"content from {url}"

    monkeypatch.setattr("mcp_toolkit.tools.fetch_url._fetch_content", fake_fetch_content)

    result = await fetch_url("https://example.com/page")

    assert "## Contenido extraído" in result
    assert "**URL:** https://example.com/page" in result
    assert "content from https://example.com/page" in result
