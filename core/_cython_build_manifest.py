"""
Módulos de core/ a compilar con Cython en builds de release.

Se descubren automáticamente todos los .py bajo core/ excepto:
  - __init__.py (marcadores de paquete; PyInstaller los necesita como .py)
  - _cython_build_manifest.py (solo build)
  - version.py / _version.py / install_manifest.py (no compilar con Cython)
"""
from __future__ import annotations

from pathlib import Path

_CORE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CORE_DIR.parent
_SKIP_FILENAMES = frozenset(
    {
        "__init__.py",
        "_cython_build_manifest.py",
        "version.py",
        "_version.py",
        "install_manifest.py",
        "modules_config.py",
        "mobile_recorder.py",
    }
)

NON_CYTHON_PY_FILENAMES = frozenset(
    name for name in _SKIP_FILENAMES if name.endswith(".py") and name != "__init__.py"
)


def discover_core_cython_modules() -> tuple[str, ...]:
    """Rutas posix relativas al repo: core/.../*.py compilables."""
    found: list[str] = []
    for path in sorted(_CORE_DIR.rglob("*.py")):
        if path.name in _SKIP_FILENAMES:
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        found.append(rel)
    return tuple(found)


CYTHON_REL_PATHS: tuple[str, ...] = discover_core_cython_modules()
