"""Rutas FastAPI del módulo API testing."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.api_automation.api_to_behave_converter import convert_traffic_to_feature, write_api_feature
from core.api_automation.locust_generator import write_locustfile
from core.api_automation.models import ApiRequest
from core.api_automation.traffic_store import (
    ensure_api_project,
    import_traffic_to_scenarios,
    list_api_projects,
    list_scenarios,
    list_traffic_captures,
    load_scenario,
    resolve_traffic_capture_path,
    save_scenario,
    traffic_path_for_script,
)
from core.elia_paths import behave_projects_dir
from core.test_runner.runner_service import test_runner_service


class ApiScenarioSaveRequest(BaseModel):
    project: str
    scenario: Dict[str, Any]
    scenario_id: Optional[str] = None


class ApiConvertRequest(BaseModel):
    project: str
    traffic_path: Optional[str] = None
    feature_name: Optional[str] = None
    scenario_ids: Optional[List[str]] = None


class ApiImportTrafficRequest(BaseModel):
    capture_id: str


class ApiRunRequest(BaseModel):
    project: str
    feature_file: Optional[str] = None
    kind: str = "behave_api"


class ApiLoadTestRequest(BaseModel):
    project: str
    users: int = Field(default=5, ge=1, le=500)
    spawn_rate: float = Field(default=1.0, ge=0.1, le=100)
    run_time: str = "1m"
    host: str = ""


def register_api_routes(app, *, require_localhost, require_active_license) -> None:
    @app.get("/api/api/projects")
    def api_list_projects(
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        return {"projects": list_api_projects()}

    @app.post("/api/api/projects/{project_name}")
    def api_create_project(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        path = ensure_api_project(project_name)
        return {"ok": True, "project": project_name, "path": str(path)}

    @app.get("/api/api/projects/{project_name}/scenarios")
    def api_list_scenarios(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        return {"scenarios": list_scenarios(project_name)}

    @app.get("/api/api/projects/{project_name}/traffic-captures")
    def api_list_traffic_captures(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        return {"captures": list_traffic_captures(project_name)}

    @app.post("/api/api/projects/{project_name}/import-traffic")
    def api_import_traffic(
        project_name: str,
        body: ApiImportTrafficRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        try:
            traffic_path = str(resolve_traffic_capture_path(project_name, body.capture_id))
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        scenario_ids = import_traffic_to_scenarios(project_name, traffic_path)
        if not scenario_ids:
            raise HTTPException(status_code=400, detail="La captura no contiene peticiones importables")
        return {"ok": True, "scenario_ids": scenario_ids, "count": len(scenario_ids)}

    @app.post("/api/api/scenarios")
    def api_save_scenario(
        body: ApiScenarioSaveRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        req = ApiRequest.from_dict(body.scenario)
        sid = save_scenario(body.project, req, scenario_id=body.scenario_id)
        return {"ok": True, "scenario_id": sid}

    @app.post("/api/api/convert")
    def api_convert(
        body: ApiConvertRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        if body.traffic_path and os.path.isfile(body.traffic_path):
            feature = convert_traffic_to_feature(
                body.project, body.traffic_path, feature_name=body.feature_name
            )
            return {"ok": True, "feature_file": feature}
        requests: List[ApiRequest] = []
        for sid in body.scenario_ids or []:
            requests.append(load_scenario(body.project, sid))
        if not requests:
            raise HTTPException(status_code=400, detail="Sin escenarios ni tráfico para convertir")
        feature = write_api_feature(
            body.project, requests, feature_name=body.feature_name or "Escenario API"
        )
        return {"ok": True, "feature_file": feature}

    @app.post("/api/runs")
    def api_start_run(
        body: ApiRunRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        project_path = str(behave_projects_dir("api") / body.project)
        if not os.path.isdir(project_path):
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        if body.kind == "behave_api":
            feature = body.feature_file or "features"
            cmd = [sys.executable, "-m", "behave", feature]
            run_id = test_runner_service.start(kind="behave_api", command=cmd, cwd=project_path)
            return {"run_id": run_id}
        raise HTTPException(status_code=400, detail=f"Tipo de ejecución no soportado: {body.kind}")

    @app.get("/api/runs/{run_id}")
    def api_get_run(
        run_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        run = test_runner_service.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run.to_dict()

    @app.get("/api/runs/{run_id}/stream")
    async def api_stream_run(
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
                    payload = {"done": True, "return_code": current.return_code, "state": current.state}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break
                await asyncio.sleep(0.2)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/api/api/load-test")
    def api_load_test(
        body: ApiLoadTestRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        project_path = str(behave_projects_dir("api") / body.project)
        if not os.path.isdir(project_path):
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        scenarios = [load_scenario(body.project, s["id"]) for s in list_scenarios(body.project)]
        if not scenarios:
            raise HTTPException(status_code=400, detail="Sin escenarios para generar Locust")
        locust_path = write_locustfile(project_path, scenarios, host=body.host)
        try:
            import locust  # noqa: F401
        except ImportError as e:
            raise HTTPException(
                status_code=503,
                detail="Locust no instalado. pip install locust",
            ) from e
        cmd = [
            sys.executable,
            "-m",
            "locust",
            "-f",
            os.path.basename(locust_path),
            "--headless",
            "-u",
            str(body.users),
            "-r",
            str(body.spawn_rate),
            "-t",
            body.run_time,
        ]
        if body.host:
            cmd.extend(["--host", body.host])
        run_id = test_runner_service.start(kind="locust", command=cmd, cwd=project_path)
        return {"run_id": run_id, "locustfile": locust_path}

    @app.get("/api/api/traffic-path")
    def api_traffic_path_for_script(
        script_path: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, str]:
        return {"traffic_path": traffic_path_for_script(script_path)}
