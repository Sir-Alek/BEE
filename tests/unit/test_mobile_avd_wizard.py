"""Pruebas del asistente AVD (orquestación Architect + fallback Studio)."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from core.ui_automation import mobile_avd_wizard as wiz


class TestOrchestrationAllowed(unittest.TestCase):
    def test_architect_and_beta(self) -> None:
        self.assertTrue(wiz.orchestration_allowed("architect"))
        self.assertTrue(wiz.orchestration_allowed("enterprise"))
        self.assertTrue(wiz.orchestration_allowed("tester", is_beta=True))
        self.assertFalse(wiz.orchestration_allowed("tester"))
        self.assertFalse(wiz.orchestration_allowed("basic"))


class TestResolveStudio(unittest.TestCase):
    def test_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            studio = os.path.join(tmp, "studio64.exe")
            open(studio, "wb").close()
            with patch.dict(os.environ, {"ELIA_ANDROID_STUDIO": studio}, clear=False):
                path, src = wiz.resolve_studio_executable()
            self.assertEqual(path, studio)
            self.assertEqual(src, "env")


class TestCreateAvd(unittest.TestCase):
    @patch.object(wiz, "list_avds", return_value=(["ELIA_Pixel_API34"], None))
    @patch.object(wiz, "_run_avdmanager")
    def test_skips_when_exists(self, mock_create, _list) -> None:
        ok, _msg, name = wiz._create_avd("standard")
        self.assertTrue(ok)
        self.assertEqual(name, "ELIA_Pixel_API34")
        mock_create.assert_not_called()

    @patch.object(wiz, "list_avds", return_value=([], None))
    @patch.object(wiz, "_run_avdmanager", return_value=(0, "Created", ""))
    def test_creates_when_missing(self, mock_create, _list) -> None:
        ok, _msg, name = wiz._create_avd("standard")
        self.assertTrue(ok)
        self.assertEqual(name, "ELIA_Pixel_API34")
        mock_create.assert_called_once()


class TestWizardCapabilities(unittest.TestCase):
    @patch.object(wiz, "resolve_studio_executable", return_value=(None, None))
    @patch.object(wiz, "list_devices", return_value=([], None))
    @patch.object(wiz, "list_avds", return_value=([], None))
    @patch.object(wiz, "resolve_emulator")
    @patch.object(wiz, "_resolve_cmdline_bin")
    @patch.object(wiz, "resolve_android_sdk", return_value=(r"C:\Sdk", "env"))
    def test_tester_not_allowed(self, _sdk, mock_bin, mock_emu, *_rest) -> None:
        mock_bin.side_effect = lambda name: (f"C:\\Sdk\\{name}.bat", "sdk")
        mock_emu.return_value = type("E", (), {"path": r"C:\Sdk\emulator\emulator.exe"})()
        caps = wiz.wizard_capabilities(tier="tester", is_beta=False)
        self.assertFalse(caps["orchestration_allowed"])
        self.assertEqual(len(caps["templates"]), 2)
        self.assertTrue(caps["sdk_ok"])
        self.assertTrue(caps["studio_missing_sdk_ok"])


class TestStudioAutoDetect(unittest.TestCase):
    @patch("os.path.isfile", return_value=True)
    @patch.object(wiz, "_where_studio_executable", return_value=(None, None))
    @patch.object(wiz, "_toolbox_studio_candidates")
    def test_toolbox_candidate(self, mock_toolbox, _where, _isfile) -> None:
        mock_toolbox.return_value = [(r"C:\Toolbox\studio64.exe", "jetbrains_toolbox")]
        with patch.dict(os.environ, {}, clear=True):
            path, source = wiz.resolve_studio_executable_auto()
        self.assertEqual(path, r"C:\Toolbox\studio64.exe")
        self.assertEqual(source, "jetbrains_toolbox")
