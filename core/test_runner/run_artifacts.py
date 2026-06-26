"""Detección de PDFs y artefactos tras una ejecución Behave."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

_PDF_MARKER_RE = re.compile(r"ELIA_PDF_REPORT:(.+)")


def parse_pdf_markers_from_lines(lines: List[str]) -> List[str]:
    found: List[str] = []
    for line in lines:
        match = _PDF_MARKER_RE.search(line)
        if match:
            path = match.group(1).strip()
            if path and os.path.isfile(path):
                found.append(path)
    return found


def list_pdfs_in_project(project_path: str | Path, *, since_ts: float) -> List[Dict[str, Any]]:
    root = Path(project_path)
    pdf_dir = root / "outputs" / "pdfReports"
    if not pdf_dir.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for pdf in pdf_dir.glob("*.pdf"):
        try:
            mtime = pdf.stat().st_mtime
        except OSError:
            continue
        if mtime >= since_ts - 1.0:
            rel = pdf.relative_to(root).as_posix()
            out.append(
                {
                    "name": pdf.name,
                    "path": rel,
                    "absolute_path": str(pdf.resolve()),
                    "size": pdf.stat().st_size,
                    "modified_at": mtime,
                }
            )
    out.sort(key=lambda x: x["modified_at"], reverse=True)
    return out


def collect_run_artifacts(
    *,
    project_path: str,
    lines: List[str],
    since_ts: float,
    generate_evidence: bool,
) -> List[Dict[str, Any]]:
    if not generate_evidence or not project_path:
        return []
    seen: set[str] = set()
    artifacts: List[Dict[str, Any]] = []

    for abs_path in parse_pdf_markers_from_lines(lines):
        if abs_path in seen:
            continue
        seen.add(abs_path)
        p = Path(abs_path)
        try:
            root = Path(project_path).resolve()
            rel = p.resolve().relative_to(root).as_posix()
        except ValueError:
            rel = p.name
        artifacts.append(
            {
                "kind": "pdf",
                "name": p.name,
                "path": rel,
                "absolute_path": str(p.resolve()),
                "size": p.stat().st_size if p.is_file() else 0,
            }
        )

    for item in list_pdfs_in_project(project_path, since_ts=since_ts):
        key = item["path"]
        if key in seen:
            continue
        seen.add(key)
        artifacts.append({"kind": "pdf", **item})

    return artifacts


def resolve_project_pdf(project_root: str | Path, filename: str) -> Path:
    name = os.path.basename(str(filename or "").replace("\\", "/"))
    if not name.lower().endswith(".pdf"):
        raise ValueError("Solo archivos PDF")
    root = Path(project_root).resolve()
    target = (root / "outputs" / "pdfReports" / name).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("Ruta fuera del proyecto")
    if not target.is_file():
        raise FileNotFoundError(name)
    return target


def resolve_project_evidence(project_root: str | Path, filename: str) -> Path:
    name = os.path.basename(str(filename or "").replace("\\", "/"))
    if not name.lower().endswith(".json"):
        raise ValueError("Solo archivos JSON de evidencia")
    root = Path(project_root).resolve()
    target = (root / "outputs" / "evidences" / name).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("Ruta fuera del proyecto")
    if not target.is_file():
        raise FileNotFoundError(name)
    return target
