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

    def test_runner_workspace_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {
                "features/environment.py": "# env",
                "features/test1.feature": "Feature: x",
                "features/steps/test1_steps.py": "pass",
                "pages/test1_page.py": "pass",
                "resources/data/test1.json": "{}",
                "utils/GUIA_FUNCIONES_PAGE.md": "# guia",
                "utils/button_functions.py": "# bf",
                "utils/gen_reporTest.py": "# other",
            }
            for rel, content in paths.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")

            listed = {f["path"] for f in project_files.list_runner_workspace_files(root)}
            self.assertNotIn("features/environment.py", listed)
            self.assertNotIn("utils/gen_reporTest.py", listed)
            self.assertNotIn("utils/button_functions.py", listed)
            self.assertIn("features/test1.feature", listed)
            self.assertIn("features/steps/test1_steps.py", listed)
            self.assertIn("pages/test1_page.py", listed)
            self.assertIn("resources/data/test1.json", listed)
            self.assertIn("utils/GUIA_FUNCIONES_PAGE.md", listed)

            advanced = {f["path"] for f in project_files.list_runner_workspace_files(root, include_advanced=True)}
            self.assertIn("utils/button_functions.py", advanced)
