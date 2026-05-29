"""Pruebas del guardián temporal beta."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import beta_time_guard as guard


class TestBetaTimeGuard(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._anchor = Path(self._tmp.name) / "anchor.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _patch_anchor(self):
        return patch.object(guard, "_anchor_path", return_value=self._anchor)

    def test_clock_tamper_detected_offline(self) -> None:
        future = 2_000_000_000.0
        self._anchor.write_text(json.dumps({"v": 1, "last_run_time": future}), encoding="utf-8")
        with self._patch_anchor(), patch.object(guard, "_fetch_network_time", return_value=None):
            with patch.object(guard.time, "time", return_value=future - 86400):
                with patch.object(guard, "elia_beta_deadline_ts", return_value=future + 86400):
                    result = guard.check_beta_expiration()
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "clock_tamper")

    def test_expired_when_past_deadline(self) -> None:
        deadline = 1_700_000_000.0
        with self._patch_anchor(), patch.object(guard, "_fetch_network_time", return_value=deadline + 10):
            with patch.object(guard, "elia_beta_deadline_ts", return_value=deadline):
                result = guard.check_beta_expiration()
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "beta_expired")


if __name__ == "__main__":
    unittest.main()
