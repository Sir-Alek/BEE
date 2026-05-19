"""Módulos de core/ a compilar con Cython en builds de release."""
from __future__ import annotations

CYTHON_REL_PATHS: tuple[str, ...] = (
    # core raíz — infraestructura compartida
    # NOTA: core/__init__.py NO se compila (contiene shims dinámicos de sys.modules).
    # Los __init__.py de subpaquetes tampoco (son marcadores de paquete, PyInstaller los necesita como .py).
    "core/__dynamic_importer.py",
    "core/gemma_inference.py",
    "core/gemma_model_paths.py",
    "core/elia_license.py",
    "core/elia_memory.py",
    "core/elia_paths.py",
    "core/modules_config.py",
    # core/ui_automation/
    "core/ui_automation/puppeteer_script_converter.py",
    "core/ui_automation/flow_analyzer.py",
    "core/ui_automation/locator_healer.py",
    "core/ui_automation/video_recorder.py",
    "core/ui_automation/step_by_step_converter.py",
    "core/ui_automation/node_wrapper.py",
    "core/ui_automation/recorder_focus.py",
    "core/ui_automation/mobile_recorder.py",
    "core/ui_automation/legacy_recorder.py",
    "core/ui_automation/recording_to_behave_converter.py",
    "core/ui_automation/mobile_dom_parser.py",
    "core/ui_automation/recording_flow_analyzer.py",
    "core/ui_automation/recording_linkage.py",
    # core/req_intelligence/
    "core/req_intelligence/jira_extractor.py",
    "core/req_intelligence/value_edge_extractor.py",
    "core/req_intelligence/gherkin_converter.py",
    "core/req_intelligence/integrations_config_loader.py",
    "core/req_intelligence/connectors_profiles_store.py",
    "core/req_intelligence/integrations_service.py",
    "core/req_intelligence/doc_ingestion.py",
    "core/req_intelligence/bdd_doc_converter.py",
    "core/req_intelligence/feature_scanner.py",
    "core/req_intelligence/recording_scanner.py",
    "core/ui_automation/linked_steps_regenerator.py",
)
