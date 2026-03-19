from __future__ import annotations

import os
import threading
import traceback
from typing import Any, Dict, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from core.puppeteer_script_converter import PuppeteerToBehaveConverter
from core.step_by_step_converter import PuppeteerToStepByStepConverter
from webui.job_manager import JobManager
from webui.webui_adapter import WebUIAdapter


class ConvertRequest(BaseModel):
    mode: Literal[
        "puppeteer_to_behave",
        "puppeteer_to_step_by_step",
        "demo",
    ]


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
                    converter = PuppeteerToBehaveConverter(base_dir, adapter)
                    converter.convert_script()
                    jm.mark_done(job_id)
                    return

                if req.mode == "puppeteer_to_step_by_step":
                    converter = PuppeteerToStepByStepConverter(base_dir, adapter)
                    converter.convert_script()
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

    return app


# Default app for `uvicorn webui.fastapi_app:app`
app = create_app()

