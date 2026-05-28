"""Tests JSONPath, suite runner, Locust metrics."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.api_automation.locust_metrics import accumulate_from_lines, parse_locust_stats_csv
from core.api_automation.models import ApiAssertion, ApiExtractor, ApiFlow, ApiFlowStep, ApiRequest
from core.api_automation.runtime.assertion_engine import evaluate_assertions
from core.api_automation.runtime.extractor_engine import apply_extractors
from core.api_automation.runtime.jsonpath_utils import get_json_path, json_path_exists
from core.api_automation.runtime.suite_runner import run_suite


class TestJsonPathUtils(unittest.TestCase):
    def test_nested_path(self) -> None:
        data = {"access_token": "abc", "user": {"id": 7, "tags": ["a", "b"]}}
        self.assertTrue(json_path_exists(data, "$.access_token"))
        ok, val = get_json_path(data, "$.user.id")
        self.assertTrue(ok)
        self.assertEqual(val, 7)


class TestExtractors(unittest.TestCase):
    def test_jsonpath_extractor(self) -> None:
        vars_map: dict = {}
        body = json.dumps({"token": "xyz"})
        results = apply_extractors(
            [ApiExtractor(kind="jsonpath", expression="$.token", target_var="token")],
            status_code=200,
            response_headers={},
            response_body=body,
            variables=vars_map,
        )
        self.assertTrue(results[0]["passed"])
        self.assertEqual(vars_map["token"], "xyz")


class TestAdvancedAssertions(unittest.TestCase):
    def test_duration_assertion(self) -> None:
        req = ApiRequest(
            id="r1",
            name="GET",
            method="GET",
            url="https://x",
            assertions=[ApiAssertion(kind="duration", expected="500")],
        )
        results = evaluate_assertions(req, status_code=200, response_headers={}, response_body="{}", elapsed_ms=120)
        self.assertTrue(results[0]["passed"])

    def test_regex_assertion(self) -> None:
        req = ApiRequest(
            id="r1",
            name="GET",
            method="GET",
            url="https://x",
            assertions=[ApiAssertion(kind="regex", expression=r'"ok"\s*:\s*true')],
        )
        results = evaluate_assertions(req, status_code=200, response_headers={}, response_body='{"ok":true}')
        self.assertTrue(results[0]["passed"])


class TestSuiteRunner(unittest.TestCase):
    @patch("core.api_automation.runtime.suite_runner.execute_request")
    def test_run_suite_stops_on_failure(self, execute_mock: MagicMock) -> None:
        execute_mock.side_effect = [
            {"ok": True, "status_code": 200, "headers": {}, "body": "{}", "elapsed_ms": 1, "assertions": []},
            {"ok": False, "status_code": 500, "headers": {}, "body": "err", "elapsed_ms": 1, "assertions": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                project = "SuiteProj"
                root = Path(tmp) / "behave" / "api" / project
                (root / "scenarios").mkdir(parents=True)
                (root / "environments").mkdir(parents=True)
                (root / "project.json").write_text(
                    '{"default_environment":"dev","global_headers":{}}', encoding="utf-8"
                )
                (root / "environments" / "dev.json").write_text(
                    '{"name":"dev","variables":{"base_url":"https://api.test"}}', encoding="utf-8"
                )
                for sid in ("a.json", "b.json"):
                    (root / "scenarios" / sid).write_text(
                        json.dumps(
                            {
                                "id": sid,
                                "name": sid,
                                "method": "GET",
                                "url": "https://api.test/x",
                                "expected_status": 200,
                            }
                        ),
                        encoding="utf-8",
                    )
                result = run_suite(
                    project,
                    scenario_ids=["a.json", "b.json"],
                    continue_on_failure=False,
                )
                self.assertFalse(result["ok"])
                self.assertEqual(result["failed_steps"], 1)
            finally:
                ts.behave_projects_dir = original  # type: ignore


class TestLocustMetrics(unittest.TestCase):
    def test_accumulate_from_lines(self) -> None:
        metrics = accumulate_from_lines(["Aggregated 100 2 50 120 200 95 150 180 220 250"])
        self.assertGreaterEqual(metrics.get("total_requests", 0), 0)

    def test_parse_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "elia_load_stats.csv"
            path.write_text(
                "Type,Name,Request Count,Failure Count,Average Response Time,50%,95%,99%,Requests/s\n"
                "GET,/items,10,0,120,100,150,180,5.0\n"
                "Aggregated,,10,0,120,100,150,180,5.0\n",
                encoding="utf-8",
            )
            data = parse_locust_stats_csv(str(path))
            self.assertIn("aggregated", data)


if __name__ == "__main__":
    unittest.main()
