"""Índice ligero de escenarios API (nombre visible sin leer cada JSON en listados)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.api_automation.collection_store import (
    collection_scenarios_dir,
    parse_scenario_ref,
    scenario_ref,
)

_INDEX_VERSION = 1


def _project_root(project: str) -> Path:
    from core.api_automation.collection_store import _project_root as root

    return root(project)


def _index_path(project: str) -> Path:
    return _project_root(project) / "scenarios_index.json"


def _empty_index() -> Dict[str, Any]:
    return {"version": _INDEX_VERSION, "updated_at": "", "entries": {}}


def _load_index_raw(project: str) -> Dict[str, Any]:
    path = _index_path(project)
    if not path.is_file():
        return _empty_index()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return _empty_index()
    if not isinstance(data, dict):
        return _empty_index()
    entries = data.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    return {
        "version": int(data.get("version") or _INDEX_VERSION),
        "updated_at": str(data.get("updated_at") or ""),
        "entries": dict(entries),
    }


def _save_index(project: str, index: Dict[str, Any]) -> None:
    path = _index_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    index = {
        "version": _INDEX_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entries": dict(index.get("entries") or {}),
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def rebuild_index(project: str) -> Dict[str, Any]:
    """Reconstruye el índice leyendo el campo name de cada escenario JSON."""
    from core.api_automation.collection_store import (
        _load_registry,
        collection_scenarios_dir,
        ensure_default_collection,
    )

    ensure_default_collection(project)
    registry = _load_registry(project)
    entries: Dict[str, Dict[str, str]] = {}
    for item in registry.get("collections") or []:
        cid = str(item.get("id") or "").strip()
        if not cid:
            continue
        sdir = collection_scenarios_dir(project, cid)
        if not sdir.is_dir():
            continue
        for path in sorted(sdir.glob("*.json")):
            sid = scenario_ref(cid, path.name)
            display_name = path.stem
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    raw_name = str(data.get("name") or "").strip()
                    if raw_name:
                        display_name = raw_name
            except (OSError, json.JSONDecodeError, TypeError):
                pass
            entries[sid] = {"name": display_name, "collection_id": cid}
    index = {"version": _INDEX_VERSION, "updated_at": "", "entries": entries}
    _save_index(project, index)
    return _load_index_raw(project)


def ensure_index(project: str) -> Dict[str, Any]:
    index = _load_index_raw(project)
    if index.get("entries"):
        return index
    return rebuild_index(project)


def upsert_scenario(project: str, scenario_id: str, *, name: str) -> None:
    sid = str(scenario_id or "").strip().replace("\\", "/")
    if not sid:
        return
    try:
        cid, _ = parse_scenario_ref(sid)
    except ValueError:
        return
    label = (name or "").strip()
    if not label:
        label = Path(sid.split("/", 1)[-1]).stem
    index = ensure_index(project)
    entries: Dict[str, Any] = dict(index.get("entries") or {})
    entries[sid] = {"name": label, "collection_id": cid}
    _save_index(project, {**index, "entries": entries})


def remove_scenario(project: str, scenario_id: str) -> None:
    sid = str(scenario_id or "").strip().replace("\\", "/")
    if not sid:
        return
    index = _load_index_raw(project)
    entries: Dict[str, Any] = dict(index.get("entries") or {})
    if sid not in entries:
        return
    entries.pop(sid, None)
    _save_index(project, {**index, "entries": entries})


def remove_collection(project: str, collection_id: str) -> None:
    cid = str(collection_id or "").strip()
    if not cid:
        return
    index = _load_index_raw(project)
    entries: Dict[str, Any] = dict(index.get("entries") or {})
    prefix = f"{cid}/"
    filtered = {k: v for k, v in entries.items() if not k.startswith(prefix)}
    if len(filtered) == len(entries):
        return
    _save_index(project, {**index, "entries": filtered})


def scenario_count_for_collection(project: str, collection_id: str, *, index: Optional[Dict[str, Any]] = None) -> int:
    idx = index if index is not None else ensure_index(project)
    entries: Dict[str, Any] = dict(idx.get("entries") or {})
    prefix = f"{collection_id}/"
    return sum(1 for key in entries if key.startswith(prefix))


def display_name_for_scenario(
    project: str,
    scenario_id: str,
    *,
    path_stem: str,
    index: Optional[Dict[str, Any]] = None,
) -> str:
    idx = index if index is not None else ensure_index(project)
    meta = (idx.get("entries") or {}).get(scenario_id)
    if isinstance(meta, dict):
        name = str(meta.get("name") or "").strip()
        if name:
            return name
    return path_stem
