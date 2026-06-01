"""
Licencia offline: activación obligatoria por clave + kill switch local.

Sin servidor externo: estado en disco local, HMAC con secreto embebido (cambiar en builds de release).

Seguridad: no se confía en ``activated`` ni en ``activated_ts`` del JSON; en cada consulta se
revalida ``saved_activation_key`` (HMAC + huella). Claves v2 incluyen ``issue_ts`` en la cadena;
la caducidad se calcula solo desde ese timestamp firmado, no desde el disco.

Respaldo oculto (comodidad): si el usuario borra ``license_state.json``, se puede restaurar la clave
desde copias firmadas; borrar todo solo desactiva la app hasta volver a introducir la clave.

Huella: identificadores de hardware estables (sin nombre de equipo). Ver ``get_machine_fingerprint()``.

Variables de entorno (desarrollo / soporte):
  ELIA_SKIP_LICENSE=1  — omite comprobación y habilita todos los módulos (no usar en entregas).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.entitlements import (
    CODE_TO_TIER,
    TIER_BASIC,
    TIER_BETA,
    TIER_CODES,
    UPGRADE_CONTACT_EMAIL,
    entitlements_payload,
    get_tier_flags,
    infer_tier_from_v2_mods,
    legacy_modules_from_features,
)
from core._version import elia_beta_deadline_ts
from core.license_verify import verify_v4_key


def _distribution_channel() -> str:
    """Canal de build (beta | release); re-leído para tests."""
    from core._version import ELIA_CHANNEL as channel

    return (channel or "release").strip().lower()

# Duraciones emitidas por el generador de claves
DURATION_15D = "15D"
DURATION_30D = "30D"
DURATION_365D = "365D"
DURATION_PERM = "PERM"

DURATION_SECONDS: Dict[str, Optional[int]] = {
    DURATION_15D: 15 * 86400,
    DURATION_30D: 30 * 86400,
    DURATION_365D: 365 * 86400,
    DURATION_PERM: None,
}

DURATION_LABELS: Dict[str, str] = {
    DURATION_15D: "15 días",
    DURATION_30D: "1 mes",
    DURATION_365D: "1 año",
    DURATION_PERM: "permanente",
}

_LICENSE_SEED = b"ELIA-LICENSE-v1-REPLACE-IN-RELEASE-BUILD"

# v3: ELIA-V3-PRO-365D-1779324449-{hmac64} — tier + duración + issue_ts firmados.
_KEY_PREFIX_V3_RE = re.compile(
    r"^ELIA-V3-(?P<tier>BASIC|PRO|ENT)-(?P<dur>15D|30D|365D|PERM)-(?P<issue_ts>\d{9,12})-(?P<sig>[0-9a-f]{64})$",
    re.IGNORECASE,
)
# Clave global beta (sin huella): ELIA-BETA-GLOBAL-1779324449-{hmac64}
_KEY_BETA_GLOBAL_RE = re.compile(
    r"^ELIA-BETA-GLOBAL-(?P<exp_ts>\d{9,12})-(?P<sig>[0-9a-f]{64})$",
    re.IGNORECASE,
)
# v2: ELIA-15D-0-1779324449-{hmac64} — issue_ts forma parte del HMAC (zero trust en caducidad).
_KEY_PREFIX_V2_RE = re.compile(
    r"^ELIA-(?P<dur>15D|30D|365D|PERM)-(?P<mods>[0ML]+)-(?P<issue_ts>\d{9,12})-(?P<sig>[0-9a-f]{64})$",
    re.IGNORECASE,
)
# v1 legado: ELIA-15D-0-{hmac64} — caducidad aún lee activated_ts del JSON (deprecado).
_KEY_PREFIX_V1_RE = re.compile(
    r"^ELIA-(?P<dur>15D|30D|365D|PERM)-(?P<mods>[0ML]+)-(?P<sig>[0-9a-f]{64})$",
    re.IGNORECASE,
)

_INVALID_HW_VALUES = frozenset(
    {
        "",
        "none",
        "null",
        "n/a",
        "na",
        "to be filled by o.e.m.",
        "default string",
        "00000000",
        "123456789",
        "ffffffff",
        "system serial number",
    }
)


def _secret_key() -> bytes:
    return hashlib.sha256(_LICENSE_SEED).digest()


def _normalize_hw_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip()
    if not v or v.lower() in _INVALID_HW_VALUES:
        return None
    return v


def _run_wmic(alias: str, field: str) -> Optional[str]:
    if sys.platform != "win32":
        return None
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(
            ["wmic", alias, "get", field],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=flags,
        )
        if proc.returncode != 0:
            return None
        lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
        if len(lines) < 2:
            return None
        return _normalize_hw_value(lines[1])
    except Exception:
        return None


def _linux_machine_id() -> Optional[str]:
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            p = Path(path)
            if p.is_file():
                return _normalize_hw_value(p.read_text(encoding="utf-8").splitlines()[0])
        except Exception:
            continue
    return None


def _collect_hardware_parts() -> List[str]:
    """Partes estables para la huella (sin nombre de equipo / platform.node)."""
    parts: List[str] = []

    if sys.platform == "win32":
        board = _run_wmic("baseboard", "serialnumber")
        if board:
            parts.append(f"board:{board}")
        product_uuid = _run_wmic("csproduct", "uuid")
        if product_uuid:
            parts.append(f"product:{product_uuid}")
        cpu_id = _run_wmic("cpu", "processorid")
        if cpu_id:
            parts.append(f"cpu:{cpu_id}")
    else:
        mid = _linux_machine_id()
        if mid:
            parts.append(f"machine-id:{mid}")

    try:
        mac = uuid.getnode()
        if mac and (mac >> 40) % 2 == 0:
            parts.append(f"mac:{mac}")
    except Exception:
        pass

    parts.append(f"arch:{platform.machine()}")
    parts.append(f"platform:{sys.platform}")
    return parts


def get_machine_fingerprint() -> str:
    """
    Huella corta por equipo. Sobrevive a reinstalar Windows si el hardware no cambia.
    No usa el nombre del equipo (platform.node).
    """
    parts = _collect_hardware_parts()
    if not parts:
        parts = [f"fallback:{uuid.getnode()}", f"arch:{platform.machine()}", f"platform:{sys.platform}"]
    raw = "|".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:32]


def _mods_token(mobile: bool, legacy: bool) -> str:
    token = ""
    if mobile:
        token += "M"
    if legacy:
        token += "L"
    return token or "0"


def _parse_mods_token(token: str) -> Tuple[bool, bool]:
    t = (token or "0").upper()
    return ("M" in t, "L" in t)


def _license_message_v3(
    machine_fp: str, tier_code: str, duration: str, issue_ts: int
) -> bytes:
    return f"{machine_fp}|V3|{tier_code.upper()}|{duration.upper()}|{issue_ts}".encode("ascii")


def _license_message_beta_global(exp_ts: int) -> bytes:
    return f"BETA|GLOBAL|{exp_ts}".encode("ascii")


def _expected_signature_v3(
    machine_fp: str,
    tier_code: str,
    duration: str,
    issue_ts: int,
) -> str:
    return hmac.new(
        _secret_key(),
        _license_message_v3(machine_fp, tier_code, duration, issue_ts),
        hashlib.sha256,
    ).hexdigest()


def _expected_signature_beta_global(exp_ts: int) -> str:
    return hmac.new(
        _secret_key(),
        _license_message_beta_global(exp_ts),
        hashlib.sha256,
    ).hexdigest()


def _license_message_v2(
    machine_fp: str, duration: str, mobile: bool, legacy: bool, issue_ts: int
) -> bytes:
    flags = _mods_token(mobile, legacy)
    return f"{machine_fp}|{duration}|{flags}|{issue_ts}".encode("ascii")


def _expected_signature_v1(
    machine_fp: str,
    duration: str,
    mobile: bool = False,
    legacy: bool = False,
) -> str:
    return hmac.new(
        _secret_key(),
        _license_message_v1(machine_fp, duration, mobile, legacy),
        hashlib.sha256,
    ).hexdigest()


def _expected_signature_v2(
    machine_fp: str,
    duration: str,
    issue_ts: int,
    mobile: bool = False,
    legacy: bool = False,
) -> str:
    return hmac.new(
        _secret_key(),
        _license_message_v2(machine_fp, duration, mobile, legacy, issue_ts),
        hashlib.sha256,
    ).hexdigest()


def _valid_issue_ts(issue_ts: int) -> bool:
    now = time.time()
    if issue_ts <= 0:
        return False
    if issue_ts > now + 300:
        return False
    if issue_ts < now - 20 * 365 * 86400:
        return False
    return True


def build_activation_key(
    machine_fp: str,
    duration: str = DURATION_365D,
    *,
    tier: str = "enterprise",
    issue_ts: Optional[int] = None,
) -> str:
    """
    Genera clave v3 legada (HMAC): ELIA-V3-{TIER}-{dur}-{issue_ts}-{hmac64}.
    Preferir ``license-tools/generate_license_key.py`` (v4 Ed25519).
    """
    tier_norm = (tier or "enterprise").strip().lower()
    tier_code = TIER_CODES.get(tier_norm)
    if tier_code is None or tier_code == TIER_CODES[TIER_BETA]:
        raise ValueError(f"Tier no válido para clave por máquina: {tier!r}")
    dur = duration.upper()
    if dur == DURATION_PERM:
        raise ValueError("Duración PERM eliminada; use 15D, 30D o 365D (o license-tools v4).")
    if dur not in DURATION_SECONDS:
        raise ValueError(f"Duración no válida: {duration}")
    fp = machine_fp.strip().lower()
    if len(fp) != 32:
        raise ValueError("La huella debe tener 32 caracteres hex.")
    ts = int(issue_ts if issue_ts is not None else time.time())
    if not _valid_issue_ts(ts):
        raise ValueError(f"issue_ts no válido: {ts}")
    sig = _expected_signature_v3(fp, tier_code, dur, ts)
    return f"ELIA-V3-{tier_code}-{dur}-{ts}-{sig}"


def build_beta_global_key(*, exp_ts: Optional[int] = None) -> str:
    """Clave única global para extender/distribuir beta (sin huella de equipo)."""
    ts = int(exp_ts if exp_ts is not None else elia_beta_deadline_ts())
    if ts <= 0:
        raise ValueError(f"exp_ts no válido: {ts}")
    sig = _expected_signature_beta_global(ts)
    return f"ELIA-BETA-GLOBAL-{ts}-{sig}"


def _license_message_v1(machine_fp: str, duration: str, mobile: bool, legacy: bool) -> bytes:
    if duration == "FULL":
        return machine_fp.encode("ascii") + b"|FULL"
    flags = _mods_token(mobile, legacy)
    return f"{machine_fp}|{duration}|{flags}".encode("ascii")


def build_activation_key_v2(
    machine_fp: str,
    duration: str = DURATION_PERM,
    *,
    mobile: bool = False,
    legacy: bool = False,
    issue_ts: Optional[int] = None,
) -> str:
    """Genera clave v2 legada (tests / compatibilidad). Preferir build_activation_key (v3)."""
    dur = duration.upper()
    if dur not in DURATION_SECONDS:
        raise ValueError(f"Duración no válida: {duration}")
    fp = machine_fp.strip().lower()
    if len(fp) != 32:
        raise ValueError("La huella debe tener 32 caracteres hex.")
    ts = int(issue_ts if issue_ts is not None else time.time())
    if not _valid_issue_ts(ts):
        raise ValueError(f"issue_ts no válido: {ts}")
    sig = _expected_signature_v2(fp, dur, ts, mobile, legacy)
    mods = _mods_token(mobile, legacy)
    return f"ELIA-{dur}-{mods}-{ts}-{sig}"


def build_activation_key_v1_legacy(
    machine_fp: str,
    duration: str = DURATION_PERM,
    *,
    mobile: bool = False,
    legacy: bool = False,
) -> str:
    """Formato v1 sin issue_ts (solo tests / claves antiguas)."""
    dur = duration.upper()
    if dur not in DURATION_SECONDS:
        raise ValueError(f"Duración no válida: {duration}")
    fp = machine_fp.strip().lower()
    if len(fp) != 32:
        raise ValueError("La huella debe tener 32 caracteres hex.")
    sig = _expected_signature_v1(fp, dur, mobile, legacy)
    mods = _mods_token(mobile, legacy)
    return f"ELIA-{dur}-{mods}-{sig}"


@dataclass
class ParsedLicenseKey:
    duration: str
    tier: str
    mobile: bool
    legacy: bool
    issue_ts: Optional[int] = None
    beta_global_exp: Optional[int] = None
    is_beta_global: bool = False
    signed_expires_at: Optional[float] = None
    license_format: str = "legacy"

    @property
    def features(self) -> Dict[str, bool]:
        if self.is_beta_global or self.tier == TIER_BETA:
            return get_tier_flags(TIER_BETA)
        return get_tier_flags(self.tier)


def _sig_matches(provided: str, expected: str) -> bool:
    provided = provided.lower()
    expected = expected.lower()
    if provided == expected:
        return True
    return len(provided) >= 32 and expected.startswith(provided[:32])


def _verified_v4_to_parsed(verified: Any) -> ParsedLicenseKey:
    return ParsedLicenseKey(
        duration=verified.duration,
        tier=verified.tier,
        mobile=verified.mobile,
        legacy=verified.legacy,
        issue_ts=verified.issue_ts,
        beta_global_exp=verified.beta_global_exp,
        is_beta_global=verified.is_beta_global,
        signed_expires_at=verified.expires_at,
        license_format="v4",
    )


def _match_v4_key(key: str, machine_fp: str) -> Optional[ParsedLicenseKey]:
    verified = verify_v4_key(key, machine_fp)
    if verified is None:
        return None
    return _verified_v4_to_parsed(verified)


def _match_beta_global_key(key: str) -> Optional[ParsedLicenseKey]:
    raw = (key or "").strip().replace(" ", "")
    v4 = verify_v4_key(raw, None)
    if v4 is not None and v4.is_beta_global:
        return _verified_v4_to_parsed(v4)
    m = _KEY_BETA_GLOBAL_RE.match(raw)
    if not m:
        return None
    try:
        exp_ts = int(m.group("exp_ts"))
    except ValueError:
        return None
    sig = m.group("sig")
    expected = _expected_signature_beta_global(exp_ts)
    if not _sig_matches(sig, expected):
        return None
    return ParsedLicenseKey(
        duration=DURATION_PERM,
        tier=TIER_BETA,
        mobile=True,
        legacy=True,
        issue_ts=exp_ts,
        beta_global_exp=exp_ts,
        is_beta_global=True,
    )


def _match_key_signature(key: str, machine_fp: str) -> Optional[ParsedLicenseKey]:
    raw = (key or "").strip().replace(" ", "")

    beta = _match_beta_global_key(raw)
    if beta is not None:
        return beta

    v4 = _match_v4_key(raw, machine_fp)
    if v4 is not None:
        return v4

    m3 = _KEY_PREFIX_V3_RE.match(raw)
    if m3:
        tier_code = m3.group("tier").upper()
        tier = CODE_TO_TIER.get(tier_code)
        if tier is None:
            return None
        dur = m3.group("dur").upper()
        try:
            issue_ts = int(m3.group("issue_ts"))
        except ValueError:
            return None
        if not _valid_issue_ts(issue_ts):
            return None
        sig = m3.group("sig")
        expected = _expected_signature_v3(machine_fp, tier_code, dur, issue_ts)
        if _sig_matches(sig, expected):
            mobile = tier in ("professional", "enterprise", "beta")
            legacy = tier in ("enterprise", "beta")
            return ParsedLicenseKey(
                duration=dur,
                tier=tier,
                mobile=mobile,
                legacy=legacy,
                issue_ts=issue_ts,
            )
        return None

    m2 = _KEY_PREFIX_V2_RE.match(raw)
    if m2:
        dur = m2.group("dur").upper()
        mobile, legacy = _parse_mods_token(m2.group("mods"))
        try:
            issue_ts = int(m2.group("issue_ts"))
        except ValueError:
            return None
        if not _valid_issue_ts(issue_ts):
            return None
        sig = m2.group("sig")
        expected = _expected_signature_v2(machine_fp, dur, issue_ts, mobile, legacy)
        if _sig_matches(sig, expected):
            tier = infer_tier_from_v2_mods(mobile, legacy)
            return ParsedLicenseKey(
                duration=dur,
                tier=tier,
                mobile=mobile,
                legacy=legacy,
                issue_ts=issue_ts,
            )
        return None

    m1 = _KEY_PREFIX_V1_RE.match(raw)
    if m1:
        dur = m1.group("dur").upper()
        mobile, legacy = _parse_mods_token(m1.group("mods"))
        sig = m1.group("sig")
        expected = _expected_signature_v1(machine_fp, dur, mobile, legacy)
        if _sig_matches(sig, expected):
            tier = infer_tier_from_v2_mods(mobile, legacy)
            return ParsedLicenseKey(
                duration=dur,
                tier=tier,
                mobile=mobile,
                legacy=legacy,
                issue_ts=None,
            )
        return None

    hex_only = raw.replace("-", "")
    if len(hex_only) < 32:
        return None

    expected_full = _expected_signature_v1(machine_fp, "FULL", False, False)
    if _sig_matches(hex_only, expected_full):
        return ParsedLicenseKey(
            duration=DURATION_PERM,
            tier=infer_tier_from_v2_mods(False, False),
            mobile=False,
            legacy=False,
            issue_ts=None,
        )

    if len(hex_only) == 64:
        for dur in DURATION_SECONDS:
            for mobile in (False, True):
                for legacy in (False, True):
                    expected = _expected_signature_v1(machine_fp, dur, mobile, legacy)
                    if hex_only.lower() == expected.lower():
                        tier = infer_tier_from_v2_mods(mobile, legacy)
                        return ParsedLicenseKey(
                            duration=dur,
                            tier=tier,
                            mobile=mobile,
                            legacy=legacy,
                            issue_ts=None,
                        )
    return None


def verify_activation_key(key: str, machine_fp: Optional[str] = None) -> bool:
    if _match_beta_global_key((key or "").strip().replace(" ", "")) is not None:
        return True
    fp = machine_fp or get_machine_fingerprint()
    return _match_key_signature(key, fp) is not None


def parse_activation_key(key: str, machine_fp: Optional[str] = None) -> Optional[ParsedLicenseKey]:
    beta = _match_beta_global_key((key or "").strip().replace(" ", ""))
    if beta is not None:
        return beta
    fp = machine_fp or get_machine_fingerprint()
    return _match_key_signature(key, fp)


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    elia = Path(base) / "ELIA"
    elia.mkdir(parents=True, exist_ok=True)
    return elia


def _state_path() -> Path:
    return _state_dir() / "license_state.json"


def _load_state() -> Dict[str, Any]:
    p = _state_path()
    if not p.is_file():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(data: Dict[str, Any]) -> None:
    p = _state_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=0)


def _get_hidden_backup_paths() -> list[Path]:
    """Rutas de respaldo de comodidad para saved_activation_key."""
    paths: list[Path] = []
    if sys.platform == "win32":
        local = Path(
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or str(Path.home())
        )
        temp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or str(local))
        paths.append(temp / "etil_sys_metrics.db")
        paths.append(
            local
            / "Microsoft"
            / "Windows"
            / "WebCache"
            / ".win_telemetry_cache"
        )
        paths.append(local / "ELIA" / ".wgx_state_cache")
    else:
        home = Path.home()
        paths.append(home / ".cache" / ".sys_bus_metrics")
        paths.append(home / ".local" / "share" / ".v8_compile_cache")
        paths.append(home / ".elia_license_stub")
    return paths


def _activation_backup_message(machine_fp: str, key: str, activated_ts: float) -> bytes:
    return f"{machine_fp}|ACTIVATION|{key}|{activated_ts:.6f}".encode("ascii")


def _activation_backup_signature(machine_fp: str, key: str, activated_ts: float) -> str:
    return hmac.new(
        _secret_key(),
        _activation_backup_message(machine_fp, key, activated_ts),
        hashlib.sha256,
    ).hexdigest()


def _read_activation_backup(path: Path, machine_fp: str) -> Optional[Tuple[str, float]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        key = _normalize_stored_key(str(data.get("key", "")))
        if not key:
            return None
        ts = float(data.get("ts", 0.0))
        sig = str(data.get("sig", "")).lower()
        expected = _activation_backup_signature(machine_fp, key, ts)
        if not hmac.compare_digest(sig, expected):
            return None
        if parse_activation_key(key, machine_fp) is None:
            return None
        return key, ts
    except Exception:
        return None


def _write_activation_backup(
    path: Path, machine_fp: str, key: str, activated_ts: float
) -> None:
    payload = {
        "v": 2,
        "key": key,
        "ts": activated_ts,
        "sig": _activation_backup_signature(machine_fp, key, activated_ts),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)
        except Exception:
            pass


def _find_activation_in_backups(machine_fp: str) -> Optional[Tuple[str, float]]:
    best: Optional[Tuple[str, float]] = None
    for path in _get_hidden_backup_paths():
        row = _read_activation_backup(path, machine_fp)
        if row is None:
            continue
        if best is None or row[1] < best[1]:
            best = row
    return best


def _sync_activation_backups(machine_fp: str, key: str, activated_ts: float) -> None:
    for path in _get_hidden_backup_paths():
        try:
            _write_activation_backup(path, machine_fp, key, activated_ts)
        except Exception:
            continue


def _load_effective_state() -> Dict[str, Any]:
    """Carga estado principal y restaura clave desde respaldos si hace falta."""
    state = _load_state()
    fp = get_machine_fingerprint()

    if _resolve_license_from_state(state, fp) is not None:
        key = _normalize_stored_key(str(state.get("saved_activation_key", "")))
        ts = float(state.get("activated_ts") or time.time())
        _sync_activation_backups(fp, key, ts)
        return state

    # Clave presente en el JSON principal pero inválida (HMAC/issue_ts alterado):
    # no restaurar desde respaldo oculto — evita extender caducidad editando license_state.json.
    if _normalize_stored_key(str(state.get("saved_activation_key", ""))):
        return state

    restored = _find_activation_in_backups(fp)
    if restored is not None:
        key, activated_ts = restored
        state["saved_activation_key"] = key
        state["activated"] = True
        state["activated_ts"] = activated_ts
        parsed = parse_activation_key(key, fp)
        if parsed:
            state["duration_code"] = parsed.duration
            state["tier"] = parsed.tier
            sec = DURATION_SECONDS.get(parsed.duration)
            if parsed.is_beta_global:
                state["expires_at"] = float(parsed.beta_global_exp or parsed.issue_ts or 0) or None
            elif parsed.signed_expires_at is not None:
                state["expires_at"] = float(parsed.signed_expires_at)
            else:
                base_ts = float(parsed.issue_ts if parsed.issue_ts is not None else activated_ts)
                state["expires_at"] = (base_ts + sec) if sec is not None else None
            state["licensed_modules"] = _licensed_modules_dict(parsed)
            state["licensed_features"] = _licensed_features_dict(parsed)
        _save_state(state)
        _sync_licensed_modules(
            bool((state.get("licensed_modules") or {}).get("mobile_recording")),
            bool((state.get("licensed_modules") or {}).get("legacy_recording")),
        )
        return state

    return state


def _sync_licensed_modules(mobile: bool, legacy: bool) -> None:
    try:
        from core.modules_config import apply_licensed_modules

        apply_licensed_modules(mobile=mobile, legacy=legacy)
    except Exception:
        pass


def _clear_licensed_modules() -> None:
    try:
        from core.modules_config import apply_licensed_modules

        apply_licensed_modules(mobile=False, legacy=False)
    except Exception:
        pass


def _normalize_stored_key(key: str) -> str:
    return (key or "").strip().replace(" ", "")


def _licensed_modules_dict(parsed: ParsedLicenseKey) -> Dict[str, bool]:
    legacy = legacy_modules_from_features(parsed.features)
    return legacy


def _licensed_features_dict(parsed: ParsedLicenseKey) -> Dict[str, bool]:
    return dict(parsed.features)


def _resolve_license_from_state(
    state: Dict[str, Any], machine_fp: str
) -> Optional[Tuple[ParsedLicenseKey, float, Optional[float]]]:
    saved_key = state.get("saved_activation_key")
    if not saved_key:
        return None
    key_norm = _normalize_stored_key(str(saved_key))
    parsed = parse_activation_key(key_norm, machine_fp)
    if parsed is None:
        return None

    if parsed.is_beta_global:
        exp_ts = float(parsed.beta_global_exp or parsed.issue_ts or 0)
        return parsed, exp_ts, exp_ts

    if parsed.issue_ts is not None:
        activated_ts = float(parsed.issue_ts)
    else:
        activated_ts = float(state.get("activated_ts") or 0.0)
        if activated_ts <= 0:
            activated_ts = time.time()
    if parsed.signed_expires_at is not None:
        exp_ts = float(parsed.signed_expires_at)
    else:
        sec = DURATION_SECONDS.get(parsed.duration)
        exp_ts = (activated_ts + sec) if sec is not None else None
    return parsed, activated_ts, exp_ts


def is_time_limited_license_active() -> bool:
    st = get_license_status()
    return st.ok and st.reason == "activated"


def get_active_license_features() -> Optional[Dict[str, bool]]:
    st = get_license_status()
    if not st.ok or st.reason not in ("activated", "beta"):
        return None
    if st.features is not None:
        return dict(st.features)
    return None


def get_active_license_modules() -> Optional[Dict[str, bool]]:
    feats = get_active_license_features()
    if feats is None:
        return None
    return legacy_modules_from_features(feats)


def activate_with_key(key: str) -> bool:
    fp = get_machine_fingerprint()
    parsed = parse_activation_key(key, fp)
    if parsed is None:
        return False
    state = _load_state()
    key_norm = _normalize_stored_key(key)
    issue_ts = float(parsed.issue_ts) if parsed.issue_ts is not None else time.time()
    if parsed.signed_expires_at is not None:
        expires_at: Optional[float] = float(parsed.signed_expires_at)
    else:
        sec = DURATION_SECONDS.get(parsed.duration)
        expires_at = (issue_ts + sec) if sec is not None else None
    state["saved_activation_key"] = key_norm
    state["activated"] = True
    state["activated_ts"] = issue_ts
    state["issue_ts"] = parsed.issue_ts
    state["duration_code"] = parsed.duration
    state["tier"] = parsed.tier
    state["expires_at"] = expires_at
    state["licensed_modules"] = _licensed_modules_dict(parsed)
    state["licensed_features"] = _licensed_features_dict(parsed)
    _save_state(state)
    _sync_activation_backups(fp, key_norm, issue_ts)
    _sync_licensed_modules(parsed.mobile, parsed.legacy)
    return True


def kill_switch_active() -> bool:
    from core.runtime_policy_cache import runtime_policy_suspend_active

    return runtime_policy_suspend_active()


@dataclass
class LicenseStatus:
    ok: bool
    reason: str
    activated: bool
    machine_fingerprint: str
    message: str
    expires_at: Optional[float] = None
    duration_code: Optional[str] = None
    licensed_modules: Optional[Dict[str, bool]] = None
    tier_name: Optional[str] = None
    features: Optional[Dict[str, bool]] = None
    is_beta: bool = False
    upgrade_email: str = UPGRADE_CONTACT_EMAIL


def _beta_guard_for_parsed(parsed: Optional[ParsedLicenseKey]) -> Optional[Any]:
    from core.beta_time_guard import BetaGuardResult, check_beta_expiration

    extra: Optional[float] = None
    if parsed is not None and parsed.is_beta_global:
        extra = float(parsed.beta_global_exp or parsed.issue_ts or 0) or None
    return check_beta_expiration(extra_deadline_ts=extra)


def _status_from_beta_guard(guard: Any, fp: str) -> LicenseStatus:
    from core.beta_time_guard import beta_expired_user_message

    features = get_tier_flags(TIER_BETA)
    legacy = legacy_modules_from_features(features)
    if guard.ok:
        days_left = max(0.0, (guard.deadline_ts - guard.effective_now) / 86400.0)
        return LicenseStatus(
            ok=True,
            reason="beta",
            activated=True,
            machine_fingerprint=fp,
            message=f"Beta ELIA: quedan aprox. {days_left:.1f} día(s).",
            expires_at=guard.deadline_ts,
            duration_code="BETA",
            licensed_modules=legacy,
            tier_name=TIER_BETA,
            features=features,
            is_beta=True,
        )
    msg = guard.message
    if guard.reason == "beta_expired":
        msg = beta_expired_user_message(UPGRADE_CONTACT_EMAIL)
    return LicenseStatus(
        ok=False,
        reason=guard.reason,
        activated=True,
        machine_fingerprint=fp,
        message=msg,
        expires_at=guard.deadline_ts,
        duration_code="BETA",
        licensed_modules=legacy,
        tier_name=TIER_BETA,
        features=features,
        is_beta=True,
    )


def can_run_jobs() -> bool:
    st = get_license_status()
    return st.ok and st.reason not in (
        "not_activated",
        "license_expired",
        "beta_expired",
        "clock_tamper",
        "killed",
    )


def is_license_operational() -> bool:
    """Licencia vigente: activada y no caducada (incluye modo dev ELIA_SKIP_LICENSE)."""
    st = get_license_status()
    if st.reason == "skip":
        return True
    return st.ok and st.reason in ("activated", "beta")


def get_entitlements() -> Dict[str, Any]:
    """Payload unificado para UI y API."""
    st = get_license_status()
    features = dict(st.features or get_tier_flags(TIER_BASIC))
    return entitlements_payload(
        tier=st.tier_name or TIER_BASIC,
        features=features,
        is_beta=st.is_beta,
        upgrade_email=st.upgrade_email,
    )


def get_license_status() -> LicenseStatus:
    all_features = get_tier_flags(TIER_BETA)
    all_legacy = legacy_modules_from_features(all_features)

    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "true", "yes"):
        return LicenseStatus(
            ok=True,
            reason="skip",
            activated=True,
            machine_fingerprint=get_machine_fingerprint(),
            message="Licencia omitida (ELIA_SKIP_LICENSE).",
            licensed_modules=all_legacy,
            tier_name=TIER_BETA,
            features=all_features,
        )

    if kill_switch_active():
        return LicenseStatus(
            ok=False,
            reason="killed",
            activated=False,
            machine_fingerprint=get_machine_fingerprint(),
            message="Esta instalación no puede iniciarse en este equipo.",
        )

    fp = get_machine_fingerprint()
    state = _load_effective_state()
    resolved = _resolve_license_from_state(state, fp)

    if resolved is not None:
        parsed, _activated_ts, exp_ts = resolved
        features = _licensed_features_dict(parsed)
        licensed_modules = _licensed_modules_dict(parsed)
        _sync_licensed_modules(parsed.mobile, parsed.legacy)

        if parsed.is_beta_global or parsed.tier == TIER_BETA:
            guard = _beta_guard_for_parsed(parsed)
            assert guard is not None
            st = _status_from_beta_guard(guard, fp)
            st.duration_code = parsed.duration if not parsed.is_beta_global else "BETA"
            return st

        if exp_ts is not None and time.time() > exp_ts:
            _clear_licensed_modules()
            left_label = DURATION_LABELS.get(parsed.duration, "limitada")
            return LicenseStatus(
                ok=False,
                reason="license_expired",
                activated=True,
                machine_fingerprint=fp,
                message=f"La licencia ({left_label}) ha caducado. Solicita una nueva clave.",
                expires_at=exp_ts,
                duration_code=parsed.duration,
                licensed_modules=licensed_modules,
                tier_name=parsed.tier,
                features=features,
            )

        dur_label = DURATION_LABELS.get(parsed.duration, "activada")
        tier_label = parsed.tier.replace("_", " ").title()
        mod_parts = []
        if licensed_modules.get("mobile_recording"):
            mod_parts.append("móvil")
        if licensed_modules.get("legacy_recording"):
            mod_parts.append("legacy")
        mod_txt = f" Módulos: {', '.join(mod_parts)}." if mod_parts else ""
        if exp_ts is not None:
            days_left = max(0.0, (exp_ts - time.time()) / 86400.0)
            msg = f"Plan {tier_label} ({dur_label}): quedan aprox. {days_left:.1f} día(s).{mod_txt}"
        else:
            msg = f"Plan {tier_label} ({dur_label}).{mod_txt}"
        return LicenseStatus(
            ok=True,
            reason="activated",
            activated=True,
            machine_fingerprint=fp,
            message=msg,
            expires_at=exp_ts,
            duration_code=parsed.duration,
            licensed_modules=licensed_modules,
            tier_name=parsed.tier,
            features=features,
        )

    if _distribution_channel() == "beta":
        guard = _beta_guard_for_parsed(None)
        assert guard is not None
        return _status_from_beta_guard(guard, fp)

    _clear_licensed_modules()
    return LicenseStatus(
        ok=False,
        reason="not_activated",
        activated=False,
        machine_fingerprint=fp,
        message=(
            "ELIA requiere una clave de activación. "
            "Configuración → Licencia (huella de equipo abajo)."
        ),
    )


def ensure_license_or_exit() -> None:
    """Al inicio: bloquea solo ante kill switch; la UI permite activar sin clave."""
    if (os.environ.get("ELIA_REVOKE_ON_START") or "").strip().lower() in ("1", "true", "yes"):
        revoke_license_local(clear_backups=True)
    try_activate_from_env()
    st = get_license_status()
    if st.reason == "killed":
        print(st.message, file=sys.stderr)
        sys.exit(2)


def try_activate_from_env() -> bool:
    key = (os.environ.get("ELIA_ACTIVATION_KEY") or "").strip()
    if not key:
        return False
    if verify_activation_key(key):
        return activate_with_key(key)
    return False


def revoke_license_local(*, clear_backups: bool = True) -> None:
    """
    Revocación suave (soporte interno / pruebas): borra activación local.
    La app sigue arrancando; jobs quedan bloqueados hasta nueva clave.
    """
    fp = get_machine_fingerprint()
    p = _state_path()
    try:
        if p.is_file():
            p.unlink()
    except OSError:
        _save_state({})

    if clear_backups:
        for path in _get_hidden_backup_paths():
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                continue
            except Exception:
                continue

    _clear_licensed_modules()
    del fp  # fingerprint unchanged; kept for callers that log after revoke
