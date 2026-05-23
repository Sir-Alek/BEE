"""Tests for offline error reporting and sanitization."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webui.error_reporting import (
    build_error_report,
    persist_job_error_snapshot,
    sanitize_text,
)


class TestErrorReporting(unittest.TestCase):
    def test_sanitize_redacts_user_home_paths(self) -> None:
        raw = r'Traceback:\n  File "C:\Users\Alejandro\Secret\app.py", line 1'
        out = sanitize_text(raw)
        self.assertNotIn("Alejandro", out)
        self.assertIn("ELIA://USER_HOME", out)

    def test_sanitize_redacts_bearer_token(self) -> None:
        raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        out = sanitize_text(raw)
        self.assertNotIn("eyJhbGci", out)
        self.assertIn("REDACTED", out)

    def test_build_error_report_includes_version_and_mode(self) -> None:
        report = build_error_report(
            job_id="00000000-0000-0000-0000-000000000001",
            mode="doc_to_bdd",
            error_msg="Sin documentos",
            traceback_str="ValueError: test",
        )
        self.assertIn("doc_to_bdd", report)
        self.assertIn("Sin documentos", report)
        self.assertIn("PRIVACY NOTICE", report)

    def test_persist_job_error_snapshot_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "logs" / "error_reports"
            with patch("webui.error_reporting.logs_dir", return_value=root / "logs"), patch(
                "webui.error_reporting.error_reports_dir",
                return_value=reports,
            ), patch(
                "webui.error_reporting.execution_log_path",
                return_value=root / "logs" / "elia_execution.log",
            ), patch("webui.error_reporting.configure_execution_logging"):
                path = persist_job_error_snapshot(
                    job_id="abc-123",
                    mode="demo",
                    error_msg="fail",
                    traceback_str="Traceback...",
                )
                self.assertTrue(path.is_file())
                text = path.read_text(encoding="utf-8")
                self.assertIn("fail", text)


if __name__ == "__main__":
    unittest.main()
