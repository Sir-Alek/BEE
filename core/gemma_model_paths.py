"""
Rutas del modelo GGUF — compatibilidad hacia core.ai.model_paths (motor Qwen).
"""

from core.ai.model_paths import (  # noqa: F401
    DEFAULT_GGUF_FILENAME,
    get_gemma_model_info,
    get_primary_model_info,
    is_frozen,
    is_gguf_available,
    models_root,
    resolve_gguf_path_legacy as resolve_gguf_path,
)

DEFAULT_GEMMA_GGUF_FILENAME = DEFAULT_GGUF_FILENAME

__all__ = [
    "DEFAULT_GEMMA_GGUF_FILENAME",
    "DEFAULT_GGUF_FILENAME",
    "get_gemma_model_info",
    "get_primary_model_info",
    "is_frozen",
    "is_gguf_available",
    "models_root",
    "resolve_gguf_path",
]
