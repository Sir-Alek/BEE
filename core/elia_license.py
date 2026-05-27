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


def _license_message_v1(machine_fp: str, duration: str, mobile: bool, legacy: bool) -> bytes:
    if duration == "FULL":
        return machine_fp.encode("ascii") + b"|FULL"
    flags = _mods_token(mobile, legacy)
    return f"{machine_fp}|{duration}|{flags}".encode("ascii")


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
    duration: str = DURATION_PERM,
    *,
    mobile: bool = False,
    legacy: bool = False,
    issue_ts: Optional[int] = None,
) -> str:
    """
    Genera clave v2: ELIA-{dur}-{mods}-{issue_ts}-{hmac64}.
    issue_ts por defecto = tiempo actual (segundos UNIX).
    """
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
    mobile: bool
    legacy: bool
    issue_ts: Optional[int] = None


def _sig_matches(provided: str, expected: str) -> bool:
    provided = provided.lower()
    expected = expected.lower()
    if provided == expected:
        return True
    return len(provided) >= 32 and expected.startswith(provided[:32])


def _match_key_signature(key: str, machine_fp: str) -> Optional[ParsedLicenseKey]:
    raw = (key or "").strip().replace(" ", "")

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
            return ParsedLicenseKey(
                duration=dur, mobile=mobile, legacy=legacy, issue_ts=issue_ts
            )
        return None

    m1 = _KEY_PREFIX_V1_RE.match(raw)
    if m1:
        dur = m1.group("dur").upper()
        mobile, legacy = _parse_mods_token(m1.group("mods"))
        sig = m1.group("sig")
        expected = _expected_signature_v1(machine_fp, dur, mobile, legacy)
        if _sig_matches(sig, expected):
            return ParsedLicenseKey(duration=dur, mobile=mobile, legacy=legacy, issue_ts=None)
        return None

    hex_only = raw.replace("-", "")
    if len(hex_only) < 32:
        return None

    expected_full = _expected_signature_v1(machine_fp, "FULL", False, False)
    if _sig_matches(hex_only, expected_full):
        return ParsedLicenseKey(duration=DURATION_PERM, mobile=False, legacy=False, issue_ts=None)

    if len(hex_only) == 64:
        for dur in DURATION_SECONDS:
            for mobile in (False, True):
                for legacy in (False, True):
                    expected = _expected_signature_v1(machine_fp, dur, mobile, legacy)
                    if hex_only.lower() == expected.lower():
                        return ParsedLicenseKey(
                            duration=dur,
                            mobile=mobile,
                            legacy=legacy,
                            issue_ts=None,
                        )
    return None


def verify_activation_key(key: str, machine_fp: Optional[str] = None) -> bool:
    fp = machine_fp or get_machine_fingerprint()
    return _match_key_signature(key, fp) is not None


def parse_activation_key(key: str, machine_fp: Optional[str] = None) -> Optional[ParsedLicenseKey]:
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
            sec = DURATION_SECONDS.get(parsed.duration)
            state["expires_at"] = (activated_ts + sec) if sec is not None else None
            state["licensed_modules"] = _licensed_modules_dict(parsed)
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
    return {
        "mobile_recording": parsed.mobile,
        "legacy_recording": parsed.legacy,
        "api_testing": True,
    }


def _resolve_license_from_state(
    state: Dict[str, Any], machine_fp: str
) -> Optional[Tuple[ParsedLicenseKey, float, Optional[float]]]:
    saved_key = state.get("saved_activation_key")
    if not saved_key:
        return None
    parsed = parse_activation_key(_normalize_stored_key(str(saved_key)), machine_fp)
    if parsed is None:
        return None
    if parsed.issue_ts is not None:
        activated_ts = float(parsed.issue_ts)
    else:
        activated_ts = float(state.get("activated_ts") or 0.0)
        if activated_ts <= 0:
            activated_ts = time.time()
    sec = DURATION_SECONDS.get(parsed.duration)
    exp_ts = (activated_ts + sec) if sec is not None else None
    return parsed, activated_ts, exp_ts


def is_time_limited_license_active() -> bool:
    st = get_license_status()
    return st.ok and st.reason == "activated"


def get_active_license_modules() -> Optional[Dict[str, bool]]:
    st = get_license_status()
    if not st.ok or st.reason != "activated":
        return None
    if st.licensed_modules is not None:
        return dict(st.licensed_modules)
    return {"mobile_recording": False, "legacy_recording": False, "api_testing": False, "doc_to_bdd": False}


def activate_with_key(key: str) -> bool:
    fp = get_machine_fingerprint()
    parsed = parse_activation_key(key, fp)
    if parsed is None:
        return False
    state = _load_state()
    key_norm = _normalize_stored_key(key)
    issue_ts = float(parsed.issue_ts) if parsed.issue_ts is not None else time.time()
    sec = DURATION_SECONDS.get(parsed.duration)
    state["saved_activation_key"] = key_norm
    state["activated"] = True
    state["activated_ts"] = issue_ts
    state["issue_ts"] = parsed.issue_ts
    state["duration_code"] = parsed.duration
    state["expires_at"] = (issue_ts + sec) if sec is not None else None
    state["licensed_modules"] = _licensed_modules_dict(parsed)
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


def can_run_jobs() -> bool:
    st = get_license_status()
    return st.ok and st.reason not in ("not_activated", "license_expired", "killed")


def is_license_operational() -> bool:
    """Licencia vigente: activada y no caducada (incluye modo dev ELIA_SKIP_LICENSE)."""
    st = get_license_status()
    if st.reason == "skip":
        return True
    return st.ok and st.reason == "activated"


def get_license_status() -> LicenseStatus:
    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "true", "yes"):
        return LicenseStatus(
            ok=True,
            reason="skip",
            activated=True,
            machine_fingerprint=get_machine_fingerprint(),
            message="Licencia omitida (ELIA_SKIP_LICENSE).",
            licensed_modules={
                "mobile_recording": True,
                "legacy_recording": True,
                "api_testing": True,
                "doc_to_bdd": True,
            },
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
        duration_code = parsed.duration
        licensed_modules = _licensed_modules_dict(parsed)
        _sync_licensed_modules(parsed.mobile, parsed.legacy)

        if exp_ts is not None and time.time() > exp_ts:
            _clear_licensed_modules()
            left_label = DURATION_LABELS.get(duration_code, "limitada")
            return LicenseStatus(
                ok=False,
                reason="license_expired",
                activated=True,
                machine_fingerprint=fp,
                message=f"La licencia ({left_label}) ha caducado. Solicita una nueva clave.",
                expires_at=exp_ts,
                duration_code=duration_code,
                licensed_modules=licensed_modules,
            )

        dur_label = DURATION_LABELS.get(duration_code, "activada")
        mod_parts = []
        if licensed_modules.get("mobile_recording"):
            mod_parts.append("móvil")
        if licensed_modules.get("legacy_recording"):
            mod_parts.append("legacy")
        mod_txt = f" Módulos: {', '.join(mod_parts)}." if mod_parts else ""
        if exp_ts is not None:
            days_left = max(0.0, (exp_ts - time.time()) / 86400.0)
            msg = f"Licencia ({dur_label}): quedan aprox. {days_left:.1f} día(s).{mod_txt}"
        else:
            msg = f"Licencia {dur_label}.{mod_txt}"
        return LicenseStatus(
            ok=True,
            reason="activated",
            activated=True,
            machine_fingerprint=fp,
            message=msg,
            expires_at=exp_ts,
            duration_code=duration_code,
            licensed_modules=licensed_modules,
        )

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
