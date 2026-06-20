"""Evaluación de condiciones para controladores lógicos (if / while).

Una condición es un dict JSON-serializable con la forma::

    {"kind": "...", "expression": "...", "expected": "...", "negate": false}

Tipos (`kind`) soportados:

- ``status``           : el último status HTTP == expected
- ``status_lt``/``status_gte`` : comparaciones numéricas de status
- ``jsonpath_exists``  : existe la ruta en el último body JSON
- ``jsonpath_equals``  : la ruta del último body JSON == expected
- ``body_contains``    : expected está contenido en el último body
- ``regex``            : expression hace match en el último body
- ``var_exists``       : la variable de sesión existe y no está vacía
- ``var_equals``       : variable (expression) == expected (con interpolación)
- ``var_gt``/``var_lt``: comparación numérica de variable vs expected
- ``always``           : siempre verdadero (útil para else explícito)

Todas las condiciones admiten ``negate: true`` para invertir el resultado.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from core.api_automation.runtime.interpolation import interpolate_text
from core.api_automation.runtime.jsonpath_utils import (
    get_json_path,
    json_path_exists,
    parse_json_body,
)


def evaluate_condition(
    condition: Optional[Dict[str, Any]],
    *,
    variables: Dict[str, str],
    last_result: Optional[Dict[str, Any]] = None,
) -> bool:
    """Evalúa una condición de control de flujo.

    `last_result` es el dict devuelto por execute_request (status_code, body, …)
    del paso inmediatamente anterior dentro del mismo flujo.
    """
    if not condition:
        return True
    kind = str(condition.get("kind") or "always").lower()
    expression = str(condition.get("expression") or "")
    expected_raw = condition.get("expected")
    expected = "" if expected_raw is None else str(expected_raw)
    negate = bool(condition.get("negate"))

    result = _evaluate(kind, expression, expected, variables, last_result or {})
    return (not result) if negate else result


def _evaluate(
    kind: str,
    expression: str,
    expected: str,
    variables: Dict[str, str],
    last: Dict[str, Any],
) -> bool:
    status = int(last.get("status_code") or 0)
    body = last.get("body")

    if kind == "always":
        return True

    if kind == "status":
        return str(status) == (expected or expression).strip()
    if kind == "status_lt":
        return _num(status) < _num(expected or expression)
    if kind == "status_gte":
        return _num(status) >= _num(expected or expression)

    if kind in ("jsonpath_exists", "jsonpath_equals"):
        path = (expression or expected).strip()
        if not path:
            return False
        valid, data = parse_json_body(body)
        if not valid:
            return False
        if kind == "jsonpath_exists":
            return json_path_exists(data, path)
        ok, value = get_json_path(data, path)
        return bool(ok) and str(value) == interpolate_text(expected, variables)

    if kind == "body_contains":
        needle = interpolate_text(expected or expression, variables)
        return bool(needle) and needle in (body or "")

    if kind == "regex":
        pattern = expression or expected
        if not pattern:
            return False
        try:
            return re.search(pattern, body or "") is not None
        except re.error:
            return False

    if kind == "var_exists":
        return bool(str(variables.get(expression, "")).strip())

    if kind == "var_equals":
        return str(variables.get(expression, "")) == interpolate_text(expected, variables)
    if kind == "var_gt":
        return _num(variables.get(expression, "")) > _num(interpolate_text(expected, variables))
    if kind == "var_lt":
        return _num(variables.get(expression, "")) < _num(interpolate_text(expected, variables))

    return False


def _num(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float("nan") if value not in (0, "0") else 0.0
