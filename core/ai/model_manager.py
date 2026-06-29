"""Gestión singleton de instancias Llama con swap entre modelos Standard."""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

from core.ai.constants import ModelRole
from core.ai.model_paths import resolve_existing_gguf_path
from core.ai.profiles import resolve_profile_from_ram

_llama_instance = None
_llama_model_path: Optional[str] = None
_llama_lock = threading.Lock()
_INFERENCE_LOCK = threading.Lock()


def inference_lock():
    return _INFERENCE_LOCK


def _llama_cpp_import():
    from llama_cpp import Llama  # type: ignore

    return Llama


def unload_llama() -> None:
    global _llama_instance, _llama_model_path
    with _llama_lock:
        _llama_instance = None
        _llama_model_path = None


def _chat_format_for_path(path: str) -> Optional[str]:
    base = os.path.basename(path).lower()
    if "coder" in base or "qwen2.5" in base:
        return "chatml"
    if "qwen3" in base or "qwen" in base:
        return "chatml"
    return None


def get_llama(*, role: ModelRole, profile: str, gguf_path: Optional[str] = None):
    global _llama_instance, _llama_model_path
    model = gguf_path or resolve_existing_gguf_path(role=role, profile=profile)  # type: ignore[arg-type]
    if not model or not os.path.isfile(model):
        raise FileNotFoundError(model or f"modelo no disponible role={role}")

    with _llama_lock:
        if _llama_instance is not None and _llama_model_path == model:
            return _llama_instance

        Llama = _llama_cpp_import()
        n_ctx = int(os.environ.get("ELIA_LLAMA_N_CTX") or "4096")
        n_gpu = int(os.environ.get("ELIA_LLAMA_N_GPU_LAYERS") or "0")
        chat_format = _chat_format_for_path(model)

        _llama_instance = None
        _llama_model_path = None

        kwargs: Dict[str, Any] = {
            "model_path": model,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu,
            "verbose": False,
        }
        if chat_format:
            kwargs["chat_format"] = chat_format

        _llama_instance = Llama(**kwargs)
        _llama_model_path = model
        return _llama_instance


def get_llama_for_route(route) -> Any:
    if not route.gguf_path:
        raise FileNotFoundError("Ruta GGUF no resuelta")
    return get_llama(role=route.role, profile=route.profile, gguf_path=route.gguf_path)


def is_ai_runtime_configured() -> bool:
    from core.ai.model_paths import is_profile_runtime_ready

    try:
        _llama_cpp_import()
    except ImportError:
        return False
    try:
        import psutil

        vm = psutil.virtual_memory()
        total = round(vm.total / (1024**3), 2)
        avail = round(vm.available / (1024**3), 2)
    except Exception:
        total = None
        avail = None
    profile = resolve_profile_from_ram(total_gb=total, available_gb=avail)
    if profile != "off" and is_profile_runtime_ready(profile):
        return True
    return is_profile_runtime_ready("lite") or is_profile_runtime_ready("standard")


def get_ai_runtime_status() -> Dict[str, Any]:
    from core.ai.model_paths import get_primary_model_info
    from core.ai.profiles import resolve_profile_from_ram

    try:
        import psutil

        vm = psutil.virtual_memory()
        total = round(vm.total / (1024**3), 2)
        avail = round(vm.available / (1024**3), 2)
    except Exception:
        total = None
        avail = None
    profile = resolve_profile_from_ram(total_gb=total, available_gb=avail)
    info = get_primary_model_info(profile)
    out: Dict[str, Any] = {
        "llama_cpp_python_available": False,
        "llama_cpp_python_version": None,
        "model": info,
        "profile": profile,
    }
    try:
        import llama_cpp

        out["llama_cpp_python_available"] = True
        out["llama_cpp_python_version"] = getattr(llama_cpp, "__version__", None)
    except ImportError as e:
        out["import_error"] = str(e)
    return out
