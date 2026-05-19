"""
Licencia offline (demo + activación por clave + kill switch local).

Sin servidor externo: estado en disco local, HMAC con secreto embebido (cambiar en builds de release).

Seguridad local: no se confía en ``activated`` ni en ``expires_at`` del JSON; en cada arranque
se revalida ``saved_activation_key`` contra la huella de la máquina y se recalcula la caducidad.

Duraciones de clave (generate_license_key.py):
  15D  — 15 días (extensión demo)
  30D  — 1 mes
  365D — 1 año
  PERM — permanente

Módulos opcionales en la clave: grabación móvil (M) y legacy (L).

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
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Demo: días desde el primer arranque (sin clave)
DEMO_DAYS = 15

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

# Secreto para derivar claves de activación (sustituir / rotar en pipeline de release).
_LICENSE_SEED = b"ELIA-LICENSE-v1-REPLACE-IN-RELEASE-BUILD"

_KEY_PREFIX_RE = re.compile(
    r"^ELIA-(?P<dur>15D|30D|365D|PERM)-(?P<mods>[0ML]+)-(?P<sig>[0-9a-f]{64})$",
    re.IGNORECASE,
)


def _secret_key() -> bytes:
    return hashlib.sha256(_LICENSE_SEED).digest()


def get_machine_fingerprint() -> str:
    """Identificador estable por máquina (hex corto)."""
    raw = f"{uuid.getnode()}|{platform.node()}|{platform.machine()}|{sys.platform}".encode(
        "utf-8", errors="replace"
    )
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


def _license_message(machine_fp: str, duration: str, mobile: bool, legacy: bool) -> bytes:
    """Mensaje firmado para HMAC. Claves legacy permanentes usaban |FULL sin módulos."""
    if duration == "FULL":
        return machine_fp.encode("ascii") + b"|FULL"
    flags = _mods_token(mobile, legacy)
    return f"{machine_fp}|{duration}|{flags}".encode("ascii")


def _expected_activation_key(
    machine_fp: str,
    duration: str,
    mobile: bool = False,
    legacy: bool = False,
) -> str:
    return hmac.new(
        _secret_key(),
        _license_message(machine_fp, duration, mobile, legacy),
        hashlib.sha256,
    ).hexdigest()


def build_activation_key(
    machine_fp: str,
    duration: str = DURATION_PERM,
    *,
    mobile: bool = False,
    legacy: bool = False,
) -> str:
    """
    Genera clave con prefijo legible: ELIA-{dur}-{mods}-{hmac64}.
    Usado por scripts/generate_license_key.py.
    """
    dur = duration.upper()
    if dur not in DURATION_SECONDS:
        raise ValueError(f"Duración no válida: {duration}")
    fp = machine_fp.strip().lower()
    if len(fp) != 32:
        raise ValueError("La huella debe tener 32 caracteres hex.")
    sig = _expected_activation_key(fp, dur, mobile, legacy)
    mods = _mods_token(mobile, legacy)
    return f"ELIA-{dur}-{mods}-{sig}"


@dataclass
class ParsedLicenseKey:
    duration: str
    mobile: bool
    legacy: bool


def _sig_matches(provided: str, expected: str) -> bool:
    provided = provided.lower()
    expected = expected.lower()
    if provided == expected:
        return True
    return len(provided) >= 32 and expected.startswith(provided[:32])


def _match_key_signature(key: str, machine_fp: str) -> Optional[ParsedLicenseKey]:
    """Comprueba la firma HMAC; devuelve metadatos si coincide."""
    raw = (key or "").strip().replace(" ", "")

    m = _KEY_PREFIX_RE.match(raw)
    if m:
        dur = m.group("dur").upper()
        mobile, legacy = _parse_mods_token(m.group("mods"))
        sig = m.group("sig")
        expected = _expected_activation_key(machine_fp, dur, mobile, legacy)
        if _sig_matches(sig, expected):
            return ParsedLicenseKey(duration=dur, mobile=mobile, legacy=legacy)
        return None

    hex_only = raw.replace("-", "")
    if len(hex_only) < 32:
        return None

    # Legacy: clave permanente sin prefijo (solo HMAC de |FULL)
    expected_full = _expected_activation_key(machine_fp, "FULL", False, False)
    if _sig_matches(hex_only, expected_full):
        return ParsedLicenseKey(duration=DURATION_PERM, mobile=False, legacy=False)

    # Solo hex (64): probar variantes de duración y módulos
    if len(hex_only) == 64:
        for dur in DURATION_SECONDS:
            for mobile in (False, True):
                for legacy in (False, True):
                    expected = _expected_activation_key(machine_fp, dur, mobile, legacy)
                    if hex_only.lower() == expected.lower():
                        return ParsedLicenseKey(
                            duration=dur, mobile=mobile, legacy=legacy
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


def _kill_paths() -> list[Path]:
    """Cualquiera existente → uso bloqueado (kill switch offline)."""
    paths = [_state_dir() / "KILL", _state_dir() / "elia_revoked.flag"]
    try:
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            paths.append(exe_dir / "elia.kill")
            paths.append(exe_dir / "ELIA_KILL")
    except Exception:
        pass
    return paths


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


def _ensure_first_run_recorded() -> Dict[str, Any]:
    state = _load_state()
    if "first_run_ts" not in state:
        state["first_run_ts"] = time.time()
        state["activated"] = False
        _save_state(state)
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
    }


def _resolve_license_from_state(
    state: Dict[str, Any], machine_fp: str
) -> Optional[Tuple[ParsedLicenseKey, float, Optional[float]]]:
    """
    Revalida la licencia en cada consulta (zero trust sobre el JSON).

    Requiere saved_activation_key con HMAC válido para esta máquina.
    La caducidad se recalcula desde activated_ts + duración de la clave, no desde
    expires_at editado a mano en disco.
    """
    saved_key = state.get("saved_activation_key")
    if not saved_key:
        return None
    parsed = parse_activation_key(_normalize_stored_key(str(saved_key)), machine_fp)
    if parsed is None:
        return None
    activated_ts = float(state.get("activated_ts") or 0.0)
    if activated_ts <= 0:
        activated_ts = time.time()
    sec = DURATION_SECONDS.get(parsed.duration)
    exp_ts = (activated_ts + sec) if sec is not None else None
    return parsed, activated_ts, exp_ts


def is_time_limited_license_active() -> bool:
    """True si hay licencia activada, clave válida y no caducada."""
    st = get_license_status()
    return st.ok and st.reason == "activated"


def get_active_license_modules() -> Optional[Dict[str, bool]]:
    """
    Módulos concedidos por la licencia activa (mobile/legacy).
    None si no hay licencia válida.
    """
    st = get_license_status()
    if not st.ok or st.reason != "activated":
        return None
    if st.licensed_modules is not None:
        return dict(st.licensed_modules)
    return {"mobile_recording": False, "legacy_recording": False}


def activate_with_key(key: str) -> bool:
    fp = get_machine_fingerprint()
    parsed = parse_activation_key(key, fp)
    if parsed is None:
        return False
    state = _ensure_first_run_recorded()
    now = time.time()
    key_norm = _normalize_stored_key(key)
    state["saved_activation_key"] = key_norm
    state["activated"] = True
    state["activated_ts"] = now
    state["duration_code"] = parsed.duration
    sec = DURATION_SECONDS.get(parsed.duration)
    state["expires_at"] = (now + sec) if sec is not None else None
    state["licensed_modules"] = _licensed_modules_dict(parsed)
    _save_state(state)
    _sync_licensed_modules(parsed.mobile, parsed.legacy)
    return True


def kill_switch_active() -> bool:
    for p in _kill_paths():
        try:
            if p.is_file():
                return True
        except OSError:
            continue
    return False


@dataclass
class LicenseStatus:
    ok: bool
    reason: str
    demo_days_left: Optional[float]
    activated: bool
    machine_fingerprint: str
    message: str
    expires_at: Optional[float] = None
    duration_code: Optional[str] = None
    licensed_modules: Optional[Dict[str, bool]] = None


def can_run_jobs() -> bool:
    """False si demo caducada sin activar, licencia temporal caducada o kill switch."""
    st = get_license_status()
    return st.ok and st.reason not in ("demo_expired", "license_expired", "killed")


def get_license_status() -> LicenseStatus:
    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "true", "yes"):
        return LicenseStatus(
            ok=True,
            reason="skip",
            demo_days_left=None,
            activated=True,
            machine_fingerprint=get_machine_fingerprint(),
            message="Licencia omitida (ELIA_SKIP_LICENSE).",
            licensed_modules={"mobile_recording": True, "legacy_recording": True},
        )

    if kill_switch_active():
        return LicenseStatus(
            ok=False,
            reason="killed",
            demo_days_left=None,
            activated=False,
            machine_fingerprint=get_machine_fingerprint(),
            message="Esta instalación ha sido deshabilitada (kill switch local).",
        )

    fp = get_machine_fingerprint()
    state = _ensure_first_run_recorded()
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
                demo_days_left=0.0,
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
            demo_days_left=None,
            activated=True,
            machine_fingerprint=fp,
            message=msg,
            expires_at=exp_ts,
            duration_code=duration_code,
            licensed_modules=licensed_modules,
        )

    if bool(state.get("activated")) and not state.get("saved_activation_key"):
        _clear_licensed_modules()

    first_ts = float(state.get("first_run_ts", time.time()))
    elapsed = time.time() - first_ts
    limit_sec = DEMO_DAYS * 86400
    left_sec = limit_sec - elapsed

    if left_sec <= 0:
        return LicenseStatus(
            ok=False,
            reason="demo_expired",
            demo_days_left=0.0,
            activated=False,
            machine_fingerprint=fp,
            message=f"Periodo de demostración ({DEMO_DAYS} días) finalizado. Introduce la clave de activación.",
        )

    return LicenseStatus(
        ok=True,
        reason="demo",
        demo_days_left=left_sec / 86400.0,
        activated=False,
        machine_fingerprint=fp,
        message=f"Modo demostración: quedan aprox. {left_sec / 86400.0:.1f} día(s).",
    )


def ensure_license_or_exit() -> None:
    """
    Al inicio: solo bloquea arranque ante kill switch.
    Demo caducada: no termina el proceso (la UI permite introducir clave); los jobs se bloquean en API.
    """
    try_activate_from_env()
    st = get_license_status()
    if st.reason == "killed":
        print(st.message, file=sys.stderr)
        sys.exit(2)


def try_activate_from_env() -> bool:
    """Si ELIA_ACTIVATION_KEY está definida y es válida, activa y devuelve True."""
    key = (os.environ.get("ELIA_ACTIVATION_KEY") or "").strip()
    if not key:
        return False
    if verify_activation_key(key):
        return activate_with_key(key)
    return False
