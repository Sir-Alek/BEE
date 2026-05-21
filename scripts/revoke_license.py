#!/usr/bin/env python3
"""
Revoca la licencia local (soporte interno / pruebas).

Borra license_state.json y respaldos horrocrux. ELIA seguirá arrancando;
jobs quedan bloqueados hasta activar una nueva clave.

Uso:
  python scripts/revoke_license.py
  python scripts/revoke_license.py --keep-backups
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import elia_license as lic


def main() -> int:
    parser = argparse.ArgumentParser(description="Revocación suave de licencia ELIA (local).")
    parser.add_argument(
        "--keep-backups",
        action="store_true",
        help="No borrar respaldos horrocrux (solo license_state.json).",
    )
    args = parser.parse_args()
    fp = lic.get_machine_fingerprint()
    lic.revoke_license_local(clear_backups=not args.keep_backups)
    st = lic.get_license_status()
    print(f"Huella: {fp}")
    print(f"Estado: {st.reason} — {st.message}")
    print("Para reactivar: Configuración → Licencia o ELIA_ACTIVATION_KEY=<clave>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
