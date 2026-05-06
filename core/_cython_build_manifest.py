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
    "core/elia_license.py",
    "core/elia_memory.py",
    "core/elia_paths.py",
    "core/__dynamic_importer.py",
    "core/jira_extractor.py",
    "core/value_edge_extractor.py",
    "core/gherkin_converter.py",
    "core/integrations_config_loader.py",
    "core/connectors_profiles_store.py",
    "core/integrations_service.py",
)
