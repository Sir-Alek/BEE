"""Tests para core.ai_policy."""
from __future__ import annotations

import unittest
from unittest import mock

from core import ai_policy


class TestAiPolicy(unittest.TestCase):
    def test_resolve_auto_capable_uses_ai(self):
        cap = {
            "capable": True,
            "reasons": [],
            "model_ok": True,
            "llama_ok": True,
            "ram_ok": True,
        }
        r = ai_policy.resolve_use_ai(preferences={"mode": "auto"}, capability=cap)
        self.assertTrue(r.use_ai)
        self.assertEqual(r.mode, "auto")
        self.assertFalse(r.degraded)

    def test_resolve_auto_not_capable_skips_ai(self):
        cap = {
            "capable": False,
            "reasons": ["RAM libre 2 GB < 4 GB requeridos"],
            "model_ok": True,
            "llama_ok": True,
            "ram_ok": False,
        }
        r = ai_policy.resolve_use_ai(preferences={"mode": "auto"}, capability=cap)
        self.assertFalse(r.use_ai)
        self.assertTrue(r.degraded)

    def test_resolve_off_always_false(self):
        cap = {"capable": True, "reasons": []}
        r = ai_policy.resolve_use_ai(preferences={"mode": "off"}, capability=cap)
        self.assertFalse(r.use_ai)

    def test_resolve_on_always_true(self):
        cap = {"capable": False, "runtime_ok": False, "reasons": ["no model"]}
        r = ai_policy.resolve_use_ai(preferences={"mode": "on"}, capability=cap)
        self.assertFalse(r.use_ai)

    def test_resolve_on_ignores_ram_but_needs_runtime(self):
        cap = {
            "capable": False,
            "runtime_ok": True,
            "ram_ok": False,
            "reasons": ["RAM libre baja"],
            "ram_min_free_gb": 4,
        }
        r = ai_policy.resolve_use_ai(preferences={"mode": "on"}, capability=cap)
        self.assertTrue(r.use_ai)
        self.assertTrue(r.degraded)

    def test_env_override(self):
        with mock.patch.dict("os.environ", {"ELIA_USE_AI": "0"}, clear=False):
            cap = {"capable": True, "reasons": []}
            r = ai_policy.resolve_use_ai(preferences={"mode": "on"}, capability=cap)
        self.assertFalse(r.use_ai)

    def test_save_and_load_preferences(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ai_preferences.json"
            with mock.patch.object(ai_policy, "_preferences_file", lambda: p):
                ai_policy.save_preferences(mode="off")
                loaded = ai_policy.load_preferences()
        self.assertEqual(loaded["mode"], "off")

    def test_assess_capability_ram_thresholds(self):
        with mock.patch.dict(
            "os.environ",
            {"ELIA_AI_MIN_RAM_GB": "8", "ELIA_AI_MIN_RAM_FREE_GB": "4"},
            clear=False,
        ):

            class VM:
                total = 16 * 1024**3
                available = 2 * 1024**3

            with mock.patch("psutil.virtual_memory", return_value=VM()):
                with mock.patch(
                    "core.ai.model_paths.get_primary_model_info",
                    return_value={"exists": True, "size_bytes": 1, "path": "/x", "frozen": False},
                ):
                    with mock.patch(
                        "core.ai.model_manager.is_ai_runtime_configured",
                        return_value=True,
                    ):
                        with mock.patch(
                            "core.ai.model_paths.is_profile_runtime_ready",
                            return_value=True,
                        ):
                            cap = ai_policy.assess_capability()
        self.assertFalse(cap["ram_ok"])
        self.assertFalse(cap["capable"])


    def test_assess_capability_standard_needs_5gb_free(self) -> None:
        class VM:
            total = 16 * 1024**3
            available = 4 * 1024**3

        with mock.patch("psutil.virtual_memory", return_value=VM()):
            with mock.patch(
                "core.ai.model_paths.get_primary_model_info",
                return_value={"exists": True, "size_bytes": 1, "path": "/x", "frozen": False},
            ):
                with mock.patch(
                    "core.ai.model_manager.is_ai_runtime_configured",
                    return_value=True,
                ):
                    with mock.patch(
                        "core.ai.model_paths.is_profile_runtime_ready",
                        return_value=True,
                    ):
                        cap = ai_policy.assess_capability()
        self.assertEqual(cap["profile"], "standard")
        self.assertFalse(cap["ram_ok"])
        self.assertFalse(cap["capable"])
        self.assertEqual(cap["ram_min_free_gb"], 5.0)


if __name__ == "__main__":
    unittest.main()
