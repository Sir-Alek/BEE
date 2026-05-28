"""Scaffold de proyecto API bajo behave/api/ (sin capa Behave por defecto)."""
from __future__ import annotations

import json
from pathlib import Path

from core.api_automation.project_config import DEFAULT_ENVIRONMENT, DEFAULT_PROJECT_CONFIG


def scaffold_api_project(project_path: Path) -> None:
    project_path.mkdir(parents=True, exist_ok=True)
    for sub in ("scripts", "scenarios", "environments", "resources/data", "outputs/evidences", "outputs/reports"):
        (project_path / sub).mkdir(parents=True, exist_ok=True)

    project_json = project_path / "project.json"
    if not project_json.is_file():
        project_json.write_text(
            json.dumps(DEFAULT_PROJECT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    dev_env = project_path / "environments" / "dev.json"
    if not dev_env.is_file():
        dev_env.write_text(
            json.dumps(DEFAULT_ENVIRONMENT, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
