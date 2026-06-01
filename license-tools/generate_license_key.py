#!/usr/bin/env python3
"""
Genera claves de activación ELIA v4 (Ed25519 + TOTP).

Uso (desde license-tools/ o repo raíz):
  python license-tools/generate_license_key.py --machine <huella32hex> --tier professional --duration 365d
  python license-tools/generate_license_key.py --beta-global
  python license-tools/generate_license_key.py --machine <huella> --tier basic --duration 15d --no-totp

Requisitos previos:
  python license-tools/setup_license_keys.py
  python license-tools/setup_license_totp.py
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from license_sign import (  # noqa: E402
    DURATION_SECONDS,
    sign_beta_global_license,
    sign_machine_license,
)

DEFAULT_PRIVATE_KEY = Path.home() / ".elia" / "elia_license_private.pem"
DEFAULT_TOTP_SECRET = Path.home() / ".elia" / "license_totp.secret"
ISSUED_LOG = Path.home() / ".elia" / "license_issued.log"


def _parse_duration(raw: str) -> str:
    m = {
        "15d": "15D",
        "30d": "30D",
        "1m": "30D",
        "month": "30D",
        "mes": "30D",
        "365d": "365D",
        "1y": "365D",
        "year": "365D",
        "anio": "365D",
        "año": "365D",
    }
    key = raw.strip().lower()
    if key not in m:
        raise ValueError(f"Duración no válida: {raw!r}. Use: 15d, 30d, 365d")
    return m[key]


def _parse_tier(raw: str) -> str:
    m = {
        "basic": "BASIC",
        "starter": "BASIC",
        "pro": "PRO",
        "professional": "PRO",
        "power": "PRO",
        "ent": "ENT",
        "enterprise": "ENT",
    }
    key = raw.strip().lower()
    if key not in m:
        raise ValueError(f"Tier no válido: {raw!r}. Use: basic, professional, enterprise")
    return m[key]


def _prompt_totp(secret_path: Path) -> None:
    bypass = (os.environ.get("ELIA_LICENSE_TOTP_BYPASS") or "").strip().lower()
    if bypass in ("1", "true", "yes"):
        print("# TOTP omitido (ELIA_LICENSE_TOTP_BYPASS)", file=sys.stderr)
        return
    if not secret_path.is_file():
        print(
            f"No existe secreto TOTP en {secret_path}. "
            "Ejecuta: python license-tools/setup_license_totp.py",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        import pyotp
    except ImportError:
        print("Instala dependencias: pip install -r license-tools/requirements.txt", file=sys.stderr)
        raise SystemExit(1) from None

    secret = secret_path.read_text(encoding="utf-8").strip()
    totp = pyotp.TOTP(secret)
    code = input("Ingresa el código de 6 dígitos de tu Authenticator (ELIA): ").strip()
    if not totp.verify(code, valid_window=1):
        print("Código TOTP incorrecto.", file=sys.stderr)
        raise SystemExit(1)


def _append_issued_log(line: str) -> None:
    try:
        ISSUED_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ISSUED_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Generar clave de licencia ELIA v4")
    ap.add_argument("--machine", help="Huella de 32 hex (get_machine_fingerprint)")
    ap.add_argument("--tier", default="enterprise", help="basic | professional | enterprise")
    ap.add_argument("--duration", default="15d", help="15d | 30d | 365d")
    ap.add_argument("--kid", default="prod-2026", help="ID de clave pública (rotación)")
    ap.add_argument(
        "--private-key",
        default=str(DEFAULT_PRIVATE_KEY),
        help=f"Ruta PEM privada (default: {DEFAULT_PRIVATE_KEY})",
    )
    ap.add_argument("--issue-ts", type=int, default=None, help="Timestamp UNIX de emisión (tests)")
    ap.add_argument("--beta-global", action="store_true", help="Clave beta global sin huella")
    ap.add_argument("--exp-ts", type=int, default=None, help="Exp UNIX para --beta-global")
    ap.add_argument(
        "--no-totp",
        action="store_true",
        help="Omitir TOTP (solo desarrollo; prohibido en producción)",
    )
    ap.add_argument(
        "--totp-secret",
        default=str(DEFAULT_TOTP_SECRET),
        help=f"Secreto TOTP (default: {DEFAULT_TOTP_SECRET})",
    )
    args = ap.parse_args()

    priv_path = Path(args.private_key)
    if not priv_path.is_file():
        print(
            f"No existe clave privada en {priv_path}. "
            "Ejecuta: python license-tools/setup_license_keys.py",
            file=sys.stderr,
        )
        return 1

    if not args.no_totp:
        _prompt_totp(Path(args.totp_secret))

    if args.beta_global:
        exp = args.exp_ts
        if exp is None:
            repo_root = TOOLS_DIR.parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            from core._version import elia_beta_deadline_ts

            exp = int(elia_beta_deadline_ts())
        key, payload = sign_beta_global_license(
            private_key_path=priv_path,
            kid=args.kid,
            exp_ts=exp,
        )
        print(key)
        print(f"# beta global v4 | kid: {args.kid} | exp: {payload['exp']}", file=sys.stderr)
        _append_issued_log(
            f"{int(time.time())}\tbeta_global\tkid={args.kid}\texp={payload['exp']}"
        )
        return 0

    if not args.machine:
        print("Indica --machine o usa --beta-global.", file=sys.stderr)
        return 1

    fp = args.machine.strip().lower()
    if len(fp) != 32 or any(c not in "0123456789abcdef" for c in fp):
        print("La huella debe ser 32 caracteres hexadecimales.", file=sys.stderr)
        return 1

    try:
        dur = _parse_duration(args.duration)
        tier_code = _parse_tier(args.tier)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    key, payload = sign_machine_license(
        private_key_path=priv_path,
        kid=args.kid,
        machine_fp=fp,
        tier_code=tier_code,
        duration=dur,
        issue_ts=args.issue_ts,
    )
    label = {"15D": "15 días", "30D": "1 mes", "365D": "1 año"}.get(dur, dur)
    print(key)
    print(
        f"# v4 | kid: {args.kid} | tier: {tier_code} | duración: {label} | iat: {payload['iat']} | exp: {payload['exp']}",
        file=sys.stderr,
    )
    _append_issued_log(
        f"{int(time.time())}\tmachine\tfp={fp}\ttier={tier_code}\tdur={dur}\tiat={payload['iat']}\texp={payload['exp']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
