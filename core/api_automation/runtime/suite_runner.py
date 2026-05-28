"""Ejecución de suites API encadenadas con correlación y data-driven."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.api_automation.data_store import read_csv_rows
from core.api_automation.models import ApiExtractor, ApiFlow, ApiFlowStep, ApiRequest
from core.api_automation.project_config import resolve_runtime_context
from core.api_automation.runtime.extractor_engine import apply_extractors
from core.api_automation.runtime.request_executor import execute_request
from core.api_automation.traffic_store import load_scenario


def run_suite(
    project: str,
    *,
    scenario_ids: Optional[List[str]] = None,
    flow: Optional[ApiFlow] = None,
    environment: Optional[str] = None,
    continue_on_failure: bool = False,
    data_file: Optional[str] = None,
) -> Dict[str, Any]:
    ctx = resolve_runtime_context(project, environment)
    base_vars = dict(ctx["variables"])
    iterations: List[Dict[str, str]] = [{}]
    csv_name = data_file or (flow.data_file if flow else None)
    if csv_name:
        iterations = read_csv_rows(project, csv_name)
        if not iterations:
            iterations = [{}]

    steps = _resolve_steps(scenario_ids, flow)
    if not steps:
        raise ValueError("Sin pasos para ejecutar")

    all_runs: List[Dict[str, Any]] = []
    total_passed = 0
    total_failed = 0

    for row_idx, row_vars in enumerate(iterations):
        session_vars = {**base_vars, **row_vars}
        iteration_results: List[Dict[str, Any]] = []
        iteration_ok = True

        for step_idx, step in enumerate(steps):
            req = _step_to_request(project, step)
            step_extractors = list(req.extractors) + list(step.extractors)
            try:
                result = execute_request(
                    req,
                    global_headers=ctx["global_headers"],
                    variables=session_vars,
                )
            except Exception as e:
                result = {
                    "ok": False,
                    "status_code": 0,
                    "headers": {},
                    "body": str(e),
                    "elapsed_ms": 0,
                    "assertions": [],
                    "request": {"method": req.method, "url": req.url},
                }

            extractor_results = apply_extractors(
                step_extractors,
                status_code=int(result.get("status_code") or 0),
                response_headers=result.get("headers") or {},
                response_body=result.get("body"),
                variables=session_vars,
            )

            step_ok = bool(result.get("ok"))
            entry = {
                "iteration": row_idx,
                "step": step_idx,
                "name": req.name,
                "scenario_id": step.scenario_id,
                "ok": step_ok,
                "result": result,
                "extractors": extractor_results,
                "variables": dict(session_vars),
            }
            iteration_results.append(entry)
            if step_ok:
                total_passed += 1
            else:
                total_failed += 1
                iteration_ok = False
                if not continue_on_failure:
                    all_runs.append(
                        {
                            "iteration": row_idx,
                            "data_row": row_vars,
                            "ok": False,
                            "steps": iteration_results,
                        }
                    )
                    return _suite_summary(all_runs, total_passed, total_failed, session_vars)

        all_runs.append(
            {
                "iteration": row_idx,
                "data_row": row_vars,
                "ok": iteration_ok,
                "steps": iteration_results,
            }
        )

    return _suite_summary(all_runs, total_passed, total_failed, session_vars)


def _suite_summary(
    runs: List[Dict[str, Any]],
    passed: int,
    failed: int,
    final_vars: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "ok": failed == 0,
        "passed_steps": passed,
        "failed_steps": failed,
        "iterations": len(runs),
        "runs": runs,
        "final_variables": final_vars,
    }


def _resolve_steps(scenario_ids: Optional[List[str]], flow: Optional[ApiFlow]) -> List[ApiFlowStep]:
    if flow and flow.steps:
        return flow.steps
    if scenario_ids:
        return [ApiFlowStep(scenario_id=sid) for sid in scenario_ids]
    return []


def _step_to_request(project: str, step: ApiFlowStep) -> ApiRequest:
    if step.request:
        return ApiRequest.from_dict(step.request)
    if step.scenario_id:
        return load_scenario(project, step.scenario_id)
    raise ValueError("Paso de suite sin escenario ni petición inline")
