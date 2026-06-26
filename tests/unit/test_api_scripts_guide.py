"""Tests para la guía de scripts API."""
from __future__ import annotations

import unittest
from pathlib import Path

from core.api_automation.scripts_guide import (
    API_SCRIPTS_GUIDE_TITLE,
    bundled_guide_path,
    load_api_scripts_guide_markdown,
)


class TestApiScriptsGuide(unittest.TestCase):
    def test_bundled_guide_exists(self) -> None:
        path = bundled_guide_path()
        self.assertTrue(path.is_file(), msg=str(path))

    def test_load_markdown(self) -> None:
        content = load_api_scripts_guide_markdown()
        self.assertIn("pm.environment", content)
        self.assertIn("pre_request_script", content)

    def test_title_constant(self) -> None:
        self.assertEqual(API_SCRIPTS_GUIDE_TITLE, "Guía de scripts API")


if __name__ == "__main__":
    unittest.main()
