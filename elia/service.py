"""
Fachada ELIA para invocar desde la UI web sin acoplarse al legacy DICAI.

Credenciales:
- Por job (`inline=True`): objeto enviado en la API por job — no lee secrets.ini ni variables.
- Legacy (`inline=False`): `secrets.ini`, `ELIA_SECRETS_INI` o variables `ELIA_*` / `BEE_ELIA_*`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from elia.config_loader import jira_settings, load_config_parser, value_edge_settings
from elia.core import JiraExtractor, UltimateGherkinConverter, ValueEdgeExtractor


def _empty_jira_inline_message() -> str:
    return (
        "Jira: faltan credenciales para este trabajo. Abre Configuración (engranaje), "
        "completa Jira en un perfil y selecciónalo en «Inteligencia de Requerimientos», o usa el modo legacy (secrets.ini)."
    )


def _empty_ve_inline_message() -> str:
    return (
        "Value Edge: faltan credenciales para este trabajo. Completa el perfil en Configuración y selecciónalo, "
        "o usa el modo legacy (secrets.ini)."
    )


def resolve_jira_credentials(*, inline: bool, creds: Optional[Mapping[str, str]]) -> Tuple[Dict[str, str], str]:
    if inline:
        if not creds:
            raise ValueError(_empty_jira_inline_message())
        url = str(creds.get("url") or "").strip()
        email = str(creds.get("email") or "").strip()
        token = str(creds.get("api_token") or "").strip()
        if not url or not email or not token:
            raise ValueError(_empty_jira_inline_message())
        return {"url": url, "email": email, "api_token": token}, "job_payload"

    cfg, path = load_config_parser()
    j = jira_settings(cfg)
    if not j["url"] or not j["email"] or not j["api_token"]:
        raise ValueError(
            "Jira: sin credenciales en línea; configura ELIA desde Configuración o "
            "legacy: secrets.ini bajo datos de usuario, o variables ELIA_JIRA_*."
        )
    return j, str(path)


def resolve_value_edge_settings(*, inline: bool, creds: Optional[Mapping[str, str]]) -> Tuple[Dict[str, str], str]:
    if inline:
        if not creds:
            raise ValueError(_empty_ve_inline_message())
        url = str(creds.get("url") or "").strip().rstrip("/")
        login = str(creds.get("login") or "").strip()
        if url and not login:
            login = f"{url}/authentication/sign_in"
        tp = str(creds.get("tech_preview_flag") or "true").strip() or "true"
        out = {
            "url": url,
            "shared_space": str(creds.get("shared_space") or "").strip(),
            "workspace": str(creds.get("workspace") or "").strip(),
            "tech_preview_flag": tp,
            "login": login,
            "user": str(creds.get("user") or "").strip(),
            "password": str(creds.get("password") or ""),
        }
        need = ["url", "shared_space", "workspace", "user", "password"]
        miss = [k for k in need if not str(out.get(k) or "").strip()]
        if miss:
            raise ValueError(_empty_ve_inline_message())
        return out, "job_payload"

    cfg, path = load_config_parser()
    ve = value_edge_settings(cfg)
    if not ve.get("url"):
        raise ValueError(
            "Value Edge: sin credenciales en línea; usa Configuración o legacy [ValueEdge] en secrets.ini / ELIA_VALUEEDGE_*."
        )
    return ve, str(path)


def get_jira_extractor(*, inline: bool, creds: Optional[Mapping[str, str]]) -> Tuple[JiraExtractor, str]:
    j, src = resolve_jira_credentials(inline=inline, creds=creds)
    return JiraExtractor(j["url"], j["email"], j["api_token"]), src


def get_value_edge_extractor(
    *,
    inline: bool,
    creds: Optional[Mapping[str, str]],
    verify_ssl: bool = False,
) -> Tuple[ValueEdgeExtractor, str]:
    ve, src = resolve_value_edge_settings(inline=inline, creds=creds)
    return ValueEdgeExtractor(settings=ve, verify_ssl=verify_ssl), src


def run_gherkin_batch(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    use_ai: bool = False,
) -> None:
    """Ejecuta conversión por lotes (escribe learned_patterns.json bajo output_dir)."""
    conv = UltimateGherkinConverter(str(input_dir), str(output_dir), use_ai=use_ai)
    conv.convert()


def jira_smoke_test(*, inline: bool, creds: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    ex, src = get_jira_extractor(inline=inline, creds=creds)
    ok = ex.check_connection()
    return {"ok": ok, "source": src}


def value_edge_smoke_test(*, inline: bool, creds: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    ex, src = get_value_edge_extractor(inline=inline, creds=creds)
    ok = ex.login()
    return {"ok": ok, "source": src}
