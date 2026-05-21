"""
Building Blocks — módulos atados estrictamente a la licencia activa.

Sin licencia vigente (caducada, no activada o revocada): todos los módulos false,
incluido doc_to_bdd.

Con licencia vigente:
  - doc_to_bdd: true (producto base)
  - mobile_recording / legacy_recording: flags M/L de la clave activa

Desarrollo:
  - ELIA_SKIP_LICENSE=1 → todos los módulos true
  - ELIA_MODULE_<NAME>=1|0 → override puntual

Las claves de módulo individuales (enable_module) no tienen efecto en producción.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict

_MODULE_NAMES: Dict[str, bool] = {
    "mobile_recording": False,
    "legacy_recording": False,
    "doc_to_bdd": False,
}


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    elia = Path(base) / "ELIA"
    elia.mkdir(parents=True, exist_ok=True)
    return elia


def modules_config_path() -> Path:
    """Ruta legacy (modules.json ya no define entitlements en producción)."""
    return _state_dir() / "modules.json"


def _env_override(name: str) -> bool | None:
    env_key = f"ELIA_MODULE_{name.upper()}"
    val = (os.environ.get(env_key) or "").strip().lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "true", "yes"):
        return True
    return None


def _modules_from_license() -> Dict[str, bool]:
    try:
        from core.elia_license import get_active_license_modules, is_license_operational

        if not is_license_operational():
            return dict(_MODULE_NAMES)
        lic = get_active_license_modules()
        if lic is None:
            return dict(_MODULE_NAMES)
        return {
            "mobile_recording": bool(lic.get("mobile_recording")),
            "legacy_recording": bool(lic.get("legacy_recording")),
            "doc_to_bdd": True,
        }
    except Exception:
        return dict(_MODULE_NAMES)


def apply_licensed_modules(*, mobile: bool, legacy: bool) -> None:
    """Compatibilidad: entitlements vienen de la clave activa, no de modules.json."""
    del mobile, legacy


def is_module_enabled(name: str) -> bool:
    if name not in _MODULE_NAMES:
        return False
    override = _env_override(name)
    if override is not None:
        return override
    return bool(_modules_from_license().get(name, False))


def list_modules() -> Dict[str, bool]:
    resolved = _modules_from_license()
    result: Dict[str, bool] = {}
    for name in _MODULE_NAMES:
        override = _env_override(name)
        if override is not None:
            result[name] = override
        else:
            result[name] = bool(resolved.get(name, False))
    return result


def enable_module(module_name: str, key: str) -> bool:
    """Sin efecto en producción (entitlements solo vía licencia principal)."""
    del module_name, key
    return False


def disable_module(module_name: str) -> None:
    """Sin efecto en producción."""
    del module_name


def verify_module_key(module_name: str, key: str, machine_fp: str | None = None) -> bool:
    """Deprecated: claves individuales deshabilitadas en producción."""
    del module_name, key, machine_fp
    return False
