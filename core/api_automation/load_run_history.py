"""Historial ligero de ejecuciones Locust para comparativa (outputs/reports/)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.api_automation.traffic_store import ensure_api_project

MAX_HISTORY = 30


def _history_path(project: str) -> Path:
    root = ensure_api_project(project)
    reports = root / "outputs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports / "load_history.json"


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


def append_load_run(project: str, entry: Dict[str, Any]) -> str:
    """Añade snapshot de métricas (sin PDF). Devuelve id del historial."""
    run_id = str(entry.get("id") or uuid.uuid4().hex[:12])
    payload = {
        "id": run_id,
        "saved_at": datetime.now().isoformat(),
        **entry,
    }
    history = _load_history(project)
    history.append(payload)
    _save_history(project, history)
    return run_id


def list_load_runs(project: str) -> List[Dict[str, Any]]:
    return list(reversed(_load_history(project)))


def get_load_run(project: str, run_id: str) -> Optional[Dict[str, Any]]:
    for item in _load_history(project):
        if str(item.get("id")) == run_id:
            return item
    return None


def _metric_value(entry: Dict[str, Any], key: str) -> float:
    metrics = entry.get("metrics") or {}
    live = metrics.get("live") or {}
    csv_summary = (metrics.get("csv") or {}).get("aggregated") or (metrics.get("csv") or {}).get("summary") or {}
    if key in live and live[key] is not None:
        return float(live[key])
    mapping = {
        "avg_ms": "avg_ms",
        "p50_ms": "p50_ms",
        "p95_ms": "p95_ms",
        "p99_ms": "p99_ms",
        "current_rps": "rps",
        "total_requests": "requests",
        "total_failures": "failures",
    }
    csv_key = mapping.get(key, key)
    val = csv_summary.get(csv_key)
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def compare_load_runs(project: str, run_id_a: str, run_id_b: str) -> Dict[str, Any]:
    a = get_load_run(project, run_id_a)
    b = get_load_run(project, run_id_b)
    if a is None or b is None:
        raise FileNotFoundError("Ejecución no encontrada en historial")
    keys = ("total_requests", "total_failures", "current_rps", "avg_ms", "p50_ms", "p95_ms", "p99_ms")
    delta: Dict[str, Dict[str, float]] = {}
    for key in keys:
        va = _metric_value(a, key)
        vb = _metric_value(b, key)
        delta[key] = {"a": va, "b": vb, "diff": round(vb - va, 3)}
    return {"run_a": a, "run_b": b, "delta": delta}
