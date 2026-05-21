#!/usr/bin/env python
"""
Ejecuta tests/integration/.

Por defecto: smoke Puppeteer (stub, sin red).
Opt-in:
  ELIA_RUN_INTEGRATION=1  → Jira / Value Edge con credenciales reales (env).
  ELIA_RUN_NIGHTLY=1      → Appium / Legacy runtime (Windows, entorno real).
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ELIA_SKIP_LICENSE", "")
os.environ.pop("ELIA_ACTIVATION_KEY", None)


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(
        str(TESTS_DIR / "integration"),
        pattern="test_*.py",
        top_level_dir=str(ROOT),
    )
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
