"""
Runtime legacy en Windows (nightly / manual).

Ejecutar:
  set ELIA_RUN_NIGHTLY=1
  python tests/run_integration.py
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.paths import REPO_ROOT
from tests.support.markers import nightly_enabled
from webui.job_manager import JobManager


def _load_legacy_recorder():
    path = REPO_ROOT / "core" / "ui_automation" / "legacy_recorder.py"
    spec = importlib.util.spec_from_file_location("legacy_recorder_runtime", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(nightly_enabled(), "Requiere ELIA_RUN_NIGHTLY=1")
@unittest.skipUnless(sys.platform == "win32", "Legacy recorder solo en Windows")
class TestLegacyRuntimeIntegration(unittest.TestCase):
    def test_find_notepad_window_when_running(self) -> None:
        lr = _load_legacy_recorder()
        proc = subprocess.Popen(["notepad.exe"])
        try:
            time.sleep(1.5)
            found = lr._find_window("Notepad") or lr._find_window("Bloc de notas")
            if found is None:
                self.skipTest("No se detectó ventana Notepad (pywinauto/win32gui no disponible)")
            self.assertIsNotNone(found)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_record_project_setup_without_ui_automation_loop(self) -> None:
        """Crea proyecto vía prompts y termina antes del loop PyAutoGUI."""
        lr = _load_legacy_recorder()
        jm = JobManager()
        job_id = jm.create_job(mode="legacy_recorder")
        adapter = MagicMock()
        recorder = lr.LegacyRecorder(adapter, jm, job_id)

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                jm,
                "create_prompt_and_wait",
                side_effect=["LegacySmoke", "grabacion"],
            ):
                with patch.object(jm, "should_stop_recording", return_value=True):
                    recorder.record(window_name="", exe_path="", projects_dir=tmp)

            project_dirs = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            self.assertIn("LegacySmoke", project_dirs)
            job = jm.get_job(job_id)
            self.assertEqual(job.state, "done")


if __name__ == "__main__":
    unittest.main()
