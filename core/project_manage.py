"""Gestión de proyectos Behave locales: info, renombrar y eliminar."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from core.elia_paths import BEHAVE_PLATFORMS, behave_projects_dir
from core.project_templates import normalize_project_name, validate_project_name


def _project_root(platform: str, project: str) -> Path:
    plat = (platform or "").strip().lower()
    if plat not in BEHAVE_PLATFORMS:
        raise ValueError(f"Plataforma no soportada: {platform}")
    name = normalize_project_name(project)
    if not name:
        raise ValueError("Nombre de proyecto no válido")
    return behave_projects_dir(plat) / name


def _metadata_path(root: Path) -> Path:
    return root / ".elia" / "project.json"


def read_project_metadata(platform: str, project: str) -> Optional[Dict[str, Any]]:
    root = _project_root(platform, project)
    if not root.is_dir():
        raise FileNotFoundError(f"Proyecto no encontrado: {platform}/{project}")
    meta_path = _metadata_path(root)
    if not meta_path.is_file():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def get_project_info(platform: str, project: str) -> Dict[str, Any]:
    root = _project_root(platform, project)
    if not root.is_dir():
        raise FileNotFoundError(f"Proyecto no encontrado: {platform}/{project}")
    meta = read_project_metadata(platform, project)
    template_id = str((meta or {}).get("template_id") or "").strip()
    return {
        "platform": platform.strip().lower(),
        "project": root.name,
        "path": str(root.resolve()),
        "from_template": bool(template_id),
        "template_id": template_id or None,
        "template_version": (meta or {}).get("template_version"),
        "created_at": (meta or {}).get("created_at"),
        "elia_version": (meta or {}).get("elia_version"),
    }


def _ensure_not_busy(platform: str, project: str) -> None:
    from core.test_runner.runner_service import test_runner_service

    if test_runner_service.project_has_running_job(platform, project):
        raise RuntimeError("Hay una ejecución en curso para este proyecto. Espera a que termine.")


def rename_project(platform: str, project: str, new_name: str) -> str:
    _ensure_not_busy(platform, project)
    src = _project_root(platform, project)
    if not src.is_dir():
        raise FileNotFoundError(f"Proyecto no encontrado: {platform}/{project}")
    target_name = normalize_project_name(new_name)
    validate_project_name(target_name)
    if target_name == src.name:
        return target_name
    dest = src.parent / target_name
    if dest.exists():
        raise FileExistsError(f"Ya existe un proyecto «{target_name}» en behave/{platform}/")
    src.rename(dest)
    return target_name


def delete_project(platform: str, project: str) -> None:
    _ensure_not_busy(platform, project)
    root = _project_root(platform, project)
    if not root.is_dir():
        raise FileNotFoundError(f"Proyecto no encontrado: {platform}/{project}")
    shutil.rmtree(root)
