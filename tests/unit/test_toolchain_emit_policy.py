"""Tests for toolchain emit policy (checkout lock)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import toolchain_emit_policy as tep


def _unlock_token() -> str:
    return "".join(map(chr, (105, 109, 109, 101, 100, 105, 97, 116, 101)))


def _unlock_payload() -> dict:
    return {tep._decode_blob(tep._BLOB_FIELD_A): _unlock_token()}


class TestToolchainEmitPolicy(unittest.TestCase):
    def test_missing_profile_defaults_locked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(tep, "_module_dir", return_value=root), patch.object(
                tep, "_developer_override_active", return_value=False
            ):
                self.assertTrue(tep.checkout_parallel_emit_locked())

    def test_unlock_profile_opens_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fname = tep._decode_blob(tep._BLOB_FN_PRIMARY)
            (root / fname).write_text(json.dumps(_unlock_payload()), encoding="utf-8")
            with patch.object(tep, "_module_dir", return_value=root):
                self.assertFalse(tep.checkout_parallel_emit_locked())

    def test_legacy_gate_field_opens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fname = tep._decode_blob(tep._BLOB_FN_FALLBACK)
            field = tep._decode_blob(tep._BLOB_FIELD_B)
            (root / fname).write_text(
                json.dumps({field: "".join(map(chr, (111, 112, 101, 110)))}),
                encoding="utf-8",
            )
            with patch.object(tep, "_module_dir", return_value=root):
                self.assertFalse(tep.checkout_parallel_emit_locked())

    def test_developer_override_via_env(self) -> None:
        env_key = tep._decode_blob(tep._BLOB_ENV_A)
        with patch.dict(os.environ, {env_key: "1"}, clear=False):
            self.assertTrue(tep._developer_override_active())
            self.assertFalse(tep.checkout_parallel_emit_locked())

    def test_frozen_runtime_never_locked(self) -> None:
        with patch.object(sys, "frozen", True, create=True):
            self.assertFalse(tep.checkout_parallel_emit_locked())


if __name__ == "__main__":
    unittest.main()
