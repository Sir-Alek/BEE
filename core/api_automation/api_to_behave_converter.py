"""Conversión de escenarios API a features Behave."""
from __future__ import annotations

import os
import re
from typing import List, Optional

from core.api_automation.api_assertion_ai import enrich_requests_with_assertions
from core.api_automation.models import ApiAssertion, ApiRequest
from core.api_automation.traffic_store import ensure_api_project


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", text.strip())[:48].strip("_")
    return s or "escenario_api"


def _assertion_to_then_line(a: ApiAssertion) -> Optional[str]:
    if a.kind == "status":
        code = a.expected or "200"
        if str(code).isdigit():
            return f"el código HTTP de respuesta es {int(code)}"
    elif a.kind == "jsonpath" and a.expression:
        key = a.expression.replace('"', "").strip()
        if key:
            return f'el JSON de respuesta contiene la clave "{key}"'
    return None


def requests_to_feature(requests: List[ApiRequest], *, feature_name: str = "Flujo API") -> str:
    lines = [
        "Feature: API generada por ELIA",
        "  Escenarios de peticiones HTTP capturadas o definidas manualmente.",
        "",
        f"  Scenario: {_slug(feature_name)}",
    ]
    for req in requests:
        for hk, hv in req.headers.items():
            lines.append(f'    Given la petición usa el header "{hk}" con valor "{hv}"')
        if req.body:
            lines.append(f'    # body: {req.body[:120].replace(chr(10), " ")}...')
            lines.append("    When envío el cuerpo JSON de la petición")
        lines.append(f'    When envío una petición "{req.method}" a "{req.url}"')
        assertions = req.assertions or [
            ApiAssertion(kind="status", expected=str(req.expected_status or 200))
        ]
        then_lines: List[str] = []
        for a in assertions:
            line = _assertion_to_then_line(a)
            if line and line not in then_lines:
                then_lines.append(line)
        if not then_lines:
            then_lines.append(f"el código HTTP de respuesta es {req.expected_status or 200}")
        for i, tl in enumerate(then_lines):
            kw = "Then" if i == 0 else "And"
            lines.append(f"    {kw} {tl}")
    return "\n".join(lines) + "\n"


def write_api_feature(
    project: str,
    requests: List[ApiRequest],
    *,
    feature_name: str = "Flujo API",
    use_ai: bool = False,
) -> str:
    from core.test_runner.behave_support import ensure_platform_behave_support

    root = ensure_api_project(project)
    ensure_platform_behave_support(root, "api")
    enriched = enrich_requests_with_assertions(requests, use_ai=use_ai)
    features_dir = root / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    fname = _slug(feature_name) + ".feature"
    path = features_dir / fname
    content = requests_to_feature(enriched, feature_name=feature_name)
    path.write_text(content, encoding="utf-8")
    return str(path)


def convert_traffic_to_feature(
    project: str,
    traffic_path: str,
    *,
    feature_name: Optional[str] = None,
    use_ai: bool = False,
) -> str:
    from core.api_automation.traffic_store import load_traffic_file

    capture = load_traffic_file(traffic_path)
    if not capture.entries:
        raise ValueError("La captura no contiene peticiones API")
    name = feature_name or os.path.splitext(os.path.basename(traffic_path))[0]
    return write_api_feature(project, capture.entries, feature_name=name, use_ai=use_ai)
