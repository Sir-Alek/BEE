"""Pruebas de tiers y mapa de features."""
from __future__ import annotations

import unittest

from core.entitlements import (
    TIER_ARCHITECT,
    TIER_BASIC,
    TIER_BETA,
    TIER_ENTERPRISE,
    TIER_PROFESSIONAL,
    TIER_TESTER,
    get_tier_flags,
    infer_tier_from_v2_mods,
    legacy_modules_from_features,
    normalize_tier,
    tier_display_name,
)


class TestEntitlements(unittest.TestCase):
    def test_legacy_basic_maps_to_tester_features(self) -> None:
        f = get_tier_flags(TIER_BASIC)
        self.assertTrue(f["web_recording"])
        self.assertTrue(f["doc_to_bdd"])
        self.assertTrue(f["mobile_recording"])
        self.assertTrue(f["api_postman_suites"])
        self.assertFalse(f["legacy_recording"])
        self.assertFalse(f["api_locust"])

    def test_tester_flags(self) -> None:
        f = get_tier_flags(TIER_TESTER)
        self.assertTrue(f["doc_to_bdd"])
        self.assertTrue(f["mobile_recording"])
        self.assertTrue(f["api_postman_suites"])
        self.assertTrue(f["publishers_standard"])
        self.assertFalse(f["legacy_recording"])
        self.assertFalse(f["api_locust"])

    def test_legacy_pro_maps_to_tester(self) -> None:
        self.assertEqual(normalize_tier(TIER_PROFESSIONAL), TIER_TESTER)
        self.assertEqual(get_tier_flags(TIER_PROFESSIONAL), get_tier_flags(TIER_TESTER))

    def test_architect_flags(self) -> None:
        f = get_tier_flags(TIER_ARCHITECT)
        self.assertTrue(f["legacy_recording"])
        self.assertTrue(f["api_locust"])
        self.assertTrue(f["team_memory_crypto"])
        self.assertTrue(f["publishers_enterprise"])

    def test_legacy_enterprise_maps_to_architect(self) -> None:
        self.assertEqual(normalize_tier(TIER_ENTERPRISE), TIER_ARCHITECT)
        self.assertEqual(get_tier_flags(TIER_ENTERPRISE), get_tier_flags(TIER_ARCHITECT))

    def test_beta_all_on(self) -> None:
        f = get_tier_flags(TIER_BETA)
        self.assertTrue(all(f.values()))

    def test_v2_mod_inference(self) -> None:
        self.assertEqual(infer_tier_from_v2_mods(False, False), TIER_TESTER)
        self.assertEqual(infer_tier_from_v2_mods(True, False), TIER_TESTER)
        self.assertEqual(infer_tier_from_v2_mods(False, True), TIER_ARCHITECT)

    def test_display_names(self) -> None:
        self.assertEqual(tier_display_name(TIER_TESTER), "ELIA Tester")
        self.assertEqual(tier_display_name(TIER_ARCHITECT), "ELIA Architect")
        self.assertEqual(tier_display_name(TIER_BASIC), "ELIA Tester")
        self.assertEqual(tier_display_name(TIER_ENTERPRISE), "ELIA Architect")

    def test_legacy_modules_from_features(self) -> None:
        legacy = legacy_modules_from_features(get_tier_flags(TIER_TESTER))
        self.assertTrue(legacy["api_testing"])
        self.assertTrue(legacy["doc_to_bdd"])


if __name__ == "__main__":
    unittest.main()
