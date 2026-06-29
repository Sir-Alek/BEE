"""Rutas de modelos Qwen GGUF (desarrollo, usuario y PyInstaller)."""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from core import elia_paths
from core.ai.constants import AiProfile, ModelRole
from core.ai.manifest import get_model_entry, list_models, verify_model_file


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def models_root() -> str:
    override = (os.environ.get("ELIA_AI_MODELS_DIR") or "").strip()
    if override:
        return os.path.abspath(override)
    if is_frozen():
        d = elia_paths.ensure_user_data_root() / "models" / "qwen"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)
    return os.path.join(_repo_root(), "resources", "models", "qwen")


def _subdir_for_profile(profile: AiProfile) -> str:
    if profile == "lite":
        return "lite"
    if profile == "standard":
        return "standard"
    return ""


def resolve_gguf_path(
    *,
    role: ModelRole,
    profile: AiProfile,
    filename: Optional[str] = None,
) -> str:
    entry = get_model_entry(role=role, profile=profile)
    name = filename or (entry or {}).get("filename") or ""
    if not name:
        raise ValueError(f"No hay filename para role={role} profile={profile}")
    sub = _subdir_for_profile(profile)
    return os.path.join(models_root(), sub, name) if sub else os.path.join(models_root(), name)


def _legacy_gemma_path() -> str:
    from core.gemma_model_paths import resolve_gguf_path as legacy

    return legacy()


def _search_candidates(path: str) -> List[str]:
    """Orden de búsqueda: ruta canónica, repo dev, legado Gemma (compat transitoria)."""
    candidates = [path]
    if not is_frozen():
        rel = os.path.relpath(path, models_root()) if path.startswith(models_root()) else os.path.basename(path)
        repo_path = os.path.join(_repo_root(), "resources", "models", "qwen", rel)
        if repo_path not in candidates:
            candidates.append(repo_path)
    try:
        gemma = _legacy_gemma_path()
        if gemma not in candidates:
            candidates.append(gemma)
    except Exception:
        pass
    return candidates


def is_role_model_available(*, role: ModelRole, profile: AiProfile) -> bool:
    entry = get_model_entry(role=role, profile=profile)
    if not entry:
        return False
    try:
        path = resolve_gguf_path(role=role, profile=profile)
    except ValueError:
        return False
    for candidate in _search_candidates(path):
        ok, _ = verify_model_file(candidate, entry)
        if ok:
            return True
    return False


def resolve_existing_gguf_path(*, role: ModelRole, profile: AiProfile) -> Optional[str]:
    entry = get_model_entry(role=role, profile=profile)
    if not entry:
        return None
    try:
        path = resolve_gguf_path(role=role, profile=profile)
    except ValueError:
        return None
    for candidate in _search_candidates(path):
        ok, _ = verify_model_file(candidate, entry)
        if ok:
            return candidate
    return None


def is_profile_runtime_ready(profile: AiProfile) -> bool:
    if profile == "off":
        return False
    from core.ai.manifest import profile_roles

    for role in profile_roles(profile):
        if not is_role_model_available(role=role, profile=profile):  # type: ignore[arg-type]
            return False
    return True


def get_model_info(*, role: ModelRole, profile: AiProfile) -> Dict[str, Any]:
    entry = get_model_entry(role=role, profile=profile) or {}
    expected = resolve_gguf_path(role=role, profile=profile) if entry else ""
    existing = resolve_existing_gguf_path(role=role, profile=profile) if entry else None
    out: Dict[str, Any] = {
        "role": role,
        "profile": profile,
        "expected_path": expected,
        "path": existing or expected,
        "exists": bool(existing),
        "size_bytes": 0,
        "verified": False,
        "entry": entry,
        "frozen": is_frozen(),
        "models_root": models_root(),
    }
    if existing:
        try:
            out["size_bytes"] = os.path.getsize(existing)
            out["verified"] = True
        except OSError:
            pass
    return out


def get_profile_models_status(profile: AiProfile) -> List[Dict[str, Any]]:
    if profile == "off":
        return []
    from core.ai.manifest import profile_roles

    return [get_model_info(role=r, profile=profile) for r in profile_roles(profile)]  # type: ignore[arg-type]


def get_primary_model_info(profile: AiProfile) -> Dict[str, Any]:
    """Info resumida para UI/diagnóstico (primer rol del perfil)."""
    from core.ai.manifest import profile_roles

    roles = profile_roles(profile)
    if not roles:
        return {
            "path": models_root(),
            "exists": False,
            "size_bytes": 0,
            "frozen": is_frozen(),
            "profile": profile,
        }
    info = get_model_info(role=roles[0], profile=profile)  # type: ignore[arg-type]
    return {
        "path": info.get("path"),
        "exists": is_profile_runtime_ready(profile),
        "size_bytes": info.get("size_bytes", 0),
        "frozen": info.get("frozen", False),
        "profile": profile,
        "models": get_profile_models_status(profile),
    }


# --- Compatibilidad Gemma ---

DEFAULT_GGUF_FILENAME = "Qwen3-4B-Q4_K_M.gguf"


def resolve_gguf_path_legacy(filename: Optional[str] = None) -> str:
    """Compat: devuelve ruta esperada del modelo activo o Lite."""
    from core.ai.profiles import resolve_profile_from_ram

    prof = resolve_profile_from_ram(total_gb=None, available_gb=None)
    if prof == "standard":
        p = resolve_existing_gguf_path(role="analysis", profile="standard")
        if p:
            return p
    if prof in ("lite", "standard"):
        p = resolve_existing_gguf_path(role="lite_unified", profile="lite")
        if p:
            return p
        p = resolve_existing_gguf_path(role="analysis", profile="standard")
        if p:
            return p
    return os.path.join(models_root(), "lite", filename or DEFAULT_GGUF_FILENAME)


def is_gguf_available(filename: Optional[str] = None) -> bool:
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
    if profile == "off":
        profile = "lite"
    if is_profile_runtime_ready(profile):
        return True
    if is_profile_runtime_ready("lite"):
        return True
    if is_profile_runtime_ready("standard"):
        return True
    return False


def get_gemma_model_info(filename: Optional[str] = None) -> dict:
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
    return get_primary_model_info(profile)
