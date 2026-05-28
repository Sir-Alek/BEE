"""Versión de producto (sincronizar con ELIA_Setup.iss y /api/app/about).

No compilar con Cython: este módulo se importa como core._version para que
un .pyd obsoleto de core.version no oculte bumps de ELIA_VERSION en desarrollo.
"""

ELIA_VERSION = "0.9.51"
ELIA_DEVELOPER = "Alejandro Ramírez </Sir_Alek>"
ELIA_CONTACT_EMAIL = "elia.qa.software+contacto@gmail.com"
# Versión comercial (≥1.0):
# - Pantalla de error del job: SupportContactLink (JobErrorPanel.tsx)
# - Configuración → Licencia: SupportSettingsContact (SettingsDialog.tsx)
# - Configuración → Acerca de: solo ELIA_CONTACT_EMAIL (sin formulario beta)
ELIA_SUPPORT_EMAIL = "elia.qa.software+soporte@gmail.com"
ELIA_BETA_FEEDBACK_URL = "https://forms.gle/LxrfHressWy48jDZ6"
ELIA_TAGLINE = "Evolving Learning & Intelligent Automation"


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


def elia_version_display() -> str:
    """Versión mostrada al usuario; incluye -beta hasta alcanzar 1.0.0."""
    if _version_tuple(ELIA_VERSION) < (1, 0, 0):
        return f"{ELIA_VERSION}-beta"
    return ELIA_VERSION
