"""
Rutas del modelo Gemma (GGUF) para desarrollo y ejecutables PyInstaller.

En modo frozen, los datos van a sys._MEIPASS/resources/... (ver BEE.spec).
En desarrollo, se resuelve desde la raíz del repositorio (directorio padre de core/).
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Nombre canónico acordado con la documentación (readme.txt).
DEFAULT_GEMMA_GGUF_FILENAME = "gemma-4-E4B-it-Q4_K_M.gguf"

_REL_GEMMA_DIR = ("resources", "models", "gemma")


def _repo_root_from_core() -> str:
    """Raíz del proyecto en desarrollo (directorio que contiene `core/` y `resources/`)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resolve_gguf_path(filename: Optional[str] = None) -> str:
    """
    Ruta absoluta esperada del archivo .gguf.

    :param filename: nombre del archivo; por defecto DEFAULT_GEMMA_GGUF_FILENAME.
    """
    name = filename or DEFAULT_GEMMA_GGUF_FILENAME
    if is_frozen():
        base = getattr(sys, "_MEIPASS", "") or os.path.dirname(sys.executable)
        return os.path.join(base, *_REL_GEMMA_DIR, name)
    return os.path.join(_repo_root_from_core(), *_REL_GEMMA_DIR, name)


def is_gguf_available(filename: Optional[str] = None) -> bool:
    """True si el archivo existe y tiene tamaño > 0."""
    path = resolve_gguf_path(filename)
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def get_gemma_model_info(filename: Optional[str] = None) -> dict:
    """
    Información para UI/diagnóstico: ruta resuelta, existencia y tamaño en bytes.
    """
    path = resolve_gguf_path(filename)
    out: dict = {
        "path": path,
        "exists": False,
        "size_bytes": 0,
        "frozen": is_frozen(),
    }
    try:
        if os.path.isfile(path):
            out["exists"] = True
            out["size_bytes"] = os.path.getsize(path)
    except OSError:
        pass
    return out


if __name__ == "__main__":
    info = get_gemma_model_info()
    print("frozen:", info["frozen"])
    print("path:", info["path"])
    print("exists:", info["exists"], "size_bytes:", info["size_bytes"])
