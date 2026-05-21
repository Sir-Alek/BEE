"""Revoca licencia local para pruebas E2E (estado limpio)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core import elia_license as lic

if __name__ == "__main__":
    lic.revoke_license_local(clear_backups=True)
