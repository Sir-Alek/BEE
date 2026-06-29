"""Estado y lógica del wizard de configuración IA (primer arranque)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core import elia_paths
from core.ai.constants import min_ram_total_gb
from core.ai.model_paths import is_profile_runtime_ready
from core.ai.profiles import min_free_gb_for_profile, resolve_profile_from_ram

WIZARD_VERSION = 1


def _wizard_path():
    return elia_paths.ensure_user_data_root() / "ai_setup_wizard.json"


def load_wizard_state() -> Dict[str, Any]:
    path = _wizard_path()
    if not path.is_file():
        return {"version": WIZARD_VERSION, "completed": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"version": WIZARD_VERSION, "completed": False}
        return data
    except Exception:
        return {"version": WIZARD_VERSION, "completed": False}


def save_wizard_state(doc: Dict[str, Any]) -> Dict[str, Any]:
    path = _wizard_path()
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc


def mark_wizard_completed(*, note: Optional[str] = None) -> Dict[str, Any]:
    doc = load_wizard_state()
    doc["completed"] = True
    doc["version"] = WIZARD_VERSION
    doc["completed_at"] = datetime.now(timezone.utc).isoformat()
    if note:
        doc["note"] = note
    return save_wizard_state(doc)


def _profile_ready(profile: str) -> bool:
    if profile == "lite":
        return is_profile_runtime_ready("lite")
    if profile == "standard":
        return is_profile_runtime_ready("standard")
    return False


def evaluate_wizard() -> Dict[str, Any]:
    ram_total_gb: Optional[float] = None
    ram_available_gb: Optional[float] = None
    try:
        import psutil

        vm = psutil.virtual_memory()
        ram_total_gb = round(vm.total / (1024**3), 2)
        ram_available_gb = round(vm.available / (1024**3), 2)
    except Exception:
        pass

    assigned = resolve_profile_from_ram(total_gb=ram_total_gb, available_gb=ram_available_gb)
    min_free = min_free_gb_for_profile(assigned if assigned != "off" else "lite")
    ram_free_ok = (
        ram_available_gb is not None
        and ram_available_gb >= min_free
        and ram_total_gb is not None
        and ram_total_gb >= min_ram_total_gb()
    )

    profile_ready = False
    if assigned == "lite":
        profile_ready = _profile_ready("lite")
    elif assigned == "standard":
        profile_ready = _profile_ready("standard")

    state = load_wizard_state()
    completed = bool(state.get("completed"))

    if assigned in ("lite", "standard") and profile_ready and not completed:
        mark_wizard_completed(note="models_ready")
        completed = True
        state = load_wizard_state()

    show_wizard = not completed
    if assigned == "off":
        show_wizard = not completed
    elif profile_ready:
        show_wizard = False

    download_size_hint_gb = 2.5 if assigned == "lite" else 10.0 if assigned == "standard" else 0.0

    return {
        "show_wizard": show_wizard,
        "wizard_completed": completed,
        "assigned_profile": assigned,
        "profile_ready": profile_ready,
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "ram_min_free_gb": min_free,
        "ram_free_ok": ram_free_ok,
        "download_size_hint_gb": download_size_hint_gb,
        "wizard_state": {
            "completed": completed,
            "completed_at": state.get("completed_at"),
            "version": state.get("version", WIZARD_VERSION),
        },
    }
