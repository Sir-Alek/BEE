"""
Protección de caducidad beta: reloj de red + ancla local anti-retroceso.

Consultado al validar licencia beta (canal beta o clave global).
"""
from __future__ import annotations

import calendar
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core._version import ELIA_BETA_DEADLINE_ISO, elia_beta_deadline_ts


@dataclass
class BetaGuardResult:
    ok: bool
    reason: str
    message: str
    effective_now: float
    deadline_ts: float


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    elia = Path(base) / "ELIA"
    elia.mkdir(parents=True, exist_ok=True)
    return elia


def _anchor_path() -> Path:
    return _state_dir() / ".beta_time_anchor"


def _read_anchor() -> Optional[float]:
    path = _anchor_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            ts = float(data.get("last_run_time", 0))
            return ts if ts > 0 else None
    except Exception:
        return None
    return None


def _write_anchor(now: float) -> None:
    path = _anchor_path()
    prev = _read_anchor()
    stored = max(now, prev or 0.0)
    payload = {"v": 1, "last_run_time": stored}
    try:
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    except OSError:
        return
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)
        except Exception:
            pass


def record_beta_session_checkpoint() -> None:
    """Persiste timestamp al cerrar o tras operación exitosa (beta)."""
    _write_anchor(time.time())


def _fetch_network_time(timeout_sec: float = 2.5) -> Optional[float]:
    urls = (
        "https://www.google.com",
        "https://github.com",
    )
    for url in urls:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                date_hdr = resp.headers.get("Date")
                if not date_hdr:
                    continue
                dt = parsedate_to_datetime(date_hdr)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
        except Exception:
            continue
    return None


def _effective_now() -> Tuple[float, str]:
    network = _fetch_network_time()
    if network is not None:
        return network, "network"
    return time.time(), "local"


def check_beta_expiration(*, extra_deadline_ts: Optional[float] = None) -> BetaGuardResult:
    """
    Valida caducidad beta y detecta retroceso de reloj offline.

    extra_deadline_ts: límite de clave global beta (min con deadline de build).
    """
    build_deadline = elia_beta_deadline_ts()
    deadline = build_deadline
    if extra_deadline_ts is not None:
        deadline = min(deadline, extra_deadline_ts)

    now, source = _effective_now()
    anchor = _read_anchor()

    if anchor is not None and now + 300 < anchor:
        return BetaGuardResult(
            ok=False,
            reason="clock_tamper",
            message=(
                "Se detectó manipulación del reloj del sistema. "
                "Esta versión beta no puede continuar."
            ),
            effective_now=now,
            deadline_ts=deadline,
        )

    if now > deadline:
        return BetaGuardResult(
            ok=False,
            reason="beta_expired",
            message=(
                "Gracias por participar en la beta de ELIA. Esta versión ha caducado. "
                f"Para continuar, adquiere tu suscripción: {ELIA_BETA_DEADLINE_ISO}"
            ),
            effective_now=now,
            deadline_ts=deadline,
        )

    _write_anchor(now)
    return BetaGuardResult(
        ok=True,
        reason="beta_active" if source == "network" else "beta_active_offline",
        message="Beta activa.",
        effective_now=now,
        deadline_ts=deadline,
    )


def beta_expired_user_message(contact_email: str) -> str:
    return (
        "Gracias por participar en la beta de ELIA. Esta versión ha caducado.\n\n"
        "Para continuar optimizando tus flujos de trabajo y automatizaciones "
        f"con la versión completa, adquiere tu suscripción aquí:\n{contact_email}"
    )
