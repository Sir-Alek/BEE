"""Tests para perfiles IA por RAM."""
from __future__ import annotations

import unittest

from core.ai.profiles import min_free_gb_for_profile, resolve_profile_from_ram


class TestAiProfiles(unittest.TestCase):
    def test_off_below_8gb(self) -> None:
        self.assertEqual(resolve_profile_from_ram(total_gb=7.5, available_gb=4.0), "off")

    def test_lite_at_8gb(self) -> None:
        self.assertEqual(resolve_profile_from_ram(total_gb=8.0, available_gb=4.0), "lite")

    def test_standard_above_8gb(self) -> None:
        self.assertEqual(resolve_profile_from_ram(total_gb=8.1, available_gb=5.0), "standard")
        self.assertEqual(resolve_profile_from_ram(total_gb=16.0, available_gb=6.0), "standard")
        self.assertEqual(resolve_profile_from_ram(total_gb=32.0, available_gb=10.0), "standard")

    def test_min_free_by_profile(self) -> None:
        self.assertEqual(min_free_gb_for_profile("lite"), 4.0)
        self.assertEqual(min_free_gb_for_profile("standard"), 5.0)


if __name__ == "__main__":
    unittest.main()
