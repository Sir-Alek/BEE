"""Pruebas de capacidades del grabador web (resolución de Chrome / preflight)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.ui_automation import chrome_resolver as cr

from tests.paths import REPO_ROOT

ROOT = REPO_ROOT


class TestChromeResolverCapabilities(unittest.TestCase):
    def test_chromium_fallback_env_flag(self) -> None:
        with patch.dict(os.environ, {"ELIA_ALLOW_CHROMIUM_FALLBACK": "1"}, clear=False):
            self.assertTrue(cr.chromium_fallback_allowed())
        with patch.dict(os.environ, {"ELIA_ALLOW_CHROMIUM_FALLBACK": "0"}, clear=False):
            self.assertFalse(cr.chromium_fallback_allowed())

    def test_exists_exe(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            path = tmp.name
        try:
            self.assertTrue(cr._exists_exe(path))
            self.assertFalse(cr._exists_exe(""))
            self.assertFalse(cr._exists_exe("/no/existe/chrome.exe"))
        finally:
            os.unlink(path)

    def test_env_candidate_paths_reads_elia_chrome_path(self) -> None:
        with patch.dict(os.environ, {"ELIA_CHROME_PATH": r"C:\Chrome\chrome.exe"}, clear=False):
            paths = cr._env_candidate_paths()
        self.assertEqual(paths, [(r"C:\Chrome\chrome.exe", "env")])

    def test_resolve_from_env_on_windows(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            chrome = tmp.name
        try:
            with patch.object(cr.sys, "platform", "win32"):
                with patch.dict(os.environ, {"ELIA_CHROME_PATH": chrome}, clear=False):
                    result = cr.resolve_chrome_for_recording(base_dir=str(ROOT))
            self.assertTrue(result.ok)
            self.assertEqual(result.chrome_path, chrome)
            self.assertEqual(result.source, "env")
        finally:
            os.unlink(chrome)

    def test_resolve_non_windows_returns_error(self) -> None:
        with patch.object(cr.sys, "platform", "linux"):
            result = cr.resolve_chrome_for_recording(base_dir=str(ROOT))
        self.assertFalse(result.ok)
        self.assertTrue(any("Windows" in e for e in result.errors))

    def test_resolve_no_chrome_installed_without_fallback(self) -> None:
        with patch.object(cr.sys, "platform", "win32"):
            with patch.object(cr, "_env_candidate_paths", return_value=[]):
                with patch.object(cr, "_windows_standard_paths", return_value=[]):
                    with patch.object(cr, "_where_chrome_exe", return_value=None):
                        with patch.object(cr, "chromium_fallback_allowed", return_value=False):
                            result = cr.resolve_chrome_for_recording(base_dir=str(ROOT))
        self.assertFalse(result.ok)
        self.assertTrue(any("Chrome" in e for e in result.errors))

    def test_to_dict_includes_preflight_fields(self) -> None:
        result = cr.ChromeResolveResult(ok=True, chrome_path="C:\\chrome.exe", source="env")
        d = result.to_dict()
        self.assertTrue(d["ok"])
        self.assertTrue(d["chrome_required"])
        self.assertIn("platform", d)
        self.assertIn("chromium_fallback_enabled", d)

    def test_candidate_chrome_executables_deduplicates(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            chrome = tmp.name
        try:
            with patch.object(cr.sys, "platform", "win32"):
                with patch.object(cr, "_env_candidate_paths", return_value=[(chrome, "env")]):
                    with patch.object(cr, "_windows_standard_paths", return_value=[chrome]):
                        with patch.object(cr, "_where_chrome_exe", return_value=chrome):
                            cands = cr.candidate_chrome_executables()
            self.assertEqual(cands, [chrome])
        finally:
            os.unlink(chrome)

    def test_api_recorder_preflight_uses_resolver(self) -> None:
        from tests.api.support import elia_test_app

        fake = cr.ChromeResolveResult(ok=True, chrome_path="C:\\chrome.exe", source="env")
        with patch("core.ui_automation.chrome_resolver.resolve_chrome_for_recording", return_value=fake):
            with elia_test_app() as (api, _):
                code, body = api.get_json("/api/recorder/preflight")
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["chrome_path"], "C:\\chrome.exe")


if __name__ == "__main__":
    unittest.main()
