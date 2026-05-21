"""
Smoke del flujo puppeteer_recorder vía API (stub de recorder.js, sin Chrome real).

Corre en CI por defecto (tests/run_integration.py).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.api.support import elia_test_app
from tests.paths import REPO_ROOT
from tests.support.recorder_stub import (
    fake_run_subprocess_with_automation_focus,
    install_puppeteer_recorder_stub,
)


class TestPuppeteerRecorderSmoke(unittest.TestCase):
    def setUp(self) -> None:
        install_puppeteer_recorder_stub()

    def test_stub_recorder_js_exits_cleanly(self) -> None:
        """Node stub: emula BROWSER_READY sin Puppeteer."""
        stub = REPO_ROOT / "tests" / "fixtures" / "stub_recorder.js"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "scripts" / "rec.js"
            proc = subprocess.run(
                ["node", str(stub), str(out.resolve()), "https://example.com"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(REPO_ROOT),
            )
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").lower()
                if "node" in err or "not found" in err or proc.returncode == 9009:
                    self.skipTest("Node.js no disponible")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("BROWSER_READY", proc.stdout)
            self.assertTrue(out.is_file(), proc.stdout + proc.stderr)

    def test_puppeteer_recorder_job_completes_with_stub(self) -> None:
        answers = ["SmokeProyecto", "grabacion_smoke.js", True, False]

        with patch(
            "core.ui_automation.recorder_focus.run_subprocess_with_automation_focus",
            fake_run_subprocess_with_automation_focus,
        ):
            with elia_test_app() as (api, _):
                code, body = api.post_json(
                    "/api/jobs/convert",
                    {"mode": "puppeteer_recorder", "url": "https://example.com"},
                )
                self.assertEqual(code, 200)
                job_id = body["job_id"]

                final = api.drive_job_prompts(job_id, answers, timeout=30.0)
                self.assertEqual(final["state"], "done", final.get("error"))
                self.assertEqual(final["mode"], "puppeteer_recorder")

    @unittest.skipUnless(sys.platform == "win32", "preflight solo aplica en Windows")
    def test_preflight_endpoint_reports_chrome_or_stub_ok(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.get_json("/api/recorder/preflight")
        self.assertEqual(code, 200)
        self.assertIn("ok", body)
        if not body["ok"] and os.environ.get("ELIA_ALLOW_CHROMIUM_FALLBACK"):
            self.skipTest("Chrome no instalado en este agente")


if __name__ == "__main__":
    unittest.main()
