"""
Política de uso de IA local (Qwen): preferencias de usuario, capacidad de hardware y resolución de use_ai.

La UI y los jobs deben usar resolve_use_ai() en el servidor; el campo use_ai del cliente se ignora.

Perfiles:
  - total < 8 GB → off
  - total ≤ 8 GB → lite (libre ≥ 4 GB)
  - total > 8 GB → standard (libre ≥ 5 GB)

Si RAM libre insuficiente → capable=false → heurísticas (modo auto).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

from core import elia_paths
from core.ai.constants import min_ram_total_gb
from core.ai.profiles import min_free_gb_for_profile, resolve_profile_from_ram

AiMode = Literal["auto", "on", "off"]
VALID_MODES: Tuple[AiMode, ...] = ("auto", "on", "off")
DEFAULT_MODE: AiMode = "auto"


def _preferences_file():
    return elia_paths.ensure_user_data_root() / "ai_preferences.json"


def load_preferences() -> Dict[str, Any]:
    path = _preferences_file()
    defaults: Dict[str, Any] = {
        "mode": DEFAULT_MODE,
        "version": 2,
        "memory_auto_learn": True,
        "memory_learn_after_retry": False,
        "gherkin_keywords_english": True,
    }
    if not path.is_file():
        return dict(defaults)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(defaults)
        mode = str(data.get("mode", DEFAULT_MODE)).strip().lower()
        if mode not in VALID_MODES:
            mode = DEFAULT_MODE
        return {
            "mode": mode,
            "version": int(data.get("version", 2)),
            "memory_auto_learn": bool(data.get("memory_auto_learn", True)),
            "memory_learn_after_retry": bool(data.get("memory_learn_after_retry", False)),
            "gherkin_keywords_english": bool(data.get("gherkin_keywords_english", True)),
        }
    except Exception:
        return dict(defaults)


def save_preferences(
    *,
    mode: Optional[AiMode] = None,
    memory_auto_learn: Optional[bool] = None,
    memory_learn_after_retry: Optional[bool] = None,
    gherkin_keywords_english: Optional[bool] = None,
) -> Dict[str, Any]:
    current = load_preferences()
    if mode is not None:
        if mode not in VALID_MODES:
            raise ValueError(f"mode inválido: {mode}")
        current["mode"] = mode
    if memory_auto_learn is not None:
        current["memory_auto_learn"] = bool(memory_auto_learn)
    if memory_learn_after_retry is not None:
        current["memory_learn_after_retry"] = bool(memory_learn_after_retry)
    if gherkin_keywords_english is not None:
        current["gherkin_keywords_english"] = bool(gherkin_keywords_english)
    current["version"] = 2
    path = _preferences_file()
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current


def _env_use_ai_override() -> Optional[bool]:
    raw = (os.environ.get("ELIA_USE_AI") or "").strip().lower()
    if not raw:
        return None
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return None


def assess_capability() -> Dict[str, Any]:
    """RAM, perfil Qwen, modelos GGUF y llama-cpp-python."""
    from core.ai.model_manager import is_ai_runtime_configured
    from core.ai.model_paths import get_primary_model_info, is_profile_runtime_ready

    ram_total_gb: Optional[float] = None
    ram_available_gb: Optional[float] = None
    ram_ok = False
    ram_reason: Optional[str] = None
    min_total = min_ram_total_gb()

    try:
        import psutil

        vm = psutil.virtual_memory()
        ram_total_gb = round(vm.total / (1024**3), 2)
        ram_available_gb = round(vm.available / (1024**3), 2)
    except Exception as e:
        ram_reason = f"No se pudo medir RAM: {e}"

    profile = resolve_profile_from_ram(total_gb=ram_total_gb, available_gb=ram_available_gb)
    min_free = min_free_gb_for_profile(profile if profile != "off" else "lite")

    if ram_total_gb is not None:
        if ram_total_gb < min_total:
            ram_reason = f"RAM total {ram_total_gb} GB < {min_total} GB requeridos"
        elif profile == "off":
            ram_reason = f"RAM total {ram_total_gb} GB insuficiente para IA local"
        elif ram_available_gb is not None and ram_available_gb < min_free:
            ram_reason = (
                f"RAM libre {ram_available_gb} GB < {min_free} GB requeridos "
                f"(perfil {profile})"
            )
        else:
            ram_ok = True

    runtime_profile = profile
    if profile == "standard" and not is_profile_runtime_ready("standard"):
        if is_profile_runtime_ready("lite"):
            runtime_profile = "lite"
        else:
            runtime_profile = profile
    elif profile == "lite" and not is_profile_runtime_ready("lite"):
        runtime_profile = profile

    model_info = get_primary_model_info(runtime_profile if runtime_profile != "off" else "lite")
    model_ok = bool(model_info.get("exists"))
    llama_ok = False
    llama_error: Optional[str] = None
    try:
        llama_ok = is_ai_runtime_configured()
    except Exception as e:
        llama_error = str(e)

    runtime_ok = model_ok and llama_ok
    capable = runtime_ok and ram_ok
    reasons: List[str] = []
    if profile == "off":
        reasons.append("RAM total inferior a 8 GB: IA local desactivada.")
    if not model_ok:
        if profile == "standard":
            reasons.append(
                "Motor IA (perfil Standard) no instalado. "
                "Usa Configuración → Inteligencia para descargar o importar."
            )
        elif profile == "lite":
            reasons.append(
                "Motor IA (perfil Lite) no instalado. "
                "Usa Configuración → Inteligencia para descargar o importar."
            )
        else:
            reasons.append("Motor de IA local no disponible.")
    if not llama_ok:
        reasons.append(
            llama_error or "Motor de inferencia local no configurado correctamente."
        )
    if not ram_ok and ram_reason:
        reasons.append(ram_reason)

    return {
        "model_ok": model_ok,
        "llama_ok": llama_ok,
        "runtime_ok": runtime_ok,
        "ram_ok": ram_ok,
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "ram_min_total_gb": min_total,
        "ram_min_free_gb": min_free,
        "profile": profile,
        "runtime_profile": runtime_profile,
        "capable": capable,
        "reasons": reasons,
        "model": model_info,
    }


@dataclass
class UseAiResolution:
    use_ai: bool
    mode: AiMode
    capable: bool
    degraded: bool
    message: str
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "use_ai": self.use_ai,
            "mode": self.mode,
            "capable": self.capable,
            "degraded": self.degraded,
            "message": self.message,
            "reasons": self.reasons,
        }


def resolve_use_ai(
    *,
    preferences: Optional[Dict[str, Any]] = None,
    capability: Optional[Dict[str, Any]] = None,
) -> UseAiResolution:
    prefs = preferences if preferences is not None else load_preferences()
    mode: AiMode = prefs.get("mode", DEFAULT_MODE)  # type: ignore[assignment]
    if mode not in VALID_MODES:
        mode = DEFAULT_MODE

    cap = capability if capability is not None else assess_capability()
    capable = bool(cap.get("capable"))
    reasons = list(cap.get("reasons") or [])
    profile = cap.get("profile") or "off"

    env_override = _env_use_ai_override()
    if env_override is not None:
        use_ai = env_override
        msg = (
            "IA activada por variable ELIA_USE_AI."
            if use_ai
            else "IA desactivada por variable ELIA_USE_AI."
        )
        return UseAiResolution(
            use_ai=use_ai,
            mode=mode,
            capable=capable,
            degraded=not use_ai and capable and mode == "auto",
            message=msg,
            reasons=reasons,
        )

    if mode == "off":
        return UseAiResolution(
            use_ai=False,
            mode=mode,
            capable=capable,
            degraded=False,
            message="Modo rápido (sin IA) activo en Configuración.",
            reasons=reasons,
        )

    if mode == "on":
        runtime_ok = bool(cap.get("runtime_ok"))
        ram_ok = bool(cap.get("ram_ok"))
        use_ai = runtime_ok
        min_free = cap.get("ram_min_free_gb", 4)
        if use_ai and not ram_ok:
            msg = (
                f"IA forzada (Siempre activada): se usará IA aunque la RAM libre "
                f"sea menor a {min_free} GB (perfil {profile}); puede ir lento o fallar."
            )
        elif use_ai:
            msg = f"IA forzada en Configuración (Siempre activada). Perfil: {profile}."
        else:
            msg = "IA forzada en Configuración, pero el motor de IA local no está disponible."
        return UseAiResolution(
            use_ai=use_ai,
            mode=mode,
            capable=capable,
            degraded=not capable or (use_ai and not ram_ok),
            message=msg,
            reasons=reasons,
        )

    # auto
    use_ai = capable
    if capable:
        runtime_profile = cap.get("runtime_profile") or profile
        msg = f"IA local activa (modo automático). Perfil: {runtime_profile}."
    else:
        msg = (
            "Recursos limitados o modelos no disponibles. La IA local se desactivó; "
            "ELIA usará heurísticas. Puedes forzar IA en Configuración → Inteligencia "
            "o instalar los modelos desde la misma sección."
        )
    return UseAiResolution(
        use_ai=use_ai,
        mode=mode,
        capable=capable,
        degraded=not capable,
        message=msg,
        reasons=reasons,
    )


def get_ai_status_payload() -> Dict[str, Any]:
    """Respuesta unificada para /api/ai/capabilities y UI."""
    from core.ai.model_download import setup_status
    from core.ai.model_manager import get_ai_runtime_status

    prefs = load_preferences()
    cap = assess_capability()
    resolution = resolve_use_ai(preferences=prefs, capability=cap)
    runtime = get_ai_runtime_status()
    setup = setup_status()
    return {
        "preferences": prefs,
        "capability": cap,
        "resolution": resolution.to_dict(),
        "runtime": runtime,
        "setup": setup,
        "brand_line": "Evolving Learning & Intelligent Automation",
    }
