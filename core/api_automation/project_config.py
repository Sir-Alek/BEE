"""Configuración de proyecto API: project.json y entornos."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.api_automation.traffic_store import _project_root

DEFAULT_PROJECT_CONFIG: Dict[str, Any] = {
    "default_environment": "dev",
    "global_headers": {},
}

DEFAULT_ENVIRONMENT: Dict[str, Any] = {
    "name": "dev",
    "variables": {
        "base_url": "https://api.ejemplo.com",
    },
}


def project_config_path(project: str) -> Path:
    return _project_root(project) / "project.json"


def environments_dir(project: str) -> Path:
    path = _project_root(project)
    env_dir = path / "environments"
    env_dir.mkdir(parents=True, exist_ok=True)
    return env_dir


def environment_path(project: str, env_name: str) -> Path:
    name = _safe_env_name(env_name)
    return environments_dir(project) / f"{name}.json"


def _safe_env_name(name: str) -> str:
    env = (name or "").strip()
    if not env or ".." in env or "/" in env or "\\" in env:
        raise ValueError("Nombre de entorno no válido")
    return env


def ensure_project_defaults(project: str) -> None:
    from core.api_automation.project_scaffold import scaffold_api_project

    path = _project_root(project)
    if not path.is_dir():
        scaffold_api_project(path)
    cfg_path = project_config_path(project)
    if not cfg_path.is_file():
        save_project_config(project, dict(DEFAULT_PROJECT_CONFIG))
    dev_path = path / "environments" / "dev.json"
    dev_path.parent.mkdir(parents=True, exist_ok=True)
    if not dev_path.is_file():
        save_environment(project, "dev", dict(DEFAULT_ENVIRONMENT))


def load_project_config(project: str) -> Dict[str, Any]:
    ensure_project_defaults(project)
    path = project_config_path(project)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("project.json inválido")
    return {
        "default_environment": str(data.get("default_environment") or "dev"),
        "global_headers": {
            str(k): str(v) for k, v in (data.get("global_headers") or {}).items()
        },
    }


def save_project_config(project: str, config: Dict[str, Any]) -> None:
    root = _project_root(project)
    root.mkdir(parents=True, exist_ok=True)
    cfg_path = project_config_path(project)
    payload = {
        "default_environment": str(config.get("default_environment") or "dev"),
        "global_headers": {
            str(k): str(v) for k, v in (config.get("global_headers") or {}).items()
        },
    }
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def list_environments(project: str) -> List[str]:
    ensure_project_defaults(project)
    env_dir = environments_dir(project)
    names: List[str] = []
    for path in sorted(env_dir.glob("*.json")):
        names.append(path.stem)
    return names


def load_environment(project: str, env_name: Optional[str] = None) -> Dict[str, Any]:
    ensure_project_defaults(project)
    cfg = load_project_config(project)
    name = _safe_env_name(env_name or cfg["default_environment"])
    path = environment_path(project, name)
    if not path.is_file():
        raise FileNotFoundError(name)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Entorno inválido")
    return {
        "name": str(data.get("name") or name),
        "variables": {str(k): str(v) for k, v in (data.get("variables") or {}).items()},
    }


def save_environment(project: str, env_name: str, env_data: Dict[str, Any]) -> None:
    name = _safe_env_name(env_name)
    path = environment_path(project, name)
    payload = {
        "name": str(env_data.get("name") or name),
        "variables": {str(k): str(v) for k, v in (env_data.get("variables") or {}).items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def resolve_runtime_context(project: str, environment: Optional[str] = None) -> Dict[str, Any]:
    cfg = load_project_config(project)
    env = load_environment(project, environment or cfg["default_environment"])
    return {
        "environment": env["name"],
        "global_headers": cfg["global_headers"],
        "variables": env["variables"],
    }
