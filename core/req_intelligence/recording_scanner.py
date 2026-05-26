"""
Escaneo de grabaciones (.json móvil/legacy, .js web) en proyectos Behave.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass
class RecordingRef:
    project: str
    file_name: str
    file_path: str
    platform: str  # web | mobile | legacy | unknown
    label: str = ""


def _detect_platform(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".js":
        return "web"
    if ext != ".json":
        return "unknown"
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, dict):
            p = str(data.get("platform") or "").lower()
            if p in ("mobile", "legacy"):
                return p
    except (OSError, json.JSONDecodeError):
        pass
    return "unknown"


def scan_project_recordings(project_dir: str, project_name: Optional[str] = None) -> List[RecordingRef]:
    """Lista grabaciones en {project}/scripts/."""
    refs: List[RecordingRef] = []
    if not os.path.isdir(project_dir):
        return refs

    proj = project_name or os.path.basename(project_dir.rstrip(os.sep))
    scripts_dir = os.path.join(project_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return refs

    for fname in sorted(os.listdir(scripts_dir)):
        lower = fname.lower()
        if not (lower.endswith(".json") or lower.endswith(".js")):
            continue
        full = os.path.join(scripts_dir, fname)
        if not os.path.isfile(full):
            continue
        platform = _detect_platform(full)
        refs.append(
            RecordingRef(
                project=proj,
                file_name=fname,
                file_path=full,
                platform=platform,
                label=f"{fname} ({platform})" if platform != "unknown" else fname,
            )
        )
    return refs


def scan_all_recordings(projects_root: str, project_filter: Optional[str] = None) -> List[RecordingRef]:
    out: List[RecordingRef] = []
    if not os.path.isdir(projects_root):
        return out

    try:
        entries = os.listdir(projects_root)
    except OSError:
        return out

    for entry in sorted(entries):
        if project_filter and entry != project_filter:
            continue
        full = os.path.join(projects_root, entry)
        if os.path.isdir(full):
            out.extend(scan_project_recordings(full, entry))
    return out


def scan_all_recordings_from_roots(
    projects_roots: Sequence[str],
    project_filter: Optional[str] = None,
) -> List[RecordingRef]:
    """Escanea varias raíces (p. ej. behave/web, behave/mobile, …)."""
    out: List[RecordingRef] = []
    seen: set[str] = set()
    for root in projects_roots:
        for ref in scan_all_recordings(root, project_filter):
            if ref.file_path in seen:
                continue
            seen.add(ref.file_path)
            out.append(ref)
    return out
