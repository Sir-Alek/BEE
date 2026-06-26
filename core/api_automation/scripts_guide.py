"""Guía de scripts API embebida (GUIA_API_SCRIPTS.md)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

API_SCRIPTS_GUIDE_REL = "utils/GUIA_API_SCRIPTS.md"
API_SCRIPTS_GUIDE_TITLE = "Guía de scripts API"


def _elia_root(elia_root: Optional[str] = None) -> Path:
    if elia_root:
        return Path(elia_root)
    from core.test_runner.behave_support import elia_base_dir

    return Path(elia_base_dir())


def bundled_guide_path(*, elia_root: Optional[str] = None) -> Path:
    return _elia_root(elia_root) / "resources" / "behave" / "utils" / "GUIA_API_SCRIPTS.md"


def load_api_scripts_guide_markdown(*, elia_root: Optional[str] = None) -> str:
    path = bundled_guide_path(elia_root=elia_root)
    if not path.is_file():
        raise FileNotFoundError("Guía de scripts API no encontrada")
    return path.read_text(encoding="utf-8")


def ensure_api_scripts_guide(project_path: Path, *, elia_root: Optional[str] = None) -> None:
    """Copia la guía al proyecto API si no existe (utils/GUIA_API_SCRIPTS.md)."""
    src = bundled_guide_path(elia_root=elia_root)
    if not src.is_file():
        return
    dst_dir = project_path / "utils"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "GUIA_API_SCRIPTS.md"
    if not dst.is_file():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
