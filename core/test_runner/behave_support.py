"""Copia utils/logo Behave y plantillas de entorno por plataforma."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

BEHAVE_PLATFORMS = ("web", "mobile", "legacy", "api")


def elia_base_dir() -> str:
    import sys

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return meipass
        return os.path.dirname(sys.executable)
    return str(Path(__file__).resolve().parents[2])


def copy_behave_utils(project_path: Path, *, elia_root: Optional[str] = None) -> None:
    root = elia_root or elia_base_dir()
    src_utils = os.path.join(root, "resources", "behave", "utils")
    dst_utils = project_path / "utils"
    exclude = {"button_functions_mod.py"}
    if os.path.isdir(src_utils):
        dst_utils.mkdir(parents=True, exist_ok=True)
        for name in os.listdir(src_utils):
            if name in exclude or not name.endswith(".py"):
                continue
            shutil.copy2(os.path.join(src_utils, name), dst_utils / name)

    logo_src = os.path.join(root, "resources", "logo_elia.png")
    logo_dst_dir = project_path / "resources"
    logo_dst_dir.mkdir(parents=True, exist_ok=True)
    if os.path.isfile(logo_src):
        shutil.copy2(logo_src, logo_dst_dir / "logo_elia.png")

    pdf_res = os.path.join(root, "resources", "behave", "resources", "resourcesPDF")
    if os.path.isdir(pdf_res):
        shutil.copytree(pdf_res, project_path / "resources" / "resourcesPDF", dirs_exist_ok=True)


def ensure_platform_behave_support(project_path: Path, platform: str, *, elia_root: Optional[str] = None) -> None:
    platform = (platform or "web").lower()
    if platform not in BEHAVE_PLATFORMS:
        raise ValueError(f"Plataforma no soportada: {platform}")
    copy_behave_utils(project_path, elia_root=elia_root)
    env_path = project_path / "features" / "environment.py"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    template = _environment_template(platform)
    if not env_path.is_file() or _needs_env_upgrade(env_path, platform):
        env_path.write_text(template, encoding="utf-8")
    for sub in ("outputs/logs", "outputs/pdfReports", "outputs/evidences"):
        (project_path / sub).mkdir(parents=True, exist_ok=True)


def _needs_env_upgrade(path: Path, platform: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return True
    marker = f"ELIA_ENV_{platform.upper()}_V2"
    return marker not in text


def _environment_template(platform: str) -> str:
    if platform == "api":
        return _API_ENVIRONMENT_PY
    if platform == "mobile":
        return _MOBILE_ENVIRONMENT_PY
    if platform == "legacy":
        return _LEGACY_ENVIRONMENT_PY
    return _WEB_ENVIRONMENT_PY


_WEB_ENVIRONMENT_PY = '''"""Entorno Behave web — ELIA_ENV_WEB_V2"""
import os
import logging
from datetime import datetime
from utils.env_manager import *

def before_all(context):
    RunLogCoordinator.init_global_logger(context)
    RunStatsTracker.init_stats(context)
    logo = os.path.join(os.getcwd(), "resources", "logo_elia.png")
    if os.path.isfile(logo):
        os.environ.setdefault("ELIA_LOGO_PATH", logo)
    logging.info("Inicio de pruebas web")

def before_feature(context, feature):
    context.generate_evidence = os.getenv("GENERATE_EVIDENCE", "false").lower() == "true"
    RunLogCoordinator.setup_feature_logger(context, feature)

def before_scenario(context, scenario):
    context.start_time = datetime.now()
    headless_mode = os.getenv("HEADLESS", "true").lower() == "true"
    context.driver = BrowserSessionFactory.create_driver(headless_mode)
    context.diagnostic_logger = logging.getLogger("diagnostic")
    FeatureDatasetLoader.load_dataset(context)
    RunEvidenceCoordinator.setup_evidence(context, scenario)
    RunLogCoordinator.setup_scenario_logger(context, scenario)

def after_step(context, step):
    RunLogCoordinator.log_step_diagnostics(context, step)
    if context.generate_evidence and step.status.name == "failed" and hasattr(context, "driver"):
        RunEvidenceCoordinator.capture_failure(context, step)

def after_scenario(context, scenario):
    if hasattr(context, "driver"):
        context.driver.quit()
    RunStatsTracker.update_stats(context, scenario)
    if context.generate_evidence and hasattr(context, "start_time"):
        end_time = datetime.now()
        if hasattr(context, "scenario_file_handler"):
            context.scenario_file_handler.flush()
            logging.root.removeHandler(context.scenario_file_handler)
            context.scenario_file_handler.close()
        RunReportPublisher.generate_scenario_report(context, scenario, end_time, getattr(context, "failure_screenshots", None))

def after_feature(context, feature):
    RunLogCoordinator.consolidate_feature_logs(context, feature)

def after_all(context):
    RunReportPublisher.generate_consolidated_report(context)
'''

_API_ENVIRONMENT_PY = '''"""Entorno Behave API — ELIA_ENV_API_V2"""
import os
import logging
from datetime import datetime
import httpx
from utils.api_run_support import RunLogCoordinator, RunReportPublisher, RunStatsTracker

def before_all(context):
    RunLogCoordinator.init_global_logger(context)
    RunStatsTracker.init_stats(context)
    logo = os.path.join(os.getcwd(), "resources", "logo_elia.png")
    if os.path.isfile(logo):
        os.environ.setdefault("ELIA_LOGO_PATH", logo)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

def before_feature(context, feature):
    RunLogCoordinator.setup_feature_logger(context, feature)

def before_scenario(context, scenario):
    context.start_time = datetime.now()
    context.http = httpx.Client(timeout=float(os.getenv("ELIA_API_TIMEOUT", "30")), follow_redirects=True)
    context.last_response = None
    RunLogCoordinator.setup_scenario_logger(context, scenario)

def after_step(context, step):
    RunLogCoordinator.log_step_diagnostics(context, step)

def after_scenario(context, scenario):
    client = getattr(context, "http", None)
    if client is not None:
        client.close()
    RunStatsTracker.update_stats(context, scenario)
    if context.generate_evidence and hasattr(context, "start_time"):
        end_time = datetime.now()
        if hasattr(context, "scenario_file_handler"):
            context.scenario_file_handler.flush()
            logging.root.removeHandler(context.scenario_file_handler)
            context.scenario_file_handler.close()
        RunReportPublisher.generate_scenario_report(context, scenario, end_time)

def after_feature(context, feature):
    RunLogCoordinator.consolidate_feature_logs(context, feature)

def after_all(context):
    RunReportPublisher.generate_consolidated_report(context)
'''

_MOBILE_ENVIRONMENT_PY = '''"""Entorno Behave móvil (Appium) — ELIA_ENV_MOBILE_V2"""
import os
import logging
from datetime import datetime
from utils.api_run_support import RunLogCoordinator, RunReportPublisher, RunStatsTracker

def before_all(context):
    RunLogCoordinator.init_global_logger(context)
    RunStatsTracker.init_stats(context)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

def before_feature(context, feature):
    RunLogCoordinator.setup_feature_logger(context, feature)

def before_scenario(context, scenario):
    context.start_time = datetime.now()
    try:
        from appium import webdriver as appium_webdriver
        from appium.options.common.base import AppiumOptions
    except ImportError as e:
        raise RuntimeError("Appium-Python-Client no instalado") from e
    opts = AppiumOptions()
    caps = {
        "platformName": os.getenv("ELIA_MOBILE_PLATFORM", "Android"),
        "appium:automationName": os.getenv("ELIA_APPIUM_AUTOMATION", "UiAutomator2"),
        "appium:deviceName": os.getenv("ELIA_ANDROID_DEVICE", "emulator-5554"),
    }
    app_pkg = os.getenv("ELIA_APP_PACKAGE", "").strip()
    if app_pkg:
        caps["appium:appPackage"] = app_pkg
    opts.load_capabilities(caps)
    server = os.getenv("ELIA_APPIUM_URL", "http://127.0.0.1:4723")
    context.driver = appium_webdriver.Remote(server, options=opts)
    RunLogCoordinator.setup_scenario_logger(context, scenario)

def after_step(context, step):
    RunLogCoordinator.log_step_diagnostics(context, step)

def after_scenario(context, scenario):
    drv = getattr(context, "driver", None)
    if drv is not None:
        drv.quit()
    RunStatsTracker.update_stats(context, scenario)
    if context.generate_evidence and hasattr(context, "start_time"):
        end_time = datetime.now()
        if hasattr(context, "scenario_file_handler"):
            context.scenario_file_handler.flush()
            logging.root.removeHandler(context.scenario_file_handler)
            context.scenario_file_handler.close()
        RunReportPublisher.generate_scenario_report(context, scenario, end_time)

def after_feature(context, feature):
    RunLogCoordinator.consolidate_feature_logs(context, feature)

def after_all(context):
    RunReportPublisher.generate_consolidated_report(context)
'''

_LEGACY_ENVIRONMENT_PY = '''"""Entorno Behave legacy (Windows) — ELIA_ENV_LEGACY_V2"""
import os
import logging
from datetime import datetime
from utils.api_run_support import RunLogCoordinator, RunReportPublisher, RunStatsTracker

def before_all(context):
    RunLogCoordinator.init_global_logger(context)
    RunStatsTracker.init_stats(context)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

def before_feature(context, feature):
    RunLogCoordinator.setup_feature_logger(context, feature)

def before_scenario(context, scenario):
    context.start_time = datetime.now()
    RunLogCoordinator.setup_scenario_logger(context, scenario)

def after_step(context, step):
    RunLogCoordinator.log_step_diagnostics(context, step)

def after_scenario(context, scenario):
    RunStatsTracker.update_stats(context, scenario)
    if context.generate_evidence and hasattr(context, "start_time"):
        end_time = datetime.now()
        if hasattr(context, "scenario_file_handler"):
            context.scenario_file_handler.flush()
            logging.root.removeHandler(context.scenario_file_handler)
            context.scenario_file_handler.close()
        RunReportPublisher.generate_scenario_report(context, scenario, end_time)

def after_feature(context, feature):
    RunLogCoordinator.consolidate_feature_logs(context, feature)

def after_all(context):
    RunReportPublisher.generate_consolidated_report(context)
'''
