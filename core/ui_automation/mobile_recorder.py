"""
Módulo de grabación móvil (Appium).

Requiere:
  - Appium Server >= 2.x corriendo en localhost:4723
  - Android SDK con adb configurado
  - Appium-Python-Client instalado (pip install Appium-Python-Client)

Building Blocks: este módulo solo se activa con licencia mobile_recording.
"""
from __future__ import annotations

import json
import os
import re
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


def _check_appium_server(host: str = "localhost", port: int = 4723) -> bool:
    """Verifica que el servidor Appium esté accesible."""
    import http.client
    try:
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request("GET", "/status")
        resp = conn.getresponse()
        return resp.status == 200
    except Exception:
        return False


def _import_appium_client() -> tuple[Any, Any]:
    """
    Importa webdriver y AppiumOptions con rutas compatibles entre versiones del cliente.

    Raises:
        RuntimeError: (message, details) empaquetados en args para mark_error del job.
    """
    import importlib
    import sys

    frozen = getattr(sys, "frozen", False)

    try:
        from appium import webdriver as appium_webdriver
    except ImportError as exc:
        if frozen:
            raise RuntimeError(
                "Appium-Python-Client no incluido",
                "Reinstala o actualiza ELIA a la última versión.\n\n"
                f"Detalle técnico: {exc}",
            ) from exc
        raise RuntimeError(
            "Appium-Python-Client no instalado",
            "Instala el cliente con:\n"
            "pip install Appium-Python-Client\n\n"
            "Luego reinicia ELIA.\n\n"
            f"Detalle técnico: {exc}",
        ) from exc

    appium_options_cls = None
    last_exc: Optional[BaseException] = None
    for mod_path in ("appium.options.common.base", "appium.options"):
        try:
            mod = importlib.import_module(mod_path)
            appium_options_cls = getattr(mod, "AppiumOptions")
            break
        except (ImportError, AttributeError) as exc:
            last_exc = exc

    if appium_options_cls is None:
        if frozen:
            raise RuntimeError(
                "Cliente Appium incompatible",
                "Reinstala o actualiza ELIA a la última versión.\n\n"
                f"Detalle técnico: {last_exc}",
            ) from last_exc
        raise RuntimeError(
            "Cliente Appium incompatible",
            "Reinstala la versión indicada en requirements.txt:\n"
            "pip install -r requirements.txt\n\n"
            "Luego reinicia ELIA.\n\n"
            f"Detalle técnico: {last_exc}",
        ) from last_exc

    return appium_webdriver, appium_options_cls


def _sleep_interruptible(seconds: float, jm: JobManager, job_id: str, *, step: float = 0.25) -> bool:
    """Duerme en tramos cortos. Devuelve True si hay que detener la grabación."""
    end = time.time() + seconds
    while time.time() < end:
        if jm.should_stop_recording(job_id):
            return True
        time.sleep(min(step, max(0.0, end - time.time())))
    return jm.should_stop_recording(job_id)


def _target_package_from_capabilities(
    capabilities: Dict[str, Any],
    *,
    app_package: str,
) -> str:
    pkg = (app_package or "").strip()
    if pkg:
        return pkg
    cap_pkg = capabilities.get("appium:appPackage") or capabilities.get("appPackage")
    return str(cap_pkg or "").strip()


def _resolve_main_activity(device_id: str, package: str) -> Optional[str]:
    """Obtiene la actividad launcher vía adb (app ya instalada)."""
    import subprocess

    package = (package or "").strip()
    if not package:
        return None
    adb_cmd = ["adb"]
    dev = (device_id or "").strip()
    if dev:
        adb_cmd.extend(["-s", dev])
    adb_cmd.extend(["shell", "cmd", "package", "resolve-activity", "--brief", package])
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(
            adb_cmd,
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=flags,
        )
        if proc.returncode != 0:
            return None
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line or line.lower() == "priority=0":
                continue
            if "/" in line:
                act = line.split("/", 1)[1].strip()
                if act:
                    return act
    except Exception:
        return None
    return None


def _apply_android_app_capabilities(
    capabilities: Dict[str, Any],
    *,
    apk_path: str,
    app_package: str,
    app_activity: str,
    device_id: str,
) -> Optional[str]:
    """
    Configura appium:app o appium:appPackage/appActivity.
    Devuelve mensaje de error si falta información; None si OK.
    """
    apk = (apk_path or "").strip()
    if apk:
        if not os.path.isfile(apk):
            return (
                f"No se encontró el APK en el PC:\n{apk}\n\n"
                "Si la app ya está en el móvil, deja la ruta vacía e indica el paquete Android "
                "(ej. com.empresa.app)."
            )
        capabilities["appium:app"] = apk
        return None

    package = (app_package or "").strip()
    if not package:
        return (
            "Indica la ruta del APK en este PC o el paquete Android de la app instalada "
            "(ej. com.empresa.app). Obtén el paquete con: adb shell pm list packages"
        )

    activity = (app_activity or "").strip()
    if not activity:
        activity = _resolve_main_activity(device_id, package) or ""
    if activity and not activity.startswith("."):
        if "/" in activity:
            activity = activity.split("/", 1)[1]

    capabilities["appium:appPackage"] = package
    if activity:
        capabilities["appium:appActivity"] = activity
    else:
        capabilities["appium:appWaitActivity"] = "*"
    return None


def _emit(jm: JobManager, job_id: str, event_type: str, **payload: Any) -> None:
    jm.add_event(job_id, event_type, payload or None)


class MobileRecorder:
    """
    Grabador de interacciones para aplicaciones Android vía Appium (iOS no soportado).

    Flujo:
      1. Verificar que Appium Server está corriendo
      2. Seleccionar/crear proyecto
      3. Iniciar sesión Appium y capturar eventos de interacción
      4. Guardar el resultado como JSON en el directorio del proyecto
    """

    def __init__(self, adapter: Any, jm: JobManager, job_id: str) -> None:
        self._adapter = adapter
        self._jm = jm
        self._job_id = job_id

    def record(
        self,
        apk_path: str,
        device_id: str,
        projects_dir: str,
        *,
        app_package: str = "",
        app_activity: str = "",
    ) -> None:
        jm = self._jm
        adapter = self._adapter
        job_id = self._job_id

        # 1. Validar entorno Android + Appium
        jm.update_progress(job_id, {"stage": "Verificando entorno Android…"})
        from core.ui_automation.mobile_android import assert_device_online

        device_err = assert_device_online(device_id)
        if device_err:
            msg, details = device_err
            _emit(jm, job_id, "device_check_failed", message=msg)
            jm.mark_error(job_id, message=msg, details=details)
            return
        _emit(jm, job_id, "device_check_ok", device_id=device_id)

        jm.update_progress(job_id, {"stage": "Verificando Appium Server…"})
        from core.ui_automation.mobile_android import ensure_appium_running

        appium_res = ensure_appium_running(auto_start=True)
        if not appium_res.get("ok"):
            tool_hint = ""
            if not appium_res.get("installed", True):
                tool_hint = (
                    "\n\nInstala Appium:\n"
                    "1. npm install -g appium\n"
                    "2. appium driver install uiautomator2"
                )
            _emit(jm, job_id, "appium_check_failed", message=appium_res.get("message"))
            jm.mark_error(
                job_id,
                message="Appium Server no disponible",
                details=(appium_res.get("message") or "No responde en localhost:4723.") + tool_hint,
            )
            return
        _emit(jm, job_id, "appium_check_ok")

        if appium_res.get("managed_by_elia"):
            jm.update_progress(job_id, {"stage": "Appium iniciado por ELIA…"})
            _emit(jm, job_id, "appium_auto_started")

        # 2. Seleccionar proyecto
        jm.update_progress(job_id, {"stage": "Seleccionar proyecto"})
        from webui.project_selection import prompt_project_path

        project_path = prompt_project_path(
            jm,
            job_id,
            projects_dir=projects_dir,
            new_project_title="Nuevo Proyecto (Móvil)",
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

        # 3. Nombre del archivo de grabación
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
        rec_name = re.sub(r"[^\w\-_.]", "_", str(rec_name_ans).strip()) or "mobile_recording"
        output_file = os.path.join(project_path, "scripts", f"{rec_name}.json")

        from core.ui_automation.window_capture import is_emulator_device_id
        from core.ui_automation.recording_video import (
            ask_record_video,
            build_video_path,
            start_window_video_recorder,
        )

        grabar_video = False
        video_path: Optional[str] = None
        video_recorder = None
        if is_emulator_device_id(device_id):
            grabar_video = ask_record_video(
                jm,
                job_id,
                _mk_prompt,
                message="¿Deseas grabar video del emulador Android?",
            )
            if grabar_video:
                video_path = build_video_path(project_path, prefix="video_emulador")

        capture_api = False
        from core.modules_config import is_module_enabled

        if is_module_enabled("api_testing"):
            cap_ans = jm.create_prompt_and_wait(
                job_id,
                prompt=_mk_prompt(
                    "yes_no",
                    title="Captura API",
                    message="¿Capturar tráfico API (WebView/Chrome) durante la grabación móvil?",
                ),
            )
            capture_api = cap_ans is True if cap_ans is not None else False

        resolved_package = (app_package or "").strip()
        resolved_activity = (app_activity or "").strip()
        if not (apk_path or "").strip() and not resolved_package:
            jm.update_progress(job_id, {"stage": "Detectando app en primer plano…"})
            from core.ui_automation.mobile_android import detect_foreground_package

            det = detect_foreground_package(device_id)
            if det.get("ok") and det.get("package"):
                resolved_package = str(det["package"])
                if not resolved_activity and det.get("activity"):
                    resolved_activity = str(det["activity"])
                _emit(
                    jm,
                    job_id,
                    "foreground_app_detected",
                    package=resolved_package,
                    activity=resolved_activity,
                )
            else:
                jm.mark_error(
                    job_id,
                    message="No se detectó la app en el móvil",
                    details=(
                        det.get("error")
                        or "Indica el paquete Android, la ruta del APK, o abre la app en primer plano."
                    ),
                )
                return

        # 4. Iniciar grabación con Appium
        jm.update_progress(job_id, {"stage": "Iniciando sesión Appium…"})
        try:
            appium_webdriver, AppiumOptions = _import_appium_client()
        except RuntimeError as exc:
            jm.mark_error(job_id, message=str(exc.args[0]), details=str(exc.args[1]))
            return

        capabilities: Dict[str, Any] = {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:deviceName": device_id or "Android",
            "appium:newCommandTimeout": 300,
        }
        if device_id.strip():
            capabilities["appium:udid"] = device_id.strip()
        if capture_api:
            capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

        app_err = _apply_android_app_capabilities(
            capabilities,
            apk_path=apk_path,
            app_package=resolved_package,
            app_activity=resolved_activity,
            device_id=device_id,
        )
        if app_err:
            jm.mark_error(job_id, message="Configuración de app móvil incompleta", details=app_err)
            return

        try:
            options = AppiumOptions().load_capabilities(capabilities)
            driver = appium_webdriver.Remote("http://localhost:4723", options=options)
            _emit(jm, job_id, "session_started", device_id=device_id)
        except Exception as e:
            _emit(jm, job_id, "session_failed", error=str(e))
            jm.mark_error(
                job_id,
                message="No se pudo iniciar la sesión Appium",
                details=(
                    f"Error: {e}\n\n"
                    "Verifica adb devices, Appium en localhost:4723, y que el paquete/actividad "
                    "o la ruta del APK sean correctos."
                ),
            )
            return

        if grabar_video and video_path:
            from core.ui_automation.window_capture import find_android_emulator_hwnd

            hwnd = find_android_emulator_hwnd(device_id)
            video_recorder, video_err = start_window_video_recorder(
                video_path,
                hwnd,
                max_duration_sec=300,
            )
            if video_err:
                adapter.info("ELIA · Móvil", f"Video no iniciado: {video_err}")
                video_path = None
                video_recorder = None
            else:
                jm.update_progress(job_id, {"stage": "Grabando video del emulador…"})
                _emit(jm, job_id, "video_started", video_path=video_path)

        jm.update_progress(
            job_id,
            {
                "stage": "Grabando… interactúa en el móvil y pulsa «Finalizar grabación» en ELIA",
                "events_captured": 0,
                "recording": True,
            },
        )
        _emit(jm, job_id, "recording_started")

        # 5. Captura de interacciones
        recorded_events = []
        api_traffic_path: Optional[str] = None
        target_package = _target_package_from_capabilities(
            capabilities,
            app_package=app_package,
        )
        try:
            prev_source = ""
            start_ts = time.time()
            max_duration = 300
            away_checks = 0

            while time.time() - start_ts < max_duration:
                if jm.should_stop_recording(job_id):
                    break

                if _sleep_interruptible(1.5, jm, job_id):
                    break

                try:
                    if target_package:
                        current_pkg = driver.current_package
                        if current_pkg and current_pkg != target_package:
                            away_checks += 1
                            if away_checks >= 2:
                                _emit(
                                    jm,
                                    job_id,
                                    "app_left_foreground",
                                    expected=target_package,
                                    current=current_pkg,
                                )
                                break
                        else:
                            away_checks = 0

                    source = driver.page_source
                    if source != prev_source:
                        interactables_index: List[Dict[str, Any]] = []
                        try:
                            from core.ui_automation.mobile_dom_parser import interactables_index_from_page_source

                            interactables_index = interactables_index_from_page_source(source, max_elements=80)
                        except Exception:
                            interactables_index = []
                        recorded_events.append({
                            "ts": round(time.time() - start_ts, 3),
                            "type": "page_source",
                            "source": source[:4000],
                            "interactables_index": interactables_index,
                        })
                        prev_source = source
                        jm.update_progress(
                            job_id,
                            {
                                "events_captured": len(recorded_events),
                                "elapsed_s": int(time.time() - start_ts),
                            },
                        )
                        _emit(jm, job_id, "screen_captured", count=len(recorded_events))
                except Exception:
                    break
            if capture_api:
                try:
                    from core.api_automation.mobile_traffic_capture import (
                        capture_from_appium_driver,
                        save_mobile_capture,
                    )

                    cap_dict = capture_from_appium_driver(
                        driver,
                        source_url=target_package or resolved_package or "",
                    )
                    if cap_dict:
                        api_project = os.path.basename(project_path)
                        api_traffic_path = save_mobile_capture(api_project, rec_name, cap_dict)
                        _emit(jm, job_id, "api_traffic_saved", path=api_traffic_path)
                except Exception as exc:
                    _emit(jm, job_id, "api_traffic_failed", error=str(exc))
            _emit(jm, job_id, "recording_stopped", events=len(recorded_events))
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        if video_recorder:
            try:
                video_recorder.stop()
                time.sleep(0.5)
            except Exception:
                pass

        # 6. Guardar resultado
        jm.update_progress(job_id, {"stage": "Guardando grabación…", "recording": False})
        result: Dict[str, Any] = {
            "platform": "mobile",
            "apk_path": apk_path,
            "app_package": (app_package or "").strip(),
            "app_activity": (app_activity or "").strip(),
            "device_id": device_id,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "events": recorded_events,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        from webui.conversion_result import conversion_result

        generated_files = [("grabación", output_file)]
        if video_path and os.path.isfile(video_path) and os.path.getsize(video_path) > 0:
            generated_files.append(("video", video_path))
        if api_traffic_path and os.path.isfile(api_traffic_path):
            generated_files.append(("tráfico API", api_traffic_path))

        adapter.info(
            "Grabación Móvil",
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
        jm.add_event(job_id, "mobile_recorder", progress)
        jm.mark_done(job_id)
