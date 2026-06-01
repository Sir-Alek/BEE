"""Pruebas de verificación de licencias v4 (Ed25519)."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from core import elia_license as lic
from core import license_verify as lv
from tests.helpers.license_v4_test import build_test_v4_beta_global, build_test_v4_key


class TestLicenseVerifyV4(unittest.TestCase):
    def setUp(self) -> None:
        self._fp = "b" * 32
        self._issue_ts = 1_770_000_000

    def test_v4_key_verifies_and_parses(self) -> None:
        key = build_test_v4_key(
            self._fp,
            tier_code="PRO",
            duration="365D",
            issue_ts=self._issue_ts,
        )
        self.assertTrue(key.startswith("ELIA-V4.test."))
        verified = lv.verify_v4_key(key, self._fp)
        self.assertIsNotNone(verified)
        assert verified is not None
        self.assertEqual(verified.tier, "professional")
        self.assertEqual(verified.duration, "365D")
        parsed = lic.parse_activation_key(key, self._fp)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.license_format, "v4")

    def test_v4_wrong_fingerprint_rejected(self) -> None:
        key = build_test_v4_key(self._fp, issue_ts=self._issue_ts)
        self.assertIsNone(lv.verify_v4_key(key, "c" * 32))

    def test_v4_perm_payload_rejected(self) -> None:
        import sys
        from pathlib import Path

        tools = Path(__file__).resolve().parents[2] / "license-tools"
        if str(tools) not in sys.path:
            sys.path.insert(0, str(tools))
        from license_sign import canonical_license_bytes, load_private_key, sign_payload

        payload = {
            "v": 4,
            "kid": "test",
            "fp": self._fp,
            "tier": "ENT",
            "dur": "PERM",
            "iat": self._issue_ts,
            "exp": self._issue_ts + 365 * 86400,
        }
        priv = load_private_key(Path("tests/fixtures/license_test_private.pem"))
        key = sign_payload(payload, priv)
        self.assertIsNone(lv.verify_v4_key(key, self._fp))

    def test_v4_beta_global_no_machine(self) -> None:
        key = build_test_v4_beta_global(exp_ts=self._issue_ts + 86400)
        self.assertIsNotNone(lv.verify_v4_key(key, None))
        self.assertTrue(lic.verify_activation_key(key))

    def test_v4_activate_and_status(self) -> None:
        issue_ts = int(time.time()) - 3600
        key = build_test_v4_key(
            self._fp,
            tier_code="BASIC",
            duration="30D",
            issue_ts=issue_ts,
        )
        tmp = tempfile.TemporaryDirectory()
        state_file = Path(tmp.name) / "license_state.json"
        with patch.object(lic, "_state_path", return_value=state_file), patch.object(
            lic, "get_machine_fingerprint", return_value=self._fp
        ), patch.object(lic, "_get_hidden_backup_paths", return_value=[]), patch.object(
            lic, "_distribution_channel", return_value="release"
        ):
            self.assertTrue(lic.activate_with_key(key))
            st = lic.get_license_status()
            self.assertTrue(st.ok)
            self.assertEqual(st.tier_name, "basic")
        tmp.cleanup()

    def test_kid_rotation_unknown_kid_rejected(self) -> None:
        keys_path = Path("core/license_public_keys.json")
        original = keys_path.read_text(encoding="utf-8")
        try:
            data = json.loads(original)
            data["keys"] = {"unknown-only": data["keys"]["test"]}
            keys_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            lv.reload_public_keys_cache()
            key = build_test_v4_key(self._fp, issue_ts=self._issue_ts)
            self.assertIsNone(lv.verify_v4_key(key, self._fp))
        finally:
            keys_path.write_text(original, encoding="utf-8")
            lv.reload_public_keys_cache()


if __name__ == "__main__":
    unittest.main()
