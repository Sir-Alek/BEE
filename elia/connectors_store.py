"""
Almacenamiento local cifrado de perfiles de conectores (Jira / Value Edge).

Usa una clave derivada de la huella de máquina (misma que licencia) para cifrar el JSON
en el disco del usuario bajo `elia/` (ver `core.bee_paths`).

Solo localhost sirve estos datos vía API; no sustituye políticas de seguridad en red.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from core import bee_license
from core import bee_paths


def _elia_data_dir() -> Path:
    """Ruta «elia» bajo datos de usuario (compat: extensiones compiladas pueden no exponer bee_paths.elia_dir)."""
    d = bee_paths.ensure_user_data_root() / "elia"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fernet() -> Fernet:
    digest = hashlib.sha256(
        bee_license.get_machine_fingerprint().encode("utf-8", errors="replace") + b"|ELIA|CONNECTORS|v1"
    ).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def store_path() -> Path:
    return _elia_data_dir() / "connectors.enc"


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
