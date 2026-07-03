"""Persistencia de flujos API (suites encadenadas)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.api_automation.models import ApiFlow
from core.api_automation.traffic_store import ensure_api_project


def flows_dir(project: str) -> Path:
    d = ensure_api_project(project) / "flows"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_flows(project: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for path in sorted(flows_dir(project).glob("*.json")):
        out.append({"id": path.name, "name": path.stem, "path": str(path)})
    return out


def load_flow(project: str, flow_id: str) -> ApiFlow:
    fid = os.path.basename(flow_id)
    if not fid.lower().endswith(".json"):
        fid += ".json"
    path = flows_dir(project) / fid
    if not path.is_file():
        raise FileNotFoundError(flow_id)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Flujo inválido")
    return ApiFlow.from_dict(data)


def save_flow(project: str, flow: ApiFlow, *, flow_id: Optional[str] = None) -> str:
    ensure_api_project(project)
    fid = flow_id or f"{flow.name}.json"
    fid = os.path.basename(fid)
    if not fid.lower().endswith(".json"):
        fid += ".json"
    path = flows_dir(project) / fid
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flow.to_dict(), f, ensure_ascii=False, indent=2)
    return fid


def delete_flow(project: str, flow_id: str) -> bool:
    fid = os.path.basename(flow_id)
    if not fid.lower().endswith(".json"):
        fid += ".json"
    path = flows_dir(project) / fid
    if not path.is_file():
        return False
    path.unlink()
    return True


def flow_exists(project: str, flow_id: str) -> bool:
    fid = os.path.basename(flow_id)
    if not fid.lower().endswith(".json"):
        fid += ".json"
    return (flows_dir(project) / fid).is_file()
