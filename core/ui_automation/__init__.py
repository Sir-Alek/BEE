"""
Automatización UI — grabación de interacciones, conversión y análisis de flujos.

Módulos:
  puppeteer_script_converter  Convierte scripts JS grabados a estructura Behave completa.
  step_by_step_converter      Convierte scripts JS al formato step-by-step.
  flow_analyzer               Detecta prefijos comunes entre grabaciones para Background.
  locator_healer              Self-healing de locators (algorítmico + Gemma 4).
  node_wrapper                Ejecuta scripts Puppeteer con el Node.js embebido.
  recorder_focus              Enfoca el navegador de automatización en Windows.
  video_recorder              Grabación de pantalla a AVI.
"""
from __future__ import annotations
