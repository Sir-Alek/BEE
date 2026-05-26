"""Tests for API automation models and traffic store."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.api_automation.models import ApiRequest, ApiTrafficCapture
from core.api_automation.sanitize import is_noise_url, sanitize_header_value
from core.api_automation.traffic_store import ingest_capture_dict, save_scenario, list_scenarios


class TestApiAutomation(unittest.TestCase):
    def test_sanitize_authorization_header(self) -> None:
        self.assertEqual(sanitize_header_value("Authorization", "Bearer secret"), "REDACTED")

    def test_is_noise_url(self) -> None:
        self.assertTrue(is_noise_url("https://www.google-analytics.com/collect"))
        self.assertFalse(is_noise_url("https://api.ejemplo.com/users"))

    def test_ingest_capture_dict(self) -> None:
        capture = ingest_capture_dict(
            {
                "version": 1,
                "entries": [
                    {
                        "id": "req-1",
                        "method": "GET",
                        "url": "https://api.ejemplo.com/items",
                        "request_headers": {"Authorization": "Bearer x"},
                        "response_status": 200,
                        "response_body": '{"ok":true}',
                    }
                ],
            }
        )
        self.assertEqual(len(capture.entries), 1)
        self.assertEqual(capture.entries[0].headers.get("Authorization"), "REDACTED")

    def test_save_and_list_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = "TestApi"
            root = Path(tmp) / "behave" / "api" / project
            root.mkdir(parents=True)
            (root / "scenarios").mkdir()
            from core import elia_paths

            original = elia_paths.behave_projects_dir
            try:
                elia_paths.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                req = ApiRequest(id="s1", name="GET items", method="GET", url="https://api.ejemplo.com/items")
                save_scenario(project, req, scenario_id="items.json")
                listed = list_scenarios(project)
                self.assertEqual(len(listed), 1)
            finally:
                elia_paths.behave_projects_dir = original  # type: ignore


if __name__ == "__main__":
    unittest.main()
