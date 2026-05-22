#!/usr/bin/env python3
"""Aplica renombrado interno de identidad (una sola ejecución)."""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

GIT_MV = [
    ("core/ui_automation/node_wrapper.py", "core/ui_automation/script_runtime_host.py"),
    ("core/ui_automation/puppeteer_script_converter.py", "core/ui_automation/web_capture_behave_builder.py"),
    ("core/ui_automation/step_by_step_converter.py", "core/ui_automation/web_capture_step_builder.py"),
    ("core/ui_automation/video_recorder.py", "core/ui_automation/viewport_capture_writer.py"),
    ("core/ui_automation/recorder.js", "core/ui_automation/web_capture_engine.js"),
    ("core/req_intelligence/gherkin_converter.py", "core/req_intelligence/story_gherkin_builder.py"),
    ("core/req_intelligence/jira_extractor.py", "core/req_intelligence/jira_story_fetcher.py"),
    ("core/req_intelligence/value_edge_extractor.py", "core/req_intelligence/value_edge_story_fetcher.py"),
]

REPLACEMENTS: list[tuple[str, str]] = [
    # behave / step_by_step template classes
    ("class BaseUtils:", "class RunPathUtils:"),
    ("class DirectoryManager:", "class ProjectDirectoryLayout:"),
    ("class DriverManager:", "class BrowserSessionFactory:"),
    ("class LogManager:", "class RunLogCoordinator:"),
    ("class DatasetManager:", "class FeatureDatasetLoader:"),
    ("class EvidenceManager:", "class RunEvidenceCoordinator:"),
    ("class StatsManager:", "class RunStatsTracker:"),
    ("class ReportManager:", "class RunReportPublisher:"),
    ("class GetEvidence():", "class RunEvidenceStore():"),
    ("class GetEvidence:", "class RunEvidenceStore:"),
    ("class PDFFeatureReport(", "class FeaturePdfReport("),
    ("class EvidenceState(", "class ThreadEvidenceContext("),
    ("class PDF(", "class PdfReportDocument("),
    ("class Browsers():", "class BrowserLauncher():"),
    ("class TestLogger:", "class CaseRunLogger:"),
    ("BaseUtils.", "RunPathUtils."),
    ("DirectoryManager.", "ProjectDirectoryLayout."),
    ("DriverManager.", "BrowserSessionFactory."),
    ("LogManager.", "RunLogCoordinator."),
    ("DatasetManager.", "FeatureDatasetLoader."),
    ("EvidenceManager.", "RunEvidenceCoordinator."),
    ("StatsManager.", "RunStatsTracker."),
    ("ReportManager.", "RunReportPublisher."),
    ("PDFFeatureReport.", "FeaturePdfReport."),
    ("GetEvidence.", "RunEvidenceStore."),
    ("GetEvidence()", "RunEvidenceStore()"),
    ("from utils.evidence import GetEvidence", "from utils.evidence import RunEvidenceStore"),
    ("from utils.PDFFeatureReport import PDFFeatureReport", "from utils.PDFFeatureReport import FeaturePdfReport"),
    ("from utils.gen_reporTest import PDF", "from utils.gen_reporTest import PdfReportDocument"),
    ("PDF.genReport", "PdfReportDocument.genReport"),
    ("EvidenceState()", "ThreadEvidenceContext()"),
    ("Browsers.", "BrowserLauncher."),
    ("TestLogger(", "CaseRunLogger("),
    ("from utils.test_logger import TestLogger", "from utils.test_logger import CaseRunLogger"),
    # core ui_automation
    ("class NodeJSWrapper:", "class ScriptRuntimeHost:"),
    ("node_wrapper = NodeJSWrapper()", "script_runtime_host = ScriptRuntimeHost()"),
    ("class PuppeteerToBehaveConverter:", "class WebCaptureBehaveBuilder:"),
    ("class PuppeteerToStepByStepConverter:", "class WebCaptureStepBuilder:"),
    ("class ScreenRecorder:", "class ViewportCaptureWriter:"),
    ("PuppeteerToBehaveConverter", "WebCaptureBehaveBuilder"),
    ("PuppeteerToStepByStepConverter", "WebCaptureStepBuilder"),
    ("NodeJSWrapper", "ScriptRuntimeHost"),
    ("node_wrapper", "script_runtime_host"),
    ("ScreenRecorder", "ViewportCaptureWriter"),
    # req_intelligence
    ("class UltimateGherkinConverter:", "class StoryGherkinBuilder:"),
    ("UltimateGherkinConverter", "StoryGherkinBuilder"),
    ("class JiraExtractor:", "class JiraStoryFetcher:"),
    ("JiraExtractor", "JiraStoryFetcher"),
    ("class ValueEdgeExtractor:", "class ValueEdgeStoryFetcher:"),
    ("ValueEdgeExtractor", "ValueEdgeStoryFetcher"),
    ("core.ui_automation.node_wrapper", "core.ui_automation.script_runtime_host"),
    ("core.ui_automation.puppeteer_script_converter", "core.ui_automation.web_capture_behave_builder"),
    ("core.ui_automation.step_by_step_converter", "core.ui_automation.web_capture_step_builder"),
    ("core.ui_automation.video_recorder", "core.ui_automation.viewport_capture_writer"),
    ("core.req_intelligence.gherkin_converter", "core.req_intelligence.story_gherkin_builder"),
    ("core.req_intelligence.jira_extractor", "core.req_intelligence.jira_story_fetcher"),
    ("core.req_intelligence.value_edge_extractor", "core.req_intelligence.value_edge_story_fetcher"),
    ("core/node_wrapper", "core/script_runtime_host"),
    ("core/puppeteer_script_converter", "core/web_capture_behave_builder"),
    ("core/video_recorder", "core/viewport_capture_writer"),
    ("core/step_by_step_converter", "core/web_capture_step_builder"),
    ("core/gherkin_converter", "core/story_gherkin_builder"),
    ("core/jira_extractor", "core/jira_story_fetcher"),
    ("core/value_edge_extractor", "core/value_edge_story_fetcher"),
    ("node_wrapper.py", "script_runtime_host.py"),
    ("puppeteer_script_converter.py", "web_capture_behave_builder.py"),
    ("step_by_step_converter.py", "web_capture_step_builder.py"),
    ("video_recorder.py", "viewport_capture_writer.py"),
    ("gherkin_converter.py", "story_gherkin_builder.py"),
    ("jira_extractor.py", "jira_story_fetcher.py"),
    ("value_edge_extractor.py", "value_edge_story_fetcher.py"),
    # recorder js
    ("recorder.js", "web_capture_engine.js"),
    ("recorder.obfuscated.js", "web_capture_engine.obfuscated.js"),
    ("function ensureHighlightOverlay()", "function initCaptureOverlay()"),
    ("ensureHighlightOverlay();", "initCaptureOverlay();"),
    ("ensureHighlightOverlay()", "initCaptureOverlay()"),
    ("#00bcd4", "#7c6af2"),
    ("rgba(0,188,212,0.15)", "rgba(124,106,242,0.15)"),
    # meta / hygiene
    ("node_wrapper", "script_runtime_host"),
    ('("_elia_meta.json", "_bee_meta.json")', '("_elia_meta.json",)'),
    ("legacy DICAI", "modo legacy"),
    ("get_core_file('recorder.js')", "get_core_file('web_capture_engine.js')"),
    ('get_core_file("recorder.js")', 'get_core_file("web_capture_engine.js")'),
]

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "ELIA",
    "core/node",
    ".cursor",
    ".venv",
    "__pycache__",
}

SKIP_FILES = {
    "apply_identity_rename.py",
    "recorder.obfuscated.js",
    "web_capture_engine.obfuscated.js",
}


def should_process(path: str) -> bool:
    rel = os.path.relpath(path, ROOT)
    parts = rel.split(os.sep)
    if any(p in SKIP_DIRS for p in parts):
        return False
    if os.path.basename(path) in SKIP_FILES:
        return False
    if rel.endswith(".pyd") or rel.endswith(".so"):
        return False
    return True


def git_mv(src: str, dst: str) -> None:
    src_abs = os.path.join(ROOT, src.replace("/", os.sep))
    dst_abs = os.path.join(ROOT, dst.replace("/", os.sep))
    if not os.path.isfile(src_abs):
        if os.path.isfile(dst_abs):
            print(f"skip mv (already): {dst}")
            return
        raise FileNotFoundError(src_abs)
    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
    subprocess.check_call(["git", "mv", src_abs, dst_abs], cwd=ROOT)


def apply_replacements(content: str) -> str:
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    return content


def process_files() -> int:
    changed = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            if not should_process(path):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext not in {".py", ".js", ".ts", ".tsx", ".md", ".spec", ".txt", ".iss"}:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    original = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            updated = apply_replacements(original)
            if updated != original:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(updated)
                changed += 1
                print(f"updated: {os.path.relpath(path, ROOT)}")
    return changed


def patch_core_init_loader() -> None:
    path = os.path.join(ROOT, "core", "__init__.py")
    loader = '''from __future__ import annotations

"""
Paquete core: carga de assets (web capture engine JS) para runtime y empaquetado.

web_capture_engine.js: prioridad `ELIA_RECORDER_JS`, `web_capture_engine.obfuscated.js`,
otros `web_capture_engine.*.js`, y `web_capture_engine.js` plano.
"""
import os
import sys


class _CaptureEngineLoader:
    _instance = None
    _cache = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _capture_engine_candidate_dirs(self) -> list[str]:
        base = os.path.dirname(__file__)
        out = [os.path.join(base, "ui_automation"), base]
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "") or ""
            if meipass:
                out.append(os.path.join(meipass, "core", "ui_automation"))
                out.append(os.path.join(meipass, "core"))
                out.append(meipass)
        seen: set[str] = set()
        uniq: list[str] = []
        for d in out:
            if d and d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    def _resolve_js_path(self, file_name: str) -> str | None:
        if file_name != "web_capture_engine.js":
            return None
        env_name = (os.environ.get("ELIA_RECORDER_JS") or "").strip()
        candidates: list[str] = []
        if env_name:
            if os.path.isabs(env_name):
                candidates.append(env_name)
            else:
                for d in self._capture_engine_candidate_dirs():
                    candidates.append(os.path.join(d, env_name))
        for name in (
            "web_capture_engine.obfuscated.js",
            "web_capture_engine.test.js",
            "web_capture_engine.min.js",
        ):
            for d in self._capture_engine_candidate_dirs():
                candidates.append(os.path.join(d, name))
        for d in self._capture_engine_candidate_dirs():
            try:
                for fn in sorted(os.listdir(d)):
                    if not fn.startswith("web_capture_engine") or not fn.endswith(".js"):
                        continue
                    if fn == "web_capture_engine.js":
                        continue
                    p = os.path.join(d, fn)
                    if p not in candidates:
                        candidates.append(p)
            except OSError:
                pass
        for p in candidates:
            if p and os.path.isfile(p):
                return p
        return None

    def _read_plain(self, relative_path: str) -> bytes | None:
        base = os.path.dirname(__file__)
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "") or ""
            candidates = [
                os.path.join(meipass, "core", "ui_automation", relative_path),
                os.path.join(meipass, "core", relative_path),
                os.path.join(meipass, relative_path),
                os.path.join(base, "ui_automation", relative_path),
                os.path.join(base, relative_path),
            ]
            if relative_path == "web_capture_engine.js":
                for extra in (
                    "web_capture_engine.obfuscated.js",
                    "web_capture_engine.test.js",
                    "web_capture_engine.min.js",
                ):
                    candidates.insert(0, os.path.join(meipass, "core", "ui_automation", extra))
                    candidates.insert(1, os.path.join(meipass, "core", extra))
                env_name = (os.environ.get("ELIA_RECORDER_JS") or "").strip()
                if env_name:
                    candidates.insert(
                        0,
                        env_name if os.path.isabs(env_name) else os.path.join(meipass, "core", "ui_automation", env_name),
                    )
        else:
            candidates = [
                os.path.join(base, "ui_automation", relative_path),
                os.path.join(base, relative_path),
            ]

        for p in candidates:
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    return f.read()
        return None

    def load_file(self, relative_path: str) -> bytes:
        if relative_path in self._cache:
            return self._cache[relative_path]

        js_alt = self._resolve_js_path(relative_path)
        if js_alt:
            with open(js_alt, "rb") as f:
                data = f.read()
                self._cache[relative_path] = data
                return data

        plain = self._read_plain(relative_path)
        if plain is not None:
            self._cache[relative_path] = plain
            return plain

        raise FileNotFoundError(f"No se encontró web capture engine JS: {relative_path}")


def get_core_file(file_name):
    return _CaptureEngineLoader.get_instance().load_file(file_name)
'''
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(loader)
    print("rewrote core/__init__.py loader")


def patch_build_release() -> None:
    path = os.path.join(ROOT, "scripts", "build_release.py")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = text.replace("def obfuscate_recorder()", "def obfuscate_capture_engine()")
    text = text.replace("obfuscate_recorder()", "obfuscate_capture_engine()")
    text = text.replace("SOURCE_RECORDER", "SOURCE_CAPTURE_ENGINE")
    text = text.replace("OBFUSCATED_JS = os.path.join(CORE_UI, \"web_capture_engine.obfuscated.js\")", "OBFUSCATED_CAPTURE_ENGINE = os.path.join(CORE_UI, \"web_capture_engine.obfuscated.js\")")
    text = text.replace("OBFUSCATED_JS", "OBFUSCATED_CAPTURE_ENGINE")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("patched build_release.py")


def patch_dynamic_importer() -> None:
    path = os.path.join(ROOT, "core", "__dynamic_importer.py")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = text.replace(
        "puppeteer_script_converter = importlib.import_module",
        "web_capture_behave_builder = importlib.import_module",
    )
    text = text.replace(
        "video_recorder = importlib.import_module",
        "viewport_capture_writer = importlib.import_module",
    )
    text = text.replace(
        "step_by_step_converter = importlib.import_module",
        "web_capture_step_builder = importlib.import_module",
    )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("patched __dynamic_importer.py")


def patch_main_dynamic_imports() -> None:
    path = os.path.join(ROOT, "main.py")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = text.replace(
        "from core.__dynamic_importer import puppeteer_script_converter, video_recorder, step_by_step_converter",
        "from core.__dynamic_importer import web_capture_behave_builder, viewport_capture_writer, web_capture_step_builder",
    )
    text = text.replace(
        "WebCaptureBehaveBuilder = web_capture_behave_builder.WebCaptureBehaveBuilder",
        "WebCaptureBehaveBuilder = web_capture_behave_builder.WebCaptureBehaveBuilder",
    )
    text = text.replace(
        "ViewportCaptureWriter = video_recorder.ViewportCaptureWriter",
        "ViewportCaptureWriter = viewport_capture_writer.ViewportCaptureWriter",
    )
    text = text.replace(
        "WebCaptureStepBuilder = step_by_step_converter.WebCaptureStepBuilder",
        "WebCaptureStepBuilder = web_capture_step_builder.WebCaptureStepBuilder",
    )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("patched main.py dynamic imports")


def main() -> int:
    os.chdir(ROOT)
    for src, dst in GIT_MV:
        git_mv(src, dst)
        print(f"git mv: {src} -> {dst}")
    n = process_files()
    patch_core_init_loader()
    patch_build_release()
    patch_dynamic_importer()
    patch_main_dynamic_imports()
    print(f"Done. {n} files updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
