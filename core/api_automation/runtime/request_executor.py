"""Ejecución HTTP directa con httpx."""
from __future__ import annotations

import time
from typing import Any, Dict, Mapping, Optional

import httpx

from core.api_automation.models import ApiRequest
from core.api_automation.runtime.assertion_engine import evaluate_assertions
from core.api_automation.runtime.context_merge import build_effective_request
from core.api_automation.runtime.pm_script import run_post_request_script, run_pre_request_script


def execute_request(
    request: ApiRequest,
    *,
    global_headers: Optional[Mapping[str, str]] = None,
    variables: Optional[Mapping[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    vars_map: Dict[str, str] = {str(k): str(v) for k, v in (variables or {}).items()}

    pre_result = run_pre_request_script(request.pre_request_script, request, vars_map)
    if pre_result.errors:
        return {
            "ok": False,
            "request": build_effective_request(request, global_headers=global_headers, variables=vars_map),
            "status_code": 0,
            "headers": {},
            "body": "",
            "elapsed_ms": 0,
            "assertions": [
                {"passed": False, "message": err, "kind": "script", "expression": "", "expected": ""}
                for err in pre_result.errors
            ],
            "script_logs": pre_result.logs,
            "variables": vars_map,
        }

    effective = build_effective_request(request, global_headers=global_headers, variables=vars_map)
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

    post_result = run_post_request_script(
        request.post_request_script,
        request,
        vars_map,
        status_code=response.status_code,
        response_headers=resp_headers,
        response_body=resp_text,
    )

    assertions = evaluate_assertions(
        request,
        status_code=response.status_code,
        response_headers=resp_headers,
        response_body=resp_text,
        elapsed_ms=elapsed_ms,
    )
    for test in post_result.script_tests:
        assertions.append(
            {
                "kind": "script",
                "expression": test.get("name", ""),
                "expected": "",
                "passed": bool(test.get("passed")),
                "message": str(test.get("message") or test.get("name") or "script test"),
            }
        )
    for err in post_result.errors:
        assertions.append(
            {"kind": "script", "expression": "", "expected": "", "passed": False, "message": err}
        )

    all_passed = all(item["passed"] for item in assertions) if assertions else True
    if not post_result.ok:
        all_passed = False

    return {
        "ok": all_passed,
        "request": effective,
        "status_code": response.status_code,
        "headers": resp_headers,
        "body": resp_text,
        "elapsed_ms": elapsed_ms,
        "assertions": assertions,
        "script_logs": pre_result.logs + post_result.logs,
        "variables": vars_map,
    }
