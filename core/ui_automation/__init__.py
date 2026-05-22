"""
Automatización UI — grabación de interacciones, conversión y análisis de flujos.

Módulos:
  web_capture_behave_builder  Convierte scripts JS grabados a estructura Behave completa.
  web_capture_step_builder    Convierte scripts JS al formato step-by-step.
  flow_analyzer               Detecta prefijos comunes entre grabaciones para Background.
  locator_healer              Self-healing de locators (algorítmico + Gemma 4).
  script_runtime_host         Ejecuta el motor de captura web con Node.js embebido.
  recorder_focus              Enfoca el navegador de automatización en Windows.
  viewport_capture_writer     Grabación de pantalla a AVI.
  mobile_recorder             Grabación de interacciones móviles vía Appium (Building Block).
  legacy_recorder             Grabación de aplicaciones de escritorio Windows (Building Block).
  recording_to_behave_converter  Conversión de grabaciones JSON móvil/legacy a Behave.
"""
from __future__ import annotations
