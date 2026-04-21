"""
Herramienta http_request: cliente HTTP genérico sin Playwright.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import httpx

MAX_BODY_CHARS = 20_000
MAX_TIMEOUT = 60
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def _is_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _truncate_body(text: str) -> str:
    if len(text) <= MAX_BODY_CHARS:
        return text
    return text[:MAX_BODY_CHARS] + f"\n\n... [truncado {len(text) - MAX_BODY_CHARS} caracteres]"


def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {str(key): str(value) for key, value in headers.items()}


def _format_headers(headers: httpx.Headers) -> str:
    if not headers:
        return "(sin headers)"
    return "\n".join(f"- `{key}`: {value}" for key, value in headers.items())


async def http_request(
    method: str,
    url: str,
    headers: dict[str, Any] | None = None,
    body: str = "",
    timeout: int = 10,
) -> str:
    """
    Ejecuta una petición HTTP genérica.

    Args:
        method:  Método HTTP: GET, POST, PUT, PATCH, DELETE, HEAD u OPTIONS.
        url:     URL absoluta HTTP o HTTPS.
        headers: Cabeceras HTTP opcionales.
        body:    Cuerpo de la petición como texto.
        timeout: Timeout en segundos, máximo 60.

    Returns:
        Respuesta formateada en Markdown con status, headers y cuerpo.
    """
    method = method.upper().strip()
    if method not in ALLOWED_METHODS:
        return f"Error: método HTTP no soportado. Usa uno de: {', '.join(sorted(ALLOWED_METHODS))}."

    if not _is_http_url(url):
        return "Error: la URL debe ser absoluta y usar http o https."

    timeout = max(1, min(timeout, MAX_TIMEOUT))
    request_headers = _normalize_headers(headers)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                headers=request_headers,
                content=body.encode("utf-8") if body else None,
            )
    except httpx.TimeoutException:
        return f"Error: la petición superó el timeout de {timeout}s."
    except httpx.HTTPError as exc:
        return f"Error al realizar la petición HTTP: {exc}"

    content_type = response.headers.get("content-type", "")
    response_text = response.text
    if "application/json" in content_type.lower():
        try:
            response_text = json.dumps(response.json(), ensure_ascii=False, indent=2)
        except ValueError:
            pass

    return "\n".join(
        [
            "## Respuesta HTTP",
            "",
            f"**Método:** {method}",
            f"**URL final:** {response.url}",
            f"**Status:** {response.status_code} {response.reason_phrase}",
            "",
            "**Headers:**",
            "",
            _format_headers(response.headers),
            "",
            "**Body:**",
            "",
            _truncate_body(response_text) if response_text else "(sin body)",
        ]
    )
