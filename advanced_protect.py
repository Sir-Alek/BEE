"""
[DEPRECADO] Antes: zlib+base64 -> *.enc para core/*.py y *.js.

Migración: usar el pipeline unificado:
  python scripts/build_release.py --cython    # opcional: compilar .pyd
  python scripts/build_release.py             # JS ofuscado + PyInstaller

Detalles: readme.txt sección «Protección / build de release».
"""
from __future__ import annotations

import sys


def main() -> None:
    print(
        "advanced_protect.py está deprecado.\n"
        "Usa: python scripts/build_release.py [--cython]\n"
        "Ver readme.txt (Protección / build de release).",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
