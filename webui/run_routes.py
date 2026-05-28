"""Rutas unificadas de ejecución Behave/Locust y edición de archivos de proyecto."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from core.elia_paths import behave_projects_dir
from core.test_runner import project_files
from core.test_runner.run_artifacts import list_pdfs_in_project, resolve_project_pdf
from core.test_runner.run_launcher import (
    BEHAVE_KINDS,
    build_behave_command,
    build_locust_command,
    build_run_env,
    normalize_kind,
    prepare_project,
)
from core.test_runner.runner_service import test_runner_service

VALID_PLATFORMS = frozenset({"web", "mobile", "legacy", "api"})


class UnifiedRunRequest(BaseModel):
    platform: str = "api"
    project: str
    kind: str = "behave"
    feature_file: Optional[str] = None
    generate_evidence: bool = True
    headless: bool = True
    env: Optional[Dict[str, str]] = None
    locust_users: int = Field(default=5, ge=1, le=500)
    locust_spawn_rate: float = Field(default=1.0, ge=0.1, le=100)
    locust_run_time: str = "1m"
    locust_host: str = ""
    locust_scenario_ids: Optional[list[str]] = None


class ProjectFileWriteRequest(BaseModel):
    content: str


class ProjectFolderOpenRequest(BaseModel):
    subpath: str = "outputs/pdfReports"


def _project_root(platform: str, project_name: str):
    plat = _check_platform(platform)
    root = behave_projects_dir(plat) / project_name
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return plat, root


def _check_platform(platform: str) -> str:
    p = (platform or "").strip().lower()
    if p not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Plataforma no válida: {platform}")
    return p


def _open_folder_in_os(folder: str) -> None:
    path = os.path.abspath(folder)
    if not os.path.isdir(path):
        raise FileNotFoundError(path)
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def _check_api_module(platform: str) -> None:
    if platform != "api":
        return
    from core.modules_config import is_module_enabled

    if not is_module_enabled("api_testing"):
        raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")


def _mobile_preflight() -> None:
    from core.ui_automation.mobile_android import ensure_appium_running

    res = ensure_appium_running(auto_start=False)
    if not res.get("ok"):
        raise HTTPException(
            status_code=503,
            detail=res.get("message") or "Appium no disponible. Inicia el servidor o instala Appium.",
        )


def register_run_routes(app, *, require_localhost, require_active_license) -> None:
    @app.get("/api/projects/{platform}")
    def list_platform_projects(
        platform: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        plat = _check_platform(platform)
        root = behave_projects_dir(plat)
        if not root.is_dir():
            return {"projects": []}
        return {"projects": sorted(d.name for d in root.iterdir() if d.is_dir())}

    @app.get("/api/projects/{platform}/{project_name}/files")
    def list_project_files(
        platform: str,
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        plat = _check_platform(platform)
        root = behave_projects_dir(plat) / project_name
        if not root.is_dir():
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        return {"files": project_files.list_runner_workspace_files(root)}

    @app.get("/api/projects/{platform}/{project_name}/file")
    def read_project_file_route(
        platform: str,
        project_name: str,
        path: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, str]:
        plat = _check_platform(platform)
        root = behave_projects_dir(plat) / project_name
        try:
            content = project_files.read_project_file(root, path)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"path": path, "content": content}

    @app.put("/api/projects/{platform}/{project_name}/file")
    def write_project_file_route(
        platform: str,
        project_name: str,
        path: str,
        body: ProjectFileWriteRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        plat = _check_platform(platform)
        root = behave_projects_dir(plat) / project_name
        try:
            project_files.write_project_file(root, path, body.content)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True, "path": path}

    @app.get("/api/projects/{platform}/{project_name}/reports")
    def list_project_reports(
        platform: str,
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _, root = _project_root(platform, project_name)
        reports = list_pdfs_in_project(root, since_ts=0)
        return {
            "reports": reports,
            "folder": str((root / "outputs" / "pdfReports").resolve()),
        }

    @app.get("/api/projects/{platform}/{project_name}/reports/file")
    def get_project_report_file(
        platform: str,
        project_name: str,
        name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> FileResponse:
        _, root = _project_root(platform, project_name)
        try:
            pdf_path = resolve_project_pdf(root, name)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=pdf_path.name,
            headers={"Content-Disposition": f'inline; filename="{pdf_path.name}"'},
        )

    @app.post("/api/projects/{platform}/{project_name}/open-folder")
    def open_project_folder(
        platform: str,
        project_name: str,
        body: ProjectFolderOpenRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _, root = _project_root(platform, project_name)
        rel = (body.subpath or "outputs/pdfReports").replace("\\", "/").strip("/")
        target = (root / rel).resolve()
        if not str(target).startswith(str(root.resolve())):
            raise HTTPException(status_code=400, detail="Ruta no permitida")
        try:
            _open_folder_in_os(str(target))
        except FileNotFoundError:
            os.makedirs(target, exist_ok=True)
            _open_folder_in_os(str(target))
        return {"ok": True, "path": str(target)}

    @app.post("/api/runs")
    def start_unified_run(
        body: UnifiedRunRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        plat = _check_platform(body.platform)
        _check_api_module(plat)
        if plat == "mobile":
            _mobile_preflight()
        try:
            project_path = prepare_project(plat, body.project.strip())
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        kind = normalize_kind(plat, body.kind)
        extra = dict(body.env or {})
        if plat == "mobile":
            extra.setdefault("ELIA_ANDROID_DEVICE", extra.get("ELIA_ANDROID_DEVICE", "emulator-5554"))

        if kind == "locust":
            from core.api_automation.locust_generator import write_locustfile
            from core.api_automation.traffic_store import list_scenarios, load_scenario

            if plat != "api":
                raise HTTPException(status_code=400, detail="Locust solo disponible para proyectos API")
            if body.locust_scenario_ids:
                scenarios = [load_scenario(body.project, sid) for sid in body.locust_scenario_ids]
            else:
                scenarios = [load_scenario(body.project, s["id"]) for s in list_scenarios(body.project)]
            if not scenarios:
                raise HTTPException(status_code=400, detail="Sin escenarios para Locust")
            locust_path = write_locustfile(project_path, scenarios, host=body.locust_host)
            try:
                import locust  # noqa: F401
            except ImportError as e:
                raise HTTPException(status_code=503, detail="Locust no instalado") from e
            cmd = build_locust_command(
                locust_path,
                users=body.locust_users,
                spawn_rate=body.locust_spawn_rate,
                run_time=body.locust_run_time,
                host=body.locust_host,
            )
            run_id = test_runner_service.start(
                kind="locust",
                command=cmd,
                cwd=project_path,
                env=build_run_env(plat, generate_evidence=False, headless=True, extra=extra),
                platform=plat,
                project=body.project.strip(),
                project_path=project_path,
            )
            return {"run_id": run_id, "locustfile": locust_path}

        if kind not in BEHAVE_KINDS and not kind.startswith("behave"):
            raise HTTPException(status_code=400, detail=f"Tipo no soportado: {body.kind}")

        feature = body.feature_file or "features"
        cmd = build_behave_command(feature)
        run_id = test_runner_service.start(
            kind=kind,
            command=cmd,
            cwd=project_path,
            env=build_run_env(
                plat,
                generate_evidence=True,
                headless=body.headless,
                extra=extra,
            ),
            platform=plat,
            project=body.project.strip(),
            project_path=project_path,
            generate_evidence=True,
        )
        return {"run_id": run_id, "project_path": project_path}

    @app.get("/api/runs/{run_id}")
    def get_run(
        run_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        run = test_runner_service.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run.to_dict()

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(
        run_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> StreamingResponse:
        run = test_runner_service.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")

        async def event_generator():
            cursor = 0
            while True:
                chunk = await asyncio.to_thread(test_runner_service.wait_lines, run_id, cursor, 5.0)
                for line in chunk:
                    cursor += 1
                    yield f"data: {json.dumps({'line': line}, ensure_ascii=False)}\n\n"
                current = test_runner_service.get(run_id)
                if current is None:
                    break
                if current.state != "running" and cursor >= len(current.lines):
                    payload = {
                        "done": True,
                        "return_code": current.return_code,
                        "state": current.state,
                        "artifacts": current.artifacts,
                        "platform": current.platform,
                        "project": current.project,
                        "project_path": current.project_path,
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break
                await asyncio.sleep(0.2)

        return StreamingResponse(event_generator(), media_type="text/event-stream")
