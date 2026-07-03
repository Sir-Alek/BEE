"""Rutas FastAPI del módulo API testing."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from core.api_automation.api_to_behave_converter import convert_traffic_to_feature, write_api_feature
from core.api_automation.locust_generator import write_locustfile
from core.api_automation.data_store import (
    import_data_file,
    list_data_files,
    preview_csv,
    read_csv_rows,
    read_csv_text,
    save_csv_content,
)
from core.api_automation.jmx_import import (
    commit_jmx_import,
    invalidate_jmx_import_meta_after_api_change,
    preview_jmx_import,
    resolve_jmx_import_meta,
)
from core.api_automation.flow_store import list_flows, load_flow, save_flow
from core.api_automation.locust_metrics import resolve_metrics
from core.api_automation.models import ApiFlow, ApiRequest
from core.api_automation.openapi_import import import_openapi_spec
from core.api_automation.postman_import import import_postman_collection, postman_collection_variables
from core.api_automation.project_config import (
    list_environments,
    load_environment,
    load_project_config,
    resolve_runtime_context,
    save_environment,
    save_project_config,
)
from core.api_automation.runtime.request_executor import execute_request
from core.api_automation.runtime.suite_runner import run_suite
from core.api_automation.load_test_profiles import list_profiles, resolve_load_profile
from core.api_automation.traffic_store import (
    delete_scenario,
    delete_scenarios,
    clone_scenario,
    ensure_api_project,
    import_requests_as_collection,
    import_traffic_to_scenarios,
    list_api_projects,
    list_scenarios,
    list_traffic_captures,
    load_scenario,
    resolve_traffic_capture_path,
    save_scenario,
    traffic_path_for_script,
)
from core.api_automation.collection_store import delete_collection, list_collections
from core.api_automation.scripts_guide import API_SCRIPTS_GUIDE_TITLE, load_api_scripts_guide_markdown
from core.elia_paths import behave_projects_dir
from core.test_runner.run_launcher import (
    build_locust_command,
    build_run_env,
    prepare_project,
    validate_distributed_load_options,
)
from core.test_runner.runner_service import test_runner_service


class ApiScenarioSaveRequest(BaseModel):
    project: str
    scenario: Dict[str, Any]
    scenario_id: Optional[str] = None
    collection_id: Optional[str] = None


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
    scenario_ids: Optional[List[str]] = None
    scenario_weights: Optional[Dict[str, int]] = None
    collect_metrics: bool = True
    csv_prefix: str = "elia_load"
    # Fase 0: think-time, ramp por etapas, multi-core local
    think_time: Optional[Dict[str, Any]] = None  # {kind, min/max | value | mean/stddev}
    stages: Optional[List[Dict[str, Any]]] = None  # [{duration, users, spawn_rate}] acumulado
    processes: int = Field(default=0, ge=-1, le=64)  # -1 = todos los núcleos
    sla: Optional[Dict[str, Any]] = None  # {max_p95_ms, max_error_pct, min_rps, ...}
    # Fase 1: carga basada en flujo con controladores
    flow_id: Optional[str] = None
    # Fase 4: carga distribuida multi-máquina
    mode: str = "standalone"  # standalone | master | worker
    master_host: str = ""
    master_port: int = Field(default=0, ge=0, le=65535)
    expect_workers: int = Field(default=0, ge=0, le=1000)
    # Setup SQL antes de Locust (nodos sql del flujo, una sola vez)
    run_setup_flow: bool = False
    environment: Optional[str] = None
    profile: Optional[str] = None  # load | stress | spike | soak | scalability | volume
    data_file: Optional[str] = None


class ApiDeleteScenariosRequest(BaseModel):
    project: str
    scenario_ids: List[str]


class ApiSqlPreflightRequest(BaseModel):
    project: str
    environment: Optional[str] = None
    sql: Dict[str, Any]


class ApiGrpcPreflightRequest(BaseModel):
    project: str
    environment: Optional[str] = None
    grpc: Dict[str, Any]


class ApiRunSuiteRequest(BaseModel):
    project: str
    environment: Optional[str] = None
    scenario_ids: Optional[List[str]] = None
    flow_id: Optional[str] = None
    # Flujo inline con árbol de nodos (controladores if/loop/while + sql/grpc).
    # Tiene prioridad sobre flow_id/scenario_ids cuando trae `nodes`.
    flow: Optional[Dict[str, Any]] = None
    continue_on_failure: bool = False
    data_file: Optional[str] = None


class ApiFlowSaveRequest(BaseModel):
    project: str
    flow: Dict[str, Any]
    flow_id: Optional[str] = None


class ApiCsvSaveRequest(BaseModel):
    project: str
    filename: str
    content: str


class ApiExecuteRequest(BaseModel):
    project: str
    request: Dict[str, Any]
    environment: Optional[str] = None


class ApiProjectConfigUpdate(BaseModel):
    default_environment: str = "dev"
    global_headers: Dict[str, str] = Field(default_factory=dict)


class ApiEnvironmentUpdate(BaseModel):
    name: str
    variables: Dict[str, str] = Field(default_factory=dict)


class ApiImportCollectionRequest(BaseModel):
    project: str
    collection: Optional[Dict[str, Any]] = None
    spec: Optional[Dict[str, Any]] = None


class ApiExportRequestEvidence(BaseModel):
    project: str
    environment: Optional[str] = None
    request: Dict[str, Any]
    result: Dict[str, Any]
    format: str = "pdf"  # pdf | json


class ApiExportLoadEvidence(BaseModel):
    project: str
    run_id: str
    users: int = 0
    run_time: str = "1m"
    host: str = ""
    scenario_count: int = 0
    format: str = "pdf"  # pdf | html | basic
    enriched: bool = True


class ApiExportSuiteEvidence(BaseModel):
    project: str
    environment: Optional[str] = None
    suite: Dict[str, Any]
    name: str = "Suite API"
    format: str = "pdf"  # pdf | json


class ApiLoadHistorySnapshot(BaseModel):
    project: str
    run_id: str
    users: int = 0
    run_time: str = "1m"
    host: str = ""
    scenario_count: int = 0
    profile: Optional[str] = None
    sla: Optional[Dict[str, Any]] = None


class ApiLoadHistoryCompare(BaseModel):
    project: str
    run_a: str
    run_b: str


def _require_api_http() -> None:
    from core.modules_config import is_feature_enabled

    if not is_feature_enabled("api_http_single"):
        raise HTTPException(status_code=403, detail="HTTP API básico no habilitado en tu plan")


def _require_api_postman() -> None:
    from core.modules_config import is_feature_enabled

    if not is_feature_enabled("api_postman_suites"):
        raise HTTPException(
            status_code=403,
            detail="Importación Postman/OpenAPI y suites requieren ELIA Tester",
        )


def _require_api_locust() -> None:
    from core.modules_config import is_feature_enabled

    if not is_feature_enabled("api_locust"):
        raise HTTPException(status_code=403, detail="Pruebas de carga Locust requieren ELIA Architect")


def _require_api_module() -> None:
    _require_api_http()


def _api_limits() -> Dict[str, Any]:
    from core.modules_config import get_api_module_limits

    return get_api_module_limits()


def _load_scenarios_for_project(project: str, scenario_ids: Optional[List[str]] = None) -> List[ApiRequest]:
    if scenario_ids:
        return [load_scenario(project, sid) for sid in scenario_ids]
    return [load_scenario(project, s["id"]) for s in list_scenarios(project)]


def register_api_routes(app, *, require_localhost, require_active_license) -> None:
    @app.get("/api/api/projects")
    def api_list_projects(
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        return {"projects": list_api_projects()}

    @app.get("/api/api/scripts-guide")
    def api_scripts_guide(
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, str]:
        _require_api_module()
        try:
            content = load_api_scripts_guide_markdown()
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"title": API_SCRIPTS_GUIDE_TITLE, "content": content}

    @app.post("/api/api/projects/{project_name}")
    def api_create_project(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        path = ensure_api_project(project_name)
        return {"ok": True, "project": project_name, "path": str(path)}

    @app.get("/api/api/projects/{project_name}/config")
    def api_get_project_config(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        try:
            return load_project_config(project_name)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.put("/api/api/projects/{project_name}/config")
    def api_update_project_config(
        project_name: str,
        body: ApiProjectConfigUpdate,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        save_project_config(
            project_name,
            {
                "default_environment": body.default_environment,
                "global_headers": body.global_headers,
            },
        )
        return {"ok": True}

    @app.get("/api/api/projects/{project_name}/environments")
    def api_list_environments(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        return {"environments": list_environments(project_name)}

    @app.get("/api/api/projects/{project_name}/environments/{env_name}")
    def api_get_environment(
        project_name: str,
        env_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        try:
            return load_environment(project_name, env_name)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.put("/api/api/projects/{project_name}/environments/{env_name}")
    def api_update_environment(
        project_name: str,
        env_name: str,
        body: ApiEnvironmentUpdate,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        save_environment(
            project_name,
            env_name,
            {"name": body.name or env_name, "variables": body.variables},
        )
        return {"ok": True}

    @app.get("/api/api/projects/{project_name}/collections")
    def api_list_collections(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        return {"collections": list_collections(project_name)}

    @app.delete("/api/api/projects/{project_name}/collections/{collection_id}")
    def api_delete_collection(
        project_name: str,
        collection_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        try:
            deleted = delete_collection(project_name, collection_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        invalidate_jmx_import_meta_after_api_change(
            project_name,
            deleted_collection_id=collection_id,
        )
        return {"ok": True, "collection_id": collection_id, "deleted_scenarios": deleted}

    @app.get("/api/api/projects/{project_name}/scenarios")
    def api_list_scenarios(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        collections = list_collections(project_name)
        return {
            "scenarios": list_scenarios(project_name, collections=collections),
            "collections": collections,
        }

    @app.get("/api/api/projects/{project_name}/scenarios/{scenario_id:path}")
    def api_get_scenario(
        project_name: str,
        scenario_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        try:
            req = load_scenario(project_name, scenario_id)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"scenario": req.to_dict()}

    @app.post("/api/api/projects/{project_name}/scenarios/{scenario_id:path}/clone")
    def api_clone_scenario(
        project_name: str,
        scenario_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        try:
            new_id = clone_scenario(project_name, scenario_id)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"ok": True, "scenario_id": new_id}

    @app.get("/api/api/projects/{project_name}/suite-history")
    def api_list_suite_history(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.suite_run_history import list_suite_runs

        _require_api_module()
        _require_api_postman()
        return {"runs": list_suite_runs(project_name)}

    @app.get("/api/api/projects/{project_name}/suite-progress")
    def api_suite_progress(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.suite_progress import read_suite_progress

        _require_api_module()
        _require_api_postman()
        progress = read_suite_progress(project_name)
        return {"progress": progress}

    @app.get("/api/api/projects/{project_name}/traffic-captures")
    def api_list_traffic_captures(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        return {"captures": list_traffic_captures(project_name)}

    @app.post("/api/api/projects/{project_name}/import-traffic")
    def api_import_traffic(
        project_name: str,
        body: ApiImportTrafficRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        try:
            traffic_path = str(resolve_traffic_capture_path(project_name, body.capture_id))
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        result = import_traffic_to_scenarios(project_name, traffic_path)
        if not result.get("scenario_ids"):
            raise HTTPException(status_code=400, detail="La captura no contiene peticiones importables")
        return {"ok": True, **result, "count": len(result["scenario_ids"])}

    @app.post("/api/api/scenarios")
    def api_save_scenario(
        body: ApiScenarioSaveRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        req = ApiRequest.from_dict(body.scenario)
        sid = save_scenario(
            body.project,
            req,
            scenario_id=body.scenario_id,
            collection_id=body.collection_id,
        )
        return {"ok": True, "scenario_id": sid}

    @app.delete("/api/api/projects/{project_name}/scenarios/{scenario_id:path}")
    def api_delete_scenario(
        project_name: str,
        scenario_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        try:
            delete_scenario(project_name, scenario_id)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        invalidate_jmx_import_meta_after_api_change(
            project_name,
            deleted_scenario_ids=[scenario_id],
        )
        return {"ok": True, "scenario_id": scenario_id}

    @app.post("/api/api/scenarios/delete")
    def api_delete_scenarios_bulk(
        body: ApiDeleteScenariosRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        if not body.scenario_ids:
            raise HTTPException(status_code=400, detail="Lista de escenarios vacía")
        deleted = delete_scenarios(body.project, body.scenario_ids)
        invalidate_jmx_import_meta_after_api_change(
            body.project,
            deleted_scenario_ids=body.scenario_ids,
        )
        return {"ok": True, "deleted": deleted}

    @app.post("/api/api/execute")
    def api_execute_request(
        body: ApiExecuteRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        req = ApiRequest.from_dict(body.request)
        ctx = resolve_runtime_context(body.project, body.environment)
        try:
            result = execute_request(
                req,
                global_headers=ctx["global_headers"],
                variables=ctx["variables"],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error HTTP: {e}") from e
        result["environment"] = ctx["environment"]
        return result

    @app.post("/api/api/run-suite")
    def api_run_suite(
        body: ApiRunSuiteRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        limits = _api_limits()
        scenario_ids = body.scenario_ids or []
        if len(scenario_ids) > int(limits.get("max_suite_scenarios", 200)):
            raise HTTPException(
                status_code=400,
                detail=f"Máximo {limits['max_suite_scenarios']} escenarios por suite",
            )
        flow = None
        if body.flow and (body.flow.get("nodes") or body.flow.get("steps")):
            from core.api_automation.models import ApiFlow

            flow = ApiFlow.from_dict(body.flow)
        elif body.flow_id:
            try:
                flow = load_flow(body.project, body.flow_id)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
        try:
            from webui.error_reporting import log_execution

            log_execution(
                "api_run_suite",
                project=body.project,
                environment=body.environment or "dev",
                flow_id=body.flow_id,
                scenario_count=len(scenario_ids),
            )
            result = run_suite(
                body.project,
                scenario_ids=body.scenario_ids,
                flow=flow,
                environment=body.environment,
                continue_on_failure=body.continue_on_failure,
                data_file=body.data_file,
            )
            from core.api_automation.suite_run_history import append_suite_run

            history_id = append_suite_run(
                body.project,
                {
                    "environment": body.environment or "dev",
                    "scenario_ids": scenario_ids,
                    "flow_id": body.flow_id,
                    "ok": result.get("ok"),
                    "passed_steps": result.get("passed_steps"),
                    "failed_steps": result.get("failed_steps"),
                    "iterations": result.get("iterations"),
                },
            )
            result["history_id"] = history_id
            log_execution(
                "api_run_suite_done",
                project=body.project,
                ok=result.get("ok"),
                passed=result.get("passed_steps"),
                failed=result.get("failed_steps"),
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.get("/api/api/projects/{project_name}/flows")
    def api_list_flows(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        return {"flows": list_flows(project_name)}

    @app.get("/api/api/projects/{project_name}/flows/{flow_id}")
    def api_get_flow(
        project_name: str,
        flow_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        try:
            flow = load_flow(project_name, flow_id)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"flow": flow.to_dict()}

    @app.post("/api/api/flows")
    def api_save_flow(
        body: ApiFlowSaveRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        flow = ApiFlow.from_dict(body.flow)
        fid = save_flow(body.project, flow, flow_id=body.flow_id)
        return {"ok": True, "flow_id": fid}

    @app.get("/api/api/capabilities/drivers")
    def api_driver_capabilities(
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.driver_capabilities import get_driver_capabilities

        _require_api_module()
        return get_driver_capabilities()

    @app.post("/api/api/sql/preflight")
    def api_sql_preflight(
        body: ApiSqlPreflightRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.runtime.sql_step import sql_preflight

        _require_api_module()
        _require_api_postman()
        ctx = resolve_runtime_context(body.project, body.environment)
        result = sql_preflight(body.sql, variables=ctx["variables"])
        return {"ok": bool(result.get("ok")), "result": result, "environment": ctx["environment"]}

    @app.post("/api/api/grpc/preflight")
    def api_grpc_preflight(
        body: ApiGrpcPreflightRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.runtime.grpc_step import grpc_preflight

        _require_api_module()
        _require_api_locust()
        ctx = resolve_runtime_context(body.project, body.environment)
        result = grpc_preflight(body.grpc, variables=ctx["variables"])
        return {"ok": bool(result.get("ok")), "result": result, "environment": ctx["environment"]}

    @app.get("/api/api/projects/{project_name}/data-files")
    def api_list_data_files(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        return {"files": list_data_files(project_name)}

    @app.get("/api/api/projects/{project_name}/data-files/{filename}")
    def api_preview_data_file(
        project_name: str,
        filename: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        try:
            return preview_csv(project_name, filename)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.get("/api/api/projects/{project_name}/data-files/{filename}/content")
    def api_data_file_content(
        project_name: str,
        filename: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, str]:
        _require_api_module()
        try:
            return {"name": filename, "content": read_csv_text(project_name, filename)}
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/api/api/projects/{project_name}/data-files/upload")
    async def api_upload_data_file(
        project_name: str,
        file: UploadFile = File(...),
        overwrite: bool = Form(False),
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        raw_name = file.filename or "datos.csv"
        lower = raw_name.lower()
        if not (lower.endswith(".csv") or lower.endswith(".xlsx")):
            raise HTTPException(status_code=400, detail="Solo se admiten archivos .csv o .xlsx")
        data = await file.read()
        try:
            return import_data_file(project_name, raw_name, data, overwrite=overwrite)
        except FileExistsError as e:
            raise HTTPException(status_code=409, detail=f"Ya existe {e}") from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/api/api/projects/{project_name}/jmx/preview")
    async def api_jmx_preview(
        project_name: str,
        file: UploadFile = File(...),
        thread_group_index: int = Form(0),
        include_disabled_controllers: bool = Form(False),
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        raw_name = file.filename or "plan.jmx"
        if not raw_name.lower().endswith(".jmx"):
            raise HTTPException(status_code=400, detail="Solo se admiten archivos .jmx")
        data = await file.read()
        try:
            report = preview_jmx_import(
                data,
                source_name=raw_name,
                thread_group_index=thread_group_index,
                include_disabled_controllers=include_disabled_controllers,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True, "report": report.to_dict()}

    @app.get("/api/api/projects/{project_name}/jmx/meta")
    def api_jmx_meta(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        meta = resolve_jmx_import_meta(project_name)
        return {"ok": True, "meta": meta}

    @app.post("/api/api/projects/{project_name}/jmx/import")
    async def api_jmx_import(
        project_name: str,
        file: UploadFile = File(...),
        thread_group_index: int = Form(0),
        include_disabled_controllers: bool = Form(False),
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        raw_name = file.filename or "plan.jmx"
        if not raw_name.lower().endswith(".jmx"):
            raise HTTPException(status_code=400, detail="Solo se admiten archivos .jmx")
        data = await file.read()
        try:
            return commit_jmx_import(
                project_name,
                data,
                source_name=raw_name,
                thread_group_index=thread_group_index,
                include_disabled_controllers=include_disabled_controllers,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/api/api/data-files")
    def api_save_data_file(
        body: ApiCsvSaveRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        try:
            path = save_csv_content(body.project, body.filename, body.content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True, "path": path, "preview": preview_csv(body.project, body.filename)}

    @app.get("/api/api/load-test/{run_id}/metrics")
    def api_load_test_metrics(
        run_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_locust()
        run = test_runner_service.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        csv_prefix = str((run.meta or {}).get("csv_prefix") or "elia_load")
        metrics = resolve_metrics(run.project_path or run.cwd, list(run.lines), csv_prefix=csv_prefix)
        sla = (run.meta or {}).get("sla") or {}
        sla_result = None
        if sla:
            from core.api_automation.locust_metrics import evaluate_load_sla

            sla_result = evaluate_load_sla(metrics, sla)
        return {
            "run_id": run_id,
            "state": run.state,
            "metrics": metrics,
            "sla": sla_result,
        }

    @app.post("/api/api/import/postman")
    def api_import_postman(
        body: ApiImportCollectionRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        if not body.collection:
            raise HTTPException(status_code=400, detail="Colección JSON requerida")
        requests, collection_name = import_postman_collection(body.collection)
        if not requests:
            raise HTTPException(status_code=400, detail="La colección no contiene peticiones")
        imported = import_requests_as_collection(
            body.project,
            requests,
            collection_name=collection_name,
            source="import_v21",
        )
        collection_vars = postman_collection_variables(body.collection)
        if collection_vars:
            cfg = load_project_config(body.project)
            env_name = cfg.get("default_environment") or "dev"
            try:
                env = load_environment(body.project, env_name)
            except FileNotFoundError:
                env = {"name": env_name, "variables": {}}
            merged = {**(env.get("variables") or {}), **collection_vars}
            save_environment(body.project, env_name, {"name": env_name, "variables": merged})
        return {
            "ok": True,
            "count": imported["count"],
            "scenario_ids": imported["scenario_ids"],
            "collection_id": imported["collection_id"],
            "collection_name": imported["collection_name"],
            "variables_imported": len(collection_vars),
        }

    @app.post("/api/api/import/openapi")
    def api_import_openapi(
        body: ApiImportCollectionRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_postman()
        if not body.spec:
            raise HTTPException(status_code=400, detail="Especificación OpenAPI requerida")
        requests, collection_name = import_openapi_spec(body.spec)
        if not requests:
            raise HTTPException(status_code=400, detail="La especificación no contiene operaciones")
        imported = import_requests_as_collection(
            body.project,
            requests,
            collection_name=collection_name,
            source="openapi",
        )
        return {
            "ok": True,
            "count": imported["count"],
            "scenario_ids": imported["scenario_ids"],
            "collection_id": imported["collection_id"],
            "collection_name": imported["collection_name"],
        }

    @app.post("/api/api/convert")
    def api_convert(
        body: ApiConvertRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        """Deprecated: conversión a Behave. Preferir ejecución directa POST /api/api/execute."""
        from core.ai_policy import resolve_use_ai

        _require_api_module()
        use_ai = resolve_use_ai().use_ai
        if body.traffic_path and os.path.isfile(body.traffic_path):
            feature = convert_traffic_to_feature(
                body.project,
                body.traffic_path,
                feature_name=body.feature_name,
                use_ai=use_ai,
            )
            return {"ok": True, "feature_file": feature, "use_ai": use_ai, "deprecated": True}
        requests = _load_scenarios_for_project(body.project, body.scenario_ids)
        if not requests:
            raise HTTPException(status_code=400, detail="Sin escenarios ni tráfico para convertir")
        feature = write_api_feature(
            body.project,
            requests,
            feature_name=body.feature_name or "Escenario API",
            use_ai=use_ai,
        )
        return {"ok": True, "feature_file": feature, "use_ai": use_ai, "deprecated": True}

    @app.post("/api/api/load-test")
    def api_load_test(
        body: ApiLoadTestRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_locust()
        try:
            from webui.error_reporting import log_execution

            log_execution(
                "api_load_test",
                project=body.project,
                users=body.users,
                run_time=body.run_time,
                flow_id=body.flow_id,
                run_setup_flow=body.run_setup_flow,
            )
        except Exception:
            pass
        project_path = prepare_project("api", body.project)

        flow_nodes = None
        flow_raw_nodes: List[Dict[str, Any]] = []
        scenarios: List[ApiRequest] = []
        setup_vars: Dict[str, str] = {}
        node_counts: Dict[str, int] = {}

        if body.flow_id:
            from core.api_automation.locust_generator import inline_flow_requests
            from core.api_automation.flow_utils import build_sql_setup_flow, count_node_types

            try:
                flow = load_flow(body.project, body.flow_id)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            if flow.nodes:
                flow_raw_nodes = flow.nodes
                node_counts = count_node_types(flow_raw_nodes)
                if body.run_setup_flow and node_counts.get("sql", 0) > 0:
                    setup_flow = build_sql_setup_flow(flow_raw_nodes)
                    setup_result = run_suite(
                        body.project,
                        flow=setup_flow,
                        environment=body.environment,
                        continue_on_failure=False,
                    )
                    if not setup_result.get("ok"):
                        raise HTTPException(
                            status_code=400,
                            detail="Setup SQL pre-carga falló; revise credenciales y consultas.",
                        )
                    setup_vars = dict(setup_result.get("final_variables") or {})
                flow_nodes = inline_flow_requests(body.project, flow.nodes)
        if not flow_nodes:
            scenarios = _load_scenarios_for_project(body.project, body.scenario_ids)
            if not scenarios:
                raise HTTPException(status_code=400, detail="Sin escenarios para generar carga")

        profile_id, resolved_stages, resolved_think, effective_run_time = resolve_load_profile(
            body.profile,
            users=body.users,
            spawn_rate=body.spawn_rate,
            run_time=body.run_time,
            think_time=body.think_time,
            stages=body.stages,
        )
        think_time = resolved_think if body.think_time is None else body.think_time
        stages = resolved_stages if body.stages is None else body.stages
        run_time = effective_run_time

        dist_ok, dist_err = validate_distributed_load_options(
            mode=body.mode,
            master_host=body.master_host,
            master_port=body.master_port,
            processes=body.processes,
        )
        if not dist_ok:
            raise HTTPException(status_code=400, detail=dist_err)

        if node_counts.get("grpc", 0) > 0:
            from core.api_automation.driver_capabilities import grpc_driver_status

            grpc_caps = grpc_driver_status()
            if not grpc_caps.get("available"):
                missing = ", ".join(grpc_caps.get("missing") or [])
                raise HTTPException(
                    status_code=503,
                    detail=f"El flujo incluye pasos gRPC pero faltan dependencias: {missing}. "
                    "pip install grpcio grpcio-reflection protobuf",
                )

        csv_rows = None
        data_file = (body.data_file or "").strip()
        if data_file:
            try:
                csv_rows = read_csv_rows(body.project, data_file)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e

        weights = body.scenario_weights or {}
        locust_path = write_locustfile(
            project_path,
            scenarios,
            host=body.host,
            weights=weights,
            think_time=think_time,
            stages=stages,
            flow_nodes=flow_nodes,
            initial_vars=setup_vars,
            csv_rows=csv_rows,
        )
        try:
            import locust  # noqa: F401
        except ImportError as e:
            raise HTTPException(
                status_code=503,
                detail="Motor de carga (Locust) no instalado. pip install locust",
            ) from e
        csv_prefix = body.csv_prefix if body.collect_metrics else ""
        cmd = build_locust_command(
            locust_path,
            users=body.users,
            spawn_rate=body.spawn_rate,
            run_time=run_time,
            host=body.host,
            csv_prefix=csv_prefix,
            processes=body.processes,
            mode=body.mode,
            master_host=body.master_host,
            master_port=body.master_port,
            expect_workers=body.expect_workers,
        )
        run_id = test_runner_service.start(
            kind="locust",
            command=cmd,
            cwd=project_path,
            env=build_run_env("api", generate_evidence=False, headless=True),
            platform="api",
            project=body.project,
            project_path=project_path,
            meta={
                "csv_prefix": csv_prefix or "elia_load",
                "collect_metrics": body.collect_metrics,
                "sla": body.sla or {},
                "profile": profile_id,
                "stages": stages or [],
                "think_time": think_time or {},
                "data_file": data_file,
                "mode": body.mode,
                "flow_node_counts": node_counts,
                "setup_sql": bool(body.run_setup_flow and node_counts.get("sql")),
            },
        )
        return {
            "run_id": run_id,
            "locustfile": locust_path,
            "scenario_count": len(scenarios),
            "flow": bool(flow_nodes),
            "flow_node_counts": node_counts,
            "setup_sql": bool(body.run_setup_flow and node_counts.get("sql")),
            "collect_metrics": body.collect_metrics,
            "profile": profile_id,
            "run_time": run_time,
            "mode": body.mode,
            "command": cmd,
        }

    @app.get("/api/api/load-test/profiles")
    def api_load_test_profiles(
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        _require_api_locust()
        return {"profiles": list_profiles()}

    @app.post("/api/api/export/request-evidence")
    def api_export_request_evidence(
        body: ApiExportRequestEvidence,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        """Exportación opt-in: solo se invoca cuando el usuario lo solicita explícitamente."""
        from core.api_automation.api_evidence_report import (
            write_request_evidence_json,
            write_request_evidence_pdf,
        )

        _require_api_module()
        payload = {
            "name": body.request.get("name") or "Petición API",
            "environment": body.environment or "dev",
            "request": body.request,
            "result": body.result,
            "exported_at": datetime.now().isoformat(),
        }
        fmt = (body.format or "pdf").lower()
        if fmt == "json":
            path = write_request_evidence_json(body.project, payload)
        elif fmt == "pdf":
            path = write_request_evidence_pdf(body.project, payload)
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado: pdf | json")
        filename = os.path.basename(path)
        return {"ok": True, "format": fmt, "path": path, "filename": filename}

    @app.post("/api/api/export/suite-evidence")
    def api_export_suite_evidence(
        body: ApiExportSuiteEvidence,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        """Exportación opt-in de suite funcional."""
        from core.api_automation.api_evidence_report import (
            write_suite_evidence_json,
            write_suite_evidence_pdf,
        )

        _require_api_module()
        _require_api_postman()
        payload = {
            "name": body.name,
            "environment": body.environment or "dev",
            "suite": body.suite,
            "exported_at": datetime.now().isoformat(),
        }
        fmt = (body.format or "pdf").lower()
        if fmt == "json":
            path = write_suite_evidence_json(body.project, payload)
        elif fmt == "pdf":
            path = write_suite_evidence_pdf(body.project, payload)
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado: pdf | json")
        filename = os.path.basename(path)
        return {"ok": True, "format": fmt, "path": path, "filename": filename}

    @app.post("/api/api/export/load-evidence")
    def api_export_load_evidence(
        body: ApiExportLoadEvidence,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        """Exportación opt-in de reporte tras prueba de carga Locust."""
        from core.api_automation.api_evidence_report import (
            write_enriched_load_test_evidence_html,
            write_enriched_load_test_evidence_pdf,
            write_load_test_evidence_pdf,
        )

        _require_api_module()
        _require_api_locust()
        run = test_runner_service.get(body.run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        csv_prefix = str((run.meta or {}).get("csv_prefix") or "elia_load")
        metrics = resolve_metrics(run.project_path or run.cwd, list(run.lines), csv_prefix=csv_prefix)
        run_meta = run.meta or {}
        profile = str(run_meta.get("profile") or "load")
        stages = run_meta.get("stages") or []
        sla_cfg = run_meta.get("sla") or {}
        sla_result = None
        if sla_cfg:
            from core.api_automation.locust_metrics import evaluate_load_sla

            sla_result = evaluate_load_sla(metrics, sla_cfg)
        fmt = (body.format or "pdf").lower()
        if fmt == "html" and body.enriched:
            path = write_enriched_load_test_evidence_html(
                body.project,
                lines=list(run.lines),
                metrics=metrics,
                users=body.users,
                run_time=body.run_time,
                host=body.host,
                scenario_count=body.scenario_count,
                run_id=body.run_id,
                profile=profile,
                sla_result=sla_result,
                stages=stages,
            )
        elif fmt == "pdf" and body.enriched:
            path = write_enriched_load_test_evidence_pdf(
                body.project,
                lines=list(run.lines),
                metrics=metrics,
                users=body.users,
                run_time=body.run_time,
                host=body.host,
                scenario_count=body.scenario_count,
                run_id=body.run_id,
                profile=profile,
                sla_result=sla_result,
                stages=stages,
            )
        else:
            path = write_load_test_evidence_pdf(
                body.project,
                lines=list(run.lines),
                users=body.users,
                run_time=body.run_time,
                host=body.host,
                scenario_count=body.scenario_count,
            )
        filename = os.path.basename(path)
        return {"ok": True, "format": fmt, "path": path, "filename": filename}

    @app.get("/api/api/projects/{project_name}/load-history")
    def api_list_load_history(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.load_run_history import list_load_runs

        _require_api_module()
        _require_api_locust()
        return {"runs": list_load_runs(project_name)}

    @app.post("/api/api/load-history/snapshot")
    def api_save_load_snapshot(
        body: ApiLoadHistorySnapshot,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.load_run_history import append_load_run

        _require_api_module()
        _require_api_locust()
        run = test_runner_service.get(body.run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        csv_prefix = str((run.meta or {}).get("csv_prefix") or "elia_load")
        metrics = resolve_metrics(run.project_path or run.cwd, list(run.lines), csv_prefix=csv_prefix)
        run_meta = run.meta or {}
        sla_cfg = body.sla if body.sla is not None else (run_meta.get("sla") or {})
        sla_result = None
        if sla_cfg:
            from core.api_automation.locust_metrics import evaluate_load_sla

            sla_result = evaluate_load_sla(metrics, sla_cfg)
        history_id = append_load_run(
            body.project,
            {
                "runner_run_id": body.run_id,
                "users": body.users,
                "run_time": body.run_time,
                "host": body.host,
                "scenario_count": body.scenario_count,
                "profile": body.profile or run_meta.get("profile") or "load",
                "sla": sla_result,
                "metrics": metrics,
            },
        )
        return {"ok": True, "history_id": history_id}

    @app.post("/api/api/load-history/compare")
    def api_compare_load_history(
        body: ApiLoadHistoryCompare,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.load_run_history import compare_load_runs

        _require_api_module()
        _require_api_locust()
        try:
            return compare_load_runs(body.project, body.run_a, body.run_b)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.post("/api/api/load-preflight")
    def api_load_preflight(
        body: Dict[str, Any],
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.load_preflight import validate_load_preflight

        _require_api_module()
        _require_api_locust()
        return validate_load_preflight(
            mode=str(body.get("mode") or "local"),
            master_host=str(body.get("master_host") or "127.0.0.1"),
            master_port=int(body.get("master_port") or 5557),
        )

    @app.post("/api/api/load-history/report")
    def api_load_history_report(
        body: Dict[str, Any],
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        """Genera PDF/HTML desde snapshot de historial (sin re-ejecutar Locust)."""
        from core.api_automation.api_evidence_report import (
            write_enriched_load_test_evidence_html,
            write_enriched_load_test_evidence_pdf,
        )
        from core.api_automation.load_run_history import get_load_run

        _require_api_module()
        _require_api_locust()
        project = str(body.get("project") or "")
        history_id = str(body.get("history_id") or "")
        fmt = str(body.get("format") or "pdf").lower()
        entry = get_load_run(project, history_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entrada de historial no encontrada")
        metrics = entry.get("metrics") or {}
        sla_result = entry.get("sla")
        profile = str(entry.get("profile") or "load")
        users = int(entry.get("users") or 5)
        run_time = str(entry.get("run_time") or "1m")
        host = str(entry.get("host") or "")
        scenario_count = int(entry.get("scenario_count") or 0)
        runner_run_id = str(entry.get("runner_run_id") or history_id)
        if fmt == "html":
            path = write_enriched_load_test_evidence_html(
                project,
                lines=[],
                metrics=metrics,
                users=users,
                run_time=run_time,
                host=host,
                scenario_count=scenario_count,
                run_id=runner_run_id,
                profile=profile,
                sla_result=sla_result,
                stages=[],
            )
        else:
            path = write_enriched_load_test_evidence_pdf(
                project,
                lines=[],
                metrics=metrics,
                users=users,
                run_time=run_time,
                host=host,
                scenario_count=scenario_count,
                run_id=runner_run_id,
                profile=profile,
                sla_result=sla_result,
                stages=[],
            )
        filename = os.path.basename(path)
        return {"ok": True, "format": fmt, "path": path, "filename": filename}

    @app.post("/api/api/projects/{project_name}/environments/{env_name}/sync-from-web")
    def api_sync_env_from_web(
        project_name: str,
        env_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.shared_env_bridge import sync_api_environment_from_web

        _require_api_module()
        try:
            result = sync_api_environment_from_web(project_name, env_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True, **result}

    @app.get("/api/api/projects/{project_name}/web-origin")
    def api_get_web_origin(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.shared_env_bridge import infer_web_origin

        _require_api_module()
        origin = infer_web_origin(project_name)
        return {"origin": origin, "available": bool(origin)}

    @app.get("/api/api/traffic-path")
    def api_traffic_path_for_script(
        script_path: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, str]:
        return {"traffic_path": traffic_path_for_script(script_path)}
