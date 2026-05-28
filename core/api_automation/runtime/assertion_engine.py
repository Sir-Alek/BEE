"""Evaluación de aserciones sobre respuestas HTTP."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from core.api_automation.models import ApiAssertion, ApiRequest
from core.api_automation.runtime.jsonpath_utils import get_json_path, json_path_exists, parse_json_body


def evaluate_assertions(
    request: ApiRequest,
    *,
    status_code: int,
    response_headers: Dict[str, str],
    response_body: Optional[str],
    elapsed_ms: float = 0.0,
) -> List[Dict[str, Any]]:
    assertions = list(request.assertions or [])
    if not assertions and request.expected_status:
        assertions.append(ApiAssertion(kind="status", expected=str(request.expected_status)))
    if request.max_duration_ms and not any(a.kind == "duration" for a in assertions):
        assertions.append(ApiAssertion(kind="duration", expected=str(request.max_duration_ms)))

    results: List[Dict[str, Any]] = []
    for assertion in assertions:
        ok, message = _check_assertion(
            assertion, status_code, response_headers, response_body, elapsed_ms
        )
        results.append(
            {
                "kind": assertion.kind,
                "expression": assertion.expression,
                "expected": assertion.expected,
                "passed": ok,
                "message": message,
            }
        )
    return results


def _check_assertion(
    assertion: ApiAssertion,
    status_code: int,
    response_headers: Dict[str, str],
    response_body: Optional[str],
    elapsed_ms: float,
) -> tuple[bool, str]:
    kind = (assertion.kind or "status").lower()
    if kind == "status":
        expected = assertion.expected or "200"
        if not str(expected).isdigit():
            return False, f"Expected status inválido: {expected!r}"
        exp = int(expected)
        if status_code == exp:
            return True, f"HTTP {status_code}"
        return False, f"Esperado HTTP {exp}, recibido {status_code}"

    if kind == "duration":
        limit = assertion.expected or assertion.expression
        if not str(limit).isdigit():
            return False, f"Límite de duración inválido: {limit!r}"
        max_ms = int(limit)
        if elapsed_ms <= max_ms:
            return True, f"Duración {elapsed_ms} ms <= {max_ms} ms"
        return False, f"Duración {elapsed_ms} ms supera {max_ms} ms"

    if kind == "header":
        name = (assertion.expression or "").strip()
        if not name:
            return False, "Nombre de header vacío"
        actual = _header_value(response_headers, name)
        expected = assertion.expected
        if expected and actual != expected:
            return False, f"Header {name!r}: esperado {expected!r}, recibido {actual!r}"
        if actual:
            return True, f"Header {name!r} presente"
        return False, f"Header {name!r} no encontrado"

    if kind == "jsonpath":
        path = (assertion.expression or assertion.expected or "").strip()
        if not path:
            return False, "JSONPath vacío"
        valid, data = parse_json_body(response_body)
        if not valid:
            return False, "Respuesta no es JSON válido"
        if json_path_exists(data, path):
            return True, f"JSONPath {path!r} presente"
        ok, value = get_json_path(data, path)
        expected = assertion.expected
        if ok and expected and str(value) != expected:
            return False, f"JSONPath {path!r}: esperado {expected!r}, recibido {value!r}"
        if ok:
            return True, f"JSONPath {path!r} = {value!r}"
        return False, f"JSONPath {path!r} no encontrado"

    if kind == "body_contains":
        needle = assertion.expected or assertion.expression
        if needle and needle in (response_body or ""):
            return True, "Texto encontrado en el cuerpo"
        return False, "Texto no encontrado en el cuerpo"

    if kind == "regex":
        pattern = assertion.expression or assertion.expected
        if not pattern:
            return False, "Regex vacío"
        if re.search(pattern, response_body or ""):
            return True, "Regex coincide con el cuerpo"
        return False, "Regex no coincide con el cuerpo"

    return False, f"Tipo de aserción no soportado: {kind!r}"


def _header_value(headers: Dict[str, str], name: str) -> str:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return ""
