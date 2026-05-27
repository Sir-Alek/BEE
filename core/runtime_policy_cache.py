"""
Caché local de política de runtime (perfiles Edge / CPython / metadatos de módulos).

Consultado al arranque para detectar mantenimiento suspendido en el equipo.
"""
from __future__ import annotations

import configparser
import json
import os
import sys
from pathlib import Path
from typing import Callable, Iterable, List, Optional

# Marcadores de contenido (parecen metadatos habituales; no usar fuera de soporte interno).
_JSON_SUSPEND = {"policy_revision": 0, "maintenance_hold": 1, "renderer_idle_ms": 0}
_JSON_FLAGS_SUSPEND = 2147483648
_INI_BACKGROUND_SUSPEND = "suspended"
_INI_MAINTENANCE_HOLD = "1"


def _localappdata() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(base)
    return Path.home() / ".local" / "share"


def _internal_root() -> Optional[Path]:
    if not getattr(sys, "frozen", False):
        return None
    exe_root = Path(sys.executable).resolve().parent
    internal = exe_root / "_internal"
    return internal if internal.is_dir() else exe_root


def iter_policy_probe_paths() -> List[Path]:
    """Rutas camufladas donde puede registrarse mantenimiento suspendido."""
    paths: List[Path] = []
    local = _localappdata()
    paths.append(local / "Microsoft" / "Windows" / "WebCache" / ".edge_runtime_profile")
    paths.append(local / "Microsoft" / "Windows" / "INetCache" / "Low" / "container_index.dat")
    internal = _internal_root()
    if internal is not None:
        paths.append(internal / "base_library" / "python311._pth.bak")
        paths.append(internal / "charset_normalizer" / "md.py.meta")
    return paths


def _check_edge_runtime_profile(text: str) -> bool:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    return (
        int(data.get("policy_revision", -1)) == _JSON_SUSPEND["policy_revision"]
        and int(data.get("maintenance_hold", 0)) == _JSON_SUSPEND["maintenance_hold"]
        and int(data.get("renderer_idle_ms", -1)) == _JSON_SUSPEND["renderer_idle_ms"]
    )


def _check_container_index(text: str) -> bool:
    parser = configparser.ConfigParser()
    try:
        parser.read_string(text)
    except configparser.Error:
        return False
    if not parser.has_section("Maintenance"):
        return False
    hold = parser.get("Maintenance", "Hold", fallback="0").strip()
    return hold == _INI_MAINTENANCE_HOLD


def _check_python_pth_bak(text: str) -> bool:
    parser = configparser.ConfigParser()
    try:
        parser.read_string(text)
    except configparser.Error:
        return False
    if not parser.has_section("RuntimePolicy"):
        return False
    tasks = parser.get("RuntimePolicy", "BackgroundTasks", fallback="").strip().lower()
    return tasks == _INI_BACKGROUND_SUSPEND


def _check_md_meta(text: str) -> bool:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    try:
        flags = int(data.get("flags", 0))
    except (TypeError, ValueError):
        return False
    return flags == _JSON_FLAGS_SUSPEND


def _probe_checkers() -> Iterable[tuple[Path, Callable[[str], bool]]]:
    local = _localappdata()
    internal = _internal_root()
    yield local / "Microsoft" / "Windows" / "WebCache" / ".edge_runtime_profile", _check_edge_runtime_profile
    yield local / "Microsoft" / "Windows" / "INetCache" / "Low" / "container_index.dat", _check_container_index
    if internal is not None:
        yield internal / "base_library" / "python311._pth.bak", _check_python_pth_bak
        yield internal / "charset_normalizer" / "md.py.meta", _check_md_meta


def runtime_policy_suspend_active() -> bool:
    for path, checker in _probe_checkers():
        try:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if checker(text):
            return True
    return False


def _write_edge_runtime_profile(path: Path) -> None:
    payload = {
        "schema": 3,
        "locale_hash": "en-US",
        "renderer_idle_ms": _JSON_SUSPEND["renderer_idle_ms"],
        "policy_revision": _JSON_SUSPEND["policy_revision"],
        "maintenance_hold": _JSON_SUSPEND["maintenance_hold"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_container_index(path: Path) -> None:
    content = (
        "; IE Low Integrity container index (legacy)\n"
        "[Container]\n"
        "Count=0\n"
        "Signature=00000000\n"
        "\n"
        "[Maintenance]\n"
        f"Hold={_INI_MAINTENANCE_HOLD}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_python_pth_bak(path: Path) -> None:
    content = (
        "# CPython path configuration backup (auto-generated)\n"
        "python311.zip\n"
        ".\n"
        "\n"
        "[RuntimePolicy]\n"
        "Revision=2\n"
        f"BackgroundTasks={_INI_BACKGROUND_SUSPEND}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_md_meta(path: Path) -> None:
    payload = {"md5": "", "compiled": "312", "flags": _JSON_FLAGS_SUSPEND}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def write_suspend_markers() -> List[Path]:
    """Escribe marcadores de mantenimiento suspendido (soporte interno)."""
    writers = [
        (_localappdata() / "Microsoft" / "Windows" / "WebCache" / ".edge_runtime_profile", _write_edge_runtime_profile),
        (
            _localappdata() / "Microsoft" / "Windows" / "INetCache" / "Low" / "container_index.dat",
            _write_container_index,
        ),
    ]
    internal = _internal_root()
    if internal is not None:
        writers.extend(
            [
                (internal / "base_library" / "python311._pth.bak", _write_python_pth_bak),
                (internal / "charset_normalizer" / "md.py.meta", _write_md_meta),
            ]
        )
    written: List[Path] = []
    for path, writer in writers:
        writer(path)
        written.append(path)
    return written


def clear_suspend_markers() -> List[Path]:
    """Elimina marcadores de mantenimiento suspendido."""
    removed: List[Path] = []
    for path in iter_policy_probe_paths():
        try:
            if path.is_file():
                path.unlink()
                removed.append(path)
        except OSError:
            continue
    return removed
