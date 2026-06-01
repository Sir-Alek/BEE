"""
Firma de licencias v4 (Ed25519). Solo para uso interno — no empaquetar en ELIA.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PathLike = Union[str, Path]

DURATION_SECONDS: Dict[str, int] = {
    "15D": 15 * 86400,
    "30D": 30 * 86400,
    "365D": 365 * 86400,
}


def _b64url_encode(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def canonical_license_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")


def load_private_key(path: PathLike) -> Ed25519PrivateKey:
    pem = Path(path).read_bytes()
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Se requiere clave privada Ed25519 (PEM).")
    return key


def export_public_key_b64url(private_key: Ed25519PrivateKey) -> str:
    pub_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return _b64url_encode(pub_raw)


def build_machine_payload(
    *,
    kid: str,
    machine_fp: str,
    tier_code: str,
    duration: str,
    issue_ts: Optional[int] = None,
) -> Dict[str, Any]:
    fp = machine_fp.strip().lower()
    if len(fp) != 32:
        raise ValueError("La huella debe tener 32 caracteres hex.")
    dur = duration.strip().upper()
    if dur not in DURATION_SECONDS:
        raise ValueError(f"Duración no válida: {duration!r}. Use: 15D, 30D, 365D")
    tier = tier_code.strip().upper()
    if tier not in ("BASIC", "PRO", "ENT"):
        raise ValueError(f"Tier no válido: {tier_code!r}")
    iat = int(issue_ts if issue_ts is not None else time.time())
    exp = iat + DURATION_SECONDS[dur]
    return {
        "v": 4,
        "kid": kid,
        "fp": fp,
        "tier": tier,
        "dur": dur,
        "iat": iat,
        "exp": exp,
    }


def build_beta_global_payload(*, kid: str, exp_ts: int) -> Dict[str, Any]:
    exp = int(exp_ts)
    if exp <= 0:
        raise ValueError(f"exp_ts no válido: {exp_ts}")
    return {
        "v": 4,
        "kid": kid,
        "type": "beta_global",
        "exp": exp,
    }


def sign_payload(payload: Dict[str, Any], private_key: Ed25519PrivateKey) -> str:
    kid = str(payload.get("kid", "")).strip()
    if not kid:
        raise ValueError("Payload sin kid.")
    message = canonical_license_bytes(payload)
    sig = private_key.sign(message)
    payload_b64 = _b64url_encode(message)
    sig_b64 = _b64url_encode(sig)
    return f"ELIA-V4.{kid}.{payload_b64}.{sig_b64}"


def sign_machine_license(
    *,
    private_key_path: PathLike,
    kid: str,
    machine_fp: str,
    tier_code: str,
    duration: str,
    issue_ts: Optional[int] = None,
) -> tuple[str, Dict[str, Any]]:
    key = load_private_key(private_key_path)
    payload = build_machine_payload(
        kid=kid,
        machine_fp=machine_fp,
        tier_code=tier_code,
        duration=duration,
        issue_ts=issue_ts,
    )
    return sign_payload(payload, key), payload


def sign_beta_global_license(
    *,
    private_key_path: PathLike,
    kid: str,
    exp_ts: int,
) -> tuple[str, Dict[str, Any]]:
    key = load_private_key(private_key_path)
    payload = build_beta_global_payload(kid=kid, exp_ts=exp_ts)
    return sign_payload(payload, key), payload
