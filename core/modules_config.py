"""
Building Blocks — módulos atados estrictamente a la licencia activa.

Sin licencia vigente (caducada, no activada o revocada): todos los módulos false.

Con licencia vigente: flags resueltos desde tier/features de la clave activa.

Desarrollo:
  - ELIA_SKIP_LICENSE=1 → todos los módulos true
  - ELIA_MODULE_<NAME>=1|0 → override puntual (legacy)
  - ELIA_FEATURE_<NAME>=1|0 → override puntual (granular)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

from core.entitlements import FEATURE_KEYS, TIER_BASIC, get_tier_flags, legacy_modules_from_features

_LEGACY_MODULE_NAMES: Dict[str, bool] = {
    "mobile_recording": False,
    "legacy_recording": False,
    "doc_to_bdd": False,
    "api_testing": False,
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


def _feature_env_override(name: str) -> bool | None:
    env_key = f"ELIA_FEATURE_{name.upper()}"
    val = (os.environ.get(env_key) or "").strip().lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "true", "yes"):
        return True
    return None


def _features_from_license() -> Dict[str, bool]:
    try:
        from core.elia_license import get_active_license_features, get_license_status, is_license_operational

        if not is_license_operational():
            return get_tier_flags(TIER_BASIC)
        feats = get_active_license_features()
        if feats is None:
            st = get_license_status()
            if st.features:
                return dict(st.features)
            return get_tier_flags(TIER_BASIC)
        return dict(feats)
    except Exception:
        return get_tier_flags(TIER_BASIC)


def _resolved_features() -> Dict[str, bool]:
    base = _features_from_license()
    out = dict(base)
    for key in FEATURE_KEYS:
        override = _feature_env_override(key)
        if override is not None:
            out[key] = override
    return out


def apply_licensed_modules(*, mobile: bool, legacy: bool) -> None:
    """Compatibilidad: entitlements vienen de la clave activa, no de modules.json."""
    del mobile, legacy


def is_feature_enabled(name: str) -> bool:
    if name not in FEATURE_KEYS:
        return False
    return bool(_resolved_features().get(name, False))


def is_module_enabled(name: str) -> bool:
    if name in FEATURE_KEYS:
        return is_feature_enabled(name)
    if name not in _LEGACY_MODULE_NAMES:
        return False
    override = _env_override(name)
    if override is not None:
        return override
    legacy = legacy_modules_from_features(_resolved_features())
    return bool(legacy.get(name, False))


def list_modules() -> Dict[str, Any]:
    features = _resolved_features()
    legacy = legacy_modules_from_features(features)
    try:
        from core.elia_license import get_entitlements

        ent = get_entitlements()
    except Exception:
        ent = {
            "tier": TIER_BASIC,
            "tier_label": "Basic",
            "is_beta": False,
            "upgrade_email": "",
        }
    result: Dict[str, Any] = {
        "tier": ent.get("tier", TIER_BASIC),
        "tier_label": ent.get("tier_label", "Basic"),
        "is_beta": bool(ent.get("is_beta")),
        "upgrade_email": ent.get("upgrade_email", ""),
        "features": dict(features),
    }
    for name in _LEGACY_MODULE_NAMES:
        override = _env_override(name)
        if override is not None:
            result[name] = override
        else:
            result[name] = bool(legacy.get(name, False))
    for key in FEATURE_KEYS:
        if key not in result:
            result[key] = bool(features.get(key, False))
    return result


def get_api_module_limits() -> Dict[str, Any]:
    """Límites documentados del módulo api_testing (carga y suites)."""
    return {
        "max_load_users": 500,
        "max_load_spawn_rate": 100.0,
        "max_suite_scenarios": 200,
        "evidence_opt_in": True,
    }


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
