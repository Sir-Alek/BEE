"""
Licencia offline (demo + activación por clave + kill switch local).

Sin servidor externo: estado en disco local, HMAC con secreto embebido (cambiar en builds de release).

Variables de entorno (desarrollo / soporte):
  ELIA_SKIP_LICENSE=1  — omite comprobación (no usar en entregas a cliente).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Demo: días desde el primer arranque
DEMO_DAYS = 15

# Secreto para derivar claves de activación (sustituir / rotar en pipeline de release).
_LICENSE_SEED = b"ELIA-LICENSE-v1-REPLACE-IN-RELEASE-BUILD"


def _secret_key() -> bytes:
    return hashlib.sha256(_LICENSE_SEED).digest()


def get_machine_fingerprint() -> str:
    """Identificador estable por máquina (hex corto)."""
    raw = f"{uuid.getnode()}|{platform.node()}|{platform.machine()}|{sys.platform}".encode(
        "utf-8", errors="replace"
    )
    return hashlib.sha256(raw).hexdigest()[:32]


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


def _expected_activation_key(machine_fp: str) -> str:
    """Clave de activación completa esperada para esta máquina (hex 64 chars)."""
    return hmac.new(
        _secret_key(),
        machine_fp.encode("ascii") + b"|FULL",
        hashlib.sha256,
    ).hexdigest()


def verify_activation_key(key: str, machine_fp: Optional[str] = None) -> bool:
    key = (key or "").strip().replace(" ", "").replace("-", "")
    if len(key) < 32:
        return False
    fp = machine_fp or get_machine_fingerprint()
    expected = _expected_activation_key(fp)
    # Aceptar clave completa o primeros 32 hex (comodidad)
    if key.lower() == expected.lower():
        return True
    if len(key) >= 32 and expected.lower().startswith(key.lower()[:32]):
        return True
    return False


def activate_with_key(key: str) -> bool:
    if not verify_activation_key(key):
        return False
    state = _ensure_first_run_recorded()
    state["activated"] = True
    state["activated_ts"] = time.time()
    _save_state(state)
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


def can_run_jobs() -> bool:
    """False si demo caducada sin activar o kill switch."""
    st = get_license_status()
    if not st.ok:
        return False
    if st.reason == "demo" and not st.activated:
        return True
    if st.reason == "activated" or st.reason == "skip":
        return True
    return False


def get_license_status() -> LicenseStatus:
    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "true", "yes"):
        return LicenseStatus(
            ok=True,
            reason="skip",
            demo_days_left=None,
            activated=True,
            machine_fingerprint=get_machine_fingerprint(),
            message="Licencia omitida (ELIA_SKIP_LICENSE).",
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
    activated = bool(state.get("activated"))

    if activated:
        return LicenseStatus(
            ok=True,
            reason="activated",
            demo_days_left=None,
            activated=True,
            machine_fingerprint=fp,
            message="Licencia activada.",
        )

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
