"""
Rutas de datos de usuario: proyectos fuera del directorio de instalación.

Por defecto: carpeta «Documents/ELIA» (Windows) o ~/Documents/ELIA (Linux/macOS).
Sobrescribible con ELIA_USER_DATA (ruta absoluta a la raíz de datos).
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
    override = (os.environ.get("ELIA_USER_DATA") or "").strip()
    if override:
        return Path(override)
    return _default_documents() / "ELIA"


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


def elia_memory_path() -> Path:
    return ensure_user_data_root() / "elia_memory.json"


def external_connectors_dir() -> Path:
    """Jira / Value Edge: secrets.ini y almacenes locales bajo datos de usuario (sin carpeta «elia»)."""
    d = ensure_user_data_root() / "external_connectors"
    d.mkdir(parents=True, exist_ok=True)
    return d


def integrations_secrets_path() -> Path:
    """Ruta recomendada para secrets.ini (Jira + Value Edge). No versionar."""
    return external_connectors_dir() / "secrets.ini"


def uploads_tmp_dir() -> Path:
    """Directorio temporal para archivos subidos (Word/Excel) — se limpia entre sesiones."""
    d = ensure_user_data_root() / "uploads_tmp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def doc_features_dir() -> Path:
    """Directorio donde se guardan los .feature generados desde documentos."""
    d = ensure_user_data_root() / "doc_features"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ai_preferences_path() -> Path:
    """Preferencias de IA local (modo auto / on / off)."""
    return ensure_user_data_root() / "ai_preferences.json"
