from __future__ import annotations

import os
import threading
import traceback
import sys
from typing import Any, Dict, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from core.puppeteer_script_converter import PuppeteerToBehaveConverter
from core.step_by_step_converter import PuppeteerToStepByStepConverter
from webui.job_manager import JobManager, Prompt
from webui.webui_adapter import WebUIAdapter


class ConvertRequest(BaseModel):
    mode: Literal[
        "puppeteer_to_behave",
        "puppeteer_to_step_by_step",
        "demo",
        "puppeteer_recorder",
    ]
    url: Optional[str] = None
    use_ai: bool = False


class PromptResponseRequest(BaseModel):
    answer: Any = None


def _repo_root() -> str:
    # webui/fastapi_app.py -> webui/ -> repo root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _require_localhost(request: Request) -> None:
    # Hardening: prevent exposing UI to other hosts.
    host = (request.client.host if request.client else "").strip()
    if host not in ("127.0.0.1", "::1", "testclient", "localhost"):
        raise HTTPException(status_code=403, detail="Forbidden: localhost only")


def create_app(*, job_manager: Optional[JobManager] = None) -> FastAPI:
    app = FastAPI(title="BEE Web UI (local)")
    jm = job_manager or JobManager()
    base_dir = _repo_root()
    frontend_dist = os.path.join(base_dir, "frontend", "dist")
    logo_path = os.path.join(base_dir, "resources", "logo_bee_png_transparente.png")
    exit_flag = {"value": False}

    @app.post("/api/app/exit")
    def app_exit(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        """
        Request the local app to exit (used when the home tab is closed).
        main.py polls /api/app/should-exit and stops Uvicorn.
        """
        exit_flag["value"] = True
        return {"ok": True}

    @app.get("/api/app/should-exit")
    def app_should_exit(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        return {"exit": bool(exit_flag["value"])}

    @app.get("/api/ai/status")
    def ai_status(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        try:
            from core import gemma_inference

            return gemma_inference.get_ai_runtime_status()
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/jobs/convert")
    def create_job(req: ConvertRequest, _: None = Depends(_require_localhost)) -> Dict[str, str]:
        job_id = jm.create_job(mode=req.mode)

        def worker() -> None:
            adapter = WebUIAdapter(job_manager=jm, job_id=job_id)
            try:
                if req.mode == "demo":
                    # Simple smoke behavior: one prompt then done.
                    choice = adapter.pick_project(["Proyecto A", "Proyecto B"])
                    jm.add_event(job_id, "demo_choice", {"choice": choice})
                    jm.mark_done(job_id)
                    return

                if req.mode == "puppeteer_to_behave":
                    converter = PuppeteerToBehaveConverter(base_dir, adapter, use_ai=req.use_ai)
                    converter.convert_script()
                    jm.mark_done(job_id)
                    return

                if req.mode == "puppeteer_to_step_by_step":
                    converter = PuppeteerToStepByStepConverter(base_dir, adapter)
                    converter.convert_script()
                    jm.mark_done(job_id)
                    return

                if req.mode == "puppeteer_recorder":
                    if not req.url:
                        jm.mark_error(job_id, message="Missing url", details="url is required for puppeteer_recorder")
                        return

                    projects_dir = os.path.join(base_dir, "behave", "proyectos")
                    os.makedirs(projects_dir, exist_ok=True)

                    import re
                    import time
                    import uuid

                    def mk_prompt(prompt_type: str, *, title: str, message: str, options=None, actions=None) -> Prompt:
                        prompt_id = str(uuid.uuid4())
                        return Prompt(
                            prompt_id=prompt_id,
                            type=prompt_type,
                            title=title,
                            message=message,
                            options=options,
                            actions=actions,
                        )

                    def sanitize_filename(file_name: str) -> str:
                        # Match Tk behavior from main.py
                        file_name = re.sub(r"[^\w\-_.]", "_", file_name)
                        file_name = re.sub(r"_{2,}", "_", file_name)
                        if not file_name.endswith(".js"):
                            file_name += ".js"
                        return file_name

                    def is_frozen() -> bool:
                        return getattr(sys, "frozen", False)

                    # --- Seleccionar/crear proyecto (prompts web)
                    projects = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
                    force_new = len(projects) == 0

                    project_path: Optional[str] = None

                    jm.update_progress(job_id, {"stage": "Seleccionar proyecto"})

                    if force_new:
                        ans = jm.create_prompt_and_wait(
                            job_id,
                            prompt=mk_prompt(
                                "input_text",
                                title="Nuevo Proyecto",
                                message="Nombre del proyecto (ej: MiProyecto)",
                            ),
                        )
                        if ans is None:
                            jm.cancel_job(job_id)
                            return
                        project_name = str(ans).strip()
                        if not project_name:
                            jm.cancel_job(job_id)
                            return
                        project_path = os.path.join(projects_dir, project_name)
                        os.makedirs(project_path, exist_ok=True)
                        os.makedirs(os.path.join(project_path, "scripts"), exist_ok=True)
                        os.makedirs(os.path.join(project_path, "features"), exist_ok=True)
                        os.makedirs(os.path.join(project_path, "features", "steps"), exist_ok=True)
                        os.makedirs(os.path.join(project_path, "pages"), exist_ok=True)
                        os.makedirs(os.path.join(project_path, "resources", "data"), exist_ok=True)
                    else:
                        is_new = jm.create_prompt_and_wait(
                            job_id,
                            prompt=mk_prompt(
                                "yes_no",
                                title="Selección de Proyecto",
                                message="¿Es un proyecto nuevo?",
                            ),
                        )
                        if is_new:
                            ans = jm.create_prompt_and_wait(
                                job_id,
                                prompt=mk_prompt(
                                    "input_text",
                                    title="Nuevo Proyecto",
                                    message="Nombre del proyecto (ej: MiProyecto)",
                                ),
                            )
                            if ans is None:
                                jm.cancel_job(job_id)
                                return
                            project_name = str(ans).strip()
                            if not project_name:
                                jm.cancel_job(job_id)
                                return
                            project_path = os.path.join(projects_dir, project_name)
                            os.makedirs(project_path, exist_ok=True)
                            os.makedirs(os.path.join(project_path, "scripts"), exist_ok=True)
                            os.makedirs(os.path.join(project_path, "features"), exist_ok=True)
                            os.makedirs(os.path.join(project_path, "features", "steps"), exist_ok=True)
                            os.makedirs(os.path.join(project_path, "pages"), exist_ok=True)
                            os.makedirs(os.path.join(project_path, "resources", "data"), exist_ok=True)
                        else:
                            chosen = jm.create_prompt_and_wait(
                                job_id,
                                prompt=mk_prompt(
                                    "pick_project",
                                    title="Seleccionar Proyecto Existente",
                                    message="Selecciona un proyecto:",
                                    options=[{"value": p, "label": p} for p in projects],
                                ),
                            )
                            if chosen is None:
                                jm.cancel_job(job_id)
                                return
                            project_name = str(chosen)
                            project_path = os.path.join(projects_dir, project_name)

                    if not project_path:
                        jm.cancel_job(job_id)
                        return

                    # --- Nombre del archivo de grabación
                    jm.update_progress(job_id, {"stage": "Nombre de grabación"})
                    default_hint = "grabacion_" + time.strftime("%Y%m%d_%H%M%S")
                    ans_file = jm.create_prompt_and_wait(
                        job_id,
                        prompt=mk_prompt(
                            "input_text",
                            title="Nombre del Archivo de Grabación",
                            message=f"Ingresa el nombre (sugerido: {default_hint})",
                        ),
                    )
                    if ans_file is None:
                        jm.cancel_job(job_id)
                        return
                    file_name = str(ans_file).strip()
                    if not file_name:
                        jm.cancel_job(job_id)
                        return
                    file_name = sanitize_filename(file_name)

                    scripts_dir = os.path.join(project_path, "scripts")
                    os.makedirs(scripts_dir, exist_ok=True)
                    output_file = os.path.join(scripts_dir, file_name)

                    # --- Confirmación grabando
                    jm.update_progress(job_id, {"stage": "Confirmar grabación"})
                    proceed = jm.create_prompt_and_wait(
                        job_id,
                        prompt=mk_prompt(
                            "yes_no_cancel",
                            title="Grabando",
                            message="Se abrirá el navegador.\nPara finalizar la grabación, cierra el navegador.\n¿Deseas continuar?",
                        ),
                    )
                    if proceed is not True:
                        jm.cancel_job(job_id)
                        return

                    # --- Video opcional
                    grabar_video = jm.create_prompt_and_wait(
                        job_id,
                        prompt=mk_prompt(
                            "yes_no",
                            title="Grabación de Video",
                            message="¿Deseas grabar video de la pantalla?",
                        ),
                    )

                    recorder_obj = None
                    video_path: Optional[str] = None

                    if grabar_video:
                        jm.update_progress(job_id, {"stage": "Grabando video"})
                        # Lazy import to avoid requiring video-capture deps when not used.
                        from core.video_recorder import ScreenRecorder

                        file_name_vid = "video_" + time.strftime("%Y%m%d_%H%M%S") + ".avi"
                        videos_dir = os.path.join(project_path, "grabaciones")
                        os.makedirs(videos_dir, exist_ok=True)
                        video_path = os.path.join(videos_dir, file_name_vid)
                        try:
                            recorder_obj = ScreenRecorder(video_path)
                            if not recorder_obj.start():
                                recorder_obj = None
                        except Exception:
                            recorder_obj = None

                    jm.update_progress(job_id, {"stage": "Preparando runtime de grabación"})

                    # --- Ejecutar recorder.js
                    if is_frozen():
                        from core.node_wrapper import node_wrapper
                        try:
                            if getattr(node_wrapper, "was_runtime_prepared_now", False):
                                jm.update_progress(job_id, {"stage": "Preparando runtime de grabación (primera vez)"})
                        except Exception:
                            pass

                        result = node_wrapper.run_obfuscated_js(
                            "recorder.js",
                            [output_file, req.url],
                            subprocess_timeout=None,
                            focus_automation_browser=True,
                        )
                    else:
                        from core.recorder_focus import run_subprocess_with_automation_focus

                        jm.update_progress(job_id, {"stage": "Ejecutando Puppeteer recorder"})
                        recorder_js_path = os.path.join(base_dir, "core", "recorder.js")
                        result = run_subprocess_with_automation_focus(
                            ["node", recorder_js_path, output_file, req.url],
                            cwd=base_dir,
                            timeout=None,
                        )

                    if result.returncode != 0:
                        error = result.stderr if result.stderr else "Error desconocido en Node.js"
                        raise Exception(f"Error en Puppeteer:\n{error}")

                    if not os.path.exists(output_file):
                        raise Exception("No se generó el archivo de grabación")

                    if recorder_obj:
                        try:
                            recorder_obj.stop()
                            time.sleep(0.5)
                        except Exception:
                            pass

                    jm.update_progress(
                        job_id,
                        {
                            "result_file": output_file,
                            "video_path": video_path,
                            "stage": "Listo",
                        },
                    )
                    jm.mark_done(job_id)
                    return

                jm.mark_error(job_id, message="Unknown mode", details=str(req.mode))
            except Exception as e:
                jm.mark_error(job_id, message="Job failed", details=f"{e}\n{traceback.format_exc()}")

        threading.Thread(target=worker, daemon=True).start()
        return {"job_id": job_id}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str, _: None = Depends(_require_localhost)) -> Dict[str, Any]:
        try:
            return jm.get_job_summary(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")

    @app.get("/api/jobs/{job_id}/events")
    def get_job_events(job_id: str, limit: int = 200, _: None = Depends(_require_localhost)) -> Dict[str, Any]:
        try:
            return {"job_id": job_id, "events": jm.get_job_events(job_id, limit=limit)}
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")

    @app.post("/api/jobs/{job_id}/prompts/{prompt_id}/response")
    def answer_prompt(
        job_id: str,
        prompt_id: str,
        req: PromptResponseRequest,
        _: None = Depends(_require_localhost),
    ) -> Dict[str, Any]:
        try:
            jm.answer_prompt(job_id, prompt_id=prompt_id, answer=req.answer)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        return {"ok": True}

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str, _: None = Depends(_require_localhost)) -> Dict[str, Any]:
        jm.cancel_job(job_id)
        return {"ok": True}

    # -----------------------
    # SPA static serving
    # -----------------------
    @app.get("/")
    def spa_root() -> Any:
        if not os.path.exists(frontend_dist):
            return HTMLResponse(
                "<h3>Frontend not built.</h3>"
                "<p>Run: <code>cd frontend && npm install && npm run build</code></p>"
            )
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/logo.png")
    def logo_png() -> Any:
        if not os.path.exists(logo_path):
            raise HTTPException(status_code=404, detail="logo not found")
        return FileResponse(logo_path, media_type="image/png")

    @app.get("/{path:path}")
    def spa_catchall(path: str, _: None = Depends(_require_localhost)) -> Any:
        # Ensure we never hijack /api routes.
        if path.startswith("api/") or path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        if not os.path.exists(frontend_dist):
            return HTMLResponse(
                "<h3>Frontend not built.</h3>"
                "<p>Run: <code>cd frontend && npm install && npm run build</code></p>"
            )

        target = os.path.join(frontend_dist, path)
        if os.path.isfile(target):
            return FileResponse(target)

        # SPA fallback: serve index.html for any other route.
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    return app


# Default app for `uvicorn webui.fastapi_app:app`
app = create_app()

