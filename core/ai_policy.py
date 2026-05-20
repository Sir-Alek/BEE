"""
Política de uso de IA local (Gemma): preferencias de usuario, capacidad de hardware y resolución de use_ai.

La UI y los jobs deben usar resolve_use_ai() en el servidor; el campo use_ai del cliente se ignora.

La medición de RAM (psutil) es puntual: al abrir Configuración/capabilities y una vez al
iniciar cada job. No se re-evalúa durante una conversión larga en curso.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

from core import elia_paths

AiMode = Literal["auto", "on", "off"]
VALID_MODES: Tuple[AiMode, ...] = ("auto", "on", "off")
DEFAULT_MODE: AiMode = "auto"


def _min_ram_total_gb() -> float:
    try:
        return float(os.environ.get("ELIA_AI_MIN_RAM_GB", "8"))
    except ValueError:
        return 8.0


def _min_ram_free_gb() -> float:
    try:
        return float(os.environ.get("ELIA_AI_MIN_RAM_FREE_GB", "4"))
    except ValueError:
        return 4.0


def _preferences_file():
    return elia_paths.ensure_user_data_root() / "ai_preferences.json"


def load_preferences() -> Dict[str, Any]:
    path = _preferences_file()
    if not path.is_file():
        return {"mode": DEFAULT_MODE, "version": 1}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"mode": DEFAULT_MODE, "version": 1}
        mode = str(data.get("mode", DEFAULT_MODE)).strip().lower()
        if mode not in VALID_MODES:
            mode = DEFAULT_MODE
        return {"mode": mode, "version": int(data.get("version", 1))}
    except Exception:
        return {"mode": DEFAULT_MODE, "version": 1}


def save_preferences(*, mode: AiMode) -> Dict[str, Any]:
    if mode not in VALID_MODES:
        raise ValueError(f"mode inválido: {mode}")
    path = _preferences_file()
    doc = {"version": 1, "mode": mode}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc


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
    """RAM, modelo GGUF y llama-cpp-python."""
    from core import gemma_inference, gemma_model_paths

    model_info = gemma_model_paths.get_gemma_model_info()
    model_ok = bool(model_info.get("exists")) and int(model_info.get("size_bytes") or 0) > 0
    llama_ok = False
    llama_error: Optional[str] = None
    try:
        llama_ok = gemma_inference.is_ai_runtime_configured()
    except Exception as e:
        llama_error = str(e)

    ram_total_gb: Optional[float] = None
    ram_available_gb: Optional[float] = None
    ram_ok = False
    ram_reason: Optional[str] = None
    min_total = _min_ram_total_gb()
    min_free = _min_ram_free_gb()

    try:
        import psutil

        vm = psutil.virtual_memory()
        ram_total_gb = round(vm.total / (1024**3), 2)
        ram_available_gb = round(vm.available / (1024**3), 2)
        if ram_total_gb < min_total:
            ram_reason = f"RAM total {ram_total_gb} GB < {min_total} GB requeridos"
        elif ram_available_gb < min_free:
            ram_reason = f"RAM libre {ram_available_gb} GB < {min_free} GB requeridos"
        else:
            ram_ok = True
    except Exception as e:
        ram_reason = f"No se pudo medir RAM: {e}"

    runtime_ok = model_ok and llama_ok
    capable = runtime_ok and ram_ok
    reasons: List[str] = []
    if not model_ok:
        reasons.append("Modelo de IA (GGUF) no encontrado en resources/models/gemma.")
    if not llama_ok:
        reasons.append(
            llama_error or "Falta llama-cpp-python o no está configurado correctamente."
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
        # Forzado: usa IA si el modelo puede cargarse; ignora solo el umbral de RAM (no el modelo).
        use_ai = runtime_ok
        if use_ai and not ram_ok:
            msg = (
                "IA forzada (Siempre activada): se usará IA aunque la RAM libre "
                f"sea menor a {cap.get('ram_min_free_gb', 4)} GB; puede ir lento o fallar."
            )
        elif use_ai:
            msg = "IA forzada en Configuración (Siempre activada)."
        else:
            msg = "IA forzada en Configuración, pero el modelo de IA o llama-cpp no están disponibles."
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
        msg = "IA local activa (modo automático)."
    else:
        msg = (
            "Recursos limitados o modelo no disponible. La IA local se desactivó para mantener fluidez. "
            "Puedes forzar su activación en Configuración → Inteligencia (IA)."
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
    from core import gemma_inference

    prefs = load_preferences()
    cap = assess_capability()
    resolution = resolve_use_ai(preferences=prefs, capability=cap)
    runtime = gemma_inference.get_ai_runtime_status()
    return {
        "preferences": prefs,
        "capability": cap,
        "resolution": resolution.to_dict(),
        "runtime": runtime,
        "brand_line": "Evolving Learning & Intelligent Automation",
    }
