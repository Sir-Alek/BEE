"""Tests for toolchain emit policy (checkout lock)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import toolchain_emit_policy as tep


class TestToolchainEmitPolicy(unittest.TestCase):
    def test_missing_profile_defaults_deferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(tep, "_module_dir", return_value=root), patch.object(
                tep, "_developer_override_active", return_value=False
            ):
                self.assertEqual(tep._profile_emit_mode(), tep._EMIT_DEFERRED)
                self.assertTrue(tep.checkout_parallel_emit_locked())

    def test_immediate_mode_unlocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / tep._PROFILE_PRIMARY).write_text(
                '{"parallel_emit_mode":"immediate"}',
                encoding="utf-8",
            )
            with patch.object(tep, "_module_dir", return_value=root):
                self.assertFalse(tep.checkout_parallel_emit_locked())

    def test_legacy_runtime_gate_open_maps_immediate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / tep._PROFILE_LEGACY).write_text(
                '{"runtime_gate":"open"}',
                encoding="utf-8",
            )
            with patch.object(tep, "_module_dir", return_value=root):
                self.assertFalse(tep.checkout_parallel_emit_locked())

    def test_developer_override_via_env(self) -> None:
        with patch.dict(os.environ, {"ELIA_PARALLEL_EMIT_OVERRIDE": "immediate"}, clear=False):
            self.assertTrue(tep._developer_override_active())
            self.assertFalse(tep.checkout_parallel_emit_locked())

    def test_frozen_runtime_never_locked(self) -> None:
        with patch.object(sys, "frozen", True, create=True):
            self.assertFalse(tep.checkout_parallel_emit_locked())


if __name__ == "__main__":
    unittest.main()
