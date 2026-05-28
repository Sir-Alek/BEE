"""Ejecución HTTP directa con httpx."""
from __future__ import annotations

import time
from typing import Any, Dict, Mapping, Optional

import httpx

from core.api_automation.models import ApiRequest
from core.api_automation.runtime.assertion_engine import evaluate_assertions
from core.api_automation.runtime.context_merge import build_effective_request


def execute_request(
    request: ApiRequest,
    *,
    global_headers: Optional[Mapping[str, str]] = None,
    variables: Optional[Mapping[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    effective = build_effective_request(request, global_headers=global_headers, variables=variables)
    method = effective["method"]
    url = effective["url"]
    headers = effective["headers"]
    body = effective["body"]

    if not url.strip():
        raise ValueError("URL vacía")

    kwargs: Dict[str, Any] = {"headers": headers, "follow_redirects": True}
    if body is not None and method not in ("GET", "HEAD"):
        kwargs["content"] = body

    started = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        response = client.request(method, url, **kwargs)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

    resp_headers = {str(k): str(v) for k, v in response.headers.items()}
    resp_text = response.text
    assertions = evaluate_assertions(
        request,
        status_code=response.status_code,
        response_headers=resp_headers,
        response_body=resp_text,
        elapsed_ms=elapsed_ms,
    )
    all_passed = all(item["passed"] for item in assertions) if assertions else True

    return {
        "ok": all_passed,
        "request": effective,
        "status_code": response.status_code,
        "headers": resp_headers,
        "body": resp_text,
        "elapsed_ms": elapsed_ms,
        "assertions": assertions,
    }
