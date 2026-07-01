"""Tests for run diagnostic parsing (P2)."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from core.test_runner.run_diagnostic import (
    RUN_HISTORY_MAX,
    build_run_diagnostic,
    list_project_run_history,
    load_project_run_manifest,
    parse_behave_failures,
    persist_run_manifest,
    prune_project_run_history,
)


class TestRunDiagnostic(unittest.TestCase):
    def test_parse_hook_error_and_failing_scenario(self) -> None:
        lines = [
            "HOOK-ERROR in before_scenario: Exception: Archivo JSON no encontrado",
            "Failing scenarios:",
            "  features/demo_login.feature:4  Login exitoso con usuario estandar",
            "ERROR: <-- Escenario FALLIDO: Login exitoso con usuario estandar",
        ]
        failures = parse_behave_failures(lines)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["scenario"], "Login exitoso con usuario estandar")
        self.assertIn("Archivo JSON", failures[0]["hook_error"])

    def test_parse_step_failed_and_diagnostic_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            diag = build_run_diagnostic(
                project_path=tmp,
                lines=[
                    "    [Step] FALLIDO: When inicia sesion con usuario \"x\" y contraseña \"y\" - TimeoutException: Elemento no encontrado",
                    "2026-07-01 12:08:38,700 WARNING: Problema en diagnóstico general: Message: no such window: target window already closed",
                ],
                since_ts=time.time(),
                return_code=1,
                kind="behave",
            )
            self.assertEqual(len(diag["failures"]), 1)
            failure = diag["failures"][0]
            self.assertIn("TimeoutException", failure["step_error"])
            self.assertIn("When inicia sesion", failure["failed_step"])
            self.assertEqual(failure["failed_step_keyword"], "When")
            self.assertEqual(failure["exception_type"], "TimeoutException")
            self.assertIn("TimeoutException", failure["failure_reason"])

    def test_build_diagnostic_lists_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs_dir = root / "outputs" / "logs"
            logs_dir.mkdir(parents=True)
            log = logs_dir / "Loginexitosoconusuarioestandar.txt"
            log.write_text("log line", encoding="utf-8")
            since = time.time() - 5
            diag = build_run_diagnostic(
                project_path=str(root),
                lines=[
                    "Failing scenarios:",
                    "  features/demo_login.feature:4  Login exitoso con usuario estandar",
                ],
                since_ts=since,
                return_code=1,
                kind="behave",
            )
            self.assertFalse(diag["ok"])
            self.assertEqual(len(diag["failures"]), 1)
            self.assertGreaterEqual(len(diag["logs"]), 1)

    def test_persist_and_list_run_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "00000000-0000-0000-0000-000000000001"
            diagnostic = build_run_diagnostic(
                project_path=str(root),
                lines=[
                    "    [Step] FALLIDO: Then ve el catalogo - AssertionError: Catalogo no visible",
                ],
                since_ts=time.time(),
                return_code=1,
                kind="behave",
                run_id=run_id,
                platform="web",
                project="Demo",
            )
            path = persist_run_manifest(str(root), run_id, diagnostic)
            self.assertIsNotNone(path)
            self.assertTrue(path.is_file())
            loaded = load_project_run_manifest(str(root), run_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["run_id"], run_id)
            history = list_project_run_history(str(root), limit=5)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["run_id"], run_id)
            self.assertIn("AssertionError", history[0]["failure_reason"] or "")

    def test_prune_run_history_keeps_max_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hist_dir = root / "outputs" / ".elia" / "runs"
            hist_dir.mkdir(parents=True)
            for i in range(7):
                path = hist_dir / f"run-{i}.json"
                path.write_text(json.dumps({"run_id": f"run-{i}"}), encoding="utf-8")
                time.sleep(0.01)
            removed = prune_project_run_history(str(root), max_files=RUN_HISTORY_MAX)
            self.assertEqual(removed, 2)
            remaining = list(hist_dir.glob("*.json"))
            self.assertEqual(len(remaining), RUN_HISTORY_MAX)
            history = list_project_run_history(str(root))
            self.assertLessEqual(len(history), RUN_HISTORY_MAX)


if __name__ == "__main__":
    unittest.main()
