"""Genera clave de activación perm para una huella (uso en E2E)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core import elia_license as lic

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: e2e_generate_license.py <fingerprint32>", file=sys.stderr)
        sys.exit(2)
    fp = sys.argv[1].strip().lower()
    key = lic.build_activation_key(fp, lic.DURATION_PERM, issue_ts=1_700_000_000)
    print(key)
