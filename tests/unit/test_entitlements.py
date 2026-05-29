"""Pruebas de tiers y mapa de features."""
from __future__ import annotations

import unittest

from core.entitlements import (
    TIER_BASIC,
    TIER_BETA,
    TIER_ENTERPRISE,
    TIER_PROFESSIONAL,
    get_tier_flags,
    infer_tier_from_v2_mods,
    legacy_modules_from_features,
)


class TestEntitlements(unittest.TestCase):
    def test_basic_flags(self) -> None:
        f = get_tier_flags(TIER_BASIC)
        self.assertTrue(f["web_recording"])
        self.assertTrue(f["api_http_single"])
        self.assertFalse(f["doc_to_bdd"])
        self.assertFalse(f["mobile_recording"])
        self.assertFalse(f["api_locust"])

    def test_professional_flags(self) -> None:
        f = get_tier_flags(TIER_PROFESSIONAL)
        self.assertTrue(f["doc_to_bdd"])
        self.assertTrue(f["mobile_recording"])
        self.assertTrue(f["api_postman_suites"])
        self.assertFalse(f["legacy_recording"])
        self.assertFalse(f["api_locust"])

    def test_enterprise_flags(self) -> None:
        f = get_tier_flags(TIER_ENTERPRISE)
        self.assertTrue(f["legacy_recording"])
        self.assertTrue(f["api_locust"])
        self.assertTrue(f["team_memory_crypto"])
        self.assertTrue(f["publishers_enterprise"])

    def test_beta_all_on(self) -> None:
        f = get_tier_flags(TIER_BETA)
        self.assertTrue(all(f.values()))

    def test_v2_mod_inference(self) -> None:
        self.assertEqual(infer_tier_from_v2_mods(False, False), TIER_BASIC)
        self.assertEqual(infer_tier_from_v2_mods(True, False), TIER_PROFESSIONAL)
        self.assertEqual(infer_tier_from_v2_mods(False, True), TIER_ENTERPRISE)

    def test_legacy_modules_from_features(self) -> None:
        legacy = legacy_modules_from_features(get_tier_flags(TIER_BASIC))
        self.assertTrue(legacy["api_testing"])
        self.assertFalse(legacy["doc_to_bdd"])


if __name__ == "__main__":
    unittest.main()
