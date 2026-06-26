"""
Planes de suscripción (tiers) y mapa de features por tier.

Tiers comerciales: tester (ELIA Tester) y architect (ELIA Architect).
El tier beta desbloquea todo (builds de distribución beta).

Claves legacy BASIC/PRO se normalizan a tester; ENT a architect.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet

TIER_TESTER = "tester"
TIER_ARCHITECT = "architect"
TIER_BETA = "beta"

# Slugs legacy (solo lectura / compatibilidad de claves antiguas)
TIER_BASIC = "basic"
TIER_PROFESSIONAL = "professional"
TIER_ENTERPRISE = "enterprise"

TIER_CODES: Dict[str, str] = {
    TIER_TESTER: "TESTER",
    TIER_ARCHITECT: "ARCH",
    TIER_BETA: "BETA",
    # Generación de claves v3 con slugs antiguos
    TIER_BASIC: "BASIC",
    TIER_PROFESSIONAL: "PRO",
    TIER_ENTERPRISE: "ENT",
}

CODE_TO_TIER: Dict[str, str] = {
    "TESTER": TIER_TESTER,
    "ARCH": TIER_ARCHITECT,
    "BETA": TIER_BETA,
    "BASIC": TIER_TESTER,
    "PRO": TIER_TESTER,
    "ENT": TIER_ARCHITECT,
}

_LEGACY_SLUG_TO_CANONICAL: Dict[str, str] = {
    TIER_BASIC: TIER_TESTER,
    TIER_PROFESSIONAL: TIER_TESTER,
    TIER_ENTERPRISE: TIER_ARCHITECT,
}

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


def normalize_tier(tier: str) -> str:
    """Normaliza slug o código legacy al tier canónico (tester | architect | beta)."""
    raw = (tier or "").strip().lower()
    if not raw:
        return ""
    if raw == TIER_BETA:
        return TIER_BETA
    code = raw.upper()
    if code in CODE_TO_TIER:
        return CODE_TO_TIER[code]
    if raw in _LEGACY_SLUG_TO_CANONICAL:
        return _LEGACY_SLUG_TO_CANONICAL[raw]
    if raw in (TIER_TESTER, TIER_ARCHITECT):
        return raw
    return ""


def _base_flags() -> Dict[str, bool]:
    return {key: False for key in FEATURE_KEYS}


def get_tier_flags(tier: str) -> Dict[str, bool]:
    """Devuelve las banderas de características según el tier seleccionado."""
    tier_norm = normalize_tier(tier)
    if not tier_norm:
        return _base_flags()

    if tier_norm == TIER_BETA:
        return {key: True for key in FEATURE_KEYS}

    flags = _base_flags()

    if tier_norm == TIER_TESTER:
        flags["web_recording"] = True
        flags["api_http_single"] = True
        flags["doc_to_bdd"] = True
        flags["api_postman_suites"] = True
        flags["mobile_recording"] = True
        flags["publishers_standard"] = True
        return flags

    if tier_norm == TIER_ARCHITECT:
        for key in FEATURE_KEYS:
            flags[key] = True
        return flags

    return flags


def infer_tier_from_v2_mods(mobile: bool, legacy: bool) -> str:
    """Compatibilidad v2: M/L → tier canónico."""
    if legacy:
        return TIER_ARCHITECT
    return TIER_TESTER


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
    tier_norm = normalize_tier(tier) or (tier or "").strip().lower()
    labels = {
        TIER_TESTER: "ELIA Tester",
        TIER_ARCHITECT: "ELIA Architect",
        TIER_BETA: "Beta",
        TIER_BASIC: "ELIA Tester",
        TIER_PROFESSIONAL: "ELIA Tester",
        TIER_ENTERPRISE: "ELIA Architect",
    }
    return labels.get(tier_norm, tier or "—")


def tier_audience(tier: str) -> str:
    tier_norm = normalize_tier(tier)
    if tier_norm == TIER_ARCHITECT:
        return (
            "Bancos, financieras, grandes corporativos y arquitectos de automatización "
            "con infraestructura pesada."
        )
    if tier_norm == TIER_TESTER:
        return (
            "Testers independientes, equipos medianos y células de desarrollo ágil estándar."
        )
    return ""


def tier_required_for_feature(feature: str) -> str:
    """Tier mínimo comercial para upsell UI."""
    tester_features = {
        "doc_to_bdd",
        "api_postman_suites",
        "mobile_recording",
        "publishers_standard",
    }
    if feature in tester_features:
        return TIER_TESTER
    return TIER_ARCHITECT


def upsell_benefits(tier: str) -> list[str]:
    tier_norm = normalize_tier(tier)
    if tier_norm == TIER_TESTER:
        return [
            "Grabación web y cliente HTTP API",
            "Pruebas API en cadena (Postman / suites)",
            "Inteligencia Doc-to-BDD (IA local desde el día uno)",
            "Automatización móvil (Appium)",
            "Publishers Git y Jira Vanilla",
        ]
    if tier_norm == TIER_ARCHITECT:
        return [
            "Todo lo incluido en ELIA Tester",
            "Automatización Legacy (escritorio / pywinauto)",
            "Pruebas de carga Locust, reportes PDF/HTML y SLA",
            "Controladores lógicos (If/Loop), gRPC, JDBC y carga distribuida local",
            "Publishers Xray, Value Edge y Azure DevOps",
            "Team Memory Crypto (seguridad asimétrica local-first)",
        ]
    return []


def entitlements_payload(
    *,
    tier: str,
    features: Dict[str, bool],
    is_beta: bool = False,
    upgrade_email: str = UPGRADE_CONTACT_EMAIL,
) -> Dict[str, Any]:
    tier_norm = normalize_tier(tier) if tier else ""
    legacy = legacy_modules_from_features(features)
    out: Dict[str, Any] = {
        "tier": tier_norm or tier or "",
        "tier_label": tier_display_name(tier_norm or tier),
        "tier_audience": tier_audience(tier_norm or tier),
        "is_beta": is_beta,
        "upgrade_email": upgrade_email,
        "features": dict(features),
        **legacy,
    }
    return out
