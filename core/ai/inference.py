"""Inferencia local Qwen vía llama-cpp-python."""
from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

from core.ai.constants import TaskKind
from core.ai.model_manager import get_ai_runtime_status, get_llama_for_route, inference_lock, is_ai_runtime_configured
from core.ai.model_paths import is_gguf_available
from core.ai.task_router import resolve_task_route

# Re-export compat
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


def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if fence:
        s = fence.group(1)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    for m in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", s, re.DOTALL):
        chunk = m.group(0)
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            continue
    return None


def _thinking_prefix(thinking: bool) -> str:
    if thinking:
        return "/think\n"
    return "/no_think\n"


def _completion_text(result: Any) -> str:
    try:
        choices = result.get("choices") if isinstance(result, dict) else None
        if choices and isinstance(choices[0], dict):
            return str(choices[0].get("text", "") or "")
    except Exception:
        pass
    return ""


def run_llama_json_prompt(
    user_prompt: str,
    *,
    gguf_path: Optional[str] = None,
    max_tokens: int = 512,
    timeout_sec: float = 120.0,
    temperature: float = 0.1,
    task: TaskKind = "generic_json",
) -> Optional[dict]:
    _ = timeout_sec
    if not is_gguf_available() and not gguf_path:
        return None

    route = resolve_task_route(task)
    if route.profile == "off" and not gguf_path:
        return None
    path = gguf_path or route.gguf_path
    if not path:
        return None
    route = replace(
        route,
        gguf_path=path,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    try:
        llm = get_llama_for_route(route)
    except (ImportError, FileNotFoundError, OSError):
        return None

    full_prompt = (
        _thinking_prefix(route.thinking)
        + "You are a test automation assistant. Reply with ONLY one valid JSON object, no markdown, no explanation.\n\n"
        + user_prompt
    )

    with inference_lock():
        try:
            result = llm.create_completion(
                prompt=full_prompt,
                max_tokens=route.max_tokens,
                temperature=float(route.temperature),
                top_p=0.9,
            )
        except Exception:
            return None

    return _extract_json_object(_completion_text(result))


def ai_cot_mode() -> str:
    mode = (os.environ.get("ELIA_AI_COT_MODE") or "single").strip().lower()
    return mode if mode in ("single", "two_pass") else "single"


def run_llama_gbnf_completion(
    user_prompt: str,
    *,
    gbnf_file: str = "bdd_response.gbnf",
    grammar: Any = None,
    gguf_path: Optional[str] = None,
    max_tokens: int = 768,
    temperature: float = 0.1,
    system_prefix: Optional[str] = None,
    task: TaskKind = "doc_to_bdd",
) -> Optional[str]:
    if not is_ai_runtime_configured() and not gguf_path:
        return None

    route = resolve_task_route(task)
    path = gguf_path or route.gguf_path
    if not path:
        return None
    route = replace(
        route,
        gguf_path=path,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    try:
        llm = get_llama_for_route(route)
    except (ImportError, FileNotFoundError, OSError):
        return None

    if grammar is None:
        from core.gemma_gbnf import load_llama_grammar

        grammar = load_llama_grammar(gbnf_file)

    prefix = system_prefix or (
        _thinking_prefix(route.thinking)
        + "You are a test automation assistant. Reply with ONLY one valid JSON object, no markdown.\n\n"
    )
    full_prompt = prefix + user_prompt

    with inference_lock():
        try:
            kwargs: Dict[str, Any] = {
                "prompt": full_prompt,
                "max_tokens": route.max_tokens,
                "temperature": float(route.temperature),
                "top_p": 0.9,
            }
            if grammar is not None:
                kwargs["grammar"] = grammar
            result = llm.create_completion(**kwargs)
        except Exception:
            return None

    return _completion_text(result).strip()


def run_llama_gbnf_json(
    user_prompt: str,
    *,
    gbnf_file: str = "bdd_response.gbnf",
    grammar: Any = None,
    gguf_path: Optional[str] = None,
    max_tokens: int = 768,
    temperature: float = 0.1,
    system_prefix: Optional[str] = None,
    task: TaskKind = "doc_to_bdd",
) -> Optional[dict]:
    text = run_llama_gbnf_completion(
        user_prompt,
        gbnf_file=gbnf_file,
        grammar=grammar,
        gguf_path=gguf_path,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prefix=system_prefix,
        task=task,
    )
    if not text:
        return None
    return _extract_json_object(text)


def suggest_bdd_steps_from_actions(
    actions: List[Tuple[str, str]],
    *,
    base_name: str,
    gguf_path: Optional[str] = None,
    temperature: float = 0.1,
    few_shot_examples: Optional[List[Dict[str, str]]] = None,
) -> Optional[List[Tuple[str, str]]]:
    lines_in = [{"type": t, "description": d} for t, d in actions]
    memory_block = ""
    if few_shot_examples:
        parts = []
        for i, ex in enumerate(few_shot_examples[:3], start=1):
            sc = (ex.get("script") or "").strip()
            ft = (ex.get("feature") or "").strip()
            if sc and ft:
                parts.append(
                    f"[EJEMPLO DE ESTILO {i} — Script (extracto)]\n{sc}\n"
                    f"[EJEMPLO DE ESTILO {i} — Feature esperado]\n{ft}\n"
                )
        if parts:
            memory_block = (
                "Imita el estilo de redacción y nivel de abstracción de estos ejemplos del usuario "
                "(no copies selectores ni nombres técnicos de los scripts):\n"
                + "\n".join(parts)
                + "\n"
            )
    prompt = (
        memory_block
        + "Eres analista de negocio para pruebas BDD en español. Tienes acciones técnicas grabadas (clics, textos).\n"
        "Escribe UN escenario con EXACTAMENTE esta forma (sin pasos de más):\n"
        "- Como mucho: Given (0 o 1), When (1), And (0 o 1), Then (1). NUNCA dos When ni dos Then.\n"
        "- El And solo si hay dos fases claras (p. ej. navegación vs. datos); si no, omítelo.\n"
        "- Lenguaje de negocio: qué hace el usuario y qué resultado espera. "
        "PROHIBIDO citar nombres técnicos de selectores, ids generados o cadenas tipo click_nav_....\n"
        "- Given: solo contexto de acceso (URL o portal) si aplica.\n"
        "- When / And: resumen del flujo en frases naturales.\n"
        "- Then: resultado verificable para el usuario (no \"completó el flujo\" genérico si puedes ser más concreto).\n"
        'Salida JSON: {"steps":[{"keyword":"Given|When|And|Then","text":"..."}]}\n'
        f"Nombre feature: {base_name}\n"
        f"Acciones (referencia, no copiar literal): {json.dumps(lines_in, ensure_ascii=False)}\n"
    )
    data = run_llama_json_prompt(
        prompt,
        gguf_path=gguf_path,
        max_tokens=768,
        temperature=temperature,
        task="bdd_steps",
    )
    if not data or "steps" not in data:
        return None
    out: List[Tuple[str, str]] = []
    for step in data["steps"]:
        if not isinstance(step, dict):
            continue
        kw = str(step.get("keyword", "")).strip().lower()
        txt = str(step.get("text", "")).strip()
        if kw not in ("given", "when", "then", "and") or not txt:
            continue
        out.append((kw, txt))
    if not out:
        return None
    given_c = sum(1 for k, _ in out if k == "given")
    when_c = sum(1 for k, _ in out if k == "when")
    and_c = sum(1 for k, _ in out if k == "and")
    then_c = sum(1 for k, _ in out if k == "then")
    if when_c != 1 or then_c != 1 or given_c > 1 or and_c > 1:
        return None
    seen = [k for k, _ in out]
    expected: List[str] = []
    if "given" in seen:
        expected.append("given")
    expected.extend(["when"])
    if "and" in seen:
        expected.append("and")
    expected.append("then")
    if seen != expected:
        return None
    return out


def suggest_preferred_locator(
    *,
    selector: str,
    xpath: str,
    tag: str = "",
    element_id: str = "",
    gguf_path: Optional[str] = None,
) -> Optional[str]:
    try:
        from core.ui_automation.locator_healer import heal_locator

        record = {
            "selector": selector,
            "xpath": xpath,
            "tag": tag,
            "id": element_id,
        }
        healed = heal_locator(record, use_ai=True, temperature=0.05)
        primary = str(healed.get("primary") or "").strip()
        if primary:
            return primary
    except Exception:
        pass

    prompt = (
        "Pick the more stable locator for automated UI tests (prefer unique id, data-testid, then robust xpath).\n"
        "Output JSON: {\"choice\": \"css\" | \"xpath\", \"reason\": \"short\"}\n"
        f"css_selector: {json.dumps(selector, ensure_ascii=False)}\n"
        f"xpath: {json.dumps(xpath, ensure_ascii=False)}\n"
        f"tag: {json.dumps(tag, ensure_ascii=False)}\n"
        f"id: {json.dumps(element_id, ensure_ascii=False)}\n"
    )
    data = run_llama_json_prompt(
        prompt,
        max_tokens=128,
        gguf_path=gguf_path,
        task="locator_heal",
    )
    if not data:
        return None
    choice = str(data.get("choice", "")).lower().strip()
    if choice == "xpath" and xpath:
        if xpath.startswith("xpath="):
            return xpath
        return "xpath=" + xpath
    if choice == "css" and selector:
        return selector
    return None
