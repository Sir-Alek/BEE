#!/usr/bin/env python3
"""
Elimina marcadores de mantenimiento suspendido (rehabilita arranque de ELIA).

Soporte interno. Ver readme_dev.md sección «Revocación».
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.runtime_policy_cache import clear_suspend_markers


def main() -> int:
    parser = argparse.ArgumentParser(description="Rehabilita arranque de ELIA (quita kill switch).")
    parser.parse_args()
    removed = clear_suspend_markers()
    if not removed:
        print("No había marcadores activos.")
        return 0
    print("Marcadores eliminados:")
    for p in removed:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
