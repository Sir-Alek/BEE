"""Ejecutor de scripts estilo Postman (subset JS) para pre-request y post-request."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.api_automation.models import ApiRequest
from core.api_automation.runtime.jsonpath_utils import parse_json_body


@dataclass
class ScriptRunResult:
    ok: bool = True
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    script_tests: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)


class _PmResponse:
    def __init__(self, *, status_code: int, headers: Dict[str, str], body: Optional[str]) -> None:
        self.code = status_code
        self.status = status_code
        self.headers = headers
        self.text = body or ""
        self._json_cache: Any = _UNSET

    def json(self) -> Any:
        if self._json_cache is _UNSET:
            valid, data = parse_json_body(self.text)
            self._json_cache = data if valid else None
        return self._json_cache


_UNSET = object()

_SET_RE = re.compile(
    r"pm\.(environment|variables|collectionVariables)\.set\s*\(\s*"
    r"(['\"])([^'\"]+)\2\s*,\s*(.+?)\s*\)\s*;?\s*$"
)
_GET_RE = re.compile(
    r"pm\.(environment|variables|collectionVariables)\.get\s*\(\s*"
    r"(['\"])([^'\"]+)\2\s*\)"
)
_HEADER_ADD_RE = re.compile(
    r"pm\.request\.headers\.(?:add|upsert)\s*\(\s*\{\s*key\s*:\s*"
    r"(['\"])([^'\"]+)\1\s*,\s*value\s*:\s*(.+?)\s*\}\s*\)\s*;?\s*$"
)
_HEADER_REMOVE_RE = re.compile(
    r"pm\.request\.headers\.remove\s*\(\s*(['\"])([^'\"]+)\1\s*\)\s*;?\s*$"
)
_JSON_BIND_RE = re.compile(
    r"(?:const|let|var)\s+(\w+)\s*=\s*pm\.response\.json\s*\(\s*\)\s*;?\s*$"
)
_PROP_SET_RE = re.compile(
    r"pm\.(environment|variables|collectionVariables)\.set\s*\(\s*"
    r"(['\"])([^'\"]+)\2\s*,\s*(\w+)\.(\w+)\s*\)\s*;?\s*$"
)
_PROP_IDX_SET_RE = re.compile(
    r"pm\.(environment|variables|collectionVariables)\.set\s*\(\s*"
    r"(['\"])([^'\"]+)\2\s*,\s*(\w+)\[\s*(['\"])([^'\"]+)\4\s*\]\s*\)\s*;?\s*$"
)
_EXPECT_STATUS_RE = re.compile(
    r"pm\.expect\s*\(\s*pm\.response\.(?:code|status)\s*\)\.(?:to\.)?(?:eql|equal|be)\s*\(\s*(\d+)\s*\)"
    r"|pm\.response\.to\.have\.status\s*\(\s*(\d+)\s*\)"
)
_EXPECT_JSONPATH_RE = re.compile(
    r"pm\.expect\s*\(\s*(\w+)\.(\w+)\s*\)\.(?:to\.)?(?:eql|equal|be)\s*\(\s*"
    r"(['\"])(.*?)\3\s*\)"
    r"|pm\.expect\s*\(\s*(\w+)\.(\w+)\s*\)\.(?:to\.)?include\s*\(\s*"
    r"(['\"])(.*?)\7\s*\)"
)
_TEST_BLOCK_RE = re.compile(
    r"pm\.test\s*\(\s*(['\"])([^'\"]+)\1\s*,\s*function\s*\(\s*\)\s*\{([^}]*)\}\s*\)\s*;?\s*$",
    re.DOTALL,
)


def run_pre_request_script(
    script: Optional[str],
    request: ApiRequest,
    variables: Dict[str, str],
) -> ScriptRunResult:
    return _run_script(script, phase="pre", request=request, variables=variables)


def run_post_request_script(
    script: Optional[str],
    request: ApiRequest,
    variables: Dict[str, str],
    *,
    status_code: int,
    response_headers: Dict[str, str],
    response_body: Optional[str],
) -> ScriptRunResult:
    response = _PmResponse(status_code=status_code, headers=response_headers, body=response_body)
    return _run_script(
        script,
        phase="post",
        request=request,
        variables=variables,
        response=response,
    )


def _run_script(
    script: Optional[str],
    *,
    phase: str,
    request: ApiRequest,
    variables: Dict[str, str],
    response: Optional[_PmResponse] = None,
) -> ScriptRunResult:
    result = ScriptRunResult()
    text = str(script or "").strip()
    if not text:
        result.variables = dict(variables)
        return result

    bindings: Dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).strip()
        if not line:
            continue
        try:
            _exec_line(line, phase=phase, request=request, result=result, variables=variables, response=response, bindings=bindings)
        except Exception as exc:  # noqa: BLE001
            result.ok = False
            result.errors.append(f"{line[:80]} -> {exc}")

    result.variables = dict(variables)
    return result


def _strip_comment(line: str) -> str:
    if "//" in line:
        return line.split("//", 1)[0]
    return line


def _exec_line(
    line: str,
    *,
    phase: str,
    request: ApiRequest,
    result: ScriptRunResult,
    variables: Dict[str, str],
    response: Optional[_PmResponse],
    bindings: Dict[str, Any],
) -> None:
    if phase == "post" and response is not None:
        m = _JSON_BIND_RE.match(line)
        if m:
            bindings[m.group(1)] = response.json()
            result.logs.append(f"var {m.group(1)} = pm.response.json()")
            return

    m = _TEST_BLOCK_RE.match(line.replace("\n", " "))
    if m and response is not None:
        title = m.group(2)
        body = m.group(3)
        passed, msg = _eval_test_body(body, response, bindings)
        result.script_tests.append({"name": title, "passed": passed, "message": msg})
        result.logs.append(f"pm.test {title!r}: {'OK' if passed else 'FAIL'}")
        if not passed:
            result.ok = False
        return

    if phase == "post" and response is not None:
        m = _EXPECT_STATUS_RE.search(line)
        if m:
            expected = int(m.group(1) or m.group(2))
            passed = response.code == expected
            result.script_tests.append(
                {
                    "name": f"HTTP {expected}",
                    "passed": passed,
                    "message": f"status {response.code} (esperado {expected})",
                }
            )
            if not passed:
                result.ok = False
            return

    m = _PROP_IDX_SET_RE.match(line)
    if m:
        scope, _, key, bind, _, prop = m.groups()
        value = _resolve_binding(bindings, bind, prop)
        _set_var(scope, key, value, variables)
        result.logs.append(f"pm.{scope}.set({key!r}, ...)")
        return

    m = _PROP_SET_RE.match(line)
    if m:
        scope, _, key, bind, prop = m.groups()
        value = _resolve_binding(bindings, bind, prop)
        _set_var(scope, key, value, variables)
        result.logs.append(f"pm.{scope}.set({key!r}, ...)")
        return

    m = _SET_RE.match(line)
    if m:
        scope, _, key, raw_value = m.groups()
        value = _eval_value(raw_value, variables, bindings, response)
        _set_var(scope, key, value, variables)
        result.logs.append(f"pm.{scope}.set({key!r}, {value!r})")
        return

    if phase == "pre":
        m = _HEADER_ADD_RE.match(line)
        if m:
            _, header_key, raw_value = m.groups()
            value = str(_eval_value(raw_value, variables, bindings, response))
            request.headers[str(header_key)] = value
            result.logs.append(f"header upsert {header_key!r}")
            return

        m = _HEADER_REMOVE_RE.match(line)
        if m:
            header_key = m.group(2)
            request.headers.pop(header_key, None)
            result.logs.append(f"header remove {header_key!r}")
            return

    result.logs.append(f"(omitido) {line[:100]}")


def _set_var(scope: str, key: str, value: Any, variables: Dict[str, str]) -> None:
    variables[str(key)] = "" if value is None else str(value)


def _resolve_binding(bindings: Dict[str, Any], bind: str, prop: str) -> Any:
    obj = bindings.get(bind)
    if isinstance(obj, dict):
        return obj.get(prop)
    if obj is not None and hasattr(obj, prop):
        return getattr(obj, prop)
    return None


def _eval_test_body(body: str, response: _PmResponse, bindings: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    bindings = bindings or {}
    m = _EXPECT_STATUS_RE.search(body)
    if m:
        expected = int(m.group(1) or m.group(2))
        passed = response.code == expected
        return passed, f"HTTP {response.code} (esperado {expected})"

    m = _EXPECT_JSONPATH_RE.search(body.replace("\n", " "))
    if m:
        if m.group(1):
            bind, prop, _, expected = m.group(1), m.group(2), m.group(3), m.group(4)
            actual = _resolve_binding(bindings, bind, prop)
            passed = str(actual) == str(expected)
            return passed, f"{bind}.{prop}={actual!r} (esperado {expected!r})"
        bind, prop, _, expected = m.group(5), m.group(6), m.group(7), m.group(8)
        actual = _resolve_binding(bindings, bind, prop)
        passed = expected in str(actual or "")
        return passed, f"{bind}.{prop} incluye {expected!r}"

    return False, "Test no reconocido en script"


def _eval_value(
    expr: str,
    variables: Dict[str, str],
    bindings: Dict[str, Any],
    response: Optional[_PmResponse],
) -> Any:
    expr = expr.strip()
    if not expr:
        return ""

    if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
        return expr[1:-1]

    if expr.isdigit():
        return expr

    m = _GET_RE.fullmatch(expr)
    if m:
        return variables.get(m.group(3), "")

    if expr.startswith("pm.response.text"):
        return response.text if response else ""

    if "+".join(part.strip() for part in expr.split("+")) and "+" in expr:
        parts = [p.strip() for p in expr.split("+")]
        return "".join(str(_eval_value(p, variables, bindings, response)) for p in parts)

    if expr.endswith(".json()") and response is not None:
        return response.json()

    return expr
