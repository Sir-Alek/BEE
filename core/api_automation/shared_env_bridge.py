"""Puente de entornos compartidos entre grabación web y proyecto API."""
from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from core.api_automation.project_config import load_environment, save_environment
from core.api_automation.traffic_store import list_traffic_captures, load_traffic_file


def infer_web_origin(api_project: str) -> Optional[str]:
    """Obtiene origen (scheme://host) desde la captura web más reciente del proyecto API."""
    captures = list_traffic_captures(api_project)
    if not captures:
        return None
    latest = captures[-1]
    try:
        capture = load_traffic_file(latest["path"])
    except (OSError, ValueError):
        return None
    source = (capture.source_url or "").strip()
    if source:
        parsed = urlparse(source)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    for entry in capture.entries:
        url = (entry.url or "").strip()
        if not url.startswith("http"):
            continue
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def sync_api_environment_from_web(api_project: str, env_name: str = "dev") -> Dict[str, Any]:
    """Copia base_url del origen web detectado al entorno API (sin sobrescribir otras variables)."""
    origin = infer_web_origin(api_project)
    if not origin:
        raise ValueError("No hay captura web con URL de origen para sincronizar")
    env = load_environment(api_project, env_name)
    variables = dict(env.get("variables") or {})
    variables["base_url"] = origin.rstrip("/")
    save_environment(api_project, env_name, {"name": env.get("name") or env_name, "variables": variables})
    return {"environment": env_name, "base_url": variables["base_url"], "origin": origin}
