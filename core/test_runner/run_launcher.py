"""Lanzamiento unificado de Behave / Locust con variables de entorno ELIA."""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from core.elia_paths import behave_projects_dir
from core.test_runner.behave_support import elia_base_dir, ensure_platform_behave_support

BEHAVE_KINDS = frozenset({"behave", "behave_web", "behave_mobile", "behave_legacy", "behave_api"})
LOCUST_KIND = "locust"


def project_path(platform: str, project: str) -> str:
    return str(behave_projects_dir(platform) / project)


def build_run_env(
    platform: str,
    *,
    generate_evidence: bool = True,
    headless: bool = True,
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    env = os.environ.copy()
    env["GENERATE_EVIDENCE"] = "true" if generate_evidence else "false"
    env["HEADLESS"] = "true" if headless else "false"
    env["ELIA_BASE_DIR"] = elia_base_dir()
    env["ELIA_PLATFORM"] = platform
    env["PYTHONIOENCODING"] = "utf-8"
    logo = os.path.join(elia_base_dir(), "resources", "logo_elia.png")
    if os.path.isfile(logo):
        env["ELIA_LOGO_PATH"] = logo
    if extra:
        env.update({k: str(v) for k, v in extra.items()})
    return env


def prepare_project(platform: str, project: str) -> str:
    path = behave_projects_dir(platform) / project
    if not path.is_dir():
        raise FileNotFoundError(f"Proyecto no encontrado: {platform}/{project}")
    ensure_platform_behave_support(path, platform)
    return str(path)


def build_behave_command(feature: str = "features") -> List[str]:
    return [sys.executable, "-m", "behave", feature]


def build_locust_command(
    locustfile: str,
    *,
    users: int = 5,
    spawn_rate: float = 1.0,
    run_time: str = "1m",
    host: str = "",
) -> List[str]:
    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        os.path.basename(locustfile),
        "--headless",
        "-u",
        str(users),
        "-r",
        str(spawn_rate),
        "-t",
        run_time,
    ]
    if host:
        cmd.extend(["--host", host])
    return cmd


def normalize_kind(platform: str, kind: str) -> str:
    k = (kind or "behave").lower()
    if k == "behave":
        return f"behave_{platform}" if platform != "web" else "behave_web"
    return k
