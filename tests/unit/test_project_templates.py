"""Tests for project template catalog and creation."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch

from core.project_templates import (
    create_project_from_template,
    list_project_templates,
    normalize_project_name,
    templates_root,
    validate_project_name,
    validate_template_project,
)


def _patch_behave_roots(user_root: Path):
    def behave_dir(platform: str = "web") -> Path:
        d = user_root / "behave" / platform
        d.mkdir(parents=True, exist_ok=True)
        return d

    stack = ExitStack()
    stack.enter_context(patch("core.elia_paths.behave_projects_dir", behave_dir))
    stack.enter_context(patch("core.project_templates.behave_projects_dir", behave_dir))
    stack.enter_context(patch("core.api_automation.traffic_store.behave_projects_dir", behave_dir))
    stack.enter_context(patch("core.api_automation.collection_store.behave_projects_dir", behave_dir))
    return stack


def _behave_dry_run(project_path: Path, feature: str) -> subprocess.CompletedProcess:
    env = {
        **dict(__import__("os").environ),
        "GENERATE_EVIDENCE": "false",
        "HEADLESS": "true",
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "behave", "--dry-run", "--no-capture", feature],
        cwd=str(project_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestProjectTemplates(unittest.TestCase):
    def test_normalize_project_name(self) -> None:
        self.assertEqual(normalize_project_name("  Mi Proyecto  "), "Mi_Proyecto")
        self.assertEqual(normalize_project_name("ELIA-Demo"), "ELIA-Demo")

    def test_validate_project_name_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            validate_project_name("")

    def test_list_templates_non_empty(self) -> None:
        root = templates_root()
        if not root.is_dir():
            self.skipTest("resources/project_templates no presente")
        items = list_project_templates()
        ids = {t["id"] for t in items}
        self.assertIn("web-login", ids)
        self.assertIn("api-smoke", ids)
        self.assertIn("full-stack-demo", ids)

    def test_create_web_login_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                result = create_project_from_template("web-login", "DemoWebTest")
                self.assertTrue(result.ok)
                self.assertEqual(len(result.projects), 1)
                self.assertEqual(result.projects[0].platform, "web")
                proj = user_root / "behave" / "web" / "DemoWebTest"
                self.assertTrue((proj / "features" / "demo_login.feature").is_file())
                self.assertTrue((proj / "features" / "environment.py").is_file())
                self.assertTrue((proj / "utils" / "button_functions.py").is_file())
                self.assertTrue((proj / "resources" / "data" / "Login demo Sauce Demo.json").is_file())
                self.assertEqual(validate_template_project("web", proj), [])
                meta = json.loads((proj / ".elia" / "project.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["template_id"], "web-login")

    def test_web_login_behave_dry_run_loads_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("web-login", "DryRunWeb")
                proj = user_root / "behave" / "web" / "DryRunWeb"
                proc = _behave_dry_run(proj, "features/demo_login.feature")
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=(proc.stdout or "") + (proc.stderr or ""),
                )
                self.assertNotIn("ModuleNotFoundError", proc.stderr)

    def test_create_api_smoke_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                result = create_project_from_template("api-smoke", "DemoApiTest")
                self.assertTrue(result.ok)
                proj = user_root / "behave" / "api" / "DemoApiTest"
                scenario = proj / "scenarios" / "demo" / "get_post_1.json"
                self.assertTrue(scenario.is_file())
                self.assertEqual(validate_template_project("api", proj), [])

    def test_api_smoke_behave_dry_run_loads_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("api-smoke", "DryRunApi")
                proj = user_root / "behave" / "api" / "DryRunApi"
                proc = _behave_dry_run(proj, "features/api_smoke.feature")
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=(proc.stdout or "") + (proc.stderr or ""),
                )
                self.assertNotIn("ModuleNotFoundError", proc.stderr)

    def test_api_smoke_scenario_executes(self) -> None:
        from core.api_automation.runtime.request_executor import execute_request
        from core.api_automation.traffic_store import load_scenario
        from core.api_automation.project_config import load_environment

        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("api-smoke", "ExecApi")
                project = "ExecApi"
                req = load_scenario(project, "demo/get_post_1.json")
                env = load_environment(project, "dev")
                result = execute_request(req, variables=env.get("variables") or {})
                self.assertTrue(result.get("ok"), msg=str(result))
                self.assertEqual(result.get("status_code"), 200)

    def test_create_full_stack_multi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                result = create_project_from_template("full-stack-demo", "StackDemo")
                self.assertEqual(len(result.projects), 2)
                names = {p.project for p in result.projects}
                self.assertIn("StackDemo-Web", names)
                self.assertIn("StackDemo-API", names)
                web_proj = user_root / "behave" / "web" / "StackDemo-Web"
                api_proj = user_root / "behave" / "api" / "StackDemo-API"
                self.assertEqual(validate_template_project("web", web_proj), [])
                self.assertEqual(validate_template_project("api", api_proj), [])

    def test_duplicate_project_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("web-login", "DupTest")
                with self.assertRaises(FileExistsError):
                    create_project_from_template("web-login", "DupTest")


if __name__ == "__main__":
    unittest.main()
