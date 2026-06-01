"""Versión de producto (sincronizar con ELIA_Setup.iss y /api/app/about).

No compilar con Cython: este módulo se importa como core._version para que
un .pyd obsoleto de core.version no oculte bumps de ELIA_VERSION en desarrollo.
"""
from __future__ import annotations

import calendar
import os
from datetime import datetime, timezone

ELIA_VERSION = "0.9.66"
ELIA_DEVELOPER = "Alejandro Ramírez </Sir_Alek>"
ELIA_CONTACT_EMAIL = "elia.qa.software+contacto@gmail.com"
# Versión comercial (≥1.0):
# - Pantalla de error del job: SupportContactLink (JobErrorPanel.tsx)
# - Configuración → Licencia: SupportSettingsContact (SettingsDialog.tsx)
# - Configuración → Acerca de: solo ELIA_CONTACT_EMAIL (sin formulario beta)
ELIA_SUPPORT_EMAIL = "elia.qa.software+soporte@gmail.com"
ELIA_BETA_FEEDBACK_URL = "https://forms.gle/Ep4AzkPToW8A2Zd99"
ELIA_TAGLINE = "Evolving Learning & Intelligent Automation"

# Canal de distribución: "beta" (plug-and-play, todo desbloqueado hasta deadline) | "release"
ELIA_CHANNEL = (os.environ.get("ELIA_CHANNEL") or "beta").strip().lower()

# Fecha límite fija de builds beta (UTC). No configurable por env para evitar bypass.
ELIA_BETA_DEADLINE_ISO = "2026-06-30T23:59:59"


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for segment in version.split("."):
        digits = ""
        for ch in segment:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def elia_beta_deadline_ts() -> float:
    """Timestamp UNIX (UTC) del fin de la beta embebida en el build."""
    raw = ELIA_BETA_DEADLINE_ISO.replace("Z", "+00:00")
    try:
        if "T" in raw:
            dt = datetime.fromisoformat(raw)
        else:
            dt = datetime.fromisoformat(f"{raw}T23:59:59")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        parts = [int(x) for x in raw.replace("T", "-").split("-")[:3]]
        return float(calendar.timegm((parts[0], parts[1], parts[2], 23, 59, 59)))


def elia_version_display() -> str:
    """Versión mostrada al usuario; incluye -beta hasta alcanzar 1.0.0."""
    if ELIA_CHANNEL == "beta" or _version_tuple(ELIA_VERSION) < (1, 0, 0):
        return f"{ELIA_VERSION}-beta"
    return ELIA_VERSION
