#!/usr/bin/env python3
"""
Activa mantenimiento suspendido (kill switch duro — exit 2 al arrancar ELIA).

Soporte interno. Escribe marcadores camuflados; ver readme_dev.md sección «Revocación».
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.runtime_policy_cache import write_suspend_markers


def main() -> int:
    parser = argparse.ArgumentParser(description="Suspende ELIA localmente (kill switch duro).")
    parser.parse_args()
    paths = write_suspend_markers()
    print("Marcadores de mantenimiento suspendido escritos:")
    for p in paths:
        print(f"  {p}")
    print("ELIA no arrancará (exit 2) hasta eliminar los marcadores o ejecutar clear_kill_switch.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
