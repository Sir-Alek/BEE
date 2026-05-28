"""Rutas FastAPI del módulo API testing."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core.api_automation.api_to_behave_converter import convert_traffic_to_feature, write_api_feature
from core.api_automation.locust_generator import write_locustfile
from core.api_automation.data_store import list_data_files, preview_csv, read_csv_rows, save_csv_content
from core.api_automation.flow_store import list_flows, load_flow, save_flow
from core.api_automation.locust_metrics import resolve_metrics
from core.api_automation.models import ApiFlow, ApiRequest
from core.api_automation.openapi_import import import_openapi_spec
from core.api_automation.postman_import import import_postman_collection
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
    scenario_ids: Optional[List[str]] = None
    scenario_weights: Optional[Dict[str, int]] = None
    collect_metrics: bool = True
    csv_prefix: str = "elia_load"


class ApiRunSuiteRequest(BaseModel):
    project: str
    environment: Optional[str] = None
    scenario_ids: Optional[List[str]] = None
    flow_id: Optional[str] = None
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


class ApiLoadHistoryCompare(BaseModel):
    project: str
    run_a: str
    run_b: str


def _require_api_module() -> None:
    from core.modules_config import get_api_module_limits, is_module_enabled

    if not is_module_enabled("api_testing"):
        raise HTTPException(status_code=403, detail="Módulo api_testing no habilitado")


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

    @app.get("/api/api/projects/{project_name}/scenarios")
    def api_list_scenarios(
        project_name: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        return {"scenarios": list_scenarios(project_name)}

    @app.get("/api/api/projects/{project_name}/scenarios/{scenario_id}")
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
        req = ApiRequest.from_dict(body.scenario)
        sid = save_scenario(body.project, req, scenario_id=body.scenario_id)
        return {"ok": True, "scenario_id": sid}

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
        limits = _api_limits()
        scenario_ids = body.scenario_ids or []
        if len(scenario_ids) > int(limits.get("max_suite_scenarios", 200)):
            raise HTTPException(
                status_code=400,
                detail=f"Máximo {limits['max_suite_scenarios']} escenarios por suite",
            )
        flow = None
        if body.flow_id:
            try:
                flow = load_flow(body.project, body.flow_id)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
        try:
            return run_suite(
                body.project,
                scenario_ids=body.scenario_ids,
                flow=flow,
                environment=body.environment,
                continue_on_failure=body.continue_on_failure,
                data_file=body.data_file,
            )
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
        return {"flows": list_flows(project_name)}

    @app.get("/api/api/projects/{project_name}/flows/{flow_id}")
    def api_get_flow(
        project_name: str,
        flow_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
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
        flow = ApiFlow.from_dict(body.flow)
        fid = save_flow(body.project, flow, flow_id=body.flow_id)
        return {"ok": True, "flow_id": fid}

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
        return {"ok": True, "path": path}

    @app.get("/api/api/load-test/{run_id}/metrics")
    def api_load_test_metrics(
        run_id: str,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        run = test_runner_service.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        csv_prefix = str((run.meta or {}).get("csv_prefix") or "elia_load")
        metrics = resolve_metrics(run.project_path or run.cwd, list(run.lines), csv_prefix=csv_prefix)
        return {
            "run_id": run_id,
            "state": run.state,
            "metrics": metrics,
        }

    @app.post("/api/api/import/postman")
    def api_import_postman(
        body: ApiImportCollectionRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        if not body.collection:
            raise HTTPException(status_code=400, detail="Colección Postman requerida")
        requests = import_postman_collection(body.collection)
        if not requests:
            raise HTTPException(status_code=400, detail="La colección no contiene peticiones")
        ids = [save_scenario(body.project, req) for req in requests]
        return {"ok": True, "count": len(ids), "scenario_ids": ids}

    @app.post("/api/api/import/openapi")
    def api_import_openapi(
        body: ApiImportCollectionRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_api_module()
        if not body.spec:
            raise HTTPException(status_code=400, detail="Especificación OpenAPI requerida")
        requests = import_openapi_spec(body.spec)
        if not requests:
            raise HTTPException(status_code=400, detail="La especificación no contiene operaciones")
        ids = [save_scenario(body.project, req) for req in requests]
        return {"ok": True, "count": len(ids), "scenario_ids": ids}

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
        project_path = prepare_project("api", body.project)
        scenarios = _load_scenarios_for_project(body.project, body.scenario_ids)
        if not scenarios:
            raise HTTPException(status_code=400, detail="Sin escenarios para generar Locust")
        weights = body.scenario_weights or {}
        locust_path = write_locustfile(
            project_path, scenarios, host=body.host, weights=weights
        )
        try:
            import locust  # noqa: F401
        except ImportError as e:
            raise HTTPException(
                status_code=503,
                detail="Locust no instalado. pip install locust",
            ) from e
        csv_prefix = body.csv_prefix if body.collect_metrics else ""
        cmd = build_locust_command(
            locust_path,
            users=body.users,
            spawn_rate=body.spawn_rate,
            run_time=body.run_time,
            host=body.host,
            csv_prefix=csv_prefix,
        )
        run_id = test_runner_service.start(
            kind="locust",
            command=cmd,
            cwd=project_path,
            env=build_run_env("api", generate_evidence=False, headless=True),
            platform="api",
            project=body.project,
            project_path=project_path,
            meta={"csv_prefix": csv_prefix or "elia_load", "collect_metrics": body.collect_metrics},
        )
        return {
            "run_id": run_id,
            "locustfile": locust_path,
            "scenario_count": len(scenarios),
            "collect_metrics": body.collect_metrics,
        }

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
        run = test_runner_service.get(body.run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        csv_prefix = str((run.meta or {}).get("csv_prefix") or "elia_load")
        metrics = resolve_metrics(run.project_path or run.cwd, list(run.lines), csv_prefix=csv_prefix)
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
        return {"runs": list_load_runs(project_name)}

    @app.post("/api/api/load-history/snapshot")
    def api_save_load_snapshot(
        body: ApiLoadHistorySnapshot,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        from core.api_automation.load_run_history import append_load_run

        _require_api_module()
        run = test_runner_service.get(body.run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución no encontrada")
        csv_prefix = str((run.meta or {}).get("csv_prefix") or "elia_load")
        metrics = resolve_metrics(run.project_path or run.cwd, list(run.lines), csv_prefix=csv_prefix)
        history_id = append_load_run(
            body.project,
            {
                "runner_run_id": body.run_id,
                "users": body.users,
                "run_time": body.run_time,
                "host": body.host,
                "scenario_count": body.scenario_count,
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
        try:
            return compare_load_runs(body.project, body.run_a, body.run_b)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

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
