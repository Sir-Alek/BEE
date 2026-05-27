"""Rutas FastAPI del módulo API testing."""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
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
from core.test_runner.run_launcher import build_locust_command, build_run_env, prepare_project
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
        from core.ai_policy import resolve_use_ai

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        use_ai = resolve_use_ai().use_ai
        if body.traffic_path and os.path.isfile(body.traffic_path):
            feature = convert_traffic_to_feature(
                body.project,
                body.traffic_path,
                feature_name=body.feature_name,
                use_ai=use_ai,
            )
            return {"ok": True, "feature_file": feature, "use_ai": use_ai}
        requests: List[ApiRequest] = []
        for sid in body.scenario_ids or []:
            requests.append(load_scenario(body.project, sid))
        if not requests:
            raise HTTPException(status_code=400, detail="Sin escenarios ni tráfico para convertir")
        feature = write_api_feature(
            body.project,
            requests,
            feature_name=body.feature_name or "Escenario API",
            use_ai=use_ai,
        )
        return {"ok": True, "feature_file": feature, "use_ai": use_ai}

    @app.post("/api/api/load-test")
    def api_load_test(
        body: ApiLoadTestRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.modules_config import is_module_enabled

        if not is_module_enabled("api_testing"):
            raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")
        project_path = prepare_project("api", body.project)
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
        cmd = build_locust_command(
            locust_path,
            users=body.users,
            spawn_rate=body.spawn_rate,
            run_time=body.run_time,
            host=body.host,
        )
        run_id = test_runner_service.start(
            kind="locust",
            command=cmd,
            cwd=project_path,
            env=build_run_env("api", generate_evidence=False, headless=True),
        )
        return {"run_id": run_id, "locustfile": locust_path}

    @app.get("/api/api/traffic-path")
    def api_traffic_path_for_script(
        script_path: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, str]:
        return {"traffic_path": traffic_path_for_script(script_path)}
