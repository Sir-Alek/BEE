"""Descarga de modelos GGUF desde Hugging Face."""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional

from core.ai.constants import AiProfile
from core.ai.manifest import list_models, verify_model_file
from core.ai.model_paths import models_root, resolve_gguf_path

_download_lock = threading.Lock()
_download_state: Dict[str, Any] = {
    "active": False,
    "profile": None,
    "current": None,
    "completed": [],
    "errors": [],
    "done": False,
}


def _reset_state(*, profile: AiProfile) -> None:
    _download_state.update(
        {
            "active": True,
            "profile": profile,
            "current": None,
            "completed": [],
            "errors": [],
            "done": False,
        }
    )


def get_download_status() -> Dict[str, Any]:
    with _download_lock:
        return dict(_download_state)


from core.ai.setup_wizard import evaluate_wizard


def setup_status() -> Dict[str, Any]:
    from core.ai.model_paths import get_profile_models_status, is_profile_runtime_ready
    from core.ai.profiles import resolve_profile_from_ram

    try:
        import psutil

        vm = psutil.virtual_memory()
        total = round(vm.total / (1024**3), 2)
        avail = round(vm.available / (1024**3), 2)
    except Exception:
        total = None
        avail = None

    assigned = resolve_profile_from_ram(total_gb=total, available_gb=avail)
    wizard = evaluate_wizard()
    return {
        "assigned_profile": assigned,
        "models_root": models_root(),
        "lite_ready": is_profile_runtime_ready("lite"),
        "standard_ready": is_profile_runtime_ready("standard"),
        "lite_models": get_profile_models_status("lite"),
        "standard_models": get_profile_models_status("standard"),
        "download": get_download_status(),
        "manifest_version": _manifest_version(),
        **wizard,
    }


def _manifest_version() -> int:
    try:
        from core.ai.manifest import load_manifest

        return int(load_manifest().get("version") or 1)
    except Exception:
        return 0


def download_profile(profile: AiProfile) -> Dict[str, Any]:
    if profile not in ("lite", "standard"):
        raise ValueError("profile debe ser lite o standard")

    with _download_lock:
        if _download_state.get("active"):
            return {"ok": False, "error": "Ya hay una descarga en curso", "status": get_download_status()}

    thread = threading.Thread(target=_download_profile_worker, args=(profile,), daemon=True)
    thread.start()
    return {"ok": True, "started": True, "profile": profile}


def _download_profile_worker(profile: AiProfile) -> None:
    _reset_state(profile=profile)
    entries = list_models(profile=profile)
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        with _download_lock:
            _download_state["errors"].append("Falta huggingface_hub (pip install huggingface_hub)")
            _download_state["active"] = False
            _download_state["done"] = True
        return

    for entry in entries:
        role = str(entry.get("role") or "")
        filename = str(entry.get("filename") or "")
        repo_id = str(entry.get("repo_id") or "")
        revision = str(entry.get("revision") or "main")
        if not filename or not repo_id:
            continue
        dest = resolve_gguf_path(role=role, profile=profile)  # type: ignore[arg-type]
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with _download_lock:
            _download_state["current"] = filename
        try:
            cached = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                revision=revision,
                local_dir=os.path.dirname(dest),
                local_dir_use_symlinks=False,
            )
            final_path = cached
            if os.path.abspath(cached) != os.path.abspath(dest):
                if os.path.isfile(dest):
                    os.remove(dest)
                os.replace(cached, dest)
                final_path = dest
            ok, err = verify_model_file(final_path, entry)
            if not ok:
                raise RuntimeError(err or "Verificación fallida")
            with _download_lock:
                _download_state["completed"].append(filename)
        except Exception as e:
            with _download_lock:
                _download_state["errors"].append(f"{filename}: {e}")

    with _download_lock:
        _download_state["active"] = False
        _download_state["current"] = None
        _download_state["done"] = True


def verify_installed(profile: AiProfile) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    ok_all = True
    for entry in list_models(profile=profile):
        role = str(entry.get("role") or "")
        path = resolve_gguf_path(role=role, profile=profile)  # type: ignore[arg-type]
        ok, err = verify_model_file(path, entry)
        if not ok:
            ok_all = False
        results.append(
            {
                "role": role,
                "filename": entry.get("filename"),
                "path": path,
                "ok": ok,
                "error": err,
            }
        )
    return {"profile": profile, "ok": ok_all, "models": results}
