"""Interpolación de variables {{nombre}} en URLs, headers y cuerpos."""
from __future__ import annotations

import re
from typing import Any, Dict, Mapping

_VAR_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


def interpolate_text(text: str, variables: Mapping[str, str]) -> str:
    if not text or "{{" not in text:
        return text

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key in variables:
            return str(variables[key])
        return match.group(0)

    return _VAR_PATTERN.sub(repl, text)


def interpolate_value(value: Any, variables: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return interpolate_text(value, variables)
    if isinstance(value, dict):
        return {str(k): interpolate_value(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate_value(item, variables) for item in value]
    return value


def extract_variable_names(text: str) -> list[str]:
    if not text:
        return []
    return [m.group(1).strip() for m in _VAR_PATTERN.finditer(text)]


def merge_variables(*layers: Mapping[str, str]) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for layer in layers:
        for key, value in layer.items():
            merged[str(key)] = str(value)
    return merged
