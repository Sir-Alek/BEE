"""Genera clave de activación v4 para E2E."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.license_v4_test import build_test_v4_key


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python e2e_generate_license.py <huella32hex>", file=sys.stderr)
        return 1
    fp = sys.argv[1].strip().lower()
    key = build_test_v4_key(fp, issue_ts=1_770_000_000)
    print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
