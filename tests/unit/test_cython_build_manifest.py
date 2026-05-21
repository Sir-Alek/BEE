"""Cobertura del manifiesto Cython vs todos los .py de core/."""
from __future__ import annotations

import unittest
from pathlib import Path

from core._cython_build_manifest import (
    CYTHON_REL_PATHS,
    NON_CYTHON_PY_FILENAMES,
    NON_CYTHON_RUNTIME_REL_PATHS,
    verify_core_manifest_coverage,
)

from tests.paths import REPO_ROOT


class TestCythonBuildManifest(unittest.TestCase):
    def test_every_core_py_is_classified(self) -> None:
        missing = verify_core_manifest_coverage()
        self.assertEqual(missing, [], f"Módulos sin clasificar: {missing}")

    def test_mobile_modules_stay_as_source_in_runtime(self) -> None:
        runtime = set(NON_CYTHON_RUNTIME_REL_PATHS)
        self.assertIn("core/ui_automation/mobile_android.py", runtime)
        self.assertIn("core/ui_automation/mobile_recorder.py", runtime)

    def test_mobile_modules_not_in_cython_manifest(self) -> None:
        cython = set(CYTHON_REL_PATHS)
        self.assertNotIn("core/ui_automation/mobile_android.py", cython)
        self.assertNotIn("core/ui_automation/mobile_recorder.py", cython)

    def test_cython_manifest_matches_discovered_count(self) -> None:
        core_dir = REPO_ROOT / "core"
        all_py = list(core_dir.rglob("*.py"))
        skip_names = NON_CYTHON_PY_FILENAMES | {"__init__.py"}
        expected_cython = sum(1 for p in all_py if p.name not in skip_names)
        self.assertEqual(len(CYTHON_REL_PATHS), expected_cython)

    def test_build_manifest_not_shipped_as_runtime(self) -> None:
        self.assertNotIn("core/_cython_build_manifest.py", NON_CYTHON_RUNTIME_REL_PATHS)


if __name__ == "__main__":
    unittest.main()
