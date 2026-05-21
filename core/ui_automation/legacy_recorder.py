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
        projects = [
            d for d in os.listdir(projects_dir)
            if os.path.isdir(os.path.join(projects_dir, d))
        ]
        force_new = len(projects) == 0
        project_path: Optional[str] = None

        if force_new:
            ans = jm.create_prompt_and_wait(
                job_id,
                prompt=_mk_prompt("input_text", title="Nuevo Proyecto (Legacy)", message="Nombre del proyecto"),
            )
            if not ans:
                jm.cancel_job(job_id)
                return
            project_name = re.sub(r"[^\w\-_.]", "_", str(ans).strip())
            project_path = os.path.join(projects_dir, project_name)
        else:
            is_new = jm.create_prompt_and_wait(
                job_id,
                prompt=_mk_prompt("yes_no", title="Selección de Proyecto", message="¿Es un proyecto nuevo?"),
            )
            if is_new:
                ans = jm.create_prompt_and_wait(
                    job_id,
                    prompt=_mk_prompt("input_text", title="Nuevo Proyecto (Legacy)", message="Nombre del proyecto"),
                )
                if not ans:
                    jm.cancel_job(job_id)
                    return
                project_name = re.sub(r"[^\w\-_.]", "_", str(ans).strip())
                project_path = os.path.join(projects_dir, project_name)
            else:
                pick = jm.create_prompt_and_wait(
                    job_id,
                    prompt=_mk_prompt(
                        "pick_project",
                        title="Proyecto existente",
                        message="Selecciona el proyecto",
                        options=[{"value": p, "label": p} for p in projects],
                    ),
                )
                if not pick:
                    jm.cancel_job(job_id)
                    return
                project_path = os.path.join(projects_dir, str(pick))

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

        # 3. Lanzar ejecutable si se proporcionó
        proc: Optional[subprocess.Popen] = None
        if exe_path:
            jm.update_progress(job_id, {"stage": f"Lanzando {os.path.basename(exe_path)}…"})
            proc = _launch_exe(exe_path)
            if proc is None and not window_name:
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
            for _ in range(10):
                win = _find_window(window_name)
                if win:
                    break
                time.sleep(0.5)
            if not win:
                adapter.info(
                    "ELIA · Legacy",
                    f"Ventana '{window_name}' no encontrada. La grabación continuará con captura global de pantalla.",
                )

        # 5. Iniciar grabación con PyAutoGUI + pynput
        jm.update_progress(job_id, {"stage": "Grabando… presiona ESC o pulsa «Finalizar grabación» en ELIA", "recording": True})
        recorded_events: List[Dict[str, Any]] = []
        stop_recording = {"value": False}
        start_ts = time.time()

        try:
            from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard  # type: ignore

            def on_click(x: int, y: int, button: Any, pressed: bool) -> Optional[bool]:
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

        except ImportError:
            # Fallback: captura básica con PyAutoGUI (sin pynput)
            import pyautogui  # type: ignore
            jm.update_progress(job_id, {"stage": "Captura de pantalla básica (instala pynput para grabación completa)…"})
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

        # 6. Terminar proceso si lo lanzamos
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass

        # 7. Guardar resultado
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
                files=[("grabación", output_file)],
            ),
        )
        jm.add_event(job_id, "legacy_recorder", {"output_file": output_file, "events": len(recorded_events)})
        jm.mark_done(job_id)
