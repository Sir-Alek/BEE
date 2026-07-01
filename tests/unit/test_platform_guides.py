"""Tests para guías rápidas móvil/legacy."""
from __future__ import annotations

import unittest

from core.platform_guides import SUPPORTED_PLATFORMS, bundled_guide_path, load_platform_guide


class TestPlatformGuides(unittest.TestCase):
    def test_supported_platforms(self) -> None:
        self.assertEqual(SUPPORTED_PLATFORMS, frozenset({"mobile", "legacy"}))

    def test_bundled_guides_exist(self) -> None:
        for plat in ("mobile", "legacy"):
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


if __name__ == "__main__":
    unittest.main()
