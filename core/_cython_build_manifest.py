"""Módulos de core/ a compilar con Cython en builds de release."""
from __future__ import annotations

CYTHON_REL_PATHS: tuple[str, ...] = (
    "core/puppeteer_script_converter.py",
    "core/video_recorder.py",
    "core/step_by_step_converter.py",
    "core/node_wrapper.py",
    "core/recorder_focus.py",
    "core/gemma_inference.py",
    "core/gemma_model_paths.py",
    "core/bee_license.py",
    "core/bee_memory.py",
    "core/bee_paths.py",
    "core/__dynamic_importer.py",
)
