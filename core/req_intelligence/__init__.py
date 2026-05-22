"""
Inteligencia de Requerimientos — integración con Jira, Value Edge, conversión Gherkin y Doc-to-BDD.

Módulos:
  story_gherkin_builder       Transforma historias de usuario en escenarios Gherkin.
  jira_story_fetcher          Extrae historias de usuario desde proyectos Jira.
  value_edge_story_fetcher    Extrae historias de usuario desde proyectos Value Edge.
  integrations_service        Fachada que coordina extractores y conversión Gherkin.
  integrations_config_loader  Lee configuración de conexión para Jira y Value Edge.
  connectors_profiles_store   Persiste perfiles de conectores en almacenamiento local.
  doc_ingestion               Ingesta de documentos Word/Excel para conversión BDD.
  bdd_doc_converter           Convierte DocChunks a BDD via LLM + GBNF grammar.
  feature_scanner             Escanea y parsea .feature files para linkage de grabaciones.
"""
from __future__ import annotations
