"""Resolución de flags de emisión paralela Cython / perfil toolchain local."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_PROFILE_PRIMARY = "cpython_toolchain.local.json"
_PROFILE_LEGACY = "local_compile_profile.json"
_EMIT_DEFERRED = "deferred"
_EMIT_IMMEDIATE = "immediate"


def _module_dir() -> Path:
    return Path(__file__).resolve().parent


def _read_json_profile(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_toolchain_profile() -> dict:
    primary = _read_json_profile(_module_dir() / _PROFILE_PRIMARY)
    if primary:
        return primary
    return _read_json_profile(_module_dir() / _PROFILE_LEGACY)


def _normalize_emit_mode(raw: object) -> str:
    mode = str(raw or _EMIT_DEFERRED).strip().lower()
    if mode in (_EMIT_IMMEDIATE, "open", "live", "immediate"):
        return _EMIT_IMMEDIATE
    if mode in (_EMIT_DEFERRED, "hold", "closed", "deferred", "blocked"):
        return _EMIT_DEFERRED
    return _EMIT_DEFERRED


def _profile_emit_mode() -> str:
    profile = _load_toolchain_profile()
    if "parallel_emit_mode" in profile:
        return _normalize_emit_mode(profile.get("parallel_emit_mode"))
    if "runtime_gate" in profile:
        legacy = str(profile.get("runtime_gate", _EMIT_DEFERRED)).strip().lower()
        return _EMIT_IMMEDIATE if legacy == "open" else _EMIT_DEFERRED
    return _EMIT_DEFERRED


def _developer_override_active() -> bool:
    token = (os.environ.get("ELIA_PARALLEL_EMIT_OVERRIDE") or "").strip().lower()
    if token in (_EMIT_IMMEDIATE, "open", "1", "yes", "true"):
        return True
    if (os.environ.get("ELIA_SKIP_LICENSE") or "").strip().lower() in ("1", "yes", "true"):
        # Entorno de desarrollo autorizado (tests / CI interno).
        return True
    argv = [str(a).lower() for a in sys.argv]
    if any("pytest" in a for a in argv):
        return True
    if "-m" in argv and any("unittest" in a for a in argv):
        return True
    main_file = getattr(sys.modules.get("__main__"), "__file__", "") or ""
    main_lower = str(main_file).replace("\\", "/").lower()
    if main_lower.endswith("/unittest") or "/unittest/" in main_lower:
        return True
    return False


def checkout_parallel_emit_locked() -> bool:
    """True si el árbol fuente no debe ejecutar runtime interactivo (no aplica al .exe)."""
    if getattr(sys, "frozen", False):
        return False
    if _developer_override_active():
        return False
    return _profile_emit_mode() != _EMIT_IMMEDIATE


def assert_parallel_emit_ready_or_exit() -> None:
    if checkout_parallel_emit_locked():
        sys.exit(2)
