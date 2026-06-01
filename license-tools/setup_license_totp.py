#!/usr/bin/env python3
"""Enrola TOTP para el generador de licencias (Google Authenticator / compatible)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_SECRET = Path.home() / ".elia" / "license_totp.secret"


def main() -> int:
    ap = argparse.ArgumentParser(description="Configurar TOTP para generate_license_key.py")
    ap.add_argument(
        "--secret-out",
        default=str(DEFAULT_SECRET),
        help=f"Ruta del secreto (default: {DEFAULT_SECRET})",
    )
    ap.add_argument("--force", action="store_true", help="Sobrescribir secreto existente")
    args = ap.parse_args()

    try:
        import pyotp
    except ImportError:
        print("pip install -r license-tools/requirements.txt", file=sys.stderr)
        return 1

    out = Path(args.secret_out)
    if out.is_file() and not args.force:
        print(f"Ya existe {out}. Usa --force para regenerar.", file=sys.stderr)
        return 1

    secret = pyotp.random_base32()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(secret + "\n", encoding="utf-8")
    try:
        out.chmod(0o600)
    except OSError:
        pass

    uri = pyotp.totp.TOTP(secret).provisioning_uri(name="ELIA License", issuer_name="ELIA")
    print(f"Secreto guardado en: {out}")
    print(f"URI (QR): {uri}")
    print("Escanea el URI con Authenticator o introduce el secreto manualmente.")
    print("Guarda una copia de respaldo del secreto en un lugar seguro.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
