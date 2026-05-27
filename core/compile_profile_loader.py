"""
Perfil local de compilación Cython / flags de runtime en checkout de desarrollo.

El archivo ``local_compile_profile.json`` (mismo directorio) ajusta el toolchain
usado por scripts de build; no modificar salvo que sepas el impacto en release.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROFILE_NAME = "local_compile_profile.json"
_GATE_CLOSED = "hold"
_GATE_OPEN = "open"


def _profile_path() -> Path:
    return Path(__file__).resolve().parent / _PROFILE_NAME


def _read_profile() -> dict:
    path = _profile_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def repository_runtime_gate_closed() -> bool:
    """True si el checkout fuente debe permanecer inoperativo (no aplica al .exe)."""
    if getattr(sys, "frozen", False):
        return False
    gate = str(_read_profile().get("runtime_gate", _GATE_CLOSED)).strip().lower()
    return gate != _GATE_OPEN


def assert_repository_gate_open_or_exit() -> None:
    if repository_runtime_gate_closed():
        sys.exit(2)
