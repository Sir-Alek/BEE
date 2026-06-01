"""
Verificación de licencias v4 (Ed25519, rotación por kid).

Solo contiene lógica de validación y claves públicas embebidas.
La firma y la clave privada viven en ``license-tools/`` (no se empaqueta en ELIA).
"""
from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from core.entitlements import CODE_TO_TIER, TIER_BETA, TIER_CODES, get_tier_flags

LICENSE_PAYLOAD_VERSION = 4

_KEY_V4_RE = re.compile(
    r"^ELIA-V4\.(?P<kid>[A-Za-z0-9_-]+)\.(?P<payload>[A-Za-z0-9_-]+)\.(?P<sig>[A-Za-z0-9_-]+)$",
    re.IGNORECASE,
)

_PUBLIC_KEYS_PATH = Path(__file__).resolve().parent / "license_public_keys.json"
_public_keys_cache: Optional[Dict[str, bytes]] = None


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def canonical_license_bytes(payload: Dict[str, Any]) -> bytes:
    """JSON canónico firmado (orden de claves estable, sin espacios)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")


def _load_public_keys_json() -> Dict[str, bytes]:
    global _public_keys_cache
    if _public_keys_cache is not None:
        return _public_keys_cache
    if not _PUBLIC_KEYS_PATH.is_file():
        _public_keys_cache = {}
        return _public_keys_cache
    data = json.loads(_PUBLIC_KEYS_PATH.read_text(encoding="utf-8"))
    keys_raw = data.get("keys") if isinstance(data, dict) else {}
    parsed: Dict[str, bytes] = {}
    if isinstance(keys_raw, dict):
        for kid, b64 in keys_raw.items():
            if isinstance(kid, str) and isinstance(b64, str) and b64.strip():
                parsed[kid] = _b64url_decode(b64.strip())
    _public_keys_cache = parsed
    return _public_keys_cache


def reload_public_keys_cache() -> None:
    """Solo tests: invalida caché tras cambiar ``license_public_keys.json``."""
    global _public_keys_cache
    _public_keys_cache = None


def get_public_key(kid: str) -> Optional[Ed25519PublicKey]:
    raw = _load_public_keys_json().get(kid)
    if raw is None:
        return None
    try:
        return Ed25519PublicKey.from_public_bytes(raw)
    except ValueError:
        return None


@dataclass
class VerifiedLicensePayload:
    duration: str
    tier: str
    mobile: bool
    legacy: bool
    issue_ts: int
    expires_at: Optional[float]
    is_beta_global: bool = False
    beta_global_exp: Optional[int] = None
    kid: str = ""

    @property
    def features(self) -> Dict[str, bool]:
        if self.is_beta_global or self.tier == TIER_BETA:
            return get_tier_flags(TIER_BETA)
        return get_tier_flags(self.tier)


def _valid_issue_ts(issue_ts: int) -> bool:
    now = time.time()
    if issue_ts <= 0:
        return False
    if issue_ts > now + 300:
        return False
    if issue_ts < now - 20 * 365 * 86400:
        return False
    return True


def _tier_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    tier_raw = payload.get("tier")
    if not isinstance(tier_raw, str):
        return None
    code = tier_raw.strip().upper()
    if code in CODE_TO_TIER:
        return CODE_TO_TIER[code]
    tier_norm = tier_raw.strip().lower()
    if tier_norm in TIER_CODES and tier_norm != TIER_BETA:
        return tier_norm
    return None


def _duration_allowed_v4(dur: str) -> bool:
    return dur in ("15D", "30D", "365D")


def verify_v4_key(key: str, machine_fp: Optional[str] = None) -> Optional[VerifiedLicensePayload]:
    raw = (key or "").strip().replace(" ", "")
    m = _KEY_V4_RE.match(raw)
    if not m:
        return None

    kid = m.group("kid")
    try:
        payload_bytes = _b64url_decode(m.group("payload"))
        sig_bytes = _b64url_decode(m.group("sig"))
    except Exception:
        return None

    pub = get_public_key(kid)
    if pub is None:
        return None

    try:
        pub.verify(sig_bytes, payload_bytes)
    except InvalidSignature:
        return None

    try:
        payload = json.loads(payload_bytes.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("v") != LICENSE_PAYLOAD_VERSION:
        return None
    if payload.get("kid") != kid:
        return None

    license_type = payload.get("type")
    if license_type == "beta_global":
        try:
            exp_ts = int(payload["exp"])
        except (KeyError, TypeError, ValueError):
            return None
        if exp_ts <= 0:
            return None
        return VerifiedLicensePayload(
            duration="365D",
            tier=TIER_BETA,
            mobile=True,
            legacy=True,
            issue_ts=exp_ts,
            expires_at=float(exp_ts),
            is_beta_global=True,
            beta_global_exp=exp_ts,
            kid=kid,
        )

    fp = (machine_fp or "").strip().lower()
    payload_fp = str(payload.get("fp", "")).strip().lower()
    if not fp or len(fp) != 32 or payload_fp != fp:
        return None

    tier = _tier_from_payload(payload)
    if tier is None:
        return None

    dur = str(payload.get("dur", "")).strip().upper()
    if not _duration_allowed_v4(dur):
        return None

    try:
        iat = int(payload.get("iat", 0))
        exp = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return None

    if not _valid_issue_ts(iat):
        return None
    if exp <= iat:
        return None

    mobile = tier in ("professional", "enterprise")
    legacy = tier == "enterprise"

    return VerifiedLicensePayload(
        duration=dur,
        tier=tier,
        mobile=mobile,
        legacy=legacy,
        issue_ts=iat,
        expires_at=float(exp),
        kid=kid,
    )
