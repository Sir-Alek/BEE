"""Tests del wizard de configuración IA."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.ai import setup_wizard


class TestSetupWizard(unittest.TestCase):
    def test_auto_complete_when_profile_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wiz = Path(td) / "ai_setup_wizard.json"
            with mock.patch.object(setup_wizard, "_wizard_path", lambda: wiz):
                with mock.patch.object(setup_wizard, "resolve_profile_from_ram", return_value="standard"):
                    with mock.patch.object(setup_wizard, "_profile_ready", return_value=True):
                        with mock.patch(
                            "psutil.virtual_memory",
                            return_value=mock.Mock(total=16 * 1024**3, available=6 * 1024**3),
                        ):
                            out = setup_wizard.evaluate_wizard()
        self.assertFalse(out["show_wizard"])
        self.assertTrue(out["wizard_completed"])

    def test_show_when_models_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wiz = Path(td) / "ai_setup_wizard.json"
            with mock.patch.object(setup_wizard, "_wizard_path", lambda: wiz):
                with mock.patch.object(setup_wizard, "resolve_profile_from_ram", return_value="standard"):
                    with mock.patch.object(setup_wizard, "_profile_ready", return_value=False):
                        with mock.patch(
                            "psutil.virtual_memory",
                            return_value=mock.Mock(total=16 * 1024**3, available=6 * 1024**3),
                        ):
                            out = setup_wizard.evaluate_wizard()
        self.assertTrue(out["show_wizard"])
        self.assertFalse(out["wizard_completed"])

    def test_off_profile_shows_until_completed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wiz = Path(td) / "ai_setup_wizard.json"
            with mock.patch.object(setup_wizard, "_wizard_path", lambda: wiz):
                with mock.patch.object(setup_wizard, "resolve_profile_from_ram", return_value="off"):
                    with mock.patch(
                        "psutil.virtual_memory",
                        return_value=mock.Mock(total=6 * 1024**3, available=2 * 1024**3),
                    ):
                        out = setup_wizard.evaluate_wizard()
                        self.assertTrue(out["show_wizard"])
                        setup_wizard.mark_wizard_completed(note="off")
                        out2 = setup_wizard.evaluate_wizard()
        self.assertFalse(out2["show_wizard"])


if __name__ == "__main__":
    unittest.main()
