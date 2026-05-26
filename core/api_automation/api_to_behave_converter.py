"""Conversión de escenarios API a features Behave."""
from __future__ import annotations

import json
import os
import re
from typing import List, Optional

from core.api_automation.models import ApiRequest
from core.api_automation.traffic_store import ensure_api_project


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", text.strip())[:48].strip("_")
    return s or "escenario_api"


def requests_to_feature(requests: List[ApiRequest], *, feature_name: str = "Flujo API") -> str:
    lines = [
        "Feature: API generada por ELIA",
        f"  Escenarios de peticiones HTTP capturadas o definidas manualmente.",
        "",
        f"  Scenario: {_slug(feature_name)}",
    ]
    for req in requests:
        for hk, hv in req.headers.items():
            lines.append(f'    Given la petición usa el header "{hk}" con valor "{hv}"')
        if req.body:
            lines.append(f'    # body: {req.body[:120].replace(chr(10), " ")}...')
        lines.append(f'    When envío una petición "{req.method}" a "{req.url}"')
        lines.append(f"    Then el código HTTP de respuesta es {req.expected_status}")
    return "\n".join(lines) + "\n"


def write_api_feature(
    project: str,
    requests: List[ApiRequest],
    *,
    feature_name: str = "Flujo API",
    use_ai: bool = False,
) -> str:
    del use_ai  # reservado para inferencia Gemma en iteración posterior
    root = ensure_api_project(project)
    features_dir = root / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    fname = _slug(feature_name) + ".feature"
    path = features_dir / fname
    content = requests_to_feature(requests, feature_name=feature_name)
    path.write_text(content, encoding="utf-8")
    return str(path)


def convert_traffic_to_feature(project: str, traffic_path: str, *, feature_name: Optional[str] = None) -> str:
    from core.api_automation.traffic_store import load_traffic_file

    capture = load_traffic_file(traffic_path)
    if not capture.entries:
        raise ValueError("La captura no contiene peticiones API")
    name = feature_name or os.path.splitext(os.path.basename(traffic_path))[0]
    return write_api_feature(project, capture.entries, feature_name=name)
