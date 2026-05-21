#!/usr/bin/env python
"""Ejecuta suites unit/ + api/ (unittest discover)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Evitar que ELIA_SKIP_LICENSE del entorno de desarrollo invalide las suites.
os.environ["ELIA_SKIP_LICENSE"] = ""
os.environ.pop("ELIA_ACTIVATION_KEY", None)


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for sub in ("unit", "api"):
        discovered = loader.discover(
            str(TESTS_DIR / sub),
            pattern="test_*.py",
            top_level_dir=str(ROOT),
        )
        suite.addTests(discovered)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
