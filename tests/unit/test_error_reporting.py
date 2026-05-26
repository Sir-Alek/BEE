"""Tests for offline error reporting and sanitization."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webui.error_reporting import (
    beta_feedback_url,
    build_error_report,
    persist_job_error_snapshot,
    prune_error_reports,
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
        self.assertIn("AVISO DE PRIVACIDAD", report)
        self.assertIn("sanitizado localmente", report)

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

    def test_prune_error_reports_keeps_newest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "error_reports"
            report_dir.mkdir(parents=True)
            for i in range(5):
                p = report_dir / f"job-{i}.txt"
                p.write_text(f"report {i}", encoding="utf-8")
            with patch("webui.error_reporting.error_reports_dir", return_value=report_dir):
                removed = prune_error_reports(max_files=2)
            self.assertEqual(removed, 3)
            remaining = list(report_dir.glob("*.txt"))
            self.assertEqual(len(remaining), 2)

    def test_beta_feedback_url_env_overrides_constant(self) -> None:
        with patch.dict(os.environ, {"ELIA_BETA_FEEDBACK_URL": "https://env.example/form"}, clear=False):
            self.assertEqual(beta_feedback_url(), "https://env.example/form")

    def test_beta_feedback_url_uses_constant_when_env_empty(self) -> None:
        env_value = os.environ.pop("ELIA_BETA_FEEDBACK_URL", None)
        try:
            with patch("core._version.ELIA_BETA_FEEDBACK_URL", "https://default.example/form"):
                self.assertEqual(beta_feedback_url(), "https://default.example/form")
        finally:
            if env_value is not None:
                os.environ["ELIA_BETA_FEEDBACK_URL"] = env_value

    def test_beta_feedback_url_empty_when_unconfigured(self) -> None:
        env_value = os.environ.pop("ELIA_BETA_FEEDBACK_URL", None)
        try:
            with patch("core._version.ELIA_BETA_FEEDBACK_URL", ""):
                self.assertEqual(beta_feedback_url(), "")
        finally:
            if env_value is not None:
                os.environ["ELIA_BETA_FEEDBACK_URL"] = env_value


if __name__ == "__main__":
    unittest.main()
