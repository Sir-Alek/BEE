"""Guías rápidas embebidas para onboarding móvil y legacy."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

_GUIDE_FILES = {
    "mobile": ("mobile_quick_start.md", "Guía rápida — Automatización móvil"),
    "legacy": ("legacy_quick_start.md", "Guía rápida — Automatización legacy"),
    "api_load": ("api_suites_quick_start.md", "Guía rápida — Suites y carga (API)"),
}

SUPPORTED_PLATFORMS = frozenset(_GUIDE_FILES.keys())


def _elia_root(elia_root: Optional[str] = None) -> Path:
    if elia_root:
        return Path(elia_root)
    from core.test_runner.behave_support import elia_base_dir

    return Path(elia_base_dir())


def bundled_guide_path(platform: str, *, elia_root: Optional[str] = None) -> Path:
    plat = (platform or "").strip().lower()
    if plat not in _GUIDE_FILES:
        raise ValueError(f"Plataforma sin guía: {platform}")
    filename, _ = _GUIDE_FILES[plat]
    return _elia_root(elia_root) / "resources" / "guides" / filename


def load_platform_guide(platform: str, *, elia_root: Optional[str] = None) -> Tuple[str, str]:
    plat = (platform or "").strip().lower()
    if plat not in _GUIDE_FILES:
        raise ValueError(f"Plataforma sin guía: {platform}")
    _, title = _GUIDE_FILES[plat]
    path = bundled_guide_path(plat, elia_root=elia_root)
    if not path.is_file():
        raise FileNotFoundError(f"Guía no encontrada para {plat}")
    return title, path.read_text(encoding="utf-8")
