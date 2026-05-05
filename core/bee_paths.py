"""
Rutas de datos de usuario: proyectos fuera del directorio de instalación.

Por defecto: carpeta «Documents/BEE» (Windows) o ~/Documents/BEE (Linux/macOS).
Sobrescribible con BEE_USER_DATA (ruta absoluta a la raíz de datos).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _default_documents() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        return Path(base) / "Documents"
    return Path.home() / "Documents"


def user_data_root() -> Path:
    override = os.environ.get("BEE_USER_DATA", "").strip()
    if override:
        return Path(override)
    return _default_documents() / "BEE"


def ensure_user_data_root() -> Path:
    root = user_data_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def behave_projects_dir() -> Path:
    d = ensure_user_data_root() / "behave" / "proyectos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def step_by_step_dir() -> Path:
    d = ensure_user_data_root() / "step_by_step"
    d.mkdir(parents=True, exist_ok=True)
    return d


def bee_memory_path() -> Path:
    return ensure_user_data_root() / "bee_memory.json"


def elia_dir() -> Path:
    """Directorio de datos ELIA (config opcional, salidas) bajo la raíz de datos de usuario."""
    d = ensure_user_data_root() / "elia"
    d.mkdir(parents=True, exist_ok=True)
    return d


def elia_secrets_path() -> Path:
    """Ruta recomendada para secrets.ini de ELIA (Jira + Value Edge). No versionar."""
    return elia_dir() / "secrets.ini"
