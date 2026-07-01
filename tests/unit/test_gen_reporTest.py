"""Tests for PDF report generation helpers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from resources.behave.utils.gen_reporTest import PdfReportDocument


class TestGenReportHelpers(unittest.TestCase):
    def test_resolve_feature_path_accepts_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature = root / "features" / "demo_login.feature"
            feature.parent.mkdir(parents=True)
            feature.write_text("Feature: Demo\n", encoding="utf-8")
            resolved = PdfReportDocument._resolve_feature_path(str(root), "features/demo_login.feature")
            self.assertTrue(Path(resolved).is_file())

    def test_step_index_images_match_numbered_screenshots(self) -> None:
        import re
        from collections import defaultdict

        step_index_images = defaultdict(list)
        for img in ("01_Login_Demo.png", "02_Usuario.png", "FAIL_120000_click.png"):
            prefix_match = re.match(r"^(\d{2})_", img, re.IGNORECASE)
            if prefix_match and not img.startswith("FAIL_"):
                step_index_images[int(prefix_match.group(1)) - 1].append(img)
        self.assertEqual(step_index_images[0], ["01_Login_Demo.png"])
        self.assertEqual(step_index_images[1], ["02_Usuario.png"])


if __name__ == "__main__":
    unittest.main()
