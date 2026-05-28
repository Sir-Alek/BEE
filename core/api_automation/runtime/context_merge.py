"""Fusión de headers globales, entorno y petición con interpolación."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from core.api_automation.models import ApiRequest
from core.api_automation.runtime.interpolation import interpolate_text, interpolate_value


def build_effective_request(
    request: ApiRequest,
    *,
    global_headers: Optional[Mapping[str, str]] = None,
    variables: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Devuelve method, url, headers y body listos para httpx."""
    vars_map = {str(k): str(v) for k, v in (variables or {}).items()}
    headers: Dict[str, str] = {}
    for key, value in (global_headers or {}).items():
        headers[str(key)] = interpolate_text(str(value), vars_map)
    for key, value in (request.headers or {}).items():
        headers[str(key)] = interpolate_text(str(value), vars_map)

    url = interpolate_text(request.url, vars_map)
    body = request.body
    if body is not None:
        body = interpolate_text(str(body), vars_map)

    return {
        "method": (request.method or "GET").upper(),
        "url": url,
        "headers": headers,
        "body": body,
    }
