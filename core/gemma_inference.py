"""
Inferencia local vía llama.cpp (subproceso aislado).

Configuración:
  BEE_LLAMA_CLI — Ruta al ejecutable llama-cli; si está vacío se busca en PATH.
  BEE_LLAMA_EXTRA_ARGS — Args opcionales separados por espacio (p. ej. "-ngl 0").

El modelo GGUF se resuelve con gemma_model_paths.resolve_gguf_path().
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.gemma_model_paths import is_gguf_available, resolve_gguf_path

# Evita arranques concurrentes del mismo binario/modelo (pesado en CPU/RAM).
_SUBPROC_LOCK = threading.Lock()


def is_ai_runtime_configured() -> bool:
    if not is_gguf_available():
        return False
    exe = (os.environ.get("BEE_LLAMA_CLI") or "").strip()
    if exe:
        return os.path.isfile(exe) or bool(shutil.which(exe))
    return bool(shutil.which("llama-cli") or shutil.which("llama-cli.exe"))


def get_ai_runtime_status() -> Dict[str, Any]:
    exe = (os.environ.get("BEE_LLAMA_CLI") or "").strip()
    from core import gemma_model_paths

    info = gemma_model_paths.get_gemma_model_info()
    return {
        "llama_cli_configured": bool(exe),
        "llama_cli_path": exe if exe else None,
        "llama_cli_on_path": bool(shutil.which("llama-cli") or shutil.which("llama-cli.exe")),
        "model": info,
    }


def _extra_args() -> List[str]:
    raw = (os.environ.get("BEE_LLAMA_EXTRA_ARGS") or "").strip()
    if not raw:
        return []
    return raw.split()


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
    # Último objeto JSON en el texto
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
) -> Optional[dict]:
    """
    Ejecuta llama-cli con un prompt que debe devolver un único JSON.
    Retorna None si no hay binario, modelo o si falla el parseo.
    """
    exe = (os.environ.get("BEE_LLAMA_CLI") or "").strip()
    if not exe:
        w = shutil.which("llama-cli") or shutil.which("llama-cli.exe")
        if not w:
            return None
        exe = w

    model = gguf_path or resolve_gguf_path()
    if not os.path.isfile(model):
        return None

    # Prompt mínimo: forzar JSON (Gemma / instruct)
    full_prompt = (
        "You are a test automation assistant. Reply with ONLY one valid JSON object, no markdown, no explanation.\n\n"
        + user_prompt
    )

    args = [
        exe,
        "-m",
        model,
        "-p",
        full_prompt,
        "-n",
        str(max_tokens),
        "--temp",
        "0.1",
        "--no-display",
    ]
    args.extend(_extra_args())

    with _SUBPROC_LOCK:
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return _extract_json_object(out)


def suggest_bdd_steps_from_actions(
    actions: List[Tuple[str, str]],
    *,
    base_name: str,
    gguf_path: Optional[str] = None,
) -> Optional[List[Tuple[str, str]]]:
    """
    actions: lista (tipo, descripción) con tipo en given|click|fill|select (como en _generate_bdd_feature).
    Retorna lista (keyword_lower, texto) p.ej. ("when", "clic en ...") o None.
    """
    lines_in = [{"type": t, "description": d} for t, d in actions]
    prompt = (
        "Given this ordered list of UI actions from a web recording, produce a Gherkin scenario body "
        "(Spanish descriptions like the input). Rules:\n"
        "- Use at most ONE line starting with And, and only immediately after a When line if needed.\n"
        "- Do not use more than one And in the whole scenario.\n"
        "- Prefer grouping multiple clicks into one When separated by commas.\n"
        "- Start with Given for navigation if present, then When, optional single And, then Then.\n"
        "Output JSON format: {\"steps\": [{\"keyword\": \"Given|When|Then|And\", \"text\": \"...\"}]}\n"
        f"Feature base name: {base_name}\n"
        f"Actions JSON: {json.dumps(lines_in, ensure_ascii=False)}\n"
    )
    data = run_llama_json_prompt(prompt, gguf_path=gguf_path)
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
    # Validar regla: máximo un And, y solo después del primer When
    and_seen = 0
    when_seen = False
    for kw, _ in out:
        if kw == "when":
            when_seen = True
        elif kw == "and":
            if not when_seen:
                return None
            and_seen += 1
            if and_seen > 1:
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
    """
    Elige entre selector CSS original y xpath del DOM para usar en Page Object.
    Retorna la cadena del locator preferido (css o xpath=...) o None.
    """
    prompt = (
        "Pick the more stable locator for automated UI tests (prefer unique id, data-testid, then robust xpath).\n"
        "Output JSON: {\"choice\": \"css\" | \"xpath\", \"reason\": \"short\"}\n"
        f"css_selector: {json.dumps(selector, ensure_ascii=False)}\n"
        f"xpath: {json.dumps(xpath, ensure_ascii=False)}\n"
        f"tag: {json.dumps(tag, ensure_ascii=False)}\n"
        f"id: {json.dumps(element_id, ensure_ascii=False)}\n"
    )
    data = run_llama_json_prompt(prompt, max_tokens=128, timeout_sec=60.0, gguf_path=gguf_path)
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
