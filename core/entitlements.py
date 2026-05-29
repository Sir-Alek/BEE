"""
Planes de suscripción (tiers) y mapa de features por tier.

Los tiers comerciales son basic, professional y enterprise.
El tier beta desbloquea todo (builds de distribución beta).
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet

TIER_BASIC = "basic"
TIER_PROFESSIONAL = "professional"
TIER_ENTERPRISE = "enterprise"
TIER_BETA = "beta"

TIER_CODES: Dict[str, str] = {
    TIER_BASIC: "BASIC",
    TIER_PROFESSIONAL: "PRO",
    TIER_ENTERPRISE: "ENT",
    TIER_BETA: "BETA",
}

CODE_TO_TIER: Dict[str, str] = {v: k for k, v in TIER_CODES.items()}

FEATURE_KEYS: FrozenSet[str] = frozenset(
    {
        "web_recording",
        "api_http_single",
        "doc_to_bdd",
        "api_postman_suites",
        "api_locust",
        "mobile_recording",
        "legacy_recording",
        "publishers_standard",
        "publishers_enterprise",
        "team_memory_crypto",
    }
)

UPGRADE_CONTACT_EMAIL = "elia.qa.software+contacto@gmail.com"


def _base_flags() -> Dict[str, bool]:
    return {key: False for key in FEATURE_KEYS}


def get_tier_flags(tier: str) -> Dict[str, bool]:
    """Devuelve las banderas de características según el tier seleccionado."""
    flags = _base_flags()
    tier_norm = (tier or "").strip().lower()

    if tier_norm == TIER_BETA:
        return {key: True for key in FEATURE_KEYS}

    if tier_norm in (TIER_BASIC, TIER_PROFESSIONAL, TIER_ENTERPRISE):
        flags["web_recording"] = True
        flags["api_http_single"] = True

    if tier_norm in (TIER_PROFESSIONAL, TIER_ENTERPRISE):
        flags["doc_to_bdd"] = True
        flags["api_postman_suites"] = True
        flags["mobile_recording"] = True
        flags["publishers_standard"] = True

    if tier_norm == TIER_ENTERPRISE:
        flags["legacy_recording"] = True
        flags["api_locust"] = True
        flags["publishers_enterprise"] = True
        flags["team_memory_crypto"] = True

    return flags


def infer_tier_from_v2_mods(mobile: bool, legacy: bool) -> str:
    """Compatibilidad v2: M/L → tier aproximado."""
    if legacy:
        return TIER_ENTERPRISE
    if mobile:
        return TIER_PROFESSIONAL
    return TIER_BASIC


def legacy_modules_from_features(features: Dict[str, bool]) -> Dict[str, bool]:
    """Booleans legacy consumidos por la UI y rutas antiguas."""
    api_any = bool(
        features.get("api_http_single")
        or features.get("api_postman_suites")
        or features.get("api_locust")
    )
    return {
        "mobile_recording": bool(features.get("mobile_recording")),
        "legacy_recording": bool(features.get("legacy_recording")),
        "doc_to_bdd": bool(features.get("doc_to_bdd")),
        "api_testing": api_any,
    }


def tier_display_name(tier: str) -> str:
    labels = {
        TIER_BASIC: "Basic",
        TIER_PROFESSIONAL: "Professional",
        TIER_ENTERPRISE: "Enterprise",
        TIER_BETA: "Beta",
    }
    return labels.get((tier or "").lower(), tier or "—")


def tier_required_for_feature(feature: str) -> str:
    """Tier mínimo comercial para upsell UI."""
    pro_features = {
        "doc_to_bdd",
        "api_postman_suites",
        "mobile_recording",
        "publishers_standard",
    }
    if feature in pro_features:
        return TIER_PROFESSIONAL
    return TIER_ENTERPRISE


def upsell_benefits(tier: str) -> list[str]:
    if tier == TIER_PROFESSIONAL:
        return [
            "Inteligencia de Requerimientos (Doc-to-BDD)",
            "Automatización Móvil (Appium)",
            "Pruebas API en cadena (Postman / suites)",
            "Publishers Git y Jira Vanilla",
        ]
    if tier == TIER_ENTERPRISE:
        return [
            "Automatización Legacy (pywinauto)",
            "Publishers Xray, Value Edge y Azure DevOps",
            "Team Memory Crypto (export/import seguro)",
            "Performance Testing con Locust y reportes PDF",
        ]
    return []


def entitlements_payload(
    *,
    tier: str,
    features: Dict[str, bool],
    is_beta: bool = False,
    upgrade_email: str = UPGRADE_CONTACT_EMAIL,
) -> Dict[str, Any]:
    legacy = legacy_modules_from_features(features)
    out: Dict[str, Any] = {
        "tier": tier,
        "tier_label": tier_display_name(tier),
        "is_beta": is_beta,
        "upgrade_email": upgrade_email,
        "features": dict(features),
        **legacy,
    }
    return out
