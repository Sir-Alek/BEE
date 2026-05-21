"""Pruebas de capacidades del grabador legacy (Windows desktop)."""
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.paths import REPO_ROOT

ROOT = REPO_ROOT


def _load_legacy_recorder_py():
    path = ROOT / "core" / "ui_automation" / "legacy_recorder.py"
    spec = importlib.util.spec_from_file_location("legacy_recorder_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lr = _load_legacy_recorder_py()


class TestLegacyRecorderCapabilities(unittest.TestCase):
    def test_mk_prompt_has_uuid_id(self) -> None:
        prompt = lr._mk_prompt("yes_no", title="T", message="M")
        self.assertEqual(prompt.type, "yes_no")
        self.assertTrue(len(prompt.prompt_id) >= 8)

    def test_launch_exe_missing_file(self) -> None:
        self.assertIsNone(lr._launch_exe("/nonexistent/app.exe"))

    def test_launch_exe_valid_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            tmp.write(b"")
            exe = tmp.name
        try:
            with patch.object(lr.subprocess, "Popen") as mock_popen:
                mock_popen.return_value = MagicMock()
                proc = lr._launch_exe(exe)
            self.assertIsNotNone(proc)
            mock_popen.assert_called_once()
        finally:
            os.unlink(exe)

    def test_find_window_non_windows_returns_none(self) -> None:
        with patch.object(lr.sys, "platform", "linux"):
            self.assertIsNone(lr._find_window("Notepad"))

    def test_find_window_returns_none_for_unknown_title_on_windows(self) -> None:
        with patch.object(lr.sys, "platform", "win32"):
            result = lr._find_window("__ventana_inexistente_xyz__")
        self.assertIsNone(result)

    def test_record_rejects_non_windows(self) -> None:
        from webui.job_manager import JobManager

        jm = JobManager()
        job_id = jm.create_job(mode="legacy_recorder")
        adapter = MagicMock()
        recorder = lr.LegacyRecorder(adapter, jm, job_id)

        with patch.object(lr.sys, "platform", "darwin"):
            with tempfile.TemporaryDirectory() as tmp:
                recorder.record(window_name="App", exe_path="", projects_dir=tmp)

        job = jm.get_job(job_id)
        self.assertEqual(job.state, "error")
        self.assertIn("Windows", job.error["message"])

    def test_sanitize_project_name_in_record_flow(self) -> None:
        """Nombre con caracteres inválidos se normaliza al crear proyecto nuevo."""
        from webui.job_manager import JobManager

        jm = JobManager()
        job_id = jm.create_job(mode="legacy_recorder")
        adapter = MagicMock()
        recorder = lr.LegacyRecorder(adapter, jm, job_id)

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(lr.sys, "platform", "win32"):
                with patch.object(jm, "create_prompt_and_wait", side_effect=["Mi Proyecto!!!", None]):
                    recorder.record(window_name="", exe_path="", projects_dir=tmp)
            project_dirs = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            self.assertEqual(project_dirs, ["Mi_Proyecto___"])


if __name__ == "__main__":
    unittest.main()
