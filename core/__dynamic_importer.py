"""
Expone los módulos críticos del conversor para main.py en modo frozen.

Carga `core.ui_automation.web_capture_behave_builder`, etc. (desde .py en desarrollo o .pyd tras Cython).
"""
from __future__ import annotations

import importlib

web_capture_behave_builder = importlib.import_module("core.ui_automation.web_capture_behave_builder")
viewport_capture_writer = importlib.import_module("core.ui_automation.viewport_capture_writer")
web_capture_step_builder = importlib.import_module("core.ui_automation.web_capture_step_builder")
