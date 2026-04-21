from mcp_toolkit.tools.web_search import (
    _clean_url,
    _is_valid_url,
    _extract_main_content,
    MAX_CONTENT_CHARS,
)


def test_clean_url_ddg_redirect():
    url = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com&rut=abc"
    assert _clean_url(url) == "https://example.com"


def test_clean_url_protocol_relative():
    url = "//example.com/path"
    assert _clean_url(url) == "https://example.com/path"


def test_clean_url_passthrough():
    url = "https://example.com/page?q=1"
    assert _clean_url(url) == url


def test_is_valid_url_http():
    assert _is_valid_url("http://example.com") is True


def test_is_valid_url_https():
    assert _is_valid_url("https://example.com/path") is True


def test_is_valid_url_invalid():
    assert _is_valid_url("not-a-url") is False


def test_is_valid_url_ftp():
    assert _is_valid_url("ftp://example.com") is False


def test_extract_main_content_uses_main_tag():
    html = "<html><body><main>Hello world</main></body></html>"
    result = _extract_main_content(html)
    assert "Hello world" in result


def test_extract_main_content_strips_noise():
    html = "<html><body><script>evil()</script><p>good</p></body></html>"
    result = _extract_main_content(html)
    assert "evil" not in result
    assert "good" in result


def test_extract_main_content_truncates():
    inner = "A" * (MAX_CONTENT_CHARS + 1000)
    html = f"<html><body><main><p>{inner}</p></main></body></html>"
    result = _extract_main_content(html)
    assert "truncado" in result
