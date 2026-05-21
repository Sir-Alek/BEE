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
    p = store_path()
    blob = _fernet().encrypt(json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    p.write_bytes(blob)


def load_document() -> dict[str, Any] | None:
    p = store_path()
    if not p.is_file():
        return None
    raw = _fernet().decrypt(p.read_bytes())
    data = json.loads(raw.decode("utf-8"))
    return data if isinstance(data, dict) else None
