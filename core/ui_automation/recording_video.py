"""Helpers compartidos para grabación de video en flujos de recorder."""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional, Tuple

from webui.job_manager import Prompt


def ask_record_video(
    jm: Any,
    job_id: str,
    mk_prompt: Callable[..., Prompt],
    *,
    message: str = "¿Deseas grabar video de la pantalla?",
) -> bool:
    ans = jm.create_prompt_and_wait(
        job_id,
        prompt=mk_prompt(
            "yes_no",
            title="Grabación de Video",
            message=message,
        ),
    )
    return bool(ans)


def build_video_path(project_path: str, *, prefix: str = "video") -> str:
    file_name = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.avi"
    videos_dir = os.path.join(project_path, "grabaciones")
    os.makedirs(videos_dir, exist_ok=True)
    return os.path.join(videos_dir, file_name)


def start_window_video_recorder(
    video_path: str,
    hwnd: Optional[int],
    *,
    max_duration_sec: int = 600,
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Inicia ScreenRecorder acotado a la ventana (hwnd).
    Devuelve (recorder, error_message).
    """
    if not hwnd:
        return None, "No se encontró la ventana para grabar."

    try:
        from core.ui_automation.video_recorder import ScreenRecorder
    except Exception as exc:
        return None, f"No se pudo cargar el grabador de video: {exc}"

    recorder = ScreenRecorder(
        video_path,
        hwnd=hwnd,
        max_duration_sec=max_duration_sec,
    )
    if recorder.start():
        return recorder, None
    return None, "No se pudo iniciar la grabación de video."
