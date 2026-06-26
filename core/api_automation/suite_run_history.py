"""Historial de ejecuciones de suites funcionales API."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.api_automation.traffic_store import ensure_api_project

MAX_HISTORY = 50


def _history_path(project: str) -> Path:
    root = ensure_api_project(project)
    reports = root / "outputs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports / "suite_history.json"


def _load_history(project: str) -> List[Dict[str, Any]]:
    path = _history_path(project)
    if not path.is_file():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _save_history(project: str, entries: List[Dict[str, Any]]) -> None:
    path = _history_path(project)
    trimmed = entries[-MAX_HISTORY:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)


def append_suite_run(project: str, entry: Dict[str, Any]) -> str:
    run_id = str(entry.get("id") or uuid.uuid4().hex[:12])
    payload = {"id": run_id, "saved_at": datetime.now().isoformat(), **entry}
    history = _load_history(project)
    history.append(payload)
    _save_history(project, history)
    return run_id


def list_suite_runs(project: str) -> List[Dict[str, Any]]:
    return list(reversed(_load_history(project)))


def get_suite_run(project: str, run_id: str) -> Optional[Dict[str, Any]]:
    for item in _load_history(project):
        if str(item.get("id")) == run_id:
            return item
    return None
