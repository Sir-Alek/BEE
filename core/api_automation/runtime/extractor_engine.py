"""Extractores post-respuesta para correlación dinámica entre pasos."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.api_automation.models import ApiExtractor
from core.api_automation.runtime.jsonpath_utils import get_json_path, parse_json_body


def apply_extractors(
    extractors: List[ApiExtractor],
    *,
    status_code: int,
    response_headers: Dict[str, str],
    response_body: Optional[str],
    variables: Dict[str, str],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for ext in extractors:
        ok, message, value = _extract_one(ext, status_code, response_headers, response_body)
        if ok and value is not None:
            variables[str(ext.target_var)] = str(value)
        results.append(
            {
                "kind": ext.kind,
                "expression": ext.expression,
                "target_var": ext.target_var,
                "passed": ok,
                "message": message,
                "value": value,
            }
        )
    return results


def _extract_one(
    ext: ApiExtractor,
    status_code: int,
    response_headers: Dict[str, str],
    response_body: Optional[str],
) -> tuple[bool, str, Optional[str]]:
    kind = (ext.kind or "jsonpath").lower()
    target = (ext.target_var or "").strip()
    if not target:
        return False, "target_var vacío", None

    if kind == "header":
        name = (ext.expression or target).strip()
        value = _header_value(response_headers, name)
        if value:
            return True, f"Header {name!r} extraído", value
        return False, f"Header {name!r} no encontrado", None

    if kind == "regex":
        pattern = ext.expression or ""
        if not pattern:
            return False, "Regex vacío", None
        match = re.search(pattern, response_body or "")
        if not match:
            return False, "Regex sin coincidencias", None
        value = match.group(1) if match.groups() else match.group(0)
        return True, "Regex aplicado", str(value)

    if kind == "jsonpath":
        path = ext.expression or ""
        if not path:
            return False, "JSONPath vacío", None
        valid, data = parse_json_body(response_body)
        if not valid:
            return False, "Respuesta no es JSON válido", None
        ok, value = get_json_path(data, path)
        if not ok or value is None:
            return False, f"JSONPath {path!r} sin valor", None
        return True, f"JSONPath {path!r} extraído", str(value)

    if kind == "status":
        return True, f"HTTP {status_code}", str(status_code)

    return False, f"Extractor no soportado: {kind!r}", None


def _header_value(headers: Dict[str, str], name: str) -> str:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return ""
