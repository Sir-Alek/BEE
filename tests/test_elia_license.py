"""Pruebas de licencia offline: activación obligatoria, claves v2 con issue_ts."""
from __future__ import annotations

import json
import re
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
        self._issue_ts = 1_700_000_000
        self._key_v2_perm = lic.build_activation_key(
            self._fp, lic.DURATION_PERM, issue_ts=self._issue_ts
        )
        self._key_v2_15d = lic.build_activation_key(
            self._fp, lic.DURATION_15D, issue_ts=self._issue_ts
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _patch_state(self):
        return patch.object(lic, "_state_path", return_value=self._state_file)

    def _patch_backups(self, *paths: Path):
        return patch.object(lic, "_get_hidden_backup_paths", return_value=list(paths))

    def _patch_fp(self):
        return patch.object(lic, "get_machine_fingerprint", return_value=self._fp)

    def test_v2_key_format_includes_issue_ts(self) -> None:
        self.assertRegex(
            self._key_v2_15d,
            re.compile(
                r"^ELIA-15D-0-" + str(self._issue_ts) + r"-[0-9a-f]{64}$",
                re.IGNORECASE,
            ),
        )

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

    def test_valid_v2_key_activates(self) -> None:
        with self._patch_state(), self._patch_fp():
            self.assertTrue(lic.activate_with_key(self._key_v2_perm))
            st = lic.get_license_status()
            self.assertTrue(st.activated)
            self.assertEqual(st.reason, "activated")
            self.assertTrue(lic.can_run_jobs())

    def test_v2_tamper_activated_ts_in_json_does_not_extend(self) -> None:
        with self._patch_state(), self._patch_fp():
            self.assertTrue(lic.activate_with_key(self._key_v2_15d))
            state = json.loads(self._state_file.read_text(encoding="utf-8"))
            state["activated_ts"] = time.time()
            state["expires_at"] = time.time() + 365 * 86400
            self._state_file.write_text(json.dumps(state), encoding="utf-8")
            past = self._issue_ts + 20 * 86400
            with patch.object(lic.time, "time", return_value=past):
                st = lic.get_license_status()
        self.assertEqual(st.reason, "license_expired")

    def test_v2_tamper_issue_ts_in_key_string_fails(self) -> None:
        with self._patch_state(), self._patch_fp():
            self.assertTrue(lic.activate_with_key(self._key_v2_15d))
            state = json.loads(self._state_file.read_text(encoding="utf-8"))
            key = state["saved_activation_key"]
            tampered = key.replace(str(self._issue_ts), str(self._issue_ts + 99999), 1)
            state["saved_activation_key"] = tampered
            self._state_file.write_text(json.dumps(state), encoding="utf-8")
            st = lic.get_license_status()
        self.assertEqual(st.reason, "not_activated")

    def test_activation_restored_from_hidden_backup(self) -> None:
        backup = Path(self._tmp.name) / "backup.db"
        lic._write_activation_backup(backup, self._fp, self._key_v2_perm, float(self._issue_ts))
        self.assertFalse(self._state_file.is_file())

        with self._patch_state(), self._patch_backups(backup), self._patch_fp():
            st = lic.get_license_status()

        self.assertEqual(st.reason, "activated")
        self.assertTrue(self._state_file.is_file())

    def test_forged_activation_backup_ignored(self) -> None:
        backup = Path(self._tmp.name) / "forged.db"
        backup.write_text(
            json.dumps({"v": 2, "key": self._key_v2_perm, "ts": time.time(), "sig": "0" * 64}),
            encoding="utf-8",
        )
        with self._patch_state(), self._patch_backups(backup), self._patch_fp():
            st = lic.get_license_status()
        self.assertEqual(st.reason, "not_activated")

    def test_v1_legacy_key_still_valid(self) -> None:
        key_v1 = lic.build_activation_key_v1_legacy(self._fp, lic.DURATION_PERM)
        with self._patch_state(), self._patch_fp():
            self.assertTrue(lic.activate_with_key(key_v1))
            st = lic.get_license_status()
        self.assertEqual(st.reason, "activated")
        parsed = lic.parse_activation_key(key_v1, self._fp)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertIsNone(parsed.issue_ts)

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

    def test_revoke_license_local_clears_state(self) -> None:
        backup = Path(self._tmp.name) / "backup.db"
        with self._patch_state(), self._patch_fp(), self._patch_backups(backup):
            self.assertTrue(lic.activate_with_key(self._key_v2_perm))
            lic.revoke_license_local(clear_backups=True)
            st = lic.get_license_status()
            self.assertEqual(st.reason, "not_activated")
            self.assertFalse(lic.can_run_jobs())


if __name__ == "__main__":
    unittest.main()
