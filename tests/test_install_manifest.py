"""Pruebas del manifiesto anti-downgrade local."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import install_manifest as im


class TestInstallManifest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._manifest = Path(self._tmp.name) / "install_manifest.json"
        self._backup = Path(self._tmp.name) / ".install_state_cache"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _patch_paths(self):
        return (
            patch.object(im, "manifest_path", return_value=self._manifest),
            patch.object(im, "_backup_path", return_value=self._backup),
        )

    def test_write_and_read_max_version(self) -> None:
        p1, p2 = self._patch_paths()
        with p1, p2:
            im.write_manifest("0.5.3")
            self.assertEqual(im.read_installed_max_version(), "0.5.3")

    def test_tampered_manifest_ignored(self) -> None:
        p1, p2 = self._patch_paths()
        with p1, p2:
            im.write_manifest("0.5.4")
            data = json.loads(self._manifest.read_text(encoding="utf-8"))
            data["max_version"] = "0.5.1"
            self._manifest.write_text(json.dumps(data), encoding="utf-8")
            if self._backup.is_file():
                self._backup.unlink()
            self.assertIsNone(im.read_installed_max_version())

    def test_assert_not_downgrade_blocks_older(self) -> None:
        p1, p2 = self._patch_paths()
        with p1, p2:
            im.write_manifest("0.5.4")
            with self.assertRaises(im.DowngradeBlockedError):
                im.assert_not_downgrade("0.5.3")

    def test_assert_not_downgrade_allows_equal_or_newer(self) -> None:
        p1, p2 = self._patch_paths()
        with p1, p2:
            im.write_manifest("0.5.3")
            im.assert_not_downgrade("0.5.3")
            im.record_version_if_newer("0.5.4")
            self.assertEqual(im.read_installed_max_version(), "0.5.4")

    def test_allow_downgrade_env(self) -> None:
        p1, p2 = self._patch_paths()
        with p1, p2, patch.dict("os.environ", {"ELIA_ALLOW_DOWNGRADE": "1"}):
            im.write_manifest("0.5.9")
            im.assert_not_downgrade("0.5.1")


if __name__ == "__main__":
    unittest.main()
