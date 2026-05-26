"""
Vinculación de conversión → escenario BDD existente (grabaciones, web, documentos).
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Literal, Optional, Tuple

from core.req_intelligence.feature_scanner import merge_steps_into_scenario

MergeMode = Literal["append", "replace"]

LINK_SEP = "\x1f"
REC_LINK_SEP = "\x1e"


def encode_scenario_link(feature_file: str, scenario_name: str) -> str:
    return f"{feature_file}{LINK_SEP}{scenario_name}"


def decode_scenario_link(link: Optional[str]) -> Optional[Tuple[str, str]]:
    if not link or not str(link).strip():
        return None
    raw = str(link).strip()
    if LINK_SEP in raw:
        ff, _, sn = raw.partition(LINK_SEP)
        if ff and sn:
            return ff, sn
    if "||" in raw:
        ff, _, sn = raw.partition("||")
        if ff and sn:
            return ff, sn
    return None


def extract_steps_for_scenario(feature_text: str, scenario_name: str) -> List[str]:
    """Extrae pasos Gherkin de un bloque Scenario por nombre."""
    lines = feature_text.splitlines()
    in_scenario = False
    steps: List[str] = []
    target = scenario_name.strip().lower()

    for line in lines:
        m = re.match(r"^\s+Scenario(?:\s+Outline)?:\s*(.+)", line)
        if m:
            in_scenario = m.group(1).strip().lower() == target
            continue
        if in_scenario and re.match(r"^\s+Scenario(?:\s+Outline)?:", line):
            break
        if in_scenario:
            sm = re.match(r"^\s+(Given|When|Then|And|But)\s+(.+)", line, re.I)
            if sm:
                steps.append(f"{sm.group(1).capitalize()} {sm.group(2).strip()}")
    return steps


def extract_all_scenario_steps(feature_text: str) -> List[str]:
    """Concatena pasos de todos los Scenario: del texto (útil en features agrupados o doc)."""
    steps: List[str] = []
    in_block = False
    for line in feature_text.splitlines():
        if re.match(r"^\s+Scenario(?:\s+Outline)?:\s*", line):
            in_block = True
            continue
        if in_block and re.match(r"^(?:Feature:|Background:)", line):
            in_block = False
        if in_block:
            sm = re.match(r"^\s+(Given|When|Then|And|But)\s+(.+)", line, re.I)
            if sm:
                step = f"{sm.group(1).capitalize()} {sm.group(2).strip()}"
                if not steps or steps[-1] != step:
                    steps.append(step)
    return steps


def apply_link_to_existing_scenario(
    feature_text: str,
    feature_file: str,
    scenario_name: str,
    *,
    mode: MergeMode = "append",
    prefer_named_scenario: bool = True,
) -> bool:
    """
    Fusiona pasos generados en un escenario .feature existente.

    Si prefer_named_scenario y no hay pasos con ese nombre, usa todos los scenarios del texto.
    """
    steps: List[str] = []
    if prefer_named_scenario:
        steps = extract_steps_for_scenario(feature_text, scenario_name)
    if not steps:
        steps = extract_all_scenario_steps(feature_text)
    if not steps:
        return False
    return merge_steps_into_scenario(feature_file, scenario_name, steps, mode=mode)


def apply_grouped_link_to_scenario(
    feature_text: str,
    feature_file: str,
    scenario_name: str,
    *,
    mode: MergeMode = "append",
) -> bool:
    """Un escenario destino recibe los pasos de todos los Scenario del feature agrupado generado."""
    steps = extract_all_scenario_steps(feature_text)
    if not steps:
        return False
    return merge_steps_into_scenario(feature_file, scenario_name, steps, mode=mode)


def annotate_scenario_recording(
    feature_file: str,
    scenario_name: str,
    recording_ref: str,
) -> bool:
    """
    Añade un comentario de trazabilidad doc/grabación tras la línea Scenario:.
    recording_ref: nombre de .json/.js o ruta relativa.
    """
    ref = (recording_ref or "").strip()
    if not ref:
        return False
    try:
        with open(feature_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return False

    scenario_line = -1
    for i, line in enumerate(lines):
        m = re.match(r"^\s+Scenario(?:\s+Outline)?:\s*(.+)", line)
        if m and m.group(1).strip().lower() == scenario_name.strip().lower():
            scenario_line = i
            break
    if scenario_line < 0:
        return False

    marker = f"    # ELIA grabación vinculada: {ref}\n"
    if scenario_line + 1 < len(lines) and "ELIA grabación vinculada" in lines[scenario_line + 1]:
        lines[scenario_line + 1] = marker
    else:
        lines.insert(scenario_line + 1, marker)

    try:
        with open(feature_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except OSError:
        return False


def encode_recording_link(project: str, file_name: str) -> str:
    return f"{project}{REC_LINK_SEP}{file_name}"


def decode_recording_link(link: Optional[str]) -> Optional[Tuple[str, str]]:
    if not link or not str(link).strip():
        return None
    raw = str(link).strip()
    if REC_LINK_SEP in raw:
        proj, _, fname = raw.partition(REC_LINK_SEP)
        if proj and fname:
            return proj, fname
    return None, os.path.basename(raw)


def resolve_recording_basename_for_doc(
    doc_path: str,
    projects_dir: Optional[str] = None,
    explicit: Optional[str] = None,
) -> Optional[str]:
    """
    Resuelve referencia de grabación para un documento.

    - explicit: nombre de archivo o project\\x1efile.json desde UI
    - si no, busca {stem}.json en cualquier proyecto/scripts/
    """
    if explicit and str(explicit).strip():
        decoded = decode_recording_link(explicit)
        if decoded:
            _proj, fname = decoded
            if fname:
                return fname
        return os.path.basename(str(explicit).strip())

    stem = os.path.splitext(os.path.basename(doc_path))[0]
    if not stem:
        return None

    roots: list[str] = []
    if projects_dir and os.path.isdir(projects_dir):
        roots.append(projects_dir)
    try:
        from core.elia_paths import behave_project_search_roots

        for root in behave_project_search_roots():
            path = str(root)
            if path not in roots:
                roots.append(path)
    except Exception:
        pass

    for root in roots:
        try:
            entries = os.listdir(root)
        except OSError:
            continue
        for name in entries:
            scripts = os.path.join(root, name, "scripts")
            if not os.path.isdir(scripts):
                continue
            for ext in (".json", ".js"):
                candidate = os.path.join(scripts, stem + ext)
                if os.path.isfile(candidate):
                    return stem + ext
    return None


def link_map_for_doc_paths(
    link_by_doc: Optional[Dict[str, str]],
    source_file: str,
    fallback: Optional[str] = None,
) -> Optional[str]:
    """Busca enlace codificado por ruta completa o basename del documento."""
    if not link_by_doc:
        return fallback
    base = os.path.basename(source_file)
    return link_by_doc.get(source_file) or link_by_doc.get(base) or fallback
