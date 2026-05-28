"""Tests for opt-in API evidence export."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.api_automation.api_evidence_report import (
    write_load_test_evidence_pdf,
    write_request_evidence_json,
    write_request_evidence_pdf,
)


class TestApiEvidenceReport(unittest.TestCase):
    def test_write_request_evidence_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                payload = {
                    "name": "GET health",
                    "environment": "dev",
                    "request": {"method": "GET", "url": "https://api.test/health"},
                    "result": {"status_code": 200, "ok": True, "body": '{"ok":true}'},
                }
                path = write_request_evidence_json("Demo", payload)
                self.assertTrue(path.endswith(".json"))
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data["name"], "GET health")
            finally:
                ts.behave_projects_dir = original  # type: ignore

    def test_write_request_evidence_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                path = write_request_evidence_pdf(
                    "Demo",
                    {
                        "name": "GET health",
                        "environment": "dev",
                        "request": {"method": "GET", "url": "https://api.test/health", "headers": {}},
                        "result": {
                            "status_code": 200,
                            "ok": True,
                            "elapsed_ms": 12.5,
                            "body": '{"ok":true}',
                            "assertions": [{"passed": True, "message": "HTTP 200"}],
                        },
                    },
                )
                self.assertTrue(path.endswith(".pdf"))
                self.assertTrue(Path(path).is_file())
            finally:
                ts.behave_projects_dir = original  # type: ignore

    def test_write_load_test_evidence_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.api_automation import traffic_store as ts

            original = ts.behave_projects_dir
            try:
                ts.behave_projects_dir = lambda platform="api": Path(tmp) / "behave" / platform  # type: ignore
                path = write_load_test_evidence_pdf(
                    "Demo",
                    lines=["Type     Name  # reqs  # fails", "Aggregated", "Total requests: 100"],
                    users=5,
                    run_time="1m",
                )
                self.assertTrue(Path(path).is_file())
            finally:
                ts.behave_projects_dir = original  # type: ignore


if __name__ == "__main__":
    unittest.main()
