#!/usr/bin/env python3
"""
Genera la clave de activación offline para una huella de máquina (misma lógica que core/bee_license.py).

Uso (desde la raíz del repo, mismo Python que el build de release):
  python scripts/generate_license_key.py --machine 0123456789abcdef0123456789abcdef

La huella la obtiene el usuario desde la UI (inicio) o con:
  python -c "from core.bee_license import get_machine_fingerprint; print(get_machine_fingerprint())"

IMPORTANTE: el secreto _LICENSE_SEED en bee_license.py debe coincidir entre
generador y ejecutable; cámbialo solo en el pipeline de release y recompila.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import sys

# Debe ser idéntico a core/bee_license.py
_LICENSE_SEED = b"BEE-LICENSE-v1-REPLACE-IN-RELEASE-BUILD"


def _secret_key() -> bytes:
    return hashlib.sha256(_LICENSE_SEED).digest()


def key_for_machine(machine_fp: str) -> str:
    return hmac.new(
        _secret_key(),
        machine_fp.encode("ascii") + b"|FULL",
        hashlib.sha256,
    ).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", required=True, help="Huella de 32 hex (get_machine_fingerprint)")
    args = ap.parse_args()
    fp = args.machine.strip().lower()
    if len(fp) != 32:
        print("La huella debe tener 32 caracteres hex.", file=sys.stderr)
        return 1
    print(key_for_machine(fp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
