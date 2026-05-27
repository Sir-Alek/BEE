"""Persistencia de capturas y escenarios API bajo behave/api/."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    from core.api_automation.project_scaffold import scaffold_api_project

    path = _project_root(project)
    if not path.is_dir():
        scaffold_api_project(path)
    return path


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
    """Ruta del JSON de tráfico bajo behave/api/{proyecto}/scripts/."""
    api_project = web_project_name_from_path(web_project_path)
    recording_base = os.path.splitext(os.path.basename(output_file))[0]
    return str(api_traffic_path_for_recording(api_project, recording_base))


def traffic_path_for_script(script_path: str) -> str:
    """Resuelve tráfico API asociado a un script web grabado."""
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


def import_traffic_to_scenarios(project: str, traffic_path: str) -> List[str]:
    """Importa cada petición de una captura como escenario en scenarios/."""
    capture = load_traffic_file(traffic_path)
    ids: List[str] = []
    for entry in capture.entries:
        ids.append(save_scenario(project, entry))
    return ids


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
    """Normaliza JSON emitido por web_capture_engine.js."""
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


def list_scenarios(project: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    sdir = scenarios_dir(project)
    for fname in sorted(os.listdir(sdir)):
        if not fname.lower().endswith(".json"):
            continue
        out.append({"id": fname, "path": str(sdir / fname), "name": os.path.splitext(fname)[0]})
    return out


def load_scenario(project: str, scenario_id: str) -> ApiRequest:
    sid = os.path.basename(scenario_id)
    path = scenarios_dir(project) / sid
    if not path.is_file():
        raise FileNotFoundError(scenario_id)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Escenario inválido")
    return ApiRequest.from_dict(data)


def save_scenario(project: str, request: ApiRequest, *, scenario_id: Optional[str] = None) -> str:
    ensure_api_project(project)
    sid = scenario_id or f"{request.id or uuid.uuid4().hex[:8]}.json"
    if not sid.endswith(".json"):
        sid += ".json"
    sid = os.path.basename(sid)
    path = scenarios_dir(project) / sid
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(request.to_dict(), f, ensure_ascii=False, indent=2)
    return sid
