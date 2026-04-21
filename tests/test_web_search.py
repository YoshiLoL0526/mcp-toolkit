from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_toolkit.tools.web_search import (
    _clean_url,
    _is_valid_url,
    _extract_with_trafilatura,
    _parse_ddg_results,
    _truncate,
    MAX_CONTENT_CHARS,
)


# ── _clean_url ────────────────────────────────────────────────────────────────


def test_clean_url_ddg_redirect():
    url = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com&rut=abc"
    assert _clean_url(url) == "https://example.com"


def test_clean_url_protocol_relative():
    url = "//example.com/path"
    assert _clean_url(url) == "https://example.com/path"


def test_clean_url_passthrough():
    url = "https://example.com/page?q=1"
    assert _clean_url(url) == url


# ── _is_valid_url ─────────────────────────────────────────────────────────────


def test_is_valid_url_http():
    assert _is_valid_url("http://example.com") is True


def test_is_valid_url_https():
    assert _is_valid_url("https://example.com/path") is True


def test_is_valid_url_invalid():
    assert _is_valid_url("not-a-url") is False


def test_is_valid_url_ftp():
    assert _is_valid_url("ftp://example.com") is False


def test_is_valid_url_rejects_ddg_ad_redirect():
    url = "https://duckduckgo.com/y.js?ad_domain=example.com"
    assert _is_valid_url(url) is False


# ── _parse_ddg_results ────────────────────────────────────────────────────────

DDG_HTML_SAMPLE = """
<div class="result">
  <a class="result__a" href="https://example.com">Example Title</a>
  <a class="result__snippet">A short snippet</a>
</div>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fother.com">Other</a>
</div>
"""


def test_parse_ddg_results_basic():
    results = _parse_ddg_results(DDG_HTML_SAMPLE, max_results=10)
    assert len(results) == 2
    assert results[0]["title"] == "Example Title"
    assert results[0]["url"] == "https://example.com"
    assert results[0]["snippet"] == "A short snippet"


def test_parse_ddg_results_decodes_redirect():
    results = _parse_ddg_results(DDG_HTML_SAMPLE, max_results=10)
    assert results[1]["url"] == "https://other.com"


def test_parse_ddg_results_respects_max():
    results = _parse_ddg_results(DDG_HTML_SAMPLE, max_results=1)
    assert len(results) == 1


def test_parse_ddg_results_skips_invalid_url():
    html = '<div class="result"><a class="result__a" href="not-a-url">Bad</a></div>'
    results = _parse_ddg_results(html, max_results=10)
    assert results == []


def test_parse_ddg_results_skips_ads_and_continues_to_max():
    html = """
    <div class="result result--ad">
      <a class="result__a" href="https://ads.example.com">Sponsored result</a>
      <a class="result__snippet">Sponsored</a>
    </div>
    <div class="result">
      <a class="result__a" href="not-a-url">Bad</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://example.com/one">One</a>
      <a class="result__snippet">First organic result</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://example.com/two">Two</a>
      <a class="result__snippet">Second organic result</a>
    </div>
    """
    results = _parse_ddg_results(html, max_results=2)
    assert [result["url"] for result in results] == [
        "https://example.com/one",
        "https://example.com/two",
    ]


def test_parse_ddg_results_deduplicates_urls():
    html = """
    <div class="result">
      <a class="result__a" href="https://example.com">Example 1</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://example.com">Example 2</a>
    </div>
    """
    results = _parse_ddg_results(html, max_results=10)
    assert len(results) == 1


# ── _extract_with_trafilatura ─────────────────────────────────────────────────


def test_extract_with_trafilatura_returns_text():
    html = "<html><body><article><p>Hello world content here</p></article></body></html>"
    result = _extract_with_trafilatura(html)
    assert result is not None
    assert "Hello world" in result


def test_extract_with_trafilatura_empty_html():
    result = _extract_with_trafilatura("<html><body></body></html>")
    assert result is None or result.strip() == ""


# ── _truncate ─────────────────────────────────────────────────────────────────


def test_truncate_short_text():
    text = "short"
    assert _truncate(text) == "short"


def test_truncate_long_text():
    text = "A" * (MAX_CONTENT_CHARS + 500)
    result = _truncate(text)
    assert "truncado" in result
    assert len(result) < len(text)
