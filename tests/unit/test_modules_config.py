"""Pruebas de módulos atados estrictamente a licencia vigente."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import elia_license as lic
from core import modules_config as mods


class TestModulesConfig(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patch = patch.dict(
            os.environ,
            {"ELIA_SKIP_LICENSE": "", "ELIA_ACTIVATION_KEY": ""},
            clear=False,
        )
        self._env_patch.start()
        self._tmp = tempfile.TemporaryDirectory()
        self._state_file = Path(self._tmp.name) / "license_state.json"
        self._fp = "b" * 32
        self._issue_ts = 1_700_000_000
        self._key_basic = lic.build_activation_key(
            self._fp, lic.DURATION_PERM, tier="basic", issue_ts=self._issue_ts
        )
        self._key_pro = lic.build_activation_key(
            self._fp, lic.DURATION_PERM, tier="professional", issue_ts=self._issue_ts
        )
        self._key_ml = lic.build_activation_key_v2(
            self._fp,
            lic.DURATION_PERM,
            mobile=True,
            legacy=True,
            issue_ts=self._issue_ts,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()
        self._env_patch.stop()

    def _patch_state(self):
        return patch.object(lic, "_state_path", return_value=self._state_file)

    def _patch_fp(self):
        return patch.object(lic, "get_machine_fingerprint", return_value=self._fp)

    def test_no_license_all_modules_disabled_including_doc(self) -> None:
        with self._patch_state(), self._patch_fp(), patch.object(lic, "_distribution_channel", return_value="release"):
            status = mods.list_modules()
        self.assertFalse(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])
        self.assertFalse(status["legacy_recording"])

    def test_basic_tier_modules(self) -> None:
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(self._key_basic)
            status = mods.list_modules()
        self.assertTrue(status["api_http_single"])
        self.assertFalse(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])
        self.assertFalse(status["legacy_recording"])

    def test_professional_tier_modules(self) -> None:
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(self._key_pro)
            status = mods.list_modules()
        self.assertTrue(status["doc_to_bdd"])
        self.assertTrue(status["mobile_recording"])
        self.assertFalse(status["legacy_recording"])

    def test_v2_ml_maps_to_enterprise(self) -> None:
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(self._key_ml)
            status = mods.list_modules()
        self.assertTrue(status["doc_to_bdd"])
        self.assertTrue(status["mobile_recording"])
        self.assertTrue(status["legacy_recording"])

    def test_expired_license_disables_all_modules(self) -> None:
        key_15d = lic.build_activation_key_v2(
            self._fp, lic.DURATION_15D, issue_ts=self._issue_ts
        )
        with self._patch_state(), self._patch_fp():
            lic.activate_with_key(key_15d)
            past = self._issue_ts + 20 * 86400
            with patch.object(lic.time, "time", return_value=past):
                status = mods.list_modules()
        self.assertFalse(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])

    def test_beta_channel_auto_entitlements(self) -> None:
        with self._patch_state(), self._patch_fp(), patch.object(
            lic, "_get_hidden_backup_paths", return_value=[]
        ), patch.object(lic, "_distribution_channel", return_value="beta"):
            with patch("core.beta_time_guard.check_beta_expiration") as mock_check:
                from core.beta_time_guard import BetaGuardResult

                mock_check.return_value = BetaGuardResult(
                    ok=True,
                    reason="beta_active",
                    message="ok",
                    effective_now=float(self._issue_ts),
                    deadline_ts=float(self._issue_ts + 86400),
                )
                status = mods.list_modules()
        self.assertEqual(status.get("tier"), "beta")
        self.assertTrue(status["legacy_recording"])
        self.assertTrue(status["doc_to_bdd"])

    def test_enable_module_has_no_effect(self) -> None:
        with self._patch_state(), self._patch_fp(), patch.object(lic, "_distribution_channel", return_value="release"):
            self.assertFalse(mods.enable_module("mobile_recording", "a" * 64))
            status = mods.list_modules()
        self.assertFalse(status["mobile_recording"])

    def test_revoke_clears_operational_modules(self) -> None:
        with self._patch_state(), self._patch_fp(), patch.object(lic, "_distribution_channel", return_value="release"):
            lic.activate_with_key(self._key_ml)
            lic.revoke_license_local(clear_backups=False)
            status = mods.list_modules()
        self.assertFalse(status["doc_to_bdd"])
        self.assertFalse(status["mobile_recording"])


if __name__ == "__main__":
    unittest.main()
