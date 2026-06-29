"""Umbrales y tipos del motor IA local (Qwen)."""
from __future__ import annotations

import os
from typing import Literal

AiProfile = Literal["off", "lite", "standard"]
ModelRole = Literal["analysis", "codegen", "lite_unified"]
TaskKind = Literal[
    "doc_to_bdd",
    "gherkin_classify",
    "gherkin_generate",
    "bdd_steps",
    "locator_heal",
    "api_assertion",
    "generic_json",
]


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def min_ram_total_gb() -> float:
    """RAM total mínima global para cualquier perfil IA (equipos < 8 GB → off)."""
    return _env_float("ELIA_AI_MIN_RAM_GB", 8.0)


def lite_max_ram_total_gb() -> float:
    """Perfil Lite: total ≤ este valor (inclusive)."""
    return _env_float("ELIA_AI_LITE_MAX_RAM_GB", 8.0)


def standard_max_ram_total_gb() -> float:
    """Banda QA habitual Standard; por encima sigue Standard en beta."""
    return _env_float("ELIA_AI_STANDARD_MAX_RAM_GB", 16.0)


def lite_min_ram_free_gb() -> float:
    return _env_float("ELIA_AI_LITE_MIN_RAM_FREE_GB", 4.0)


def standard_min_ram_free_gb() -> float:
    return _env_float("ELIA_AI_STANDARD_MIN_RAM_FREE_GB", 5.0)
