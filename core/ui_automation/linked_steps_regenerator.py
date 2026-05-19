"""
Regeneración / fusión de step definitions al vincular conversión a escenario existente.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

from core.ui_automation.recording_linkage import extract_steps_for_scenario


def project_path_from_feature_file(feature_file: str) -> Optional[str]:
    """Resuelve raíz del proyecto Behave a partir de .../proyecto/features/....feature"""
    path = os.path.normpath(feature_file)
    parts = path.split(os.sep)
    for i, part in enumerate(parts):
        if part == "features" and i > 0:
            return os.sep.join(parts[:i])
    return None


def _escape_for_regex(text: str) -> str:
    return re.escape(text.strip())


def find_steps_file_for_scenario(
    project_path: str,
    feature_file: str,
    scenario_name: str,
) -> Optional[str]:
    """
    Localiza el *_steps.py más probable para un escenario (por coincidencia de decoradores).
    """
    steps_dir = os.path.join(project_path, "features", "steps")
    if not os.path.isdir(steps_dir):
        return None

    try:
        with open(feature_file, "r", encoding="utf-8", errors="replace") as f:
            feature_text = f.read()
    except OSError:
        feature_text = ""

    gherkin_steps = extract_steps_for_scenario(feature_text, scenario_name)
    if not gherkin_steps:
        gherkin_steps = []
        for _kw, body in re.findall(
            r"^\s+(Given|When|Then|And|But)\s+(.+)$",
            feature_text,
            re.MULTILINE | re.I,
        ):
            gherkin_steps.append(f"{_kw.capitalize()} {body.strip()}")

    best_path: Optional[str] = None
    best_score = 0

    for fname in os.listdir(steps_dir):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(steps_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            continue

        score = 0
        for step in gherkin_steps:
            frag = step.split(" ", 1)[-1] if " " in step else step
            if frag and frag in content:
                score += 1
            elif frag and re.search(_escape_for_regex(frag[: min(40, len(frag))]), content):
                score += 1

        if score > best_score:
            best_score = score
            best_path = path

    if best_path and best_score > 0:
        return best_path

    # Fallback: único archivo steps del proyecto
    py_files = [f for f in os.listdir(steps_dir) if f.endswith(".py")]
    if len(py_files) == 1:
        return os.path.join(steps_dir, py_files[0])
    return None


def _split_step_functions(steps_module_content: str) -> Tuple[str, List[str]]:
    """Separa imports cabecera y bloques de funciones step."""
    text = (steps_module_content or "").strip()
    if not text:
        return "", []

    parts = re.split(r"\n(?=@(?:given|when|then|and)\b)", text, flags=re.I)
    if not parts:
        return text, []

    if re.match(r"^@(?:given|when|then|and)\b", parts[0], re.I):
        return "", [p.strip() for p in parts if p.strip()]

    header = parts[0].strip()
    blocks = [p.strip() for p in parts[1:] if p.strip()]
    return header, blocks


def _decorator_key(block: str) -> Optional[str]:
    m = re.search(
        r"@(given|when|then|and)\s*\(\s*['\"](.+?)['\"]",
        block,
        re.I | re.DOTALL,
    )
    if m:
        return f"@{m.group(1).lower()}('{m.group(2)}')"
    return None


def _ensure_imports(content: str, required_lines: List[str]) -> str:
    out = content
    for line in required_lines:
        if line.strip() and line.strip() not in out:
            if "from behave import" in line and "from behave import" in out:
                continue
            out = line + "\n" + out
    return out


def regenerate_linked_steps(
    *,
    project_path: str,
    feature_file: str,
    scenario_name: str,
    steps_module_content: str,
    page_import_line: Optional[str] = None,
) -> str:
    """
    Fusiona definiciones step generadas en el archivo steps del escenario vinculado.

    Devuelve la ruta del archivo steps actualizado o creado.
    """
    steps_dir = os.path.join(project_path, "features", "steps")
    os.makedirs(steps_dir, exist_ok=True)

    target = find_steps_file_for_scenario(project_path, feature_file, scenario_name)
    header, new_blocks = _split_step_functions(steps_module_content)

    required_imports: List[str] = ["from behave import *"]
    if page_import_line and page_import_line.strip():
        required_imports.append(page_import_line.strip())
    if "from environment import" not in (header or steps_module_content):
        required_imports.append("from environment import *")

    new_keys = {_decorator_key(b) for b in new_blocks}
    new_keys.discard(None)

    if target and os.path.isfile(target):
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            existing = f.read()
        existing_keys = {_decorator_key(b) for b in _split_step_functions(existing)[1]}

        to_append = []
        for block in new_blocks:
            key = _decorator_key(block)
            if key and key in existing_keys:
                continue
            to_append.append(block)

        if not to_append:
            return target

        merged = existing.rstrip() + "\n\n# --- ELIA: steps vinculados (grabación) ---\n\n"
        merged += "\n\n".join(to_append) + "\n"
        merged = _ensure_imports(merged, required_imports)

        with open(target, "w", encoding="utf-8") as f:
            f.write(merged)
        return target

    slug = re.sub(r"[^\w]+", "_", scenario_name).strip("_")[:50] or "linked"
    target = os.path.join(steps_dir, f"elia_linked_{slug}_steps.py")
    body = _ensure_imports(header + "\n\n" if header else "", required_imports)
    body += "\n\n" + "\n\n".join(new_blocks) + "\n"
    with open(target, "w", encoding="utf-8") as f:
        f.write(body)
    return target
