"""Persistencia de capturas y escenarios API bajo behave/api/."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.api_automation.collection_store import (
    DEFAULT_COLLECTION_ID,
    collection_scenarios_dir,
    create_collection,
    delete_collection,
    ensure_default_collection,
    get_collection_name,
    list_collections,
    parse_scenario_ref,
    scenario_ref,
)
from core.api_automation.models import ApiRequest, ApiTrafficCapture
from core.api_automation.sanitize import is_noise_url, sanitize_body, sanitize_headers
from core.elia_paths import behave_projects_dir


def _project_root(project: str) -> Path:
    name = (project or "").strip()
    if not name or ".." in name or "/" in name or "\\" in name:
        raise ValueError("Nombre de proyecto no válido")
    return behave_projects_dir("api") / name


def list_api_projects() -> List[str]:
    root = behave_projects_dir("api")
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def ensure_api_project(project: str) -> Path:
    from core.api_automation.project_config import ensure_project_defaults
    from core.api_automation.project_scaffold import scaffold_api_project

    path = _project_root(project)
    if not path.is_dir():
        scaffold_api_project(path)
    ensure_project_defaults(project)
    ensure_default_collection(project)
    from core.api_automation.scripts_guide import ensure_api_scripts_guide

    ensure_api_scripts_guide(path)
    _migrate_legacy_flat_scenarios(project)
    return path


def _migrate_legacy_flat_scenarios(project: str) -> None:
    """Mueve escenarios sueltos en scenarios/*.json a scenarios/_default/."""
    root = _project_root(project) / "scenarios"
    if not root.is_dir():
        return
    target = collection_scenarios_dir(project, DEFAULT_COLLECTION_ID)
    target.mkdir(parents=True, exist_ok=True)
    for path in root.glob("*.json"):
        dest = target / path.name
        if dest.exists():
            continue
        try:
            path.replace(dest)
        except OSError:
            continue


def web_project_name_from_path(project_path: str) -> str:
    return os.path.basename(os.path.normpath(project_path))


def api_scripts_dir(project: str) -> Path:
    d = ensure_api_project(project) / "scripts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def api_traffic_path_for_recording(api_project: str, recording_basename: str) -> Path:
    base = os.path.basename(recording_basename)
    if base.lower().endswith(".js"):
        base = base[:-3]
    return api_scripts_dir(api_project) / f"{base}_api_traffic.json"


def traffic_path_for_web_recording(web_project_path: str, output_file: str) -> str:
    api_project = web_project_name_from_path(web_project_path)
    recording_base = os.path.splitext(os.path.basename(output_file))[0]
    return str(api_traffic_path_for_recording(api_project, recording_base))


def traffic_path_for_script(script_path: str) -> str:
    recording_base = os.path.splitext(os.path.basename(script_path))[0]
    norm = os.path.normpath(script_path)
    parts = norm.split(os.sep)
    try:
        idx = parts.index("web")
        if idx + 1 < len(parts):
            return str(api_traffic_path_for_recording(parts[idx + 1], recording_base))
    except ValueError:
        pass
    base, _ = os.path.splitext(script_path)
    return base + "_api_traffic.json"


def list_traffic_captures(project: str) -> List[Dict[str, str]]:
    sdir = api_scripts_dir(project)
    if not sdir.is_dir():
        return []
    out: List[Dict[str, str]] = []
    for path in sorted(sdir.glob("*_api_traffic.json")):
        out.append(
            {
                "id": path.name,
                "path": str(path),
                "name": path.stem.replace("_api_traffic", ""),
            }
        )
    return out


def resolve_traffic_capture_path(project: str, capture_id: str) -> Path:
    cid = os.path.basename(capture_id)
    if not cid.lower().endswith(".json"):
        raise ValueError("Identificador de captura no válido")
    path = api_scripts_dir(project) / cid
    if not path.is_file():
        raise FileNotFoundError(capture_id)
    return path


def request_fingerprint(request: ApiRequest) -> str:
    url = (request.url or "").split("?")[0].strip().lower()
    return f"{(request.method or 'GET').upper()}:{url}"


def _existing_fingerprints(project: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in list_scenarios(project):
        try:
            req = load_scenario(project, item["id"])
        except (FileNotFoundError, ValueError):
            continue
        out[request_fingerprint(req)] = item["id"]
    return out


def import_traffic_to_scenarios(
    project: str,
    traffic_path: str,
    *,
    dedupe: bool = True,
    collection_name: Optional[str] = None,
) -> Dict[str, Any]:
    capture = load_traffic_file(traffic_path)
    label = (collection_name or "").strip() or Path(traffic_path).stem.replace("_api_traffic", "") or "Captura web"
    collection_id = create_collection(project, label, source="capture")
    ids: List[str] = []
    skipped = 0
    known = _existing_fingerprints(project) if dedupe else {}
    for entry in capture.entries:
        fp = request_fingerprint(entry)
        if dedupe and fp in known:
            skipped += 1
            ids.append(known[fp])
            continue
        sid = save_scenario(project, entry, collection_id=collection_id)
        ids.append(sid)
        if dedupe:
            known[fp] = sid
    return {
        "scenario_ids": ids,
        "imported": len(ids) - skipped,
        "skipped": skipped,
        "total": len(capture.entries),
        "collection_id": collection_id,
        "collection_name": get_collection_name(project, collection_id),
    }


def scenarios_dir(project: str) -> Path:
    return ensure_api_project(project) / "scenarios"


def load_traffic_file(path: str) -> ApiTrafficCapture:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Archivo de tráfico inválido")
    return ApiTrafficCapture.from_dict(data)


def save_traffic_file(path: str, capture: ApiTrafficCapture) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(capture.to_dict(), f, ensure_ascii=False, indent=2)


def ingest_capture_dict(data: Dict[str, Any], *, source_url: str = "") -> ApiTrafficCapture:
    entries: List[ApiRequest] = []
    raw_entries = data.get("entries") if isinstance(data, dict) else []
    if not isinstance(raw_entries, list):
        raw_entries = []
    for idx, item in enumerate(raw_entries):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not url or is_noise_url(url):
            continue
        method = str(item.get("method") or "GET").upper()
        req_id = str(item.get("id") or f"req-{idx + 1}")
        headers = sanitize_headers(
            {str(k): str(v) for k, v in (item.get("request_headers") or {}).items()}
        )
        resp_headers = sanitize_headers(
            {str(k): str(v) for k, v in (item.get("response_headers") or {}).items()}
        )
        status = item.get("response_status")
        expected = int(status) if status is not None else 200
        entries.append(
            ApiRequest(
                id=req_id,
                name=f"{method} {url.split('?')[0][-60:]}",
                method=method,
                url=url,
                headers=headers,
                body=sanitize_body(item.get("request_body")),
                expected_status=expected,
                response_status=int(status) if status is not None else None,
                response_headers=resp_headers,
                response_body=sanitize_body(item.get("response_body")),
                source="capture",
            )
        )
    captured_at = str(data.get("captured_at") or datetime.now(timezone.utc).isoformat())
    return ApiTrafficCapture(
        version=int(data.get("version") or 1),
        captured_at=captured_at,
        source_url=source_url or str(data.get("source_url") or ""),
        entries=entries,
    )


def list_scenarios(
    project: str,
    *,
    collection_id: Optional[str] = None,
    collections: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    from core.api_automation.scenario_index import display_name_for_scenario, ensure_index

    ensure_api_project(project)
    out: List[Dict[str, str]] = []
    if collections is None:
        collections = list_collections(project)
    name_by_id = {str(c["id"]): str(c.get("name") or c["id"]) for c in collections}
    allowed = set(name_by_id)
    targets = [collection_id] if collection_id else sorted(allowed)
    index = ensure_index(project)
    for cid in targets:
        if cid not in allowed:
            continue
        sdir = collection_scenarios_dir(project, cid)
        if not sdir.is_dir():
            continue
        cname = name_by_id.get(cid, cid)
        for path in sorted(sdir.glob("*.json")):
            sid = scenario_ref(cid, path.name)
            display_name = display_name_for_scenario(
                project, sid, path_stem=path.stem, index=index
            )
            out.append(
                {
                    "id": sid,
                    "path": str(path),
                    "name": display_name,
                    "collection_id": cid,
                    "collection_name": cname,
                }
            )
    return out


def load_scenario(project: str, scenario_id: str) -> ApiRequest:
    collection_id, fname = parse_scenario_ref(scenario_id)
    path = collection_scenarios_dir(project, collection_id) / fname
    if not path.is_file():
        raise FileNotFoundError(scenario_id)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Escenario inválido")
    return ApiRequest.from_dict(data)


def save_scenario(
    project: str,
    request: ApiRequest,
    *,
    scenario_id: Optional[str] = None,
    collection_id: Optional[str] = None,
) -> str:
    ensure_api_project(project)
    if scenario_id:
        cid, fname = parse_scenario_ref(scenario_id)
    else:
        cid = collection_id or DEFAULT_COLLECTION_ID
        if cid == DEFAULT_COLLECTION_ID:
            ensure_default_collection(project)
        fname = os.path.basename(request.id or uuid.uuid4().hex[:8])
        if not fname.lower().endswith(".json"):
            fname += ".json"
    target = collection_scenarios_dir(project, cid)
    target.mkdir(parents=True, exist_ok=True)
    path = target / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(request.to_dict(), f, ensure_ascii=False, indent=2)
    sid = scenario_ref(cid, fname)
    try:
        from core.api_automation.scenario_index import upsert_scenario

        upsert_scenario(project, sid, name=str(request.name or path.stem))
    except Exception:
        pass
    return sid


def delete_scenario(project: str, scenario_id: str) -> None:
    collection_id, fname = parse_scenario_ref(scenario_id)
    path = collection_scenarios_dir(project, collection_id) / fname
    if not path.is_file():
        raise FileNotFoundError(scenario_id)
    path.unlink()
    try:
        from core.api_automation.scenario_index import remove_scenario

        remove_scenario(project, scenario_id)
    except Exception:
        pass


def clone_scenario(project: str, scenario_id: str, *, new_name: Optional[str] = None) -> str:
    req = load_scenario(project, scenario_id)
    collection_id, _ = parse_scenario_ref(scenario_id)
    label = (new_name or "").strip() or f"{req.name} (copia)"
    req.name = label
    req.id = f"clone-{uuid.uuid4().hex[:8]}"
    return save_scenario(project, req, collection_id=collection_id)


def delete_scenarios(project: str, scenario_ids: List[str]) -> int:
    deleted = 0
    for sid in scenario_ids:
        try:
            delete_scenario(project, sid)
            deleted += 1
        except FileNotFoundError:
            continue
    return deleted


def import_requests_as_collection(
    project: str,
    requests: List[ApiRequest],
    *,
    collection_name: str,
    source: str,
) -> Dict[str, Any]:
    if not requests:
        raise ValueError("Sin peticiones para importar")
    cid = create_collection(project, collection_name, source=source)
    ids = [save_scenario(project, req, collection_id=cid) for req in requests]
    return {
        "collection_id": cid,
        "collection_name": get_collection_name(project, cid),
        "scenario_ids": ids,
        "count": len(ids),
    }
