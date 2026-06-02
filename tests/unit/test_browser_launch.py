"""Tests for ELIA browser launch helpers."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from webui import browser_launch as bl


class TestBrowserLaunch(unittest.TestCase):
    def test_elia_browser_profile_dir_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ELIA_BROWSER_USER_DATA_DIR", None)
            path = bl.elia_browser_profile_dir()
        self.assertTrue(path.replace("\\", "/").endswith("/ELIA/browser-profile"))

    def test_elia_browser_profile_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"ELIA_BROWSER_USER_DATA_DIR": tmp}, clear=False):
                self.assertEqual(bl.elia_browser_profile_dir(), tmp)

    def test_chromium_argv_uses_isolated_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"ELIA_BROWSER_USER_DATA_DIR": tmp}, clear=False):
                argv = bl._chromium_elia_launch_argv(["http://127.0.0.1:8765/"], new_window=True)
        self.assertIn(f"--user-data-dir={tmp}", argv)
        self.assertIn("--disable-restore-session-state", argv)
        self.assertIn("--new-window", argv)
        self.assertEqual(argv[-1], "http://127.0.0.1:8765/")

    def test_chromium_argv_tab_mode_skips_new_window(self) -> None:
        argv = bl._chromium_elia_launch_argv(["http://127.0.0.1:8765/"], new_window=False)
        self.assertNotIn("--new-window", argv)
        self.assertTrue(any(a.startswith("--user-data-dir=") for a in argv))


if __name__ == "__main__":
    unittest.main()
