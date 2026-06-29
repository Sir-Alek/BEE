"""Tests for API scenario index and fast listing."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.api_automation import scenario_index as idx
from core.api_automation.collection_store import create_collection, list_collections
from core.api_automation.models import ApiRequest
from core.api_automation.traffic_store import list_scenarios, save_scenario


class TestScenarioIndex(unittest.TestCase):
    def test_list_scenarios_uses_index_without_reading_each_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def fake_behave_projects_dir(platform: str) -> Path:
                self.assertEqual(platform, "api")
                return root

            with patch("core.api_automation.collection_store.behave_projects_dir", fake_behave_projects_dir):
                with patch("core.api_automation.traffic_store.behave_projects_dir", fake_behave_projects_dir):
                    project = "PerfProj"
                    req = ApiRequest(
                        id="req1",
                        name="Login usuario",
                        method="GET",
                        url="{{base_url}}/login",
                    )
                    save_scenario(project, req)
                    index_path = root / project / "scenarios_index.json"
                    self.assertTrue(index_path.is_file())

                    json_path = root / project / "scenarios" / "_default" / "req1.json"
                    self.assertTrue(json_path.is_file())

                    original_load = json.load
                    load_calls = {"n": 0}

                    def counting_load(fp, *args, **kwargs):
                        load_calls["n"] += 1
                        return original_load(fp, *args, **kwargs)

                    with patch("core.api_automation.scenario_index.json.load", side_effect=counting_load):
                        collections = list_collections(project)
                        scenarios = list_scenarios(project, collections=collections)

                    self.assertEqual(load_calls["n"], 0)
                    self.assertEqual(len(scenarios), 1)
                    self.assertEqual(scenarios[0]["name"], "Login usuario")

    def test_rebuild_index_picks_display_names(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def fake_behave_projects_dir(platform: str) -> Path:
                return root

            with patch("core.api_automation.collection_store.behave_projects_dir", fake_behave_projects_dir):
                    project = "IdxProj"
                    cid = create_collection(project, "Importada", source="postman")
                    sdir = root / project / "scenarios" / cid
                    sdir.mkdir(parents=True, exist_ok=True)
                    path = sdir / "abc.json"
                    path.write_text(
                        json.dumps({"name": "Crear pedido", "method": "POST", "url": "/orders"}),
                        encoding="utf-8",
                    )
                    rebuilt = idx.rebuild_index(project)
                    entry = rebuilt["entries"].get(f"{cid}/abc.json")
                    self.assertIsNotNone(entry)
                    assert entry is not None
                    self.assertEqual(entry["name"], "Crear pedido")


if __name__ == "__main__":
    unittest.main()
