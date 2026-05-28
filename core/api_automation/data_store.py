"""CSV data-driven bajo behave/api/{proyecto}/resources/data/."""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any, Dict, List

from core.api_automation.traffic_store import _project_root, ensure_api_project


def data_dir(project: str) -> Path:
    root = ensure_api_project(project)
    d = root / "resources" / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_data_files(project: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for path in sorted(data_dir(project).glob("*.csv")):
        out.append({"name": path.name, "path": str(path)})
    return out


def _safe_csv_name(name: str) -> str:
    base = os.path.basename(name)
    if not base.lower().endswith(".csv"):
        base += ".csv"
    if ".." in base or "/" in base or "\\" in base:
        raise ValueError("Nombre CSV no válido")
    return base


def read_csv_rows(project: str, filename: str) -> List[Dict[str, str]]:
    path = data_dir(project) / _safe_csv_name(filename)
    if not path.is_file():
        raise FileNotFoundError(filename)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = []
        for row in reader:
            rows.append({str(k): str(v or "") for k, v in row.items() if k})
        return rows


def preview_csv(project: str, filename: str, *, limit: int = 5) -> Dict[str, Any]:
    rows = read_csv_rows(project, filename)
    columns = list(rows[0].keys()) if rows else []
    return {"name": _safe_csv_name(filename), "columns": columns, "rows": rows[:limit], "total": len(rows)}


def save_csv_content(project: str, filename: str, content: str) -> str:
    path = data_dir(project) / _safe_csv_name(filename)
    path.write_text(content, encoding="utf-8")
    return str(path)
