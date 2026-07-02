"""Tests para guías rápidas móvil/legacy."""
from __future__ import annotations

import unittest

from core.platform_guides import SUPPORTED_PLATFORMS, bundled_guide_path, load_platform_guide


class TestPlatformGuides(unittest.TestCase):
    def test_supported_platforms(self) -> None:
        self.assertEqual(SUPPORTED_PLATFORMS, frozenset({"mobile", "legacy", "api_load"}))

    def test_bundled_guides_exist(self) -> None:
        for plat in ("mobile", "legacy", "api_load"):
            path = bundled_guide_path(plat)
            self.assertTrue(path.is_file(), msg=str(path))

    def test_load_mobile_guide(self) -> None:
        title, content = load_platform_guide("mobile")
        self.assertIn("móvil", title.lower())
        self.assertIn("grabación", content.lower())

    def test_load_legacy_guide(self) -> None:
        title, content = load_platform_guide("legacy")
        self.assertIn("legacy", title.lower())
        self.assertIn("ventana", content.lower())

    def test_load_api_load_guide(self) -> None:
        title, content = load_platform_guide("api_load")
        self.assertIn("suites", title.lower())
        self.assertIn("locust", content.lower())


if __name__ == "__main__":
    unittest.main()
