"""Inferencia de aserciones API (Gemma + heurística offline)."""
from __future__ import annotations

import json
import re
from typing import List

from core.api_automation.models import ApiAssertion, ApiRequest


def _heuristic_assertions(req: ApiRequest) -> List[ApiAssertion]:
    out: List[ApiAssertion] = [
        ApiAssertion(kind="status", expression="", expected=str(req.expected_status or 200))
    ]
    body = (req.response_body or "").strip()
    if not body or not body.startswith(("{", "[")):
        return out
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return out
    if isinstance(data, dict):
        for key in list(data.keys())[:3]:
            out.append(ApiAssertion(kind="jsonpath", expression=key, expected="present"))
    return out


def _assertions_to_then_steps(assertions: List[ApiAssertion]) -> List[str]:
    steps: List[str] = []
    for a in assertions:
        if a.kind == "status":
            code = a.expected or "200"
            if str(code).isdigit():
                steps.append(f"el código HTTP de respuesta es {int(code)}")
        elif a.kind == "jsonpath" and a.expression:
            key = a.expression.replace('"', "").strip()
            if key:
                steps.append(f'el JSON de respuesta contiene la clave "{key}"')
    return steps


def infer_api_assertions(req: ApiRequest, *, use_ai: bool = False) -> List[ApiAssertion]:
    """Devuelve aserciones para una petición; usa Gemma si use_ai y runtime disponible."""
    if not use_ai:
        return _heuristic_assertions(req)

    from core.gemma_inference import is_ai_runtime_configured, run_llama_json_prompt

    if not is_ai_runtime_configured():
        return _heuristic_assertions(req)

    prompt = (
        "Given this HTTP API exchange, suggest test assertions as JSON.\n"
        f"Method: {req.method}\nURL: {req.url}\n"
        f"Request body (truncated): {(req.body or '')[:400]}\n"
        f"Response status: {req.response_status or req.expected_status}\n"
        f"Response body (truncated): {(req.response_body or '')[:800]}\n\n"
        'Return ONLY: {"assertions":[{"kind":"status"|"jsonpath","expression":"","expected":"..."}]}\n'
        "Max 4 assertions. Prefer status code and top-level JSON keys."
    )
    data = run_llama_json_prompt(prompt, max_tokens=384, temperature=0.15, task="api_assertion")
    if not isinstance(data, dict):
        return _heuristic_assertions(req)

    raw = data.get("assertions")
    if not isinstance(raw, list):
        return _heuristic_assertions(req)

    parsed: List[ApiAssertion] = []
    for item in raw[:6]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "status").lower()
        if kind not in ("status", "jsonpath", "header"):
            kind = "jsonpath" if item.get("expression") else "status"
        parsed.append(
            ApiAssertion(
                kind=kind,
                expression=str(item.get("expression") or ""),
                expected=str(item.get("expected") or ""),
            )
        )
    if not parsed:
        return _heuristic_assertions(req)
    if not any(a.kind == "status" for a in parsed):
        parsed.insert(0, ApiAssertion(kind="status", expected=str(req.expected_status or 200)))
    return parsed


def enrich_requests_with_assertions(requests: List[ApiRequest], *, use_ai: bool = False) -> List[ApiRequest]:
    enriched: List[ApiRequest] = []
    for req in requests:
        assertions = infer_api_assertions(req, use_ai=use_ai)
        then_steps = _assertions_to_then_steps(assertions)
        enriched.append(
            ApiRequest(
                id=req.id,
                name=req.name,
                method=req.method,
                url=req.url,
                headers=dict(req.headers),
                body=req.body,
                expected_status=req.expected_status,
                assertions=assertions,
                response_status=req.response_status,
                response_headers=dict(req.response_headers),
                response_body=req.response_body,
                source="ai" if use_ai else req.source,
            )
        )
        del then_steps  # used in converter via assertions
    return enriched
