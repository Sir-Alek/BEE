"""Progreso en vivo de ejecución de suite (polling desde UI)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from core.api_automation.traffic_store import ensure_api_project


def _progress_path(project: str) -> Path:
    root = ensure_api_project(project)
    reports = root / "outputs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports / "suite_progress.json"


def write_suite_progress(project: str, payload: Dict[str, Any]) -> None:
    path = _progress_path(project)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_suite_progress(project: str) -> Optional[Dict[str, Any]]:
    path = _progress_path(project)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def clear_suite_progress(project: str) -> None:
    path = _progress_path(project)
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
