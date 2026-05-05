"""
Carga de configuración ELIA (Jira + Value Edge) desde datos de usuario o variables de entorno.

Prioridad:
1. Archivo en core.bee_paths.elia_secrets_path() si existe
2. ELIA_SECRETS_INI (ruta absoluta a un secrets.ini)
3. Env individuales (prefijo ELIA_ / BEE_ELIA_) para sustituir claves del ini cuando existan
"""
from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Optional

from core import bee_paths


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(key, "").strip()
    if v:
        return v
    alt = os.environ.get(f"BEE_{key}", "").strip()
    if alt:
        return alt
    return default


def secrets_ini_path() -> Path:
    override = _env("ELIA_SECRETS_INI")
    if override:
        return Path(override)
    return bee_paths.elia_secrets_path()


def load_config_parser() -> tuple[configparser.ConfigParser, Path]:
    """
    Lee secrets.ini si existe. Si no hay archivo, devuelve parser vacío y la ruta canónica
    (el llamador puede validar y pedir credenciales por otro canal).
    """
    path = secrets_ini_path()
    cfg = configparser.ConfigParser(interpolation=None)
    if path.is_file():
        cfg.read(path, encoding="utf-8")
    return cfg, path


def jira_settings(cfg: configparser.ConfigParser) -> dict[str, str]:
    url = _env("ELIA_JIRA_URL") or (cfg.get("JIRA", "URL", fallback="").strip() if cfg.has_section("JIRA") else "")
    email = _env("ELIA_JIRA_EMAIL") or (cfg.get("JIRA", "EMAIL", fallback="").strip() if cfg.has_section("JIRA") else "")
    token = _env("ELIA_JIRA_API_TOKEN") or (
        cfg.get("JIRA", "API_TOKEN", fallback="").strip() if cfg.has_section("JIRA") else ""
    )
    return {"url": url, "email": email, "api_token": token}


def value_edge_settings(cfg: configparser.ConfigParser) -> dict[str, str]:
    def g(section: str, opt: str, **kw: object) -> str:
        if cfg.has_section(section):
            return str(cfg.get(section, opt, **kw))
        return ""

    return {
        "url": (_env("ELIA_VALUEEDGE_URL") or g("ValueEdge", "URL", fallback="")).strip().rstrip("/"),
        "shared_space": (_env("ELIA_VALUEEDGE_SHARED_SPACE") or g("ValueEdge", "SHARED_SPACE", fallback="")).strip(),
        "workspace": (_env("ELIA_VALUEEDGE_WORKSPACE") or g("ValueEdge", "WORKSPACE", fallback="")).strip(),
        "tech_preview_flag": (
            _env("ELIA_VALUEEDGE_TECH_PREVIEW") or g("ValueEdge", "TECH_PREVIEW_FLAG", fallback="")
        ).strip(),
        "user": (_env("ELIA_VALUEEDGE_USER") or g("ValueEdge", "USER", fallback="")).strip(),
        "password": _env("ELIA_VALUEEDGE_PASSWORD") or g("ValueEdge", "PASSWORD", raw=True, fallback=""),
        "login": (_env("ELIA_VALUEEDGE_LOGIN") or g("ValueEdge", "LOGIN", fallback="")).strip(),
    }
