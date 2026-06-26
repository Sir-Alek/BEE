"""Importación de especificaciones OpenAPI 3.x a escenarios ApiRequest."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Set

from core.api_automation.models import ApiRequest

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def import_openapi_spec(data: Dict[str, Any], *, source_name: str = "OpenAPI") -> tuple[List[ApiRequest], str]:
    if not isinstance(data, dict):
        raise ValueError("Especificación OpenAPI inválida")
    info = data.get("info") or {}
    title = str(info.get("title") or source_name).strip() or "OpenAPI"
    base_url = _resolve_server(data)
    paths = data.get("paths") or {}
    if not isinstance(paths, dict):
        return [], title

    requests: List[ApiRequest] = []
    for path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            req = _operation_to_request(data, base_url, path, method, operation)
            if req:
                requests.append(req)
    return requests, title


def import_openapi_file(path: str) -> List[ApiRequest]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return import_openapi_spec(data, source_name=path)[0]


def _resolve_server(data: Dict[str, Any]) -> str:
    servers = data.get("servers") or []
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict):
            url = str(first.get("url") or "").strip()
            if url:
                return url.rstrip("/")
    return "{{base_url}}"


def _resolve_ref(root: Dict[str, Any], ref: str, *, _seen: Optional[Set[str]] = None) -> Any:
    if not ref or not ref.startswith("#/"):
        return None
    if _seen is None:
        _seen = set()
    if ref in _seen:
        return None
    _seen.add(ref)
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    if isinstance(node, dict) and "$ref" in node:
        return _resolve_ref(root, str(node["$ref"]), _seen=_seen)
    return node


def _example_from_schema(root: Dict[str, Any], schema: Any) -> Any:
    if not isinstance(schema, dict):
        return None
    if "example" in schema:
        return schema.get("example")
    if "$ref" in schema:
        resolved = _resolve_ref(root, str(schema["$ref"]))
        if isinstance(resolved, dict):
            return _example_from_schema(root, resolved)
        return None
    schema_type = schema.get("type")
    if schema_type == "object":
        props = schema.get("properties") or {}
        if not isinstance(props, dict):
            return {}
        out: Dict[str, Any] = {}
        for key, sub in props.items():
            val = _example_from_schema(root, sub)
            if val is not None:
                out[str(key)] = val
        return out if out else None
    if schema_type == "array":
        items = schema.get("items")
        item_ex = _example_from_schema(root, items)
        return [item_ex] if item_ex is not None else []
    if schema_type == "string":
        return schema.get("default") or "string"
    if schema_type == "integer":
        return schema.get("default") or 0
    if schema_type == "number":
        return schema.get("default") or 0.0
    if schema_type == "boolean":
        return schema.get("default") if "default" in schema else False
    return schema.get("default")


def _resolve_param(root: Dict[str, Any], param: Dict[str, Any]) -> Dict[str, Any]:
    if "$ref" in param:
        resolved = _resolve_ref(root, str(param["$ref"]))
        if isinstance(resolved, dict):
            return resolved
    return param


def _operation_to_request(
    root: Dict[str, Any],
    base_url: str,
    path: str,
    method: str,
    operation: Dict[str, Any],
) -> Optional[ApiRequest]:
    summary = str(operation.get("summary") or operation.get("operationId") or f"{method.upper()} {path}")
    url = f"{base_url}{path}"
    headers: Dict[str, str] = {}
    body: Optional[str] = None

    request_body = operation.get("requestBody")
    if isinstance(request_body, dict):
        if "$ref" in request_body:
            request_body = _resolve_ref(root, str(request_body["$ref"])) or request_body
        content = request_body.get("content") or {}
        if isinstance(content, dict):
            json_content = content.get("application/json")
            if isinstance(json_content, dict):
                example = json_content.get("example")
                if example is None:
                    example = _example_from_schema(root, json_content.get("schema"))
                if example is not None:
                    body = json.dumps(example, ensure_ascii=False)
                headers.setdefault("Content-Type", "application/json")

    parameters = operation.get("parameters") or []
    if isinstance(parameters, list):
        for raw_param in parameters:
            if not isinstance(raw_param, dict):
                continue
            param = _resolve_param(root, raw_param)
            if param.get("in") == "header" and param.get("name"):
                example = param.get("example")
                if example is None and isinstance(param.get("schema"), dict):
                    example = _example_from_schema(root, param["schema"])
                headers[str(param["name"])] = str(example or "{{" + str(param["name"]) + "}}")

    req_id = f"openapi-{uuid.uuid4().hex[:8]}"
    return ApiRequest(
        id=req_id,
        name=summary,
        method=method.upper(),
        url=url,
        headers=headers,
        body=body,
        expected_status=200,
        source="openapi",
    )
