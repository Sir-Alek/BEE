"""Cifrado Fernet para memoria IA local y exportación de equipo."""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict

from cryptography.fernet import Fernet

from core import elia_license

MEMORY_LOCAL_SALT = b"|ELIA|MEMORY|v1"
MEMORY_TEAM_SALT = b"|ELIA|MEMORY|TEAM|v1"
EXPORT_FORMAT = "elia_memory_team_v1"

# Revisión BDD: edición manual a partir del 3.er intento (max 4 intentos).
MAX_AI_REVIEW_ATTEMPTS = 4
MANUAL_EDIT_FROM_ATTEMPT = 3


def _fernet_from_material(material: bytes) -> Fernet:
    digest = hashlib.sha256(material).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def local_fernet() -> Fernet:
    fp = elia_license.get_machine_fingerprint().encode("utf-8", errors="replace")
    return _fernet_from_material(fp + MEMORY_LOCAL_SALT)


def team_fernet(team_passphrase: str) -> Fernet:
    normalized = (team_passphrase or "").strip().encode("utf-8", errors="replace")
    if not normalized:
        raise ValueError("La frase de equipo no puede estar vacía.")
    return _fernet_from_material(normalized + MEMORY_TEAM_SALT)


def encrypt_local_document(data: Dict[str, Any]) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return local_fernet().encrypt(payload)


def decrypt_local_blob(blob: bytes) -> Dict[str, Any]:
    raw = local_fernet().decrypt(blob)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Memoria local inválida.")
    return data


def encrypt_team_export(data: Dict[str, Any], team_passphrase: str) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ciphertext = team_fernet(team_passphrase).encrypt(payload).decode("ascii")
    wrapper = {"format": EXPORT_FORMAT, "ciphertext": ciphertext}
    return json.dumps(wrapper, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decrypt_team_import(blob: bytes, team_passphrase: str) -> Dict[str, Any]:
    text = blob.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("Archivo de importación vacío.")

    if text.startswith("{"):
        wrapper = json.loads(text)
        if not isinstance(wrapper, dict):
            raise ValueError("Formato de importación inválido.")
        fmt = str(wrapper.get("format") or "")
        if fmt != EXPORT_FORMAT:
            raise ValueError(f"Formato no soportado: {fmt or 'desconocido'}.")
        ciphertext = wrapper.get("ciphertext")
        if not isinstance(ciphertext, str) or not ciphertext.strip():
            raise ValueError("Archivo de importación corrupto (sin ciphertext).")
        raw = team_fernet(team_passphrase).decrypt(ciphertext.encode("ascii"))
    else:
        raw = team_fernet(team_passphrase).decrypt(blob)

    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Memoria importada inválida.")
    return data
