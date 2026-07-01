"""Tests for local project management (rename, delete, info)."""
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from core.project_manage import delete_project, get_project_info, rename_project
from core.project_templates import create_project_from_template


def _patch_behave_roots(user_root: Path):
    def behave_dir(platform: str = "web") -> Path:
        d = user_root / "behave" / platform
        d.mkdir(parents=True, exist_ok=True)
        return d

    stack = ExitStack()
    stack.enter_context(patch("core.elia_paths.behave_projects_dir", behave_dir))
    stack.enter_context(patch("core.project_templates.behave_projects_dir", behave_dir))
    stack.enter_context(patch("core.project_manage.behave_projects_dir", behave_dir))
    stack.enter_context(patch("core.api_automation.traffic_store.behave_projects_dir", behave_dir))
    stack.enter_context(patch("core.api_automation.collection_store.behave_projects_dir", behave_dir))
    return stack


class TestProjectManage(unittest.TestCase):
    def test_get_project_info_from_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("web-login", "InfoTest")
                info = get_project_info("web", "InfoTest")
                self.assertTrue(info["from_template"])
                self.assertEqual(info["template_id"], "web-login")

    def test_rename_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("web-login", "OldName")
                new_name = rename_project("web", "OldName", "NewName")
                self.assertEqual(new_name, "NewName")
                self.assertFalse((user_root / "behave" / "web" / "OldName").exists())
                self.assertTrue((user_root / "behave" / "web" / "NewName").exists())
                meta = json.loads(
                    (user_root / "behave" / "web" / "NewName" / ".elia" / "project.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(meta["template_id"], "web-login")

    def test_delete_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("web-login", "ToDelete")
                path = user_root / "behave" / "web" / "ToDelete"
                self.assertTrue(path.is_dir())
                delete_project("web", "ToDelete")
                self.assertFalse(path.exists())

    def test_delete_blocked_when_run_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_root = Path(tmp) / "ELIA"
            with _patch_behave_roots(user_root):
                create_project_from_template("web-login", "BusyProj")
                from core.test_runner.runner_service import test_runner_service

                with patch.object(test_runner_service, "project_has_running_job", return_value=True):
                    with self.assertRaises(RuntimeError):
                        delete_project("web", "BusyProj")


if __name__ == "__main__":
    unittest.main()
