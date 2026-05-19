"""Pruebas de licencia offline: revalidación criptográfica en cada consulta."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from core import elia_license as lic


class TestEliaLicenseZeroTrust(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._state_file = Path(self._tmp.name) / "license_state.json"
        self._fp = "a" * 32
        self._key = lic.build_activation_key(self._fp, lic.DURATION_PERM)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _patch_state(self):
        return patch.object(lic, "_state_path", return_value=self._state_file)

    def test_tamper_activated_without_key_fails(self) -> None:
        self._state_file.write_text(
            json.dumps({"first_run_ts": time.time(), "activated": True}),
            encoding="utf-8",
        )
        with self._patch_state(), patch.object(lic, "get_machine_fingerprint", return_value=self._fp):
            st = lic.get_license_status()
        self.assertFalse(st.activated)
        self.assertEqual(st.reason, "demo")

    def test_tamper_fake_key_fails(self) -> None:
        self._state_file.write_text(
            json.dumps(
                {
                    "first_run_ts": time.time(),
                    "activated": True,
                    "saved_activation_key": "ELIA-PERM-M-" + "0" * 64,
                }
            ),
            encoding="utf-8",
        )
        with self._patch_state(), patch.object(lic, "get_machine_fingerprint", return_value=self._fp):
            st = lic.get_license_status()
        self.assertEqual(st.reason, "demo")

    def test_valid_saved_key_activates(self) -> None:
        with self._patch_state(), patch.object(lic, "get_machine_fingerprint", return_value=self._fp):
            self.assertTrue(lic.activate_with_key(self._key))
            st = lic.get_license_status()
        self.assertTrue(st.activated)
        self.assertEqual(st.reason, "activated")
        self.assertIsNone(st.expires_at)

    def test_tamper_expires_at_extended_still_respects_duration(self) -> None:
        with self._patch_state(), patch.object(lic, "get_machine_fingerprint", return_value=self._fp):
            short_key = lic.build_activation_key(self._fp, lic.DURATION_15D)
            self.assertTrue(lic.activate_with_key(short_key))
            state = json.loads(self._state_file.read_text(encoding="utf-8"))
            state["expires_at"] = time.time() + 365 * 86400
            state["activated"] = True
            self._state_file.write_text(json.dumps(state), encoding="utf-8")
            past = time.time() + 20 * 86400
            with patch.object(lic.time, "time", return_value=past):
                st = lic.get_license_status()
        self.assertEqual(st.reason, "license_expired")


if __name__ == "__main__":
    unittest.main()
