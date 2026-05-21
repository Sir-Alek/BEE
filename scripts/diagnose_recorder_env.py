#!/usr/bin/env python3
"""Diagnóstico de entorno de grabación: Chrome/Node, Appium móvil y legacy Windows."""
from __future__ import annotations

import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _check_import(label: str, module: str) -> bool:
    try:
        importlib.import_module(module)
        print(f"  {label:<28} OK")
        return True
    except ImportError as exc:
        print(f"  {label:<28} FALTA ({exc})")
        return False


def main() -> int:
    print("ELIA — diagnóstico grabadores (web / móvil / legacy)\n")
    print(f"  python       = {sys.executable}")
    print(f"  platform     = {sys.platform}")
    print(f"  frozen exe   = {getattr(sys, 'frozen', False)}")
    print(f"  ELIA_ALLOW_CHROMIUM_FALLBACK = {os.environ.get('ELIA_ALLOW_CHROMIUM_FALLBACK', '')!r}")

    ok = True

    print("\n--- Dependencias pip (requirements.txt) ---")
    ok &= _check_import("Appium-Python-Client", "appium")
    try:
        from appium.options.common.base import AppiumOptions  # noqa: F401

        print(f"  {'AppiumOptions (API)':<28} OK")
    except ImportError as exc:
        ok = False
        print(f"  {'AppiumOptions (API)':<28} FALTA ({exc})")
    ok &= _check_import("pynput", "pynput")
    ok &= _check_import("pywinauto", "pywinauto")
    if sys.platform == "win32":
        ok &= _check_import("pywin32", "win32gui")
        ok &= _check_import("comtypes", "comtypes")

    print("\n--- Grabación web (Chrome / Node) ---")
    from core.ui_automation.chrome_resolver import (
        chromium_fallback_allowed,
        resolve_chrome_for_recording,
    )

    result = resolve_chrome_for_recording(ROOT)
    web_ok = result.ok
    print(f"\n  chrome ok      = {result.ok}")
    print(f"  chrome_path    = {result.chrome_path}")
    print(f"  source         = {result.source}")
    if result.warnings:
        print("  warnings:")
        for w in result.warnings:
            print(f"    - {w}")
    if result.errors:
        print("  errors:")
        for e in result.errors:
            print(f"    - {e}")

    node_dir = os.path.join(ROOT, "core", "node")
    pup = os.path.join(node_dir, "node_modules", "puppeteer")
    print(f"\n  core/node/puppeteer existe = {os.path.isdir(pup)}")
    print(f"  chromium_fallback_allowed  = {chromium_fallback_allowed()}")

    try:
        from core.ui_automation.node_wrapper import node_wrapper

        np = node_wrapper.get_node_path()
        print(f"  node_path                  = {np}")
    except Exception as exc:
        print(f"  node_path                  = ERROR: {exc}")

    print("\n--- Appium Server (localhost:4723) ---")
    try:
        import http.client

        conn = http.client.HTTPConnection("localhost", 4723, timeout=3)
        conn.request("GET", "/status")
        resp = conn.getresponse()
        appium_up = resp.status == 200
        print(f"  appium /status             = {'OK' if appium_up else resp.status}")
    except Exception as exc:
        appium_up = False
        print(f"  appium /status             = no accesible ({exc})")

    if not ok:
        print("\n  → Reinstala dependencias: pip install -r requirements.txt")
        if getattr(sys, "frozen", False):
            print("  → Si usas el .exe, reinstala o actualiza ELIA.")

    return 0 if (web_ok and ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
