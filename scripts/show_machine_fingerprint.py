#!/usr/bin/env python3
"""
Muestra la huella de equipo de esta máquina (misma lógica que la UI de ELIA).

Uso (desde la raíz del repo, sin arrancar ELIA ni ELIA_SKIP_LICENSE):
  python scripts/show_machine_fingerprint.py

Soporte puede ejecutarlo en el PC del usuario para generar la clave con
generate_license_key.py --machine <huella>.

No requiere licencia activa: solo lee identificadores de hardware vía core/elia_license.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_elia_license():
    import importlib.util

    py_path = ROOT / "core" / "elia_license.py"
    if py_path.is_file():
        mod_name = "elia_license_fp"
        spec = importlib.util.spec_from_file_location(mod_name, py_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            return mod
    from core import elia_license

    return elia_license


def main() -> int:
    lic = _load_elia_license()
    fp = lic.get_machine_fingerprint()
    print(fp)
    if sys.platform == "win32":
        parts = lic._collect_hardware_parts()
        if parts:
            print("\nComponentes (diagnóstico):", file=sys.stderr)
            for p in parts:
                print(f"  - {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
