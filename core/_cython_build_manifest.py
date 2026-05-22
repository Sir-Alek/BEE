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
        "mobile_android.py",
        "elia_memory.py",
        "elia_memory_crypto.py",
        "elia_paths.py",
    }
)

NON_CYTHON_PY_FILENAMES = frozenset(
    name for name in _SKIP_FILENAMES if name.endswith(".py") and name != "__init__.py"
)

# Solo build; no debe empaquetarse ni importarse en el exe.
_BUILD_ONLY_PY_FILENAMES = frozenset({"_cython_build_manifest.py"})


def discover_core_cython_modules() -> tuple[str, ...]:
    """Rutas posix relativas al repo: core/.../*.py compilables."""
    found: list[str] = []
    for path in sorted(_CORE_DIR.rglob("*.py")):
        if path.name in _SKIP_FILENAMES:
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        found.append(rel)
    return tuple(found)


def discover_non_cython_runtime_modules() -> tuple[str, ...]:
    """Módulos core/ que permanecen como .py en el bundle (imports lazy / metadatos)."""
    found: list[str] = []
    for path in sorted(_CORE_DIR.rglob("*.py")):
        if path.name not in _SKIP_FILENAMES or path.name == "__init__.py":
            continue
        if path.name in _BUILD_ONLY_PY_FILENAMES:
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        found.append(rel)
    return tuple(found)


def verify_core_manifest_coverage() -> list[str]:
    """
    Comprueba que cada .py bajo core/ esté en CYTHON o en la lista de exclusión.
    Devuelve rutas relativas sin clasificar (vacío = OK).
    """
    cython = set(CYTHON_REL_PATHS)
    missing: list[str] = []
    for path in sorted(_CORE_DIR.rglob("*.py")):
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if path.name in _SKIP_FILENAMES or rel in cython:
            continue
        missing.append(rel)
    return missing


def rel_path_to_module(rel_py: str) -> str:
    return rel_py.replace("\\", "/").removesuffix(".py").replace("/", ".")


CYTHON_REL_PATHS: tuple[str, ...] = discover_core_cython_modules()
NON_CYTHON_RUNTIME_REL_PATHS: tuple[str, ...] = discover_non_cython_runtime_modules()
