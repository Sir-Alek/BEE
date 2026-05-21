#!/usr/bin/env python3
"""
Genera claves de activación offline (misma lógica que core/elia_license.py).

Uso (desde la raíz del repo):
  python scripts/generate_license_key.py --machine <huella32hex>
  python scripts/generate_license_key.py --machine <huella> --duration 15d
  python scripts/generate_license_key.py --machine <huella> --duration 30d --mobile --legacy
  python scripts/generate_license_key.py --machine <huella> --duration perm

Duraciones:
  15d   — 15 días (por defecto)
  30d   — 1 mes
  365d  — 1 año
  perm  — permanente 

Módulos opcionales:
  --mobile   incluye grabación móvil (flag M en la clave)
  --legacy   incluye grabación legacy (flag L en la clave)

La huella la obtiene el usuario desde la UI o con:
  python -c "from core.elia_license import get_machine_fingerprint; print(get_machine_fingerprint())"

IMPORTANTE: _LICENSE_SEED en elia_license.py debe coincidir entre generador y ejecutable.
"""
from __future__ import annotations

import argparse
import sys
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Generar clave de licencia ELIA")
    ap.add_argument(
        "--machine",
        required=True,
        help="Huella de 32 hex (get_machine_fingerprint)",
    )
    ap.add_argument(
        "--duration",
        default="15d",
        help="Opciones: 15d, 30d, 365d, perm. (Por defecto: 15d)",
    )
    ap.add_argument(
        "--mobile",
        action="store_true",
        help="Incluir módulo de grabación móvil",
    )
    ap.add_argument(
        "--legacy",
        action="store_true",
        help="Incluir módulo de grabación legacy (escritorio)",
    )
    args = ap.parse_args()

    fp = args.machine.strip().lower()
    if len(fp) != 32 or any(c not in "0123456789abcdef" for c in fp):
        print("La huella debe ser 32 caracteres hexadecimales.", file=sys.stderr)
        return 1

    try:
        dur = _parse_duration(args.duration)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    key = build_activation_key(fp, dur, mobile=args.mobile, legacy=args.legacy)
    label = DURATION_LABELS.get(dur, dur)
    mods = []
    if args.mobile:
        mods.append("móvil")
    if args.legacy:
        mods.append("legacy")
    mod_txt = ", ".join(mods) if mods else "ninguno"

    print(key)
    print(f"# duración: {label} | módulos: {mod_txt}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
