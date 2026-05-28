"""Tests fases 6-7: historial carga, entornos compartidos, deduplicación."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.api_automation.load_run_history import append_load_run, compare_load_runs, list_load_runs
from core.api_automation.shared_env_bridge import infer_web_origin, sync_api_environment_from_web
from core.api_automation.traffic_store import import_traffic_to_scenarios, save_traffic_file
from core.api_automation.models import ApiRequest, ApiTrafficCapture


class TestLoadRunHistory(unittest.TestCase):
    def test_append_and_compare(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                project = "HistProj"
                id_a = append_load_run(
                    project,
                    {
                        "users": 5,
                        "metrics": {"live": {"p95_ms": 100, "current_rps": 10, "total_requests": 50}},
                    },
                )
                id_b = append_load_run(
                    project,
                    {
                        "users": 10,
                        "metrics": {"live": {"p95_ms": 150, "current_rps": 20, "total_requests": 100}},
                    },
                )
                runs = list_load_runs(project)
                self.assertEqual(len(runs), 2)
                cmp = compare_load_runs(project, id_a, id_b)
                self.assertGreater(cmp["delta"]["p95_ms"]["diff"], 0)
            finally:
                ts.behave_projects_dir = original  # type: ignore


class TestSharedEnvBridge(unittest.TestCase):
    def test_infer_and_sync_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                project = "WebSync"
                root = Path(tmp) / "behave" / "api" / project
                scripts = root / "scripts"
                scripts.mkdir(parents=True)
                (root / "environments").mkdir(parents=True)
                (root / "project.json").write_text(
                    '{"default_environment":"dev","global_headers":{}}', encoding="utf-8"
                )
                (root / "environments" / "dev.json").write_text(
                    '{"name":"dev","variables":{"base_url":"https://old.test"}}', encoding="utf-8"
                )
                capture = ApiTrafficCapture(
                    source_url="https://app.ejemplo.com/login",
                    entries=[
                        ApiRequest(
                            id="1",
                            name="GET",
                            method="GET",
                            url="https://app.ejemplo.com/api/items",
                        )
                    ],
                )
                path = scripts / "rec_api_traffic.json"
                save_traffic_file(str(path), capture)
                origin = infer_web_origin(project)
                self.assertEqual(origin, "https://app.ejemplo.com")
                result = sync_api_environment_from_web(project, "dev")
                self.assertEqual(result["base_url"], "https://app.ejemplo.com")
            finally:
                ts.behave_projects_dir = original  # type: ignore


class TestTrafficDedupe(unittest.TestCase):
    def test_import_skips_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                project = "DedupeProj"
                root = Path(tmp) / "behave" / "api" / project
                (root / "scenarios").mkdir(parents=True)
                (root / "environments").mkdir(parents=True)
                (root / "project.json").write_text(
                    '{"default_environment":"dev","global_headers":{}}', encoding="utf-8"
                )
                (root / "environments" / "dev.json").write_text(
                    '{"name":"dev","variables":{}}', encoding="utf-8"
                )
                traffic = root / "scripts" / "cap_api_traffic.json"
                traffic.parent.mkdir(parents=True)
                req = ApiRequest(id="a", name="GET x", method="GET", url="https://api.test/x")
                save_traffic_file(str(traffic), ApiTrafficCapture(entries=[req, req]))
                first = import_traffic_to_scenarios(project, str(traffic))
                second = import_traffic_to_scenarios(project, str(traffic))
                self.assertEqual(first["imported"], 1)
                self.assertEqual(first["skipped"], 1)
                self.assertEqual(second["imported"], 0)
                self.assertEqual(second["skipped"], 2)
            finally:
                ts.behave_projects_dir = original  # type: ignore


if __name__ == "__main__":
    unittest.main()
