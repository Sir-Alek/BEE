"""
Inferencia local vía llama-cpp-python (llama.cpp embebido, sin binario llama-cli).

Variables de entorno opcionales:
  ELIA_LLAMA_N_CTX — contexto en tokens (default 4096). (Compat: BEE_LLAMA_N_CTX)
  ELIA_LLAMA_N_GPU_LAYERS — capas en GPU (default 0 = solo CPU). (Compat: BEE_LLAMA_N_GPU_LAYERS)

El modelo GGUF se resuelve con gemma_model_paths.resolve_gguf_path().
"""

from __future__ import annotations

import json
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.gemma_model_paths import is_gguf_available, resolve_gguf_path

# Carga del modelo e inferencias: una a la vez (evita condiciones de carrera / RAM).
_INFERENCE_LOCK = threading.Lock()

_llama_instance = None
_llama_model_path: Optional[str] = None
_llama_lock = threading.Lock()


def _llama_cpp_import():
    """Import lazy para que el resto del core funcione sin llama-cpp-python instalado."""
    from llama_cpp import Llama  # type: ignore

    return Llama


def is_ai_runtime_configured() -> bool:
    if not is_gguf_available():
        return False
    try:
        _llama_cpp_import()
    except ImportError:
        return False
    return True


def get_ai_runtime_status() -> Dict[str, Any]:
    from core import gemma_model_paths

    info = gemma_model_paths.get_gemma_model_info()
    out: Dict[str, Any] = {
        "llama_cpp_python_available": False,
        "llama_cpp_python_version": None,
        "model": info,
    }
    try:
        import llama_cpp

        out["llama_cpp_python_available"] = True
        out["llama_cpp_python_version"] = getattr(llama_cpp, "__version__", None)
    except ImportError as e:
        out["import_error"] = str(e)
    return out


def _get_llama(gguf_path: Optional[str] = None):
    """Instancia singleton de Llama para la ruta de modelo actual."""
    global _llama_instance, _llama_model_path
    model = gguf_path or resolve_gguf_path()
    if not os.path.isfile(model):
        raise FileNotFoundError(model)

    with _llama_lock:
        if _llama_instance is not None and _llama_model_path == model:
            return _llama_instance

        Llama = _llama_cpp_import()
        n_ctx = int(os.environ.get("ELIA_LLAMA_N_CTX") or os.environ.get("BEE_LLAMA_N_CTX") or "4096")
        n_gpu = int(os.environ.get("ELIA_LLAMA_N_GPU_LAYERS") or os.environ.get("BEE_LLAMA_N_GPU_LAYERS") or "0")

        _llama_instance = Llama(
            model_path=model,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu,
            verbose=False,
        )
        _llama_model_path = model
        return _llama_instance


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


def run_llama_json_prompt(
    user_prompt: str,
    *,
    gguf_path: Optional[str] = None,
    max_tokens: int = 512,
    timeout_sec: float = 120.0,
    temperature: float = 0.1,
) -> Optional[dict]:
    """
    Ejecuta el modelo con un prompt que debe devolver un único JSON.
    timeout_sec se reserva para compatibilidad; la inferencia puede bloquear hasta terminar.
    (No usar ``del`` sobre el parámetro: Cython no lo admite al compilar a extensión.)
    """
    # Parámetro reservado para API; llama-cpp-python no expone timeout portable aquí.
    _ = timeout_sec
    if not is_gguf_available():
        return None
    try:
        llm = _get_llama(gguf_path)
    except (ImportError, FileNotFoundError, OSError):
        return None

    full_prompt = (
        "You are a test automation assistant. Reply with ONLY one valid JSON object, no markdown, no explanation.\n\n"
        + user_prompt
    )

    with _INFERENCE_LOCK:
        try:
            result = llm.create_completion(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=float(temperature),
                top_p=0.9,
            )
        except Exception:
            return None

    text = ""
    try:
        choices = result.get("choices") if isinstance(result, dict) else None
        if choices and isinstance(choices[0], dict):
            text = str(choices[0].get("text", "") or "")
    except Exception:
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
    # Estructura estricta: ≤1 Given, 1 When, ≤1 And, 1 Then; orden Given→When→And?→Then
    given_c = sum(1 for k, _ in out if k == "given")
    when_c = sum(1 for k, _ in out if k == "when")
    and_c = sum(1 for k, _ in out if k == "and")
    then_c = sum(1 for k, _ in out if k == "then")
    if when_c != 1 or then_c != 1 or given_c > 1 or and_c > 1:
        return None
    order_ok = ["given", "when", "and", "then"]
    seen = [k for k, _ in out]
    # comprimir orden esperado sin claves faltantes
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
    prompt = (
        "Pick the more stable locator for automated UI tests (prefer unique id, data-testid, then robust xpath).\n"
        "Output JSON: {\"choice\": \"css\" | \"xpath\", \"reason\": \"short\"}\n"
        f"css_selector: {json.dumps(selector, ensure_ascii=False)}\n"
        f"xpath: {json.dumps(xpath, ensure_ascii=False)}\n"
        f"tag: {json.dumps(tag, ensure_ascii=False)}\n"
        f"id: {json.dumps(element_id, ensure_ascii=False)}\n"
    )
    data = run_llama_json_prompt(prompt, max_tokens=128, gguf_path=gguf_path)
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
