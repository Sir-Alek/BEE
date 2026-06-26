"""Tests for load test profile templates."""
from __future__ import annotations

import unittest

from core.api_automation.load_test_profiles import (
    list_profiles,
    parse_run_time_seconds,
    resolve_load_profile,
)


class TestLoadTestProfiles(unittest.TestCase):
    def test_parse_run_time_seconds(self) -> None:
        self.assertEqual(parse_run_time_seconds("1m"), 60)
        self.assertEqual(parse_run_time_seconds("30s"), 30)
        self.assertEqual(parse_run_time_seconds("2h"), 7200)

    def test_list_profiles(self) -> None:
        profiles = list_profiles()
        self.assertGreaterEqual(len(profiles), 6)
        self.assertEqual(profiles[0]["id"], "load")

    def test_stress_generates_stages(self) -> None:
        pid, stages, think, run_time = resolve_load_profile(
            "stress",
            users=40,
            spawn_rate=2,
            run_time="4m",
        )
        self.assertEqual(pid, "stress")
        self.assertIsNotNone(stages)
        self.assertEqual(len(stages or []), 4)
        self.assertEqual(run_time, "4m")
        self.assertEqual((think or {}).get("kind"), "between")

    def test_explicit_stages_respected(self) -> None:
        custom = [{"duration": 60, "users": 5, "spawn_rate": 1}]
        pid, stages, _, run_time = resolve_load_profile(
            "spike",
            users=10,
            spawn_rate=1,
            run_time="2m",
            stages=custom,
        )
        self.assertEqual(stages, custom)
        self.assertEqual(run_time, "2m")
        self.assertEqual(pid, "spike")


if __name__ == "__main__":
    unittest.main()
