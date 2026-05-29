#!/usr/bin/env python3
"""
Genera claves de activación offline (misma lógica que core/elia_license.py).

Uso (desde la raíz del repo):
  python scripts/generate_license_key.py --machine <huella32hex> --tier professional
  python scripts/generate_license_key.py --machine <huella> --tier basic --duration 30d
  python scripts/generate_license_key.py --machine <huella> --tier enterprise --duration 365d
  python scripts/generate_license_key.py --beta-global
  python scripts/generate_license_key.py --beta-global --exp-ts 1782863999

Tiers:
  basic | professional | enterprise

Duraciones:
  15d | 30d | 365d | perm

Formato v3: ELIA-V3-{TIER}-{dur}-{issue_ts}-{hmac64}
Clave beta global: ELIA-BETA-GLOBAL-{exp_ts}-{hmac64}

La huella la obtiene el usuario desde la UI o con:
  python scripts/show_machine_fingerprint.py

IMPORTANTE: _LICENSE_SEED en elia_license.py debe coincidir entre generador y ejecutable.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_elia_license():
    """Carga elia_license.py fuente (evita .pyd desactualizado tras editar el repo)."""
    import importlib.util

    py_path = ROOT / "core" / "elia_license.py"
    if py_path.is_file():
        mod_name = "elia_license_keygen"
        spec = importlib.util.spec_from_file_location(mod_name, py_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            return mod
    from core import elia_license

    return elia_license


_lic = _load_elia_license()
DURATION_15D = _lic.DURATION_15D
DURATION_30D = _lic.DURATION_30D
DURATION_365D = _lic.DURATION_365D
DURATION_LABELS = _lic.DURATION_LABELS
DURATION_PERM = _lic.DURATION_PERM
build_activation_key = _lic.build_activation_key
build_beta_global_key = _lic.build_beta_global_key


def _parse_duration(raw: str) -> str:
    m = {
        "15d": DURATION_15D,
        "30d": DURATION_30D,
        "1m": DURATION_30D,
        "month": DURATION_30D,
        "mes": DURATION_30D,
        "365d": DURATION_365D,
        "1y": DURATION_365D,
        "year": DURATION_365D,
        "anio": DURATION_365D,
        "año": DURATION_365D,
        "perm": DURATION_PERM,
        "permanent": DURATION_PERM,
        "permanente": DURATION_PERM,
        "full": DURATION_PERM,
    }
    key = raw.strip().lower()
    if key not in m:
        raise ValueError(
            f"Duración no válida: {raw!r}. Use: 15d, 30d, 365d, perm"
        )
    return m[key]


def _parse_tier(raw: str) -> str:
    m = {
        "basic": "basic",
        "starter": "basic",
        "pro": "professional",
        "professional": "professional",
        "power": "professional",
        "ent": "enterprise",
        "enterprise": "enterprise",
    }
    key = raw.strip().lower()
    if key not in m:
        raise ValueError(f"Tier no válido: {raw!r}. Use: basic, professional, enterprise")
    return m[key]


def main() -> int:
    ap = argparse.ArgumentParser(description="Generar clave de licencia ELIA")
    ap.add_argument("--machine", help="Huella de 32 hex (get_machine_fingerprint)")
    ap.add_argument(
        "--tier",
        default="enterprise",
        help="Plan: basic, professional, enterprise (default: enterprise)",
    )
    ap.add_argument(
        "--duration",
        default="15d",
        help="Opciones: 15d, 30d, 365d, perm. (Por defecto: 15d)",
    )
    ap.add_argument(
        "--issue-ts",
        type=int,
        default=None,
        help="Timestamp UNIX de emisión (default: ahora). Solo pruebas/soporte.",
    )
    ap.add_argument(
        "--beta-global",
        action="store_true",
        help="Genera clave beta global (sin huella, misma para todos)",
    )
    ap.add_argument(
        "--exp-ts",
        type=int,
        default=None,
        help="Expiración UNIX para --beta-global (default: ELIA_BETA_DEADLINE del build)",
    )
    args = ap.parse_args()

    if args.beta_global:
        key = build_beta_global_key(exp_ts=args.exp_ts)
        exp = args.exp_ts
        if exp is None:
            from core._version import elia_beta_deadline_ts

            exp = int(elia_beta_deadline_ts())
        print(key)
        print(f"# beta global | exp_ts: {exp}", file=sys.stderr)
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
        tier = _parse_tier(args.tier)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    key = build_activation_key(
        fp,
        dur,
        tier=tier,
        issue_ts=args.issue_ts,
    )
    label = DURATION_LABELS.get(dur, dur)
    issue_ts = args.issue_ts if args.issue_ts is not None else int(time.time())

    print(key)
    print(f"# tier: {tier} | duración: {label} | issue_ts: {issue_ts}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
