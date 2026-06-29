"""Carga y validación del manifest de modelos GGUF."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ai.constants import AiProfile, ModelRole

_MANIFEST_REL = ("resources", "models", "models_manifest.json")


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def manifest_path() -> str:
    if is_frozen():
        base = getattr(sys, "_MEIPASS", "") or os.path.dirname(sys.executable)
        return os.path.join(base, *_MANIFEST_REL)
    return os.path.join(_repo_root(), *_MANIFEST_REL)


@lru_cache(maxsize=1)
def load_manifest() -> Dict[str, Any]:
    path = manifest_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Manifest de modelos no encontrado: {path}")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Manifest inválido: se esperaba un objeto JSON")
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("Manifest inválido: falta lista models")
    return data


def list_models(*, profile: Optional[AiProfile] = None, role: Optional[ModelRole] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for entry in load_manifest().get("models") or []:
        if not isinstance(entry, dict):
            continue
        if profile and profile != "off" and entry.get("profile") != profile:
            continue
        if role and entry.get("role") != role:
            continue
        out.append(dict(entry))
    return out


def get_model_entry(*, role: ModelRole, profile: AiProfile) -> Optional[Dict[str, Any]]:
    if profile == "off":
        return None
    matches = list_models(profile=profile, role=role)
    return matches[0] if matches else None


def profile_roles(profile: AiProfile) -> List[ModelRole]:
    if profile == "off":
        return []
    prof = (load_manifest().get("profiles") or {}).get(profile) or {}
    roles = prof.get("roles") or []
    return [str(r) for r in roles if r]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_model_file(path: str, entry: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    if not os.path.isfile(path):
        return False, "Archivo no encontrado"
    try:
        size = os.path.getsize(path)
    except OSError as e:
        return False, str(e)
    expected = int(entry.get("size_bytes") or 0)
    if expected > 0:
        tolerance = max(int(expected * 0.002), 4096)
        if abs(size - expected) > tolerance:
            return False, f"Tamaño {size} no coincide con manifest ({expected} bytes)"
    expected_sha = (entry.get("sha256") or "").strip().lower()
    if expected_sha:
        digest = sha256_file(path)
        if digest.lower() != expected_sha:
            return False, "SHA-256 no coincide con manifest"
    elif size <= 0:
        return False, "Archivo vacío"
    return True, None
