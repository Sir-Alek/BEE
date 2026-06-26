"""Tests for API automation models and traffic store."""
from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from core.api_automation.collection_store import (
    DEFAULT_COLLECTION_ID,
    create_collection,
    delete_collection,
    list_collections,
)
from core.api_automation.models import ApiRequest
from core.api_automation.sanitize import is_noise_url, sanitize_header_value
from core.api_automation.traffic_store import (
    api_traffic_path_for_recording,
    delete_scenario,
    import_requests_as_collection,
    ingest_capture_dict,
    list_traffic_captures,
    list_scenarios,
    save_scenario,
    traffic_path_for_script,
    traffic_path_for_web_recording,
)


@contextmanager
def _patch_api_root(tmp: str):
    root = Path(tmp) / "behave"

    def behave_dir(platform: str = "api") -> Path:
        return root / platform

    with (
        patch("core.elia_paths.behave_projects_dir", behave_dir),
        patch("core.api_automation.traffic_store.behave_projects_dir", behave_dir),
        patch("core.api_automation.collection_store.behave_projects_dir", behave_dir),
    ):
        yield


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
            with _patch_api_root(tmp):
                req = ApiRequest(id="s1", name="GET items", method="GET", url="https://api.ejemplo.com/items")
                sid = save_scenario(project, req, scenario_id="items.json")
                self.assertEqual(sid, f"{DEFAULT_COLLECTION_ID}/items.json")
                listed = list_scenarios(project)
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["name"], "GET items")
                self.assertEqual(listed[0]["collection_id"], DEFAULT_COLLECTION_ID)

    def test_delete_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = "TestApi"
            with _patch_api_root(tmp):
                req = ApiRequest(id="s1", name="DELETE me", method="GET", url="https://api.ejemplo.com/x")
                sid = save_scenario(project, req, scenario_id="to_delete.json")
                self.assertEqual(len(list_scenarios(project)), 1)
                delete_scenario(project, sid)
                self.assertEqual(len(list_scenarios(project)), 0)

    def test_import_requests_as_collection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = "TestApi"
            with _patch_api_root(tmp):
                reqs = [
                    ApiRequest(id="a", name="Req A", method="GET", url="https://api.ejemplo.com/a"),
                    ApiRequest(id="b", name="Req B", method="POST", url="https://api.ejemplo.com/b"),
                ]
                result = import_requests_as_collection(
                    project,
                    reqs,
                    collection_name="Mi API",
                    source="import",
                )
                self.assertEqual(result["count"], 2)
                self.assertEqual(result["collection_name"], "Mi API")
                cols = list_collections(project)
                imported = [c for c in cols if c["id"] == result["collection_id"]]
                self.assertEqual(len(imported), 1)
                self.assertEqual(imported[0]["scenario_count"], 2)
                listed = list_scenarios(project)
                self.assertEqual(len(listed), 2)
                self.assertTrue(all(s["collection_id"] == result["collection_id"] for s in listed))

    def test_delete_collection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = "TestApi"
            with _patch_api_root(tmp):
                cid = create_collection(project, "Temporal", source="manual")
                req = ApiRequest(id="x", name="X", method="GET", url="https://api.ejemplo.com/x")
                save_scenario(project, req, collection_id=cid)
                self.assertEqual(len(list_scenarios(project)), 1)
                deleted = delete_collection(project, cid)
                self.assertEqual(deleted, 1)
                self.assertEqual(len(list_scenarios(project)), 0)
                self.assertFalse(any(c["id"] == cid for c in list_collections(project)))

    def test_delete_default_collection_clears_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = "TestApi"
            with _patch_api_root(tmp):
                req = ApiRequest(id="x", name="X", method="GET", url="https://api.ejemplo.com/x")
                save_scenario(project, req, scenario_id="x.json")
                self.assertEqual(len(list_scenarios(project)), 1)
                deleted = delete_collection(project, DEFAULT_COLLECTION_ID)
                self.assertEqual(deleted, 1)
                self.assertEqual(len(list_scenarios(project)), 0)
                self.assertTrue(any(c["id"] == DEFAULT_COLLECTION_ID for c in list_collections(project)))

    def test_api_traffic_path_under_api_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with _patch_api_root(tmp):
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


if __name__ == "__main__":
    unittest.main()
