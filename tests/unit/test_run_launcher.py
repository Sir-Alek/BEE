"""Tests for unified run launcher."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.test_runner import project_files
from core.test_runner.run_launcher import (
    build_behave_command,
    build_locust_command,
    normalize_kind,
    prepare_project,
)


class TestRunLauncher(unittest.TestCase):
    def test_build_behave_command(self) -> None:
        cmd = build_behave_command("features/smoke.feature")
        self.assertEqual(cmd[-2:], ["behave", "features/smoke.feature"])

    def test_build_locust_command(self) -> None:
        cmd = build_locust_command("locustfile.py", users=10, host="https://api.test")
        self.assertIn("-u", cmd)
        self.assertIn("10", cmd)
        self.assertIn("--host", cmd)

    def test_normalize_kind(self) -> None:
        self.assertEqual(normalize_kind("api", "behave"), "behave_api")
        self.assertEqual(normalize_kind("mobile", "behave"), "behave_mobile")

    def test_prepare_project_creates_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from core.test_runner import run_launcher

            original = run_launcher.behave_projects_dir
            try:
                run_launcher.behave_projects_dir = lambda platform="web": Path(tmp) / platform  # type: ignore
                root = Path(tmp) / "api" / "Demo"
                (root / "features").mkdir(parents=True)
                path = prepare_project("api", "Demo")
                env_file = Path(path) / "features" / "environment.py"
                self.assertTrue(env_file.is_file())
                self.assertIn("ELIA_ENV_API_V2", env_file.read_text(encoding="utf-8"))
            finally:
                run_launcher.behave_projects_dir = original  # type: ignore


class TestProjectFiles(unittest.TestCase):
    def test_list_read_write_editable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feat = root / "features" / "demo.feature"
            feat.parent.mkdir(parents=True)
            feat.write_text("Feature: demo", encoding="utf-8")
            listed = project_files.list_editable_files(root)
            self.assertTrue(any(f["path"] == "features/demo.feature" for f in listed))
            content = project_files.read_project_file(root, "features/demo.feature")
            self.assertIn("Feature:", content)
            project_files.write_project_file(root, "features/demo.feature", "Feature: updated")
            self.assertIn("updated", feat.read_text(encoding="utf-8"))

    def test_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                project_files.read_project_file(tmp, "../outside.txt")
