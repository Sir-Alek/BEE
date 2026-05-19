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

    def record(self, apk_path: str, device_id: str, projects_dir: str) -> None:
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
            from appium import webdriver as appium_webdriver
            from appium.options import AppiumOptions
        except ImportError:
            jm.mark_error(
                job_id,
                message="Appium-Python-Client no instalado",
                details=(
                    "Instala el cliente Python de Appium:\n"
                    "pip install Appium-Python-Client\n\n"
                    "Luego reinicia ELIA."
                ),
            )
            return

        capabilities: Dict[str, Any] = {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:deviceName": device_id or "Android",
            "appium:newCommandTimeout": 300,
        }
        if apk_path and os.path.isfile(apk_path):
            capabilities["appium:app"] = apk_path

        try:
            options = AppiumOptions().load_capabilities(capabilities)
            driver = appium_webdriver.Remote("http://localhost:4723", options=options)
        except Exception as e:
            jm.mark_error(
                job_id,
                message="No se pudo iniciar la sesión Appium",
                details=(
                    f"Error: {e}\n\n"
                    "Verifica que el dispositivo/emulador esté conectado y el APK sea válido."
                ),
            )
            return

        jm.update_progress(job_id, {"stage": "Grabando… cierra la app para finalizar"})

        # 5. Captura de interacciones
        # En la versión actual grabamos la jerarquía de pantalla periódicamente.
        # Una implementación completa requeriría un event listener de Appium o
        # un servicio de accesibilidad en el dispositivo.
        recorded_events = []
        try:
            prev_source = ""
            start_ts = time.time()
            max_duration = 300  # 5 minutos máximo

            while time.time() - start_ts < max_duration:
                time.sleep(1.5)
                try:
                    source = driver.page_source
                    if source != prev_source:
                        recorded_events.append({
                            "ts": time.time() - start_ts,
                            "type": "page_source",
                            "source": source[:4000],  # limitar tamaño
                        })
                        prev_source = source
                except Exception:
                    break
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        # 6. Guardar resultado
        result: Dict[str, Any] = {
            "platform": "mobile",
            "apk_path": apk_path,
            "device_id": device_id,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "events": recorded_events,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        adapter.info(
            "Grabación Móvil",
            f"Grabación completada.\n\nArchivo: {output_file}\nEventos capturados: {len(recorded_events)}",
        )
        jm.add_event(job_id, "mobile_recorder", {"output_file": output_file, "events": len(recorded_events)})
        jm.mark_done(job_id)
