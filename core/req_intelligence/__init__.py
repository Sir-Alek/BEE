"""
Inteligencia de Requerimientos — integración con Jira, Value Edge y conversión Gherkin.

Módulos:
  gherkin_converter           Transforma historias de usuario en escenarios Gherkin.
  jira_extractor              Extrae historias de usuario desde proyectos Jira.
  value_edge_extractor        Extrae historias de usuario desde proyectos Value Edge.
  integrations_service        Fachada que coordina extractores y conversión Gherkin.
  integrations_config_loader  Lee configuración de conexión para Jira y Value Edge.
  connectors_profiles_store   Persiste perfiles de conectores en almacenamiento local.
"""
from __future__ import annotations
