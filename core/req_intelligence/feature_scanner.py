"""
Escáner de archivos .feature para el módulo de vinculación BDD ↔ Grabaciones.

Parsea archivos .feature con regex simples (sin depender de behave) para extraer
referencias a Feature: y Scenario: con sus números de línea.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Literal, Optional

MergeMode = Literal["append", "replace"]


@dataclass
class ScenarioRef:
    """Referencia a un escenario dentro de un archivo .feature."""
    feature_file: str
    scenario_name: str
    line_number: int
    feature_name: str = ""


_FEATURE_RE = re.compile(r"^Feature:\s*(.+)", re.MULTILINE)
_SCENARIO_RE = re.compile(r"^\s+Scenario(?:\s+Outline)?:\s*(.+)", re.MULTILINE)


def _parse_feature_file(file_path: str) -> List[ScenarioRef]:
    """Parsea un .feature y devuelve todos sus ScenarioRef."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return []

    refs: List[ScenarioRef] = []

    # Extraer nombre del Feature
    feature_match = _FEATURE_RE.search(content)
    feature_name = feature_match.group(1).strip() if feature_match else os.path.basename(file_path)

    # Encontrar todos los Scenario: con sus posiciones
    lines = content.splitlines()
    for line_num, line in enumerate(lines, start=1):
        m = re.match(r"^\s+Scenario(?:\s+Outline)?:\s*(.+)", line)
        if m:
            refs.append(ScenarioRef(
                feature_file=file_path,
                scenario_name=m.group(1).strip(),
                line_number=line_num,
                feature_name=feature_name,
            ))

    return refs


def scan_project_scenarios(project_dir: str) -> List[ScenarioRef]:
    """
    Escanea recursivamente un directorio en busca de .feature files.
    Devuelve todos los ScenarioRef encontrados.
    """
    refs: List[ScenarioRef] = []
    if not os.path.isdir(project_dir):
        return refs

    for root, _dirs, files in os.walk(project_dir):
        for fname in files:
            if fname.endswith(".feature"):
                full_path = os.path.join(root, fname)
                refs.extend(_parse_feature_file(full_path))

    return refs


def find_scenario_in_file(feature_file: str, scenario_name: str) -> int:
    """
    Devuelve el número de línea del Scenario: indicado en el archivo feature.
    Devuelve -1 si no se encuentra.
    """
    refs = _parse_feature_file(feature_file)
    for ref in refs:
        if ref.scenario_name.lower() == scenario_name.lower():
            return ref.line_number
    return -1


def _parse_step_line(line: str) -> Optional[str]:
    sm = re.match(r"^\s+(Given|When|Then|And|But)\s+(.+)", line, re.I)
    if sm:
        return f"{sm.group(1).capitalize()} {sm.group(2).strip()}"
    return None


def merge_steps_into_scenario(
    feature_file: str,
    scenario_name: str,
    new_steps: List[str],
    *,
    mode: MergeMode = "append",
) -> bool:
    """
    Fusiona pasos en un Scenario: existente.

    mode:
      - append: añade new_steps tras los pasos actuales (sin duplicar líneas idénticas seguidas)
      - replace: sustituye el bloque de pasos por new_steps

    new_steps: lista como ["Given el usuario está en...", "When hace clic en..."]

    Devuelve True si el merge fue exitoso.
    """
    try:
        with open(feature_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return False

    # Encontrar la línea del scenario
    scenario_line = -1
    for i, line in enumerate(lines):
        m = re.match(r"^\s+Scenario(?:\s+Outline)?:\s*(.+)", line)
        if m and m.group(1).strip().lower() == scenario_name.strip().lower():
            scenario_line = i
            break

    if scenario_line == -1:
        return False

    # Encontrar el rango de pasos: desde scenario_line+1 hasta el siguiente Scenario: o EOF
    step_start = scenario_line + 1
    step_end = len(lines)
    for i in range(step_start, len(lines)):
        line = lines[i]
        # Fin del bloque: nueva sección, Feature:, o Scenario:
        if re.match(r"^(?:Feature:|Background:|\s+Scenario(?:\s+Outline)?:)", line):
            step_end = i
            break
        # Saltar líneas vacías al inicio del bloque de pasos
        if i == step_start and not line.strip():
            step_start = i + 1

    existing_steps: List[str] = []
    for i in range(step_start, step_end):
        parsed = _parse_step_line(lines[i])
        if parsed:
            existing_steps.append(parsed)

    if mode == "append":
        combined: List[str] = list(existing_steps)
        for step in new_steps:
            s = step.strip()
            if not s:
                continue
            if not re.match(r"^(Given|When|Then|And|But)\s", s, re.I):
                s = f"And {s}"
            norm = s[0].upper() + s[1:] if s else s
            if not combined or combined[-1] != norm:
                combined.append(norm)
    else:
        combined = []
        for step in new_steps:
            s = step.strip()
            if s:
                combined.append(s)

    # Construir los nuevos pasos con indentación correcta (4 espacios)
    formatted_steps = []
    for step in combined:
        step = step.strip()
        if step:
            # Asegurar que empiece con una keyword BDD
            if not re.match(r"^(Given|When|Then|And|But)\s", step):
                step = f"And {step}"
            formatted_steps.append(f"    {step}\n")

    # Reensamblar el archivo
    new_lines = (
        lines[:step_start]
        + formatted_steps
        + ([""] if formatted_steps else [])
        + lines[step_end:]
    )

    try:
        with open(feature_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except OSError:
        return False
