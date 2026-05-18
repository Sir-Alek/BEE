"""
Expone los módulos críticos del conversor para main.py en modo frozen.

Carga `core.puppeteer_script_converter`, etc. (desde .py en desarrollo o .pyd tras Cython).
"""
from __future__ import annotations

import importlib

puppeteer_script_converter = importlib.import_module("core.ui_automation.puppeteer_script_converter")
video_recorder = importlib.import_module("core.ui_automation.video_recorder")
step_by_step_converter = importlib.import_module("core.ui_automation.step_by_step_converter")
