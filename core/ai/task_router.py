"""Enrutamiento de tareas IA → rol de modelo y parámetros."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.ai.constants import AiProfile, ModelRole, TaskKind
from core.ai.model_paths import is_profile_runtime_ready, resolve_existing_gguf_path
from core.ai.profiles import resolve_profile_from_ram


@dataclass(frozen=True)
class TaskRoute:
    profile: AiProfile
    role: ModelRole
    gguf_path: Optional[str]
    thinking: bool
    max_tokens: int
    temperature: float


_ANALYSIS_TASKS = frozenset({"doc_to_bdd", "gherkin_generate"})
_CODE_TASKS = frozenset(
    {
        "gherkin_classify",
        "bdd_steps",
        "locator_heal",
        "api_assertion",
        "generic_json",
    }
)


def _effective_profile(
    *,
    total_gb: Optional[float],
    available_gb: Optional[float],
) -> AiProfile:
    assigned = resolve_profile_from_ram(total_gb=total_gb, available_gb=available_gb)
    if assigned == "off":
        return "off"
    if is_profile_runtime_ready(assigned):
        return assigned
    if assigned == "standard" and is_profile_runtime_ready("lite"):
        return "lite"
    if is_profile_runtime_ready("lite"):
        return "lite"
    if is_profile_runtime_ready("standard"):
        return "standard"
    return assigned


def _role_for_task(profile: AiProfile, task: TaskKind) -> ModelRole:
    if profile == "lite":
        return "lite_unified"
    if task in _ANALYSIS_TASKS:
        return "analysis"
    if task in _CODE_TASKS:
        return "codegen"
    return "analysis"


def _thinking_for(profile: AiProfile, role: ModelRole, task: TaskKind) -> bool:
    if profile == "lite":
        return task in _ANALYSIS_TASKS
    if role == "analysis":
        return True
    return False


def _params_for(task: TaskKind) -> tuple[int, float]:
    if task == "doc_to_bdd":
        return 768, 0.1
    if task == "locator_heal":
        return 384, 0.05
    if task == "gherkin_classify":
        return 32, 0.05
    if task == "gherkin_generate":
        return 350, 0.1
    if task == "api_assertion":
        return 384, 0.15
    return 512, 0.1


def resolve_task_route(
    task: TaskKind,
    *,
    total_gb: Optional[float] = None,
    available_gb: Optional[float] = None,
) -> TaskRoute:
    profile = _effective_profile(total_gb=total_gb, available_gb=available_gb)
    if profile == "off":
        return TaskRoute(
            profile="off",
            role="lite_unified",
            gguf_path=None,
            thinking=False,
            max_tokens=512,
            temperature=0.1,
        )
    role = _role_for_task(profile, task)
    path = resolve_existing_gguf_path(role=role, profile=profile)
    if not path and profile == "standard":
        role = "lite_unified"
        profile = "lite"
        path = resolve_existing_gguf_path(role="lite_unified", profile="lite")
    max_tokens, temperature = _params_for(task)
    thinking = _thinking_for(profile, role, task)
    return TaskRoute(
        profile=profile,
        role=role,
        gguf_path=path,
        thinking=thinking,
        max_tokens=max_tokens,
        temperature=temperature,
    )
