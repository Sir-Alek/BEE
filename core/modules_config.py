"""
Building Blocks — motor de módulos por licencia.

Cada módulo adicional (mobile_recording, legacy_recording, doc_to_bdd) se activa
escribiendo un modules.json en el directorio de estado local de ELIA.

Estructura de modules.json:
  {
    "mobile_recording": false,
    "legacy_recording": false,
    "doc_to_bdd": true
  }

En desarrollo se puede usar ELIA_SKIP_LICENSE=1 o ELIA_MODULE_<NAME>=1 para
forzar un módulo habilitado sin archivo.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Dict

# Módulos disponibles con su estado por defecto.
# doc_to_bdd viene habilitado por defecto porque forma parte de la licencia base.
_DEFAULTS: Dict[str, bool] = {
    "mobile_recording": False,
    "legacy_recording": False,
    "doc_to_bdd": True,
}

# Secreto para validar claves de activación de módulos individuales.
# Debe coincidir con el generador de claves del backoffice.
_MODULE_SEED = b"ELIA-MODULE-v1-REPLACE-IN-RELEASE-BUILD"


def _secret_key() -> bytes:
    return hashlib.sha256(_MODULE_SEED).digest()


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    elia = Path(base) / "ELIA"
    elia.mkdir(parents=True, exist_ok=True)
    return elia


def modules_config_path() -> Path:
    return _state_dir() / "modules.json"


def _load_modules() -> Dict[str, bool]:
    p = modules_config_path()
    data: Dict[str, bool] = dict(_DEFAULTS)
    if p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if k in _DEFAULTS:
                        data[k] = bool(v)
        except Exception:
            pass
    return data


def _save_modules(data: Dict[str, bool]) -> None:
    p = modules_config_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _env_override(name: str) -> bool | None:
    """Devuelve True/False si hay variable de entorno, None si no."""
    env_key = f"ELIA_MODULE_{name.upper()}"
    val = (os.environ.get(env_key) or "").strip().lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "true", "yes"):
        # En modo dev sin licencia, todos los módulos están habilitados.
        return True
    return None


def is_module_enabled(name: str) -> bool:
    """Devuelve True si el módulo está habilitado (env override > modules.json > default)."""
    override = _env_override(name)
    if override is not None:
        return override
    data = _load_modules()
    return data.get(name, _DEFAULTS.get(name, False))


def list_modules() -> Dict[str, bool]:
    """Devuelve el estado de todos los módulos respetando overrides de entorno."""
    data = _load_modules()
    result: Dict[str, bool] = {}
    for name in _DEFAULTS:
        override = _env_override(name)
        result[name] = override if override is not None else data.get(name, False)
    return result


def _expected_module_key(module_name: str, machine_fp: str) -> str:
    """Clave HMAC para activar un módulo específico en una máquina concreta."""
    msg = f"{module_name}|{machine_fp}|MODULE".encode("ascii", errors="replace")
    return hmac.new(_secret_key(), msg, hashlib.sha256).hexdigest()


def verify_module_key(module_name: str, key: str, machine_fp: str | None = None) -> bool:
    """Verifica una clave de activación de módulo (acepta clave completa o primeros 32 hex)."""
    from core.elia_license import get_machine_fingerprint
    key = (key or "").strip().replace(" ", "").replace("-", "")
    if len(key) < 32:
        return False
    fp = machine_fp or get_machine_fingerprint()
    expected = _expected_module_key(module_name, fp)
    if key.lower() == expected.lower():
        return True
    if len(key) >= 32 and expected.lower().startswith(key.lower()[:32]):
        return True
    return False


def enable_module(module_name: str, key: str) -> bool:
    """Activa un módulo si la clave es válida. Devuelve True si se activó."""
    if module_name not in _DEFAULTS:
        return False
    if not verify_module_key(module_name, key):
        return False
    data = _load_modules()
    data[module_name] = True
    _save_modules(data)
    return True


def disable_module(module_name: str) -> None:
    """Deshabilita un módulo (operación de administración)."""
    data = _load_modules()
    data[module_name] = False
    _save_modules(data)
