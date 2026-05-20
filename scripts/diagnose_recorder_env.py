#!/usr/bin/env python3
"""Diagnóstico de Chrome + Node para grabación Puppeteer (Windows)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    print("ELIA — diagnóstico grabador (Chrome / Node)\n")
    print(f"  platform     = {sys.platform}")
    print(f"  ELIA_ALLOW_CHROMIUM_FALLBACK = {os.environ.get('ELIA_ALLOW_CHROMIUM_FALLBACK', '')!r}")

    from core.ui_automation.chrome_resolver import (
        chromium_fallback_allowed,
        resolve_chrome_for_recording,
    )

    result = resolve_chrome_for_recording(ROOT)
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

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
