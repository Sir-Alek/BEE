"""Motor de IA local ELIA (Qwen GGUF + llama-cpp-python)."""

from core.ai.constants import AiProfile, ModelRole, TaskKind
from core.ai.profiles import resolve_profile_from_ram

__all__ = [
    "AiProfile",
    "ModelRole",
    "TaskKind",
    "resolve_profile_from_ram",
]
