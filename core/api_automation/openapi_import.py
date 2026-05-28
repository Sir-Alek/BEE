"""Importación de especificaciones OpenAPI 3.x a escenarios ApiRequest."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from core.api_automation.models import ApiRequest

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def import_openapi_spec(data: Dict[str, Any], *, source_name: str = "OpenAPI") -> List[ApiRequest]:
    if not isinstance(data, dict):
        raise ValueError("Especificación OpenAPI inválida")
    info = data.get("info") or {}
    title = str(info.get("title") or source_name)
    base_url = _resolve_server(data)
    paths = data.get("paths") or {}
    if not isinstance(paths, dict):
        return []

    requests: List[ApiRequest] = []
    for path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            req = _operation_to_request(base_url, path, method, operation, title=title)
            if req:
                requests.append(req)
    return requests


def import_openapi_file(path: str) -> List[ApiRequest]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return import_openapi_spec(data, source_name=path)


def _resolve_server(data: Dict[str, Any]) -> str:
    servers = data.get("servers") or []
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict):
            url = str(first.get("url") or "").strip()
            if url:
                return url.rstrip("/")
    return "{{base_url}}"


def _operation_to_request(
    base_url: str,
    path: str,
    method: str,
    operation: Dict[str, Any],
    *,
    title: str,
) -> Optional[ApiRequest]:
    summary = str(operation.get("summary") or operation.get("operationId") or f"{method.upper()} {path}")
    url = f"{base_url}{path}"
    headers: Dict[str, str] = {}
    body: Optional[str] = None

    request_body = operation.get("requestBody")
    if isinstance(request_body, dict):
        content = request_body.get("content") or {}
        if isinstance(content, dict):
            json_content = content.get("application/json")
            if isinstance(json_content, dict):
                example = json_content.get("example")
                if example is not None:
                    body = json.dumps(example, ensure_ascii=False)
                headers.setdefault("Content-Type", "application/json")

    parameters = operation.get("parameters") or []
    if isinstance(parameters, list):
        for param in parameters:
            if not isinstance(param, dict):
                continue
            if param.get("in") == "header" and param.get("name"):
                headers[str(param["name"])] = str(param.get("example") or "{{" + str(param["name"]) + "}}")

    req_id = f"openapi-{uuid.uuid4().hex[:8]}"
    return ApiRequest(
        id=req_id,
        name=f"{title}: {summary}",
        method=method.upper(),
        url=url,
        headers=headers,
        body=body,
        expected_status=200,
        source="openapi",
    )
