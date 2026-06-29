"""
Inferencia local — compatibilidad hacia core.ai.inference (motor Qwen).

El código nuevo vive en core/ai/. Este módulo conserva imports existentes.
"""

from core.ai.inference import (  # noqa: F401
    ai_cot_mode,
    get_ai_runtime_status,
    is_ai_runtime_configured,
    run_llama_gbnf_completion,
    run_llama_gbnf_json,
    run_llama_json_prompt,
    suggest_bdd_steps_from_actions,
    suggest_preferred_locator,
)

__all__ = [
    "ai_cot_mode",
    "get_ai_runtime_status",
    "is_ai_runtime_configured",
    "run_llama_gbnf_completion",
    "run_llama_gbnf_json",
    "run_llama_json_prompt",
    "suggest_bdd_steps_from_actions",
    "suggest_preferred_locator",
]
