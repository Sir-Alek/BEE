#!/usr/bin/env python3
"""Genera par Ed25519 y exporta la clave pública para core/license_public_keys.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from license_sign import export_public_key_b64url  # noqa: E402

DEFAULT_PRIVATE = Path.home() / ".elia" / "elia_license_private.pem"
PUBLIC_KEYS_JSON = REPO_ROOT / "core" / "license_public_keys.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Crear par de claves Ed25519 para licencias ELIA")
    ap.add_argument("--kid", default="prod-2026", help="Identificador de rotación (kid)")
    ap.add_argument(
        "--private-out",
        default=str(DEFAULT_PRIVATE),
        help=f"Ruta de salida PEM privada (default: {DEFAULT_PRIVATE})",
    )
    ap.add_argument(
        "--update-repo",
        action="store_true",
        help="Actualiza core/license_public_keys.json con la clave pública",
    )
    ap.add_argument("--force", action="store_true", help="Sobrescribir PEM privada existente")
    args = ap.parse_args()

    priv_path = Path(args.private_out)
    if priv_path.is_file() and not args.force:
        print(f"Ya existe {priv_path}. Usa --force para regenerar.", file=sys.stderr)
        return 1

    priv_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    from cryptography.hazmat.primitives import serialization

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_path.write_bytes(pem)
    try:
        priv_path.chmod(0o600)
    except OSError:
        pass

    pub_b64 = export_public_key_b64url(private_key)
    print(f"Clave privada: {priv_path}")
    print(f"kid: {args.kid}")
    print(f"Clave pública (base64url): {pub_b64}")

    if args.update_repo:
        data: dict = {"keys": {}, "default_kid": args.kid}
        if PUBLIC_KEYS_JSON.is_file():
            try:
                existing = json.loads(PUBLIC_KEYS_JSON.read_text(encoding="utf-8"))
                if isinstance(existing, dict) and isinstance(existing.get("keys"), dict):
                    data["keys"] = dict(existing["keys"])
                    if existing.get("default_kid"):
                        data["default_kid"] = str(existing["default_kid"])
            except json.JSONDecodeError:
                pass
        data["keys"][args.kid] = pub_b64
        data["default_kid"] = args.kid
        PUBLIC_KEYS_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Actualizado: {PUBLIC_KEYS_JSON}")
    else:
        print(
            "\nAñade manualmente a core/license_public_keys.json:\n"
            f'  "keys": {{ "{args.kid}": "{pub_b64}" }},\n'
            f'  "default_kid": "{args.kid}"'
        )

    print("\nNUNCA subas el .pem privado al repositorio ni al instalador.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
