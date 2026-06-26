"""Importación de colecciones Postman v2.1 a escenarios ApiRequest."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from core.api_automation.models import ApiRequest


def import_postman_collection(data: Dict[str, Any], *, source_name: str = "Colección") -> tuple[List[ApiRequest], str]:
    info = data.get("info") if isinstance(data, dict) else {}
    collection_name = str((info or {}).get("name") or source_name).strip() or "Colección"
    variables = _postman_variables(data)
    items = data.get("item") if isinstance(data, dict) else []
    if not isinstance(items, list):
        items = []
    requests = _walk_items(items, variables, prefix="")
    return requests, collection_name


def import_postman_file(path: str) -> List[ApiRequest]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Colección Postman inválida")
    return import_postman_collection(data, source_name=path)[0]


def postman_collection_variables(data: Dict[str, Any]) -> Dict[str, str]:
    """Variables de colección Postman (variable[])."""
    return _postman_variables(data)


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
            folder = str(item.get("name") or "").strip()
            nested_prefix = f"{prefix} / {folder}" if prefix and folder else (folder or prefix)
            requests.extend(_walk_items(nested, variables, prefix=nested_prefix))
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

    auth = raw.get("auth") if isinstance(raw.get("auth"), dict) else item.get("auth")
    if isinstance(auth, dict):
        auth_type = str(auth.get("type") or "").lower()
        if auth_type == "bearer":
            for entry in auth.get("bearer") or []:
                if isinstance(entry, dict) and str(entry.get("key") or "").lower() == "token":
                    token = str(entry.get("value") or "{{token}}")
                    headers.setdefault("Authorization", f"Bearer {token}")
        elif auth_type == "apikey":
            for entry in auth.get("apikey") or []:
                if not isinstance(entry, dict):
                    continue
                key = str(entry.get("key") or "").strip()
                val = str(entry.get("value") or "")
                where = str(entry.get("in") or "header").lower()
                if key and where == "header":
                    headers.setdefault(key, val or "{{" + key + "}}")

    body = _postman_body(raw.get("body"))
    name = str(item.get("name") or f"{method} {url}")
    pre_script, post_script = _postman_item_scripts(item)
    req_id = f"postman-{uuid.uuid4().hex[:8]}"
    display_name = f"{prefix} / {name}" if prefix else name
    return ApiRequest(
        id=req_id,
        name=display_name,
        method=method,
        url=url,
        headers=headers,
        body=body,
        expected_status=200,
        source="postman",
        pre_request_script=pre_script or None,
        post_request_script=post_script or None,
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


def _postman_item_scripts(item: Dict[str, Any]) -> tuple[str, str]:
    pre_lines: List[str] = []
    post_lines: List[str] = []
    for event in item.get("event") or []:
        if not isinstance(event, dict):
            continue
        listen = str(event.get("listen") or "").lower()
        script = event.get("script")
        if not isinstance(script, dict):
            continue
        exec_lines = script.get("exec")
        if isinstance(exec_lines, list):
            block = "\n".join(str(line) for line in exec_lines if str(line).strip())
        else:
            block = str(script.get("exec") or script.get("src") or "").strip()
        if not block:
            continue
        if listen == "prerequest":
            pre_lines.append(block)
        elif listen == "test":
            post_lines.append(block)
    return ("\n\n".join(pre_lines).strip(), "\n\n".join(post_lines).strip())


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
