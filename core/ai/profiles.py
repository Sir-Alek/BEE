"""Asignación de perfil IA según RAM total."""
from __future__ import annotations

from typing import Optional

from core.ai.constants import (
    AiProfile,
    lite_max_ram_total_gb,
    min_ram_total_gb,
)


def resolve_profile_from_ram(
    *,
    total_gb: Optional[float],
    available_gb: Optional[float] = None,
) -> AiProfile:
    """
    Perfil por RAM total (independiente de RAM libre; eso lo valida ai_policy).

    - total < 8 GB → off
    - total ≤ 8 GB → lite
    - total > 8 GB → standard (incluye > 16 GB en beta)
    """
    _ = available_gb
    if total_gb is None:
        return "standard"
    if total_gb < min_ram_total_gb():
        return "off"
    if total_gb <= lite_max_ram_total_gb():
        return "lite"
    return "standard"


def min_free_gb_for_profile(profile: AiProfile) -> float:
    from core.ai.constants import lite_min_ram_free_gb, standard_min_ram_free_gb

    if profile == "lite":
        return lite_min_ram_free_gb()
    if profile == "standard":
        return standard_min_ram_free_gb()
    return lite_min_ram_free_gb()
