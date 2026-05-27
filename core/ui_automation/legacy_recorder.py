"""
Módulo de grabación legacy (aplicaciones de escritorio Windows).

Usa PyAutoGUI (ya instalado) para captura de interacciones.
Si pywinauto está disponible, lo usa para obtener metadatos de controles UI.

Building Blocks: este módulo solo se activa con licencia legacy_recording.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from webui.job_manager import JobManager, Prompt


def _mk_prompt(prompt_type: str, *, title: str, message: str, options=None) -> Prompt:
    return Prompt(
        prompt_id=str(uuid.uuid4()),
        type=prompt_type,
        title=title,
        message=message,
        options=options,
        actions=None,
    )


def _find_window(window_name: str) -> Optional[Any]:
    """Intenta encontrar una ventana por su título usando pywinauto o win32gui."""
    if sys.platform != "win32":
        return None
    try:
        from pywinauto import Desktop
        app = Desktop(backend="uia")
        wins = app.windows(title_re=f".*{re.escape(window_name)}.*")
        return wins[0] if wins else None
    except ImportError:
        pass
    try:
        import win32gui  # type: ignore
        hwnd = win32gui.FindWindow(None, window_name)
        return hwnd if hwnd else None
    except ImportError:
        pass
    return None


def _launch_exe(exe_path: str) -> Optional[subprocess.Popen]:
    """Lanza un ejecutable y devuelve el proceso."""
    if not exe_path or not os.path.isfile(exe_path):
        return None
    try:
        proc = subprocess.Popen([exe_path])
        time.sleep(2)  # esperar a que la app cargue
        return proc
    except Exception:
        return None


def _emit(jm: JobManager, job_id: str, event_type: str, **payload: Any) -> None:
    jm.add_event(job_id, event_type, payload or None)


class LegacyRecorder:
    """
    Grabador de interacciones para aplicaciones de escritorio Windows.

    Estrategia de grabación:
    - Usa PyAutoGUI para detectar clicks del mouse y teclas presionadas
    - Si pywinauto está disponible, enriquece con metadata de controles UI
    - Guarda el resultado como JSON compatible con el flujo de conversión a Behave
    """

    def __init__(self, adapter: Any, jm: JobManager, job_id: str) -> None:
        self._adapter = adapter
        self._jm = jm
        self._job_id = job_id

    def record(self, window_name: str, exe_path: str, projects_dir: str) -> None:
        jm = self._jm
        adapter = self._adapter
        job_id = self._job_id

        if sys.platform != "win32":
            jm.mark_error(
                job_id,
                message="Solo Windows",
                details="La grabación de aplicaciones legacy solo está disponible en Windows.",
            )
            return

        # 1. Seleccionar proyecto
        jm.update_progress(job_id, {"stage": "Seleccionar proyecto"})
        from webui.project_selection import prompt_project_path

        project_path = prompt_project_path(
            jm,
            job_id,
            projects_dir=projects_dir,
            new_project_title="Nuevo Proyecto (Legacy)",
            new_project_message="Nombre del proyecto",
            existing_title="Proyecto existente",
            existing_message="Selecciona el proyecto",
        )
        if not project_path:
            jm.cancel_job(job_id)
            return

        os.makedirs(project_path, exist_ok=True)
        os.makedirs(os.path.join(project_path, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "features"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "features", "steps"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "pages"), exist_ok=True)

        # 2. Nombre del archivo
        rec_name_ans = jm.create_prompt_and_wait(
            job_id,
            prompt=_mk_prompt(
                "input_text",
                title="Nombre de la grabación",
                message="Nombre del archivo de grabación (sin extensión)",
            ),
        )
        if not rec_name_ans:
            jm.cancel_job(job_id)
            return
        rec_name = re.sub(r"[^\w\-_.]", "_", str(rec_name_ans).strip()) or "legacy_recording"
        output_file = os.path.join(project_path, "scripts", f"{rec_name}.json")

        from core.ui_automation.recording_video import (
            ask_record_video,
            build_video_path,
            start_window_video_recorder,
        )

        grabar_video = ask_record_video(
            jm,
            job_id,
            _mk_prompt,
            message="¿Deseas grabar video de la ventana de la aplicación?",
        )
        video_path: Optional[str] = build_video_path(project_path) if grabar_video else None
        video_recorder = None

        # 3. Lanzar ejecutable si se proporcionó
        proc: Optional[subprocess.Popen] = None
        if exe_path:
            jm.update_progress(job_id, {"stage": f"Lanzando {os.path.basename(exe_path)}…"})
            _emit(jm, job_id, "exe_launch_started", exe_path=exe_path)
            proc = _launch_exe(exe_path)
            if proc is None and not window_name:
                _emit(jm, job_id, "exe_launch_failed", exe_path=exe_path)
                jm.mark_error(
                    job_id,
                    message="No se pudo lanzar el ejecutable",
                    details=f"Ruta: {exe_path}\nVerifica que el archivo existe y tienes permisos.",
                )
                return

        # 4. Verificar que la ventana existe
        jm.update_progress(job_id, {"stage": "Buscando ventana…"})
        win = None
        if window_name:
            _emit(jm, job_id, "window_search_started", window_name=window_name)
            for _ in range(10):
                win = _find_window(window_name)
                if win:
                    break
                time.sleep(0.5)
            if win:
                _emit(jm, job_id, "window_found", window_name=window_name)
            else:
                _emit(jm, job_id, "window_not_found", window_name=window_name)
                adapter.info(
                    "ELIA · Legacy",
                    f"Ventana '{window_name}' no encontrada. La grabación continuará con captura global de pantalla.",
                )

        if grabar_video and video_path:
            from core.ui_automation.window_capture import find_legacy_app_hwnd

            hwnd = find_legacy_app_hwnd(window_name) if window_name else None
            if hwnd is None and win is not None:
                from core.ui_automation.window_capture import resolve_hwnd

                hwnd = resolve_hwnd(win)
            video_recorder, video_err = start_window_video_recorder(
                video_path,
                hwnd,
                max_duration_sec=300,
            )
            if video_err:
                adapter.info("ELIA · Legacy", f"Video no iniciado: {video_err}")
                _emit(jm, job_id, "video_failed", error=video_err)
                video_path = None
                video_recorder = None
            else:
                jm.update_progress(job_id, {"stage": "Grabando video de la ventana…"})
                _emit(jm, job_id, "video_started", video_path=video_path)

        # 5. Iniciar grabación con PyAutoGUI + pynput
        jm.update_progress(job_id, {"stage": "Grabando… presiona ESC o pulsa «Finalizar grabación» en ELIA", "recording": True})
        recorded_events: List[Dict[str, Any]] = []
        stop_recording = {"value": False}
        start_ts = time.time()
        last_event_emit = 0

        try:
            from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard  # type: ignore

            _emit(jm, job_id, "hook_started")
            _emit(jm, job_id, "recording_started")

            def on_click(x: int, y: int, button: Any, pressed: bool) -> Optional[bool]:
                nonlocal last_event_emit
                if not pressed:
                    return None
                event: Dict[str, Any] = {
                    "ts": round(time.time() - start_ts, 3),
                    "type": "click",
                    "x": x,
                    "y": y,
                    "button": str(button),
                }
                # Enriquecer con metadata de control UI si pywinauto disponible
                try:
                    from pywinauto import Desktop  # type: ignore
                    ctrl = Desktop(backend="uia").from_point(x, y)
                    if ctrl:
                        event["control_name"] = ctrl.window_text()
                        event["control_type"] = ctrl.element_info.control_type
                except Exception:
                    pass
                recorded_events.append(event)
                count = len(recorded_events)
                if count == 1 or count - last_event_emit >= 5:
                    _emit(jm, job_id, "event_captured", count=count)
                    last_event_emit = count
                return None

            def on_key_press(key: Any) -> Optional[bool]:
                try:
                    key_str = key.char
                except AttributeError:
                    key_str = str(key)
                if key_str == "Key.esc":
                    stop_recording["value"] = True
                    return False
                recorded_events.append({
                    "ts": round(time.time() - start_ts, 3),
                    "type": "key",
                    "key": key_str,
                })
                count = len(recorded_events)
                if count == 1 or count - last_event_emit >= 5:
                    _emit(jm, job_id, "event_captured", count=count)
                    last_event_emit = count
                return None

            mouse_listener = pynput_mouse.Listener(on_click=on_click)
            key_listener = pynput_keyboard.Listener(on_press=on_key_press)
            mouse_listener.start()
            key_listener.start()

            max_duration = 300
            while time.time() - start_ts < max_duration and not stop_recording["value"]:
                if jm.should_stop_recording(job_id):
                    stop_recording["value"] = True
                    break
                time.sleep(0.5)
                jm.update_progress(job_id, {"events_captured": len(recorded_events)})

            mouse_listener.stop()
            key_listener.stop()
            _emit(jm, job_id, "recording_stopped", events=len(recorded_events))

        except ImportError:
            # Fallback: captura básica con PyAutoGUI (sin pynput)
            import pyautogui  # type: ignore
            _emit(jm, job_id, "hook_failed", reason="pynput_not_installed")
            jm.update_progress(job_id, {"stage": "Captura de pantalla básica (instala pynput para grabación completa)…"})
            _emit(jm, job_id, "recording_started")
            max_duration = 60
            interval = 2.0
            elapsed = 0.0
            while elapsed < max_duration:
                if jm.should_stop_recording(job_id):
                    break
                time.sleep(interval)
                elapsed += interval
                pos = pyautogui.position()
                recorded_events.append({
                    "ts": round(elapsed, 1),
                    "type": "position",
                    "x": pos.x,
                    "y": pos.y,
                })
            _emit(jm, job_id, "recording_stopped", events=len(recorded_events))

        # 6. Terminar proceso si lo lanzamos
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass

        if video_recorder:
            try:
                video_recorder.stop()
                time.sleep(0.5)
            except Exception:
                pass

        api_traffic_path: Optional[str] = None
        from core.modules_config import is_module_enabled

        if is_module_enabled("api_testing"):
            url_ans = jm.create_prompt_and_wait(
                job_id,
                prompt=_mk_prompt(
                    "input_text",
                    title="Captura API (opcional)",
                    message=(
                        "URL del componente web (WebView2/híbrido) para capturar tráfico API. "
                        "Deja vacío para omitir."
                    ),
                ),
            )
            hybrid_url = str(url_ans or "").strip()
            if hybrid_url.startswith("http"):
                jm.update_progress(job_id, {"stage": "Capturando tráfico API…"})
                try:
                    from core.api_automation.legacy_traffic_capture import (
                        capture_from_url_via_puppeteer,
                        save_legacy_capture,
                    )
                    from core.test_runner.behave_support import elia_base_dir

                    elia_root = elia_base_dir()
                    probe_path = os.path.join(
                        project_path,
                        "scripts",
                        f"{rec_name}_api_probe_traffic.json",
                    )
                    if capture_from_url_via_puppeteer(
                        hybrid_url,
                        probe_path,
                        cwd=elia_root,
                    ):
                        api_project = os.path.basename(project_path)
                        api_traffic_path = save_legacy_capture(api_project, rec_name, probe_path)
                        _emit(jm, job_id, "api_traffic_saved", path=api_traffic_path)
                    else:
                        _emit(jm, job_id, "api_traffic_failed", error="Puppeteer no generó captura")
                except Exception as exc:
                    _emit(jm, job_id, "api_traffic_failed", error=str(exc))

        # 7. Guardar resultado
        generated_files = [("grabación", output_file)]
        if video_path and os.path.isfile(video_path) and os.path.getsize(video_path) > 0:
            generated_files.append(("video", video_path))
        if api_traffic_path and os.path.isfile(api_traffic_path):
            generated_files.append(("tráfico API", api_traffic_path))

        result: Dict[str, Any] = {
            "platform": "legacy",
            "window_name": window_name,
            "exe_path": exe_path,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "events": recorded_events,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        from webui.conversion_result import conversion_result

        adapter.info(
            "Grabación Legacy",
            f"Grabación completada.\n\nEventos capturados: {len(recorded_events)}",
            result=conversion_result(
                project_dir=project_path,
                files=generated_files,
            ),
        )
        progress: Dict[str, Any] = {"output_file": output_file, "events": len(recorded_events)}
        if video_path and os.path.isfile(video_path):
            progress["video_path"] = video_path
        jm.update_progress(job_id, progress)
        jm.add_event(job_id, "legacy_recorder", progress)
        jm.mark_done(job_id)
