"""
Análisis de flujos para grabaciones JSON (móvil / legacy) — prefijos comunes y Background.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.ui_automation.flow_analyzer import ActionTuple, FlowAnalyzer
from core.ui_automation.mobile_dom_parser import (
    parse_android_page_source,
    screen_anchor_element,
    screen_signature,
)

# kind extendido: launch | screen | click | fill | key (legacy key ignorado en prefix)


def extract_legacy_recording_actions(
    events: List[Dict[str, Any]],
    meta: Optional[Dict[str, Any]] = None,
) -> List[ActionTuple]:
    meta = meta or {}
    actions: List[ActionTuple] = []
    win = str(meta.get("window_name") or meta.get("exe_path") or "aplicacion")
    actions.append(("launch", win, None))
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "click":
            label = str(ev.get("control_name") or f"{ev.get('x')},{ev.get('y')}")
            actions.append(("click", label, None))
    return actions


def extract_mobile_recording_actions(
    events: List[Dict[str, Any]],
    meta: Optional[Dict[str, Any]] = None,
) -> List[ActionTuple]:
    meta = meta or {}
    actions: List[ActionTuple] = []
    apk = str(meta.get("apk_path") or meta.get("app_package") or meta.get("device_id") or "app_movil")
    actions.append(("launch", apk, None))

    screen_idx = 0
    for ev in events:
        if not isinstance(ev, dict) or ev.get("type") != "page_source":
            continue
        screen_idx += 1
        source = str(ev.get("source") or "")
        elements = parse_android_page_source(source)
        sig = screen_signature(elements, f"screen_{screen_idx}")
        actions.append(("screen", sig, str(screen_idx)))

        stored = ev.get("elements")
        if isinstance(stored, list) and stored:
            elems = stored
        else:
            elems = [e.to_dict() for e in elements]

        for el in elems[:5]:
            if not isinstance(el, dict):
                continue
            rid = str(el.get("resource_id") or "")
            if rid:
                actions.append(("click", rid, str(el.get("text") or el.get("content_desc") or "")))

    return actions


def extract_recording_actions(
    events: List[Dict[str, Any]],
    platform: str,
    meta: Optional[Dict[str, Any]] = None,
) -> List[ActionTuple]:
    if platform == "mobile":
        return extract_mobile_recording_actions(events, meta)
    return extract_legacy_recording_actions(events, meta)


def extract_recording_background_steps(
    common_prefix: List[ActionTuple],
    platform: str,
    meta: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, str]]:
    """Pasos Gherkin para Background a partir del prefijo común de grabaciones."""
    if not common_prefix:
        return []

    meta = meta or {}
    steps: List[Tuple[str, str]] = []

    if platform == "mobile":
        launch_val = next((v for k, v, _ in common_prefix if k == "launch"), None)
        label = launch_val or meta.get("apk_path") or "la aplicación móvil"
        steps.append(("given", f'el usuario abre la aplicación móvil "{label}"'))
        screens = [v for k, v, _ in common_prefix if k == "screen"]
        if len(screens) >= 1:
            steps.append(("and", "la pantalla inicial está disponible"))
        return steps

    if platform == "legacy":
        launch_val = next((v for k, v, _ in common_prefix if k == "launch"), None)
        win = launch_val or meta.get("window_name") or "la aplicación de escritorio"
        steps.append(("given", f'el usuario tiene abierta la ventana "{win}"'))
        clicks = [v for k, v, _ in common_prefix if k == "click"]
        if clicks:
            steps.append(("and", "el usuario completa el acceso inicial en la ventana"))
        return steps

    return FlowAnalyzer.extract_background_steps(common_prefix)


def enrich_mobile_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Añade 'elements' parseados a cada evento page_source (para page objects)."""
    out: List[Dict[str, Any]] = []
    screen_idx = 0
    for ev in events:
        if not isinstance(ev, dict):
            continue
        item = dict(ev)
        if item.get("type") == "page_source":
            screen_idx += 1
            elements = parse_android_page_source(str(item.get("source") or ""))
            item["elements"] = [e.to_dict() for e in elements]
            anchor = screen_anchor_element(elements)
            if anchor:
                item["anchor"] = anchor.to_dict()
            item["screen_signature"] = screen_signature(elements, f"screen_{screen_idx}")
        out.append(item)
    return out
