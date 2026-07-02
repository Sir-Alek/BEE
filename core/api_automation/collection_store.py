"""Registro de colecciones API (agrupación de escenarios por importación o manual)."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.elia_paths import behave_projects_dir

DEFAULT_COLLECTION_ID = "_default"
DEFAULT_COLLECTION_NAME = "General"
_COLLECTION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _project_root(project: str) -> Path:
    name = (project or "").strip()
    if not name or ".." in name or "/" in name or "\\" in name:
        raise ValueError("Nombre de proyecto no válido")
    return behave_projects_dir("api") / name


def _registry_path(project: str) -> Path:
    root = _project_root(project)
    root.mkdir(parents=True, exist_ok=True)
    return root / "collections.json"


def _load_registry(project: str) -> Dict[str, Any]:
    path = _registry_path(project)
    if not path.is_file():
        return {"collections": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {"collections": []}
    if not isinstance(data, dict):
        return {"collections": []}
    items = data.get("collections")
    if not isinstance(items, list):
        items = []
    return {"collections": [c for c in items if isinstance(c, dict)]}


def _save_registry(project: str, registry: Dict[str, Any]) -> None:
    path = _registry_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_collection_id(raw: str) -> str:
    cid = (raw or "").strip()
    if not cid or not _COLLECTION_ID_RE.match(cid) or ".." in cid:
        raise ValueError("Identificador de colección no válido")
    return cid


def ensure_default_collection(project: str) -> str:
    path = _registry_path(project)
    if not path.is_file():
        registry: Dict[str, Any] = {"collections": []}
    else:
        registry = _load_registry(project)
        if registry["collections"]:
            for item in registry["collections"]:
                if str(item.get("id") or "") == DEFAULT_COLLECTION_ID:
                    collection_scenarios_dir(project, DEFAULT_COLLECTION_ID).mkdir(parents=True, exist_ok=True)
                    return DEFAULT_COLLECTION_ID
            # Registry exists with collections but no _default — append without wiping.
            now = datetime.now(timezone.utc).isoformat()
            registry["collections"].insert(
                0,
                {
                    "id": DEFAULT_COLLECTION_ID,
                    "name": DEFAULT_COLLECTION_NAME,
                    "created_at": now,
                    "source": "manual",
                },
            )
            _save_registry(project, registry)
            collection_scenarios_dir(project, DEFAULT_COLLECTION_ID).mkdir(parents=True, exist_ok=True)
            return DEFAULT_COLLECTION_ID
        # File exists but parsed empty — do not overwrite; ensure folder only.
        collection_scenarios_dir(project, DEFAULT_COLLECTION_ID).mkdir(parents=True, exist_ok=True)
        return DEFAULT_COLLECTION_ID

    now = datetime.now(timezone.utc).isoformat()
    registry["collections"].insert(
        0,
        {
            "id": DEFAULT_COLLECTION_ID,
            "name": DEFAULT_COLLECTION_NAME,
            "created_at": now,
            "source": "manual",
        },
    )
    _save_registry(project, registry)
    collection_scenarios_dir(project, DEFAULT_COLLECTION_ID).mkdir(parents=True, exist_ok=True)
    return DEFAULT_COLLECTION_ID


def collection_scenarios_dir(project: str, collection_id: str) -> Path:
    cid = _normalize_collection_id(collection_id)
    return _project_root(project) / "scenarios" / cid


def list_collections(project: str) -> List[Dict[str, Any]]:
    from core.api_automation.scenario_index import ensure_index, scenario_count_for_collection

    ensure_default_collection(project)
    registry = _load_registry(project)
    index = ensure_index(project)
    out: List[Dict[str, Any]] = []
    for item in registry["collections"]:
        cid = str(item.get("id") or "").strip()
        if not cid:
            continue
        sdir = collection_scenarios_dir(project, cid)
        count = scenario_count_for_collection(project, cid, index=index)
        if count == 0 and sdir.is_dir():
            count = len(list(sdir.glob("*.json")))
        out.append(
            {
                "id": cid,
                "name": str(item.get("name") or cid),
                "created_at": str(item.get("created_at") or ""),
                "source": str(item.get("source") or "manual"),
                "scenario_count": count,
            }
        )
    return out


def get_collection_name(project: str, collection_id: str) -> str:
    cid = _normalize_collection_id(collection_id)
    for item in list_collections(project):
        if item["id"] == cid:
            return str(item["name"])
    return cid


def create_collection(project: str, name: str, *, source: str = "manual") -> str:
    root = _project_root(project)
    root.mkdir(parents=True, exist_ok=True)
    (root / "scenarios").mkdir(parents=True, exist_ok=True)
    label = (name or "").strip() or "Colección"
    cid = uuid.uuid4().hex[:10]
    while (_project_root(project) / "scenarios" / cid).exists():
        cid = uuid.uuid4().hex[:10]
    now = datetime.now(timezone.utc).isoformat()
    registry = _load_registry(project)
    registry["collections"].append(
        {"id": cid, "name": label, "created_at": now, "source": source or "manual"}
    )
    _save_registry(project, registry)
    collection_scenarios_dir(project, cid).mkdir(parents=True, exist_ok=True)
    return cid


def delete_collection(project: str, collection_id: str) -> int:
    cid = _normalize_collection_id(collection_id)
    sdir = collection_scenarios_dir(project, cid)
    deleted = 0
    if sdir.is_dir():
        for path in sdir.glob("*.json"):
            try:
                path.unlink()
                deleted += 1
            except OSError:
                continue
        if cid != DEFAULT_COLLECTION_ID:
            try:
                sdir.rmdir()
            except OSError:
                pass
    if cid == DEFAULT_COLLECTION_ID:
        ensure_default_collection(project)
        try:
            from core.api_automation.scenario_index import remove_collection

            remove_collection(project, cid)
        except Exception:
            pass
        return deleted
    registry = _load_registry(project)
    registry["collections"] = [c for c in registry["collections"] if str(c.get("id") or "") != cid]
    _save_registry(project, registry)
    ensure_default_collection(project)
    try:
        from core.api_automation.scenario_index import remove_collection

        remove_collection(project, cid)
    except Exception:
        pass
    return deleted


def parse_scenario_ref(scenario_id: str) -> tuple[str, str]:
    """Devuelve (collection_id, filename.json)."""
    raw = str(scenario_id or "").strip().replace("\\", "/")
    if not raw:
        raise ValueError("Identificador de escenario no válido")
    if "/" in raw:
        collection_id, fname = raw.split("/", 1)
        collection_id = _normalize_collection_id(collection_id)
        fname = fname.strip()
    else:
        collection_id = DEFAULT_COLLECTION_ID
        fname = raw
    if not fname.lower().endswith(".json"):
        fname += ".json"
    fname = Path(fname).name
    if not fname or fname in (".json", "..json"):
        raise ValueError("Identificador de escenario no válido")
    return collection_id, fname


def scenario_ref(collection_id: str, filename: str) -> str:
    cid = _normalize_collection_id(collection_id)
    fname = Path(str(filename or "")).name
    if not fname.lower().endswith(".json"):
        fname += ".json"
    return f"{cid}/{fname}"
