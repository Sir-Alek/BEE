"""Pruebas de módulos atados estrictamente a licencia vigente."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import elia_license as lic
from core import modules_config as mods


class TestModulesConfig(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._state_file = Path(self._tmp.name) / "license_state.json"
        self._fp = "b" * 32
        self._issue_ts = 1_700_000_000
        self._key_perm = lic.build_activation_key(
            self._fp, lic.DURATION_PERM, issue_ts=self._issue_ts
        )
        self._key_ml = lic.build_activation_key(
            self._fp,
            lic.DURATION_PERM,
            mobile=True,
            legacy=True,
            issue_ts=self._issue_ts,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _patch_state(self):
        return patch.object(lic, "_state_path", return_value=self._state_file)

    def _patch_fp(self):
        return patch.object(lic, "get_machine_fingerprint", return_value=self._fp)

    def test_no_license_all_modules_disabled_including_doc(self) -> None:
        with self._patch_state(), self._patch_fp():
            status = mods.list_modules()
        self.assertFalse(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])
        self.assertFalse(status["legacy_recording"])

    def test_active_license_enables_doc_to_bdd(self) -> None:
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(self._key_perm)
            status = mods.list_modules()
        self.assertTrue(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])
        self.assertFalse(status["legacy_recording"])

    def test_active_license_modules_from_key_flags(self) -> None:
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(self._key_ml)
            status = mods.list_modules()
        self.assertTrue(status["doc_to_bdd"])
        self.assertTrue(status["mobile_recording"])
        self.assertTrue(status["legacy_recording"])

    def test_expired_license_disables_all_modules(self) -> None:
        key_15d = lic.build_activation_key(
            self._fp, lic.DURATION_15D, issue_ts=self._issue_ts
        )
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(key_15d)
            past = self._issue_ts + 20 * 86400
            with patch.object(lic.time, "time", return_value=past):
                status = mods.list_modules()
        self.assertFalse(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])

    def test_enable_module_has_no_effect(self) -> None:
        with self._patch_state(), self._patch_fp():
            self.assertFalse(mods.enable_module("mobile_recording", "a" * 64))
            status = mods.list_modules()
        self.assertFalse(status["mobile_recording"])

    def test_revoke_clears_operational_modules(self) -> None:
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(self._key_ml)
            lic.revoke_license_local(clear_backups=False)
            status = mods.list_modules()
        self.assertFalse(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])


if __name__ == "__main__":
    unittest.main()
