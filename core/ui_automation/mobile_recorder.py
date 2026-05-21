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
from typing import Any, Dict, Optional

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


class MobileRecorder:
    """
    Grabador de interacciones para aplicaciones móviles Android/iOS vía Appium.

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

        # 1. Validar Appium
        jm.update_progress(job_id, {"stage": "Verificando Appium Server…"})
        if not _check_appium_server():
            jm.mark_error(
                job_id,
                message="Appium Server no detectado",
                details=(
                    "No se pudo conectar a Appium en localhost:4723.\n\n"
                    "Pasos para solucionarlo:\n"
                    "1. Instala Appium: npm install -g appium\n"
                    "2. Instala el driver Android: appium driver install uiautomator2\n"
                    "3. Inicia el servidor: appium\n"
                    "4. Verifica que el dispositivo/emulador esté conectado: adb devices"
                ),
            )
            return

        # 2. Seleccionar proyecto
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
                prompt=_mk_prompt("input_text", title="Nuevo Proyecto (Móvil)", message="Nombre del proyecto"),
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
                    prompt=_mk_prompt("input_text", title="Nuevo Proyecto (Móvil)", message="Nombre del proyecto"),
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

        app_err = _apply_android_app_capabilities(
            capabilities,
            apk_path=apk_path,
            app_package=app_package,
            app_activity=app_activity,
            device_id=device_id,
        )
        if app_err:
            jm.mark_error(job_id, message="Configuración de app móvil incompleta", details=app_err)
            return

        try:
            options = AppiumOptions().load_capabilities(capabilities)
            driver = appium_webdriver.Remote("http://localhost:4723", options=options)
        except Exception as e:
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

        jm.update_progress(
            job_id,
            {
                "stage": "Grabando… interactúa en el móvil y pulsa «Finalizar grabación» en ELIA",
                "events_captured": 0,
                "recording": True,
            },
        )

        # 5. Captura de interacciones
        recorded_events = []
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
                                break
                        else:
                            away_checks = 0

                    source = driver.page_source
                    if source != prev_source:
                        recorded_events.append({
                            "ts": round(time.time() - start_ts, 3),
                            "type": "page_source",
                            "source": source[:4000],
                        })
                        prev_source = source
                        jm.update_progress(
                            job_id,
                            {
                                "events_captured": len(recorded_events),
                                "elapsed_s": int(time.time() - start_ts),
                            },
                        )
                except Exception:
                    break
        finally:
            try:
                driver.quit()
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

        adapter.info(
            "Grabación Móvil",
            f"Grabación completada.\n\nEventos capturados: {len(recorded_events)}",
            result=conversion_result(
                project_dir=project_path,
                files=[("grabación", output_file)],
            ),
        )
        jm.add_event(job_id, "mobile_recorder", {"output_file": output_file, "events": len(recorded_events)})
        jm.mark_done(job_id)
