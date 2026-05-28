"""Utilidades JSONPath ligeras ($.a.b[0].c) sin dependencias externas."""
from __future__ import annotations

import json
import re
from typing import Any, List, Optional, Tuple


def _parse_path(path: str) -> List[str | int]:
    raw = (path or "").strip()
    if raw.startswith("$"):
        raw = raw[1:]
    if raw.startswith("."):
        raw = raw[1:]
    tokens: List[str | int] = []
    for part in re.split(r"\.(?![^\[]*\])", raw):
        part = part.strip()
        if not part:
            continue
        bracket = re.match(r"^([^\[]+)(\[(\d+)\])?$", part)
        if not bracket:
            tokens.append(part)
            continue
        key = bracket.group(1)
        if key:
            tokens.append(key)
        if bracket.group(3) is not None:
            tokens.append(int(bracket.group(3)))
        elif part.endswith("[]"):
            tokens.append(part[:-2])
    return tokens


def get_json_path(data: Any, path: str) -> Tuple[bool, Any]:
    if not path:
        return False, None
    tokens = _parse_path(path)
    if not tokens and path.strip().startswith("$"):
        return True, data
    current = data
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return False, None
            current = current[token]
            continue
        if isinstance(current, dict) and token in current:
            current = current[token]
            continue
        return False, None
    return True, current


def json_path_exists(data: Any, path: str) -> bool:
    ok, _ = get_json_path(data, path)
    return ok


def json_path_value(data: Any, path: str) -> Optional[Any]:
    ok, value = get_json_path(data, path)
    return value if ok else None


def parse_json_body(body: Optional[str]) -> Tuple[bool, Any]:
    if body is None or body == "":
        return True, {}
    try:
        return True, json.loads(body)
    except json.JSONDecodeError:
        return False, None
