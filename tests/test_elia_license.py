"""Pruebas de licencia offline: activación obligatoria y respaldo de comodidad."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from core import elia_license as lic


class TestEliaLicense(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._state_file = Path(self._tmp.name) / "license_state.json"
        self._fp = "a" * 32
        self._key = lic.build_activation_key(self._fp, lic.DURATION_PERM)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _patch_state(self):
        return patch.object(lic, "_state_path", return_value=self._state_file)

    def _patch_backups(self, *paths: Path):
        return patch.object(lic, "_get_hidden_backup_paths", return_value=list(paths))

    def _patch_fp(self):
        return patch.object(lic, "get_machine_fingerprint", return_value=self._fp)

    def test_not_activated_without_key(self) -> None:
        with self._patch_state(), self._patch_fp():
            st = lic.get_license_status()
        self.assertFalse(st.ok)
        self.assertEqual(st.reason, "not_activated")

    def test_tamper_activated_without_key_fails(self) -> None:
        self._state_file.write_text(
            json.dumps({"activated": True}),
            encoding="utf-8",
        )
        with self._patch_state(), self._patch_fp():
            st = lic.get_license_status()
        self.assertEqual(st.reason, "not_activated")

    def test_valid_saved_key_activates(self) -> None:
        with self._patch_state(), self._patch_fp():
            self.assertTrue(lic.activate_with_key(self._key))
            st = lic.get_license_status()
            self.assertTrue(st.activated)
            self.assertEqual(st.reason, "activated")
            self.assertTrue(lic.can_run_jobs())

    def test_activation_restored_from_hidden_backup(self) -> None:
        backup = Path(self._tmp.name) / "backup.db"
        activated_ts = time.time() - 86400
        lic._write_activation_backup(backup, self._fp, self._key, activated_ts)
        self.assertFalse(self._state_file.is_file())

        with self._patch_state(), self._patch_backups(backup), self._patch_fp():
            st = lic.get_license_status()

        self.assertEqual(st.reason, "activated")
        self.assertTrue(self._state_file.is_file())
        restored = json.loads(self._state_file.read_text(encoding="utf-8"))
        self.assertEqual(restored.get("saved_activation_key"), self._key)

    def test_forged_activation_backup_ignored(self) -> None:
        backup = Path(self._tmp.name) / "forged.db"
        backup.write_text(
            json.dumps({"v": 2, "key": self._key, "ts": time.time(), "sig": "0" * 64}),
            encoding="utf-8",
        )
        with self._patch_state(), self._patch_backups(backup), self._patch_fp():
            st = lic.get_license_status()
        self.assertEqual(st.reason, "not_activated")

    def test_tamper_expires_at_extended_still_respects_duration(self) -> None:
        with self._patch_state(), self._patch_fp():
            short_key = lic.build_activation_key(self._fp, lic.DURATION_15D)
            self.assertTrue(lic.activate_with_key(short_key))
            state = json.loads(self._state_file.read_text(encoding="utf-8"))
            state["expires_at"] = time.time() + 365 * 86400
            self._state_file.write_text(json.dumps(state), encoding="utf-8")
            past = time.time() + 20 * 86400
            with patch.object(lic.time, "time", return_value=past):
                st = lic.get_license_status()
        self.assertEqual(st.reason, "license_expired")

    def test_fingerprint_ignores_hostname(self) -> None:
        with patch.object(
            lic,
            "_collect_hardware_parts",
            return_value=["board:ABC123", "arch:AMD64", "platform:win32"],
        ):
            fp_a = lic.get_machine_fingerprint()
        with patch.object(lic, "platform") as mock_platform:
            mock_platform.node.return_value = "OTHER-PC-NAME"
            with patch.object(
                lic,
                "_collect_hardware_parts",
                return_value=["board:ABC123", "arch:AMD64", "platform:win32"],
            ):
                fp_b = lic.get_machine_fingerprint()
        self.assertEqual(fp_a, fp_b)


if __name__ == "__main__":
    unittest.main()
