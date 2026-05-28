"""Tests for API automation models and traffic store."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.api_automation.models import ApiRequest, ApiTrafficCapture
from core.api_automation.sanitize import is_noise_url, sanitize_header_value
from core.api_automation.traffic_store import (
    api_traffic_path_for_recording,
    ingest_capture_dict,
    list_traffic_captures,
    save_scenario,
    list_scenarios,
    traffic_path_for_script,
    traffic_path_for_web_recording,
)


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
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                req = ApiRequest(id="s1", name="GET items", method="GET", url="https://api.ejemplo.com/items")
                save_scenario(project, req, scenario_id="items.json")
                listed = list_scenarios(project)
                self.assertEqual(len(listed), 1)
            finally:
                ts.behave_projects_dir = original  # type: ignore

    def test_api_traffic_path_under_api_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                web_project = str(Path(tmp) / "behave" / "web" / "MiProyecto")
                output_js = str(Path(web_project) / "scripts" / "grabacion_test.js")
                expected = Path(tmp) / "behave" / "api" / "MiProyecto" / "scripts" / "grabacion_test_api_traffic.json"
                self.assertEqual(traffic_path_for_web_recording(web_project, output_js), str(expected))
                self.assertEqual(traffic_path_for_script(output_js), str(expected))
                path = api_traffic_path_for_recording("MiProyecto", "grabacion_test.js")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"version":1,"entries":[]}', encoding="utf-8")
                listed = list_traffic_captures("MiProyecto")
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["id"], "grabacion_test_api_traffic.json")
            finally:
                ts.behave_projects_dir = original  # type: ignore


if __name__ == "__main__":
    unittest.main()
