"""
Parseo de page_source XML (UiAutomator2 / Appium) para extraer localizadores reales.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MobileElement:
    """Elemento interactivo detectado en la jerarquía Android."""

    resource_id: str = ""
    text: str = ""
    content_desc: str = ""
    class_name: str = ""
    bounds: str = ""
    clickable: bool = False
    appium_by: str = ""
    appium_value: str = ""
    method_suffix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "text": self.text,
            "content_desc": self.content_desc,
            "class_name": self.class_name,
            "bounds": self.bounds,
            "clickable": self.clickable,
            "appium_by": self.appium_by,
            "appium_value": self.appium_value,
            "method_suffix": self.method_suffix,
        }


_INTERACTIVE_CLASS_HINTS = (
    "Button",
    "EditText",
    "CheckBox",
    "Switch",
    "ImageButton",
    "TextView",
    "android.view.View",
)


def _attr(node: ET.Element, *names: str) -> str:
    for n in names:
        v = node.get(n)
        if v:
            return str(v).strip()
    return ""


def _is_interactive(node: ET.Element) -> bool:
    clickable = _attr(node, "clickable", "clickable").lower() == "true"
    cls = _attr(node, "class", "class")
    if clickable:
        return True
    return any(hint in cls for hint in _INTERACTIVE_CLASS_HINTS if cls)


def _build_locator(resource_id: str, text: str, content_desc: str) -> tuple[str, str]:
    if resource_id and ":" in resource_id:
        return "ID", resource_id
    if content_desc:
        return "ACCESSIBILITY_ID", content_desc
    if text and len(text) <= 80:
        return "ANDROID_UIAUTOMATOR", f'new UiSelector().text("{text.replace(chr(34), "")}")'
    return "", ""


def _safe_method_suffix(resource_id: str, text: str, content_desc: str, index: int) -> str:
    base = resource_id.split("/")[-1] if resource_id else ""
    if not base:
        base = content_desc or text or f"element_{index}"
    base = re.sub(r"[^\w]", "_", base.lower()).strip("_")
    if not base:
        base = f"element_{index}"
    if base[0].isdigit():
        base = f"el_{base}"
    return base[:48]


def parse_android_page_source(xml_source: str, *, max_elements: int = 12) -> List[MobileElement]:
    """
    Extrae elementos interactivos del XML de page_source.
    Prioriza resource-id, luego content-desc y texto visible.
    """
    if not (xml_source or "").strip():
        return []

    snippet = xml_source.strip()
    if len(snippet) > 500_000:
        snippet = snippet[:500_000]

  # UiAutomator a veces devuelve XML sin declaración única raíz envolvente
    try:
        root = ET.fromstring(snippet)
    except ET.ParseError:
        wrapped = f"<hierarchy>{snippet}</hierarchy>"
        try:
            root = ET.fromstring(wrapped)
        except ET.ParseError:
            return []

    candidates: List[MobileElement] = []
    seen_ids: set[str] = set()
    idx = 0

    for node in root.iter():
        if not _is_interactive(node):
            continue
        resource_id = _attr(node, "resource-id", "resourceId")
        text = _attr(node, "text", "text")
        content_desc = _attr(node, "content-desc", "contentDescription", "content-desc")
        cls = _attr(node, "class", "class")
        bounds = _attr(node, "bounds", "bounds")
        clickable = _attr(node, "clickable", "clickable").lower() == "true"

        if not resource_id and not text and not content_desc:
            continue

        dedupe_key = resource_id or f"{content_desc}|{text}|{cls}"
        if dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)

        by, value = _build_locator(resource_id, text, content_desc)
        if not by:
            continue

        idx += 1
        candidates.append(
            MobileElement(
                resource_id=resource_id,
                text=text,
                content_desc=content_desc,
                class_name=cls,
                bounds=bounds,
                clickable=clickable,
                appium_by=by,
                appium_value=value,
                method_suffix=_safe_method_suffix(resource_id, text, content_desc, idx),
            )
        )

    # Priorizar: clickable + resource-id > content-desc > text
    def _score(el: MobileElement) -> int:
        s = 0
        if el.clickable:
            s += 10
        if el.resource_id:
            s += 8
        if el.content_desc:
            s += 4
        if el.text:
            s += 2
        return s

    candidates.sort(key=_score, reverse=True)
    return candidates[:max_elements]


def screen_anchor_element(elements: List[MobileElement]) -> Optional[MobileElement]:
    """Elemento principal para esperar que la pantalla cargó."""
    if not elements:
        return None
    for el in elements:
        if el.resource_id:
            return el
    return elements[0]


def screen_signature(elements: List[MobileElement], fallback: str) -> str:
    if not elements:
        return fallback
    el = screen_anchor_element(elements)
    if el and el.resource_id:
        return el.resource_id.split("/")[-1]
    if el and el.content_desc:
        return re.sub(r"[^\w]", "_", el.content_desc.lower())[:32]
    return fallback
