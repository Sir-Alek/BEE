"""Parseo y renderizado de respuestas JSON del LLM para Doc-to-BDD."""
from __future__ import annotations

import json
import re
from typing import Any, List, Optional, Tuple

_KW_MAP = {"given": "Given", "when": "When", "then": "Then", "and": "And", "but": "But"}
_VALID_KW = frozenset(_KW_MAP.keys())


def extract_json_object(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if fence:
        s = fence.group(1)
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", s, re.DOTALL):
        chunk = match.group(0)
        try:
            parsed = json.loads(chunk)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def normalize_bdd_steps(raw_steps: Any) -> Optional[List[Tuple[str, str]]]:
    if not isinstance(raw_steps, list):
        return None
    out: List[Tuple[str, str]] = []
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        kw = str(step.get("keyword", "")).strip().lower()
        txt = str(step.get("text", "")).strip()
        if kw not in _VALID_KW or not txt:
            continue
        out.append((kw, txt[:120]))
    if not out:
        return None
    given_c = sum(1 for k, _ in out if k == "given")
    when_c = sum(1 for k, _ in out if k == "when")
    and_c = sum(1 for k, _ in out if k == "and")
    then_c = sum(1 for k, _ in out if k == "then")
    if when_c != 1 or then_c != 1 or given_c > 1 or and_c > 1:
        return None
    seen = [k for k, _ in out]
    expected: List[str] = []
    if "given" in seen:
        expected.append("given")
    expected.append("when")
    if "and" in seen:
        expected.append("and")
    expected.append("then")
    if seen != expected:
        return None
    return out


def render_scenario_block(scenario_title: str, steps: List[Tuple[str, str]]) -> str:
    title = (scenario_title or "Escenario generado").strip()[:80]
    lines = [f"  Scenario: {title}"]
    for kw, txt in steps:
        lines.append(f"    {_KW_MAP.get(kw, 'When')} {txt}")
    return "\n".join(lines)


def render_gherkin_from_bdd_response(data: dict[str, Any], *, feature_name: str = "") -> Optional[str]:
    steps = normalize_bdd_steps(data.get("steps"))
    if not steps:
        return None
    scenario_title = str(data.get("scenario_title") or feature_name or "Escenario").strip()
    feature_line = f"Feature: {(feature_name or scenario_title).strip()[:80]}\n"
    return feature_line + render_scenario_block(scenario_title, steps) + "\n"


def parse_bdd_llm_text(text: str, *, feature_name: str = "") -> Optional[str]:
    data = extract_json_object(text)
    if not data:
        return None
    return render_gherkin_from_bdd_response(data, feature_name=feature_name)
