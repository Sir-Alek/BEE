"""Rutas de herramientas locales persistidas en Documents/ELIA/tool_paths.json."""
from __future__ import annotations

import json
import os
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple

from core import elia_paths

TOOL_PATH_KEYS: Tuple[str, ...] = (
    "android_studio",
    "android_sdk",
    "adb",
    "emulator",
    "appium",
    "chrome",
)

TOOL_PATH_META: Dict[str, Dict[str, Any]] = {
    "android_studio": {
        "label": "Android Studio",
        "kind": "file",
        "accept": (".exe",),
        "env": ("ELIA_ANDROID_STUDIO", "ANDROID_STUDIO"),
    },
    "android_sdk": {
        "label": "Android SDK",
        "kind": "dir",
        "env": ("ELIA_ANDROID_HOME", "ANDROID_HOME", "ANDROID_SDK_ROOT"),
    },
    "adb": {
        "label": "adb (platform-tools)",
        "kind": "file",
        "accept": (".exe",) if sys.platform == "win32" else tuple(),
        "env": ("ELIA_ADB_PATH",),
    },
    "emulator": {
        "label": "Android Emulator",
        "kind": "file",
        "accept": (".exe",) if sys.platform == "win32" else tuple(),
        "env": ("ELIA_EMULATOR_PATH",),
    },
    "appium": {
        "label": "Appium",
        "kind": "file",
        "accept": (".exe", ".cmd", ".bat") if sys.platform == "win32" else tuple(),
        "env": ("ELIA_APPIUM_PATH",),
    },
    "chrome": {
        "label": "Google Chrome",
        "kind": "file",
        "accept": (".exe",),
        "env": ("ELIA_CHROME_PATH", "CHROME_PATH", "ELIA_BROWSER_PATH"),
    },
}

_cache_lock = threading.Lock()
_cache: Optional[Dict[str, str]] = None


def _tool_paths_file():
    return elia_paths.ensure_user_data_root() / "tool_paths.json"


def _normalize_stored_value(key: str, raw: str) -> Optional[str]:
    val = (raw or "").strip().strip('"')
    if not val:
        return None
    return val


def load_tool_paths(*, force: bool = False) -> Dict[str, str]:
    global _cache
    with _cache_lock:
        if _cache is not None and not force:
            return dict(_cache)
        out: Dict[str, str] = {}
        path = _tool_paths_file()
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for key in TOOL_PATH_KEYS:
                        raw = data.get(key)
                        if isinstance(raw, str):
                            norm = _normalize_stored_value(key, raw)
                            if norm:
                                out[key] = norm
            except Exception:
                out = {}
        _cache = dict(out)
        return dict(out)


def get_tool_path(key: str) -> Optional[str]:
    if key not in TOOL_PATH_META:
        return None
    return load_tool_paths().get(key)


def save_tool_paths(updates: Dict[str, Optional[str]]) -> Dict[str, str]:
    current = load_tool_paths(force=True)
    for key, value in updates.items():
        if key not in TOOL_PATH_META:
            continue
        if value is None or not str(value).strip():
            current.pop(key, None)
        else:
            norm = _normalize_stored_value(key, str(value))
            if norm:
                current[key] = norm
            else:
                current.pop(key, None)
    payload = {"version": 1, **current}
    _tool_paths_file().write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with _cache_lock:
        global _cache
        _cache = dict(current)
    return dict(current)


def validate_studio_path(raw: str) -> Tuple[bool, Optional[str], str]:
    val = _normalize_stored_value("android_studio", raw)
    if not val:
        return False, None, "Ruta vacía."
    if os.path.isdir(val):
        for rel in (
            os.path.join("bin", "studio64.exe"),
            os.path.join("bin", "studio.exe"),
            os.path.join("bin", "studio"),
        ):
            candidate = os.path.join(val, rel)
            if os.path.isfile(candidate):
                return True, candidate, "OK"
        return False, None, "Carpeta válida pero sin bin/studio64.exe."
    if not os.path.isfile(val):
        return False, None, "El archivo no existe."
    base = os.path.basename(val).lower()
    if base not in ("studio64.exe", "studio.exe", "studio"):
        return False, None, "Selecciona studio64.exe o la carpeta de instalación."
    return True, val, "OK"


def validate_tool_path(key: str, raw: str) -> Tuple[bool, Optional[str], str]:
    if key not in TOOL_PATH_META:
        return False, None, "Clave no válida."
    val = _normalize_stored_value(key, raw)
    if not val:
        return False, None, "Ruta vacía."
    meta = TOOL_PATH_META[key]
    if meta["kind"] == "dir":
        if not os.path.isdir(val):
            return False, None, "Debe ser una carpeta existente."
        return True, val, "OK"
    if key == "android_studio":
        return validate_studio_path(val)
    if not os.path.isfile(val):
        return False, None, "El archivo no existe."
    return True, val, "OK"


def studio_search_candidates() -> List[str]:
    from core.ui_automation.mobile_avd_wizard import list_studio_search_candidates

    return list_studio_search_candidates()


def run_environment_diagnostic(*, base_dir: Optional[str] = None) -> Dict[str, Any]:
    from core.ui_automation.chrome_resolver import resolve_chrome_for_recording
    from core.ui_automation.mobile_android import run_preflight

    mobile = run_preflight().to_dict()
    chrome = resolve_chrome_for_recording(base_dir).to_dict()
    paths_status = build_tool_paths_status()
    path_items = paths_status.get("paths") or {}
    paths_ok = all(entry.get("ok") for entry in path_items.values() if entry.get("effective"))
    return {
        "ok": bool(mobile.get("ok")) and bool(chrome.get("ok")) and paths_ok,
        "mobile": {
            "ok": mobile.get("ok"),
            "errors": mobile.get("errors") or [],
            "warnings": mobile.get("warnings") or [],
            "items": mobile.get("items") or [],
        },
        "chrome": {
            "ok": chrome.get("ok"),
            "path": chrome.get("chrome_path"),
            "errors": chrome.get("errors") or [],
        },
        "tool_paths": paths_status,
    }


TOOL_PATH_GROUPS: Dict[str, Dict[str, Any]] = {
    "android": {
        "label": "Android / Móvil",
        "keys": ("android_studio", "android_sdk", "adb", "emulator", "appium"),
    },
    "web": {
        "label": "Web / Chrome",
        "keys": ("chrome",),
    },
}


def detect_tool_paths() -> Dict[str, Dict[str, Any]]:
    """Valores auto-detectados actuales (sin override ELIA)."""
    from core.ui_automation.chrome_resolver import resolve_chrome_for_recording_auto
    from core.ui_automation.mobile_android import (
        _resolve_from_env_or_sdk,
        resolve_android_sdk_auto,
        resolve_appium,
    )
    from core.ui_automation.mobile_avd_wizard import resolve_studio_executable_auto

    sdk, sdk_src = resolve_android_sdk_auto()
    adb_path, adb_src = _resolve_from_env_or_sdk(
        ("ELIA_ADB_PATH",),
        os.path.join("platform-tools", "adb.exe" if sys.platform == "win32" else "adb"),
        "adb",
    )
    emulator_path, emulator_src = _resolve_from_env_or_sdk(
        ("ELIA_EMULATOR_PATH",),
        os.path.join("emulator", "emulator.exe" if sys.platform == "win32" else "emulator"),
        "emulator",
    )
    appium = resolve_appium(skip_config=True)
    appium_path, appium_src = appium.path, appium.source
    chrome = resolve_chrome_for_recording_auto("")
    studio, studio_src = resolve_studio_executable_auto()

    return {
        "android_sdk": {"path": sdk, "source": sdk_src},
        "adb": {"path": adb_path, "source": adb_src},
        "emulator": {"path": emulator_path, "source": emulator_src},
        "appium": {"path": appium_path, "source": appium_src},
        "chrome": {"path": chrome.chrome_path if chrome.ok else None, "source": chrome.source},
        "android_studio": {"path": studio, "source": studio_src},
    }


def build_tool_paths_status() -> Dict[str, Any]:
    overrides = load_tool_paths()
    detected = detect_tool_paths()
    items: Dict[str, Any] = {}
    for key in TOOL_PATH_KEYS:
        meta = TOOL_PATH_META[key]
        override = overrides.get(key)
        det = detected.get(key, {})
        effective = override or det.get("path")
        ok = False
        msg = ""
        if override:
            ok, resolved, msg = validate_tool_path(key, override)
            if ok and resolved:
                effective = resolved
        elif effective:
            ok, _, msg = validate_tool_path(key, str(effective))
        items[key] = {
            "label": meta["label"],
            "kind": meta["kind"],
            "override": override,
            "detected": det.get("path"),
            "detected_source": det.get("source"),
            "effective": effective,
            "effective_source": "elia_config" if override else det.get("source"),
            "ok": ok if effective else False,
            "message": msg or ("Detectado" if effective else "No detectado"),
        }
    return {"version": 1, "paths": items, "config_file": str(_tool_paths_file()), "groups": TOOL_PATH_GROUPS}


def test_tool_path_entry(key: str, raw: Optional[str] = None) -> Dict[str, Any]:
    value = raw if raw is not None else get_tool_path(key) or ""
    ok, resolved, message = validate_tool_path(key, value)
    return {"ok": ok, "key": key, "path": resolved or value, "message": message}
