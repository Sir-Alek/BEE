"""
Fachada ELIA para invocar desde BEE (web o Tk) sin acoplarse a la UI legacy DICAI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from elia.config_loader import jira_settings, load_config_parser, value_edge_settings
from elia.core import JiraExtractor, UltimateGherkinConverter, ValueEdgeExtractor


def get_jira_extractor() -> tuple[JiraExtractor, Path]:
    cfg, path = load_config_parser()
    j = jira_settings(cfg)
    if not j["url"] or not j["email"] or not j["api_token"]:
        raise ValueError(
            "Jira: configure ELIA en secrets.ini (Documents/BEE/elia/secrets.ini) o variables "
            "ELIA_JIRA_URL, ELIA_JIRA_EMAIL, ELIA_JIRA_API_TOKEN."
        )
    return JiraExtractor(j["url"], j["email"], j["api_token"]), path


def get_value_edge_extractor(*, verify_ssl: bool = False) -> tuple[ValueEdgeExtractor, Path]:
    cfg, path = load_config_parser()
    ve = value_edge_settings(cfg)
    if not ve.get("url"):
        raise ValueError(
            "Value Edge: configure [ValueEdge] en secrets.ini o variables ELIA_VALUEEDGE_* "
            f"(archivo esperado: {path})."
        )
    return ValueEdgeExtractor(settings=ve, verify_ssl=verify_ssl), path


def run_gherkin_batch(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    use_ai: bool = False,
) -> None:
    """Ejecuta conversión por lotes (escribe learned_patterns.json bajo output_dir)."""
    conv = UltimateGherkinConverter(str(input_dir), str(output_dir), use_ai=use_ai)
    conv.convert()


def jira_smoke_test() -> Dict[str, Any]:
    """Comprueba credenciales Jira (sin escribir issues)."""
    ex, secrets_path = get_jira_extractor()
    ok = ex.check_connection()
    return {"ok": ok, "secrets_path": str(secrets_path)}


def value_edge_smoke_test() -> Dict[str, Any]:
    ex, secrets_path = get_value_edge_extractor()
    ok = ex.login()
    return {"ok": ok, "secrets_path": str(secrets_path)}
