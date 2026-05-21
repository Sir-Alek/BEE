"""Marcadores opt-in para suites de integración / nightly."""
from __future__ import annotations

import os


def integration_enabled() -> bool:
    return os.environ.get("ELIA_RUN_INTEGRATION", "").strip().lower() in ("1", "true", "yes")


def nightly_enabled() -> bool:
    return os.environ.get("ELIA_RUN_NIGHTLY", "").strip().lower() in ("1", "true", "yes")
