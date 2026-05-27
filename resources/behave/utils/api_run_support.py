"""Soporte Behave API (HTTP) sin Selenium: logs y PDF."""
from __future__ import annotations

import glob
import logging
import os
from datetime import datetime

from utils.gen_reporTest import PdfReportDocument
from utils.PDFFeatureReport import FeaturePdfReport


class RunPathUtils:
    @staticmethod
    def sanitize_filename(name: str) -> str:
        return (
            str(name)
            .replace(" ", "")
            .replace("/", "")
            .replace("\\", "")
            .replace(":", "")
            .replace("*", "")
            .replace("?", "")
        )


class RunStatsTracker:
    @staticmethod
    def init_stats(context) -> None:
        context._runner.summary = {
            "scenarios_passed": 0,
            "scenarios_failed": 0,
            "scenarios_skipped": 0,
            "steps_passed": 0,
            "steps_failed": 0,
            "steps_skipped": 0,
            "steps_undefined": 0,
        }

    @staticmethod
    def update_stats(context, scenario) -> None:
        status_name = scenario.status.name
        stats = context._runner.summary
        if status_name == "passed":
            stats["scenarios_passed"] += 1
        elif status_name == "failed":
            stats["scenarios_failed"] += 1
        elif status_name == "skipped":
            stats["scenarios_skipped"] += 1
        for step in scenario.steps:
            st = step.status.name
            if st == "passed":
                stats["steps_passed"] += 1
            elif st == "failed":
                stats["steps_failed"] += 1
            elif st == "skipped":
                stats["steps_skipped"] += 1
            elif st == "undefined":
                stats["steps_undefined"] += 1

    @staticmethod
    def get_execution_summary(context, duration) -> str:
        stats = context._runner.summary
        executed = stats["scenarios_passed"] + stats["scenarios_failed"] + stats["scenarios_skipped"]
        mins, secs = divmod(duration.total_seconds(), 60)
        return "\n".join(
            [
                f"\n{executed} scenarios ({stats['scenarios_passed']} passed, {stats['scenarios_failed']} failed, {stats['scenarios_skipped']} skipped)",
                f"{stats['steps_passed']} steps passed, {stats['steps_failed']} failed",
                f"Took {int(mins)}m{secs:.3f}s",
            ]
        )


class RunLogCoordinator:
    @staticmethod
    def init_global_logger(context) -> None:
        context.generate_evidence = os.getenv("GENERATE_EVIDENCE", "false").lower() == "true"
        context.all_feature_logs = []

    @staticmethod
    def setup_feature_logger(context, feature) -> None:
        if not context.generate_evidence:
            return
        logs_dir = os.path.join(os.getcwd(), "outputs", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        feature_name = RunPathUtils.sanitize_filename(feature.name)
        feature_log_path = os.path.join(logs_dir, f"{feature_name}_feature.txt")
        handler = logging.FileHandler(feature_log_path, mode="w", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logging.root.addHandler(handler)
        context.feature_log_path = feature_log_path
        context.feature_start_time = datetime.now()
        context.all_feature_logs.append(feature_log_path)
        context.feature_log_handler = handler
        logging.info("==== INICIO DE FEATURE: %s ====", feature.name)

    @staticmethod
    def setup_scenario_logger(context, scenario) -> None:
        if not context.generate_evidence:
            return
        logs_dir = os.path.join(os.getcwd(), "outputs", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        scenario_name = RunPathUtils.sanitize_filename(scenario.name)
        context.txt_filename = os.path.join(logs_dir, f"{scenario_name}.txt")
        handler = logging.FileHandler(context.txt_filename, mode="w", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logging.root.addHandler(handler)
        context.scenario_file_handler = handler

    @staticmethod
    def log_step_diagnostics(context, step) -> None:
        if step.status.name == "passed":
            logging.info("    [Step] PASADO: %s %s", step.keyword, step.name)
        elif step.status.name == "failed":
            logging.error("    [Step] FALLIDO: %s %s", step.keyword, step.name)
        resp = getattr(context, "last_response", None)
        if resp is not None:
            logging.info("    HTTP %s %s", getattr(resp, "status_code", "?"), (getattr(resp, "text", "") or "")[:200])

    @staticmethod
    def consolidate_feature_logs(context, feature) -> None:
        if not context.generate_evidence or not getattr(context, "feature_log_path", None):
            return
        with open(context.feature_log_path, "a", encoding="utf-8") as feature_log:
            feature_log.write("\n=== RESUMEN API ===\n")
            if hasattr(context, "feature_start_time"):
                summary = RunStatsTracker.get_execution_summary(
                    context, datetime.now() - context.feature_start_time
                )
                feature_log.write(summary)
        if hasattr(context, "feature_log_handler") and context.feature_log_handler:
            logging.root.removeHandler(context.feature_log_handler)
            context.feature_log_handler.close()


class RunReportPublisher:
    @staticmethod
    def generate_scenario_report(context, scenario, end_time, failure_screenshots=None) -> None:
        if not context.generate_evidence:
            return
        try:
            PdfReportDocument.genReport(
                context.feature.name,
                scenario.name,
                context.start_time.strftime("%Y-%m-%d_%H-%M-%S"),
                end_time.strftime("%Y-%m-%d_%H-%M-%S"),
                screenshots=failure_screenshots,
            )
            logging.info("Reporte PDF API generado: %s", scenario.name)
        except Exception as e:
            logging.error("Error generando PDF API: %s", e)

    @staticmethod
    def generate_consolidated_report(context) -> None:
        if os.getenv("GENERATE_EVIDENCE", "false").lower() != "true":
            return
        if not getattr(context, "all_feature_logs", None):
            return
        stats = getattr(context._runner, "summary", {})
        total = stats.get("scenarios_passed", 0) + stats.get("scenarios_failed", 0)
        if total <= 1:
            return
        try:
            FeaturePdfReport.generate_consolidated_report(context.all_feature_logs)
        except Exception as e:
            logging.error("Fallo reporte consolidado API: %s", e)
