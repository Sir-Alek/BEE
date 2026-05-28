"""Importación de colecciones Postman v2.1 a escenarios ApiRequest."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from core.api_automation.models import ApiRequest


def import_postman_collection(data: Dict[str, Any], *, source_name: str = "Postman") -> List[ApiRequest]:
    info = data.get("info") if isinstance(data, dict) else {}
    collection_name = str((info or {}).get("name") or source_name)
    variables = _postman_variables(data)
    items = data.get("item") if isinstance(data, dict) else []
    if not isinstance(items, list):
        items = []
    return _walk_items(items, variables, prefix=collection_name)


def import_postman_file(path: str) -> List[ApiRequest]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Colección Postman inválida")
    return import_postman_collection(data, source_name=path)


def _postman_variables(data: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in data.get("variable") or []:
        if isinstance(item, dict):
            key = str(item.get("key") or "").strip()
            if key:
                out[key] = str(item.get("value") or "")
    return out


def _walk_items(
    items: List[Any],
    variables: Dict[str, str],
    *,
    prefix: str,
) -> List[ApiRequest]:
    requests: List[ApiRequest] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if "request" in item:
            req = _item_to_request(item, variables, prefix=prefix)
            if req:
                requests.append(req)
            continue
        nested = item.get("item")
        if isinstance(nested, list):
            folder = str(item.get("name") or prefix)
            requests.extend(_walk_items(nested, variables, prefix=folder))
    return requests


def _item_to_request(
    item: Dict[str, Any],
    variables: Dict[str, str],
    *,
    prefix: str,
) -> Optional[ApiRequest]:
    raw = item.get("request")
    if not isinstance(raw, dict):
        return None
    if isinstance(raw.get("url"), dict):
        url = _postman_url(raw["url"])
    else:
        url = str(raw.get("url") or "")
    method = str(raw.get("method") or "GET").upper()
    if not url:
        return None

    headers: Dict[str, str] = {}
    for header in raw.get("header") or []:
        if isinstance(header, dict) and not header.get("disabled"):
            key = str(header.get("key") or "").strip()
            if key:
                headers[key] = str(header.get("value") or "")

    body = _postman_body(raw.get("body"))
    name = str(item.get("name") or f"{method} {url}")
    req_id = f"postman-{uuid.uuid4().hex[:8]}"
    return ApiRequest(
        id=req_id,
        name=f"{prefix}: {name}" if prefix else name,
        method=method,
        url=url,
        headers=headers,
        body=body,
        expected_status=200,
        source="postman",
    )


def _postman_url(url_obj: Dict[str, Any]) -> str:
    raw = str(url_obj.get("raw") or "").strip()
    if raw:
        return raw
    protocol = str(url_obj.get("protocol") or "https")
    host_parts = url_obj.get("host") or []
    if isinstance(host_parts, list):
        host = ".".join(str(p) for p in host_parts)
    else:
        host = str(host_parts)
    path_parts = url_obj.get("path") or []
    if isinstance(path_parts, list):
        path = "/".join(str(p) for p in path_parts)
    else:
        path = str(path_parts)
    if not host:
        return path
    return f"{protocol}://{host}/{path.lstrip('/')}"


def _postman_body(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    mode = str(body.get("mode") or "")
    if mode == "raw":
        raw = body.get("raw")
        return str(raw) if raw is not None else None
    if mode == "urlencoded":
        pairs = []
        for item in body.get("urlencoded") or []:
            if isinstance(item, dict) and not item.get("disabled"):
                pairs.append(f"{item.get('key')}={item.get('value')}")
        return "&".join(pairs) if pairs else None
    return None
