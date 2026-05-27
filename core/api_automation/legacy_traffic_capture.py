"""Captura tráfico API para apps legacy con componente web (URL conocida)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Optional

from core.api_automation.traffic_store import ingest_capture_dict, save_traffic_file, api_traffic_path_for_recording


def capture_from_url_via_puppeteer(
    url: str,
    output_traffic_path: str,
    *,
    cwd: str,
    timeout_sec: int = 90,
) -> bool:
    """Ejecuta web_capture_engine.js en modo captura API contra una URL (app híbrida)."""
    engine = os.path.join(cwd, "core", "ui_automation", "web_capture_engine.js")
    if not os.path.isfile(engine):
        return False
    stub_js = os.path.join(cwd, "tests", "fixtures", "stub_web_capture_engine.js")
    script = engine if os.path.isfile(engine) else stub_js
    dummy_js = output_traffic_path.replace("_api_traffic.json", "_probe.js")
    cmd = [
        "node",
        script,
        dummy_js,
        url,
        "1",
        output_traffic_path,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and os.path.isfile(output_traffic_path)


def save_legacy_capture(api_project: str, recording_basename: str, traffic_path: str) -> str:
    if not os.path.isfile(traffic_path):
        raise FileNotFoundError(traffic_path)
    with open(traffic_path, encoding="utf-8") as f:
        data = json.load(f)
    capture = ingest_capture_dict(data if isinstance(data, dict) else {})
    path = str(api_traffic_path_for_recording(api_project, recording_basename))
    save_traffic_file(path, capture)
    return path
