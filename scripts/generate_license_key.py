#!/usr/bin/env python3
"""
DEPRECATED — use license-tools/generate_license_key.py (v4 Ed25519 + TOTP).

Este stub redirige al generador externo que no se empaqueta en ELIA.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "license-tools" / "generate_license_key.py"


def main() -> int:
    if not GENERATOR.is_file():
        print(
            "Generador movido a license-tools/generate_license_key.py\n"
            "Ejecuta: python license-tools/generate_license_key.py --help",
            file=sys.stderr,
        )
        return 1
    cmd = [sys.executable, str(GENERATOR), *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
