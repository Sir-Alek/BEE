"""Ejecución de suites API encadenadas con correlación y data-driven.

Soporta dos modos:

1. **Lineal** (retrocompatible): lista de `ApiFlowStep` ejecutada en orden.
2. **Árbol de nodos** (`ApiFlow.nodes`): controladores lógicos (if / loop / while)
   y pasos de tipo `request`, `sql` y `grpc`. Si `flow.nodes` está presente se
   usa el intérprete de árbol; si no, se ejecuta la lista lineal de siempre.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.api_automation.data_store import read_csv_rows
from core.api_automation.models import ApiExtractor, ApiFlow, ApiFlowStep, ApiRequest
from core.api_automation.project_config import resolve_runtime_context
from core.api_automation.runtime.condition_engine import evaluate_condition
from core.api_automation.runtime.extractor_engine import apply_extractors
from core.api_automation.runtime.request_executor import execute_request
from core.api_automation.runtime.grpc_step import run_grpc_step
from core.api_automation.runtime.sql_step import run_sql_step
from core.api_automation.traffic_store import load_scenario

# Tope de seguridad absoluto para bucles (evita loops infinitos por `while`).
_LOOP_HARD_CAP = 10000


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

    use_tree = bool(flow and flow.nodes)
    steps = [] if use_tree else _resolve_steps(scenario_ids, flow)
    if not use_tree and not steps:
        raise ValueError("Sin pasos para ejecutar")

    all_runs: List[Dict[str, Any]] = []
    state = _SuiteState()

    for row_idx, row_vars in enumerate(iterations):
        session_vars = {**base_vars, **row_vars}
        iteration_results: List[Dict[str, Any]] = []
        iteration_ok = True

        if use_tree:
            executor = _TreeExecutor(
                project=project,
                ctx=ctx,
                continue_on_failure=continue_on_failure,
                state=state,
            )
            iteration_ok = executor.run(
                flow.nodes, session_vars, iteration_results, row_idx
            )
        else:
            iteration_ok = _run_linear(
                project,
                steps,
                ctx,
                session_vars,
                iteration_results,
                row_idx,
                continue_on_failure,
                state,
            )

        all_runs.append(
            {
                "iteration": row_idx,
                "data_row": row_vars,
                "ok": iteration_ok,
                "steps": iteration_results,
            }
        )
        if not iteration_ok and not continue_on_failure:
            break

    return _suite_summary(all_runs, state.passed, state.failed, session_vars)


class _SuiteState:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0


# --------------------------------------------------------------------------- #
# Modo lineal (retrocompatible)
# --------------------------------------------------------------------------- #
def _run_linear(
    project, steps, ctx, session_vars, iteration_results, row_idx, continue_on_failure, state
) -> bool:
    iteration_ok = True
    for step_idx, step in enumerate(steps):
        req = _step_to_request(project, step)
        step_extractors = list(req.extractors) + list(step.extractors)
        result = _safe_execute(req, ctx, session_vars)
        extractor_results = apply_extractors(
            step_extractors,
            status_code=int(result.get("status_code") or 0),
            response_headers=result.get("headers") or {},
            response_body=result.get("body"),
            variables=session_vars,
        )
        step_ok = bool(result.get("ok"))
        iteration_results.append(
            {
                "iteration": row_idx,
                "step": step_idx,
                "type": "request",
                "name": req.name,
                "scenario_id": step.scenario_id,
                "ok": step_ok,
                "result": result,
                "extractors": extractor_results,
                "variables": dict(session_vars),
            }
        )
        if step_ok:
            state.passed += 1
        else:
            state.failed += 1
            iteration_ok = False
            if not continue_on_failure:
                return False
    return iteration_ok


# --------------------------------------------------------------------------- #
# Modo árbol de nodos (controladores lógicos + SQL + gRPC)
# --------------------------------------------------------------------------- #
class _StopExecution(Exception):
    """Señal interna para abortar el flujo en el primer fallo."""


class _TreeExecutor:
    def __init__(self, *, project, ctx, continue_on_failure, state: _SuiteState) -> None:
        self.project = project
        self.ctx = ctx
        self.continue_on_failure = continue_on_failure
        self.state = state
        self.last_result: Dict[str, Any] = {}
        self._counter = 0

    def run(self, nodes, session_vars, results, row_idx) -> bool:
        try:
            ok = self._exec_nodes(nodes, session_vars, results, row_idx)
            return ok
        except _StopExecution:
            return False

    def _exec_nodes(self, nodes, session_vars, results, row_idx) -> bool:
        ok_all = True
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            node_ok = self._exec_node(node, session_vars, results, row_idx)
            ok_all = ok_all and node_ok
        return ok_all

    def _exec_node(self, node, session_vars, results, row_idx) -> bool:
        ntype = str(node.get("type") or "request").lower()
        if ntype == "if":
            return self._exec_if(node, session_vars, results, row_idx)
        if ntype == "loop":
            return self._exec_loop(node, session_vars, results, row_idx)
        if ntype == "sql":
            return self._exec_leaf("sql", node, session_vars, results, row_idx)
        if ntype == "grpc":
            return self._exec_leaf("grpc", node, session_vars, results, row_idx)
        return self._exec_leaf("request", node, session_vars, results, row_idx)

    def _exec_if(self, node, session_vars, results, row_idx) -> bool:
        cond = node.get("condition") or {}
        taken = evaluate_condition(cond, variables=session_vars, last_result=self.last_result)
        branch = node.get("then") if taken else node.get("else")
        results.append(
            {
                "iteration": row_idx,
                "step": self._next_idx(),
                "type": "if",
                "condition": cond,
                "branch": "then" if taken else "else",
                "ok": True,
            }
        )
        return self._exec_nodes(branch or [], session_vars, results, row_idx)

    def _exec_loop(self, node, session_vars, results, row_idx) -> bool:
        mode = str(node.get("mode") or "count").lower()
        body = node.get("body") or []
        max_iter = min(int(node.get("max_iterations") or 100), _LOOP_HARD_CAP)
        ok_all = True
        i = 0
        if mode == "count":
            count_raw = node.get("count")
            count = self._resolve_count(count_raw, session_vars)
            count = max(0, min(count, max_iter))
            for i in range(count):
                session_vars["loop_index"] = str(i)
                ok_all = self._exec_nodes(body, session_vars, results, row_idx) and ok_all
        else:  # while
            cond = node.get("condition") or {}
            while i < max_iter and evaluate_condition(
                cond, variables=session_vars, last_result=self.last_result
            ):
                session_vars["loop_index"] = str(i)
                ok_all = self._exec_nodes(body, session_vars, results, row_idx) and ok_all
                i += 1
        results.append(
            {
                "iteration": row_idx,
                "step": self._next_idx(),
                "type": "loop",
                "mode": mode,
                "iterations": i if mode == "while" else None,
                "ok": ok_all,
            }
        )
        return ok_all

    def _exec_leaf(self, kind, node, session_vars, results, row_idx) -> bool:
        if kind == "sql":
            result = run_sql_step(node.get("sql") or {}, variables=session_vars)
            entry_name = "SQL"
        elif kind == "grpc":
            result = run_grpc_step(node.get("grpc") or {}, variables=session_vars)
            entry_name = f"{(node.get('grpc') or {}).get('service', 'gRPC')}"
        else:
            step = ApiFlowStep.from_dict(
                {
                    "scenario_id": node.get("scenario_id"),
                    "request": node.get("request"),
                    "extractors": node.get("extractors") or [],
                }
            )
            req = _step_to_request(self.project, step)
            result = _safe_execute(req, self.ctx, session_vars)
            self.last_result = result
            extractor_results = apply_extractors(
                list(req.extractors) + list(step.extractors),
                status_code=int(result.get("status_code") or 0),
                response_headers=result.get("headers") or {},
                response_body=result.get("body"),
                variables=session_vars,
            )
            result = {**result, "extractor_results": extractor_results}
            entry_name = req.name

        ok = bool(result.get("ok"))
        results.append(
            {
                "iteration": row_idx,
                "step": self._next_idx(),
                "type": kind,
                "name": entry_name,
                "ok": ok,
                "result": result,
                "variables": dict(session_vars),
            }
        )
        if ok:
            self.state.passed += 1
        else:
            self.state.failed += 1
            if not self.continue_on_failure:
                raise _StopExecution()
        return ok

    def _resolve_count(self, raw, session_vars) -> int:
        if isinstance(raw, int):
            return raw
        text = str(raw or "0")
        if text.startswith("{{") and text.endswith("}}"):
            text = session_vars.get(text[2:-2].strip(), "0")
        try:
            return int(float(str(text).strip()))
        except (TypeError, ValueError):
            return 0

    def _next_idx(self) -> int:
        idx = self._counter
        self._counter += 1
        return idx


# --------------------------------------------------------------------------- #
# Helpers compartidos
# --------------------------------------------------------------------------- #
def _safe_execute(req: ApiRequest, ctx: Dict[str, Any], session_vars: Dict[str, str]) -> Dict[str, Any]:
    try:
        return execute_request(
            req,
            global_headers=ctx["global_headers"],
            variables=session_vars,
        )
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": 0,
            "headers": {},
            "body": str(e),
            "elapsed_ms": 0,
            "assertions": [],
            "request": {"method": req.method, "url": req.url},
        }


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
