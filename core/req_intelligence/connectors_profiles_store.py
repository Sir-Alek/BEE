"""
Almacenamiento local cifrado de perfiles de conectores (Jira / Value Edge).

Usa una clave derivada de la huella de máquina (misma que licencia) para cifrar el JSON
bajo ``external_connectors/`` en datos de usuario (ver ``core.elia_paths``).

Solo localhost sirve estos datos vía API; no sustituye políticas de seguridad en red.
"""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from core import elia_license
from core import elia_paths


def store_path() -> Path:
    d = elia_paths.external_connectors_dir()
    p = d / "connectors.enc"
    legacy = elia_paths.ensure_user_data_root() / "elia" / "connectors.enc"
    if not p.is_file() and legacy.is_file():
        try:
            shutil.copy2(legacy, p)
        except OSError:
            pass
    return p


def _fernet() -> Fernet:
    digest = hashlib.sha256(
        elia_license.get_machine_fingerprint().encode("utf-8", errors="replace") + b"|ELIA|CONNECTORS|v1"
    ).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def save_document(doc: dict[str, Any]) -> None:
    doc = normalize_document(doc)
    p = store_path()
    blob = _fernet().encrypt(json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    p.write_bytes(blob)


def load_document() -> dict[str, Any] | None:
    p = store_path()
    if not p.is_file():
        return None
    raw = _fernet().decrypt(p.read_bytes())
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        return None
    return normalize_document(data)


def normalize_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Migra v1 → v2 y rellena defaults de publicación."""
    version = int(doc.get("version") or 1)
    profiles_in = doc.get("profiles") if isinstance(doc.get("profiles"), list) else []
    profiles: list[dict[str, Any]] = []
    for item in profiles_in:
        if not isinstance(item, dict):
            continue
        profiles.append(normalize_profile(item))
    out_version = max(version, 2)
    return {"version": out_version, "profiles": profiles}


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    jira = dict(profile.get("jira") or {})
    jira.setdefault("mode", "vanilla")
    jira.setdefault("project_key", "")
    jira.setdefault("xray_base_url", "")
    jira.setdefault("target_field", "description")
    jira.setdefault("default_issue_key", "")
    ve = dict(profile.get("value_edge") or {})
    ve.setdefault("default_requirement_id", "")
    git = dict(profile.get("git") or {})
    git.setdefault("provider", "github")
    git.setdefault("repo_url", "")
    git.setdefault("branch", "main")
    git.setdefault("base_path", "features/")
    git.setdefault("token", "")
    azure = dict(profile.get("azure_devops") or {})
    azure.setdefault("org", "")
    azure.setdefault("project", "")
    azure.setdefault("pat", "")
    azure.setdefault("default_work_item_id", "")
    azure.setdefault("target_field", "System.Description")
    return {
        "id": str(profile.get("id") or ""),
        "name": str(profile.get("name") or "Perfil"),
        "jira": jira,
        "value_edge": ve,
        "git": git,
        "azure_devops": azure,
    }


def load_profile_by_id(profile_id: str) -> dict[str, Any] | None:
    doc = load_document()
    if not doc:
        return None
    pid = (profile_id or "").strip()
    for item in doc.get("profiles") or []:
        if isinstance(item, dict) and str(item.get("id")) == pid:
            return normalize_profile(item)
    return None

