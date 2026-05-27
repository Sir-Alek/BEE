"""Prompts compartidos del flujo puppeteer_recorder (web UI)."""
from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

from webui.job_manager import JobManager, Prompt


def _recording_option_defs() -> list[dict[str, Any]]:
    from core.modules_config import is_module_enabled

    options: list[dict[str, Any]] = [
        {
            "key": "video",
            "label": "Grabación de video de la pantalla",
            "default": False,
        },
    ]
    if is_module_enabled("api_testing"):
        options.append(
            {
                "key": "capture_api",
                "label": "Capturar tráfico API (XHR/fetch) junto con la grabación",
                "default": False,
            }
        )
    return options


def prompt_web_recording_options(
    jm: JobManager,
    job_id: str,
    mk_prompt: Callable[..., Prompt],
) -> Optional[Tuple[bool, bool]]:
    """
    Pregunta por video y captura API (checkboxes independientes).
    Devuelve (grabar_video, capture_api) o None si el usuario cancela.
    """
    jm.update_progress(job_id, {"stage": "Opciones de captura"})
    ans = jm.create_prompt_and_wait(
        job_id,
        prompt=mk_prompt(
            type="recording_options",
            title="Opciones de captura",
            message=(
                "Marca los complementos que deseas activar durante la sesión. "
                "Puedes elegir ninguno, uno o ambos."
            ),
            payload={"options": _recording_option_defs()},
        ),
    )
    if ans is None:
        return None
    if isinstance(ans, dict):
        return bool(ans.get("video")), bool(ans.get("capture_api"))
    return False, False


def prompt_web_recording_proceed(
    jm: JobManager,
    job_id: str,
    mk_prompt: Callable[..., Prompt],
) -> Optional[bool]:
    """Confirmación final antes de abrir el navegador. True=continuar, False=no, None=cancelar."""
    jm.update_progress(job_id, {"stage": "Confirmar grabación"})
    proceed = jm.create_prompt_and_wait(
        job_id,
        prompt=mk_prompt(
            type="yes_no_cancel",
            title="Grabando",
            message=(
                "Se abrirá el navegador.\n"
                "Para finalizar la grabación, cierra el navegador.\n"
                "¿Deseas continuar?"
            ),
        ),
    )
    if proceed is None:
        return None
    return proceed is True
