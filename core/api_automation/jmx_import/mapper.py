"""Mapeo JMeter parseado → modelos ELIA e informe scaffolding."""

from __future__ import annotations



import json

import os

import re

import uuid

from datetime import datetime, timezone

from pathlib import Path

from typing import Any, Dict, List, Optional, Tuple



from core.api_automation.jmx_import.groovy_translate import merge_groovy_translations, translate_groovy_scripts

from core.api_automation.jmx_import.parser import ParsedJmxPlan, extract_thread_group_samplers, parse_jmx_bytes

from core.api_automation.jmx_import.types import JmxCsvRef, JmxImportItem, JmxImportReport, JmxThreadGroupInfo

from core.api_automation.models import ApiExtractor, ApiFlow, ApiRequest



_JMETER_VAR_RE = re.compile(r"\$\{([^}]+)\}")

JMX_META_FILENAME = "last_import.meta.json"





def jmeter_to_elia_text(text: str) -> str:

    if not text:

        return text



    def repl(match: re.Match[str]) -> str:

        inner = match.group(1).strip()

        if inner.startswith("__"):

            return match.group(0)

        return "{{" + inner + "}}"



    return _JMETER_VAR_RE.sub(repl, text)





def jmx_meta_path(project: str) -> Path:

    from core.api_automation.traffic_store import ensure_api_project



    return ensure_api_project(project) / "resources" / "jmeter" / JMX_META_FILENAME





def save_jmx_import_meta(project: str, payload: Dict[str, Any]) -> Path:

    path = jmx_meta_path(project)

    path.parent.mkdir(parents=True, exist_ok=True)

    enriched = {

        **payload,

        "updated_at": datetime.now(timezone.utc).isoformat(),

    }

    path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")

    return path





def load_jmx_import_meta(project: str) -> Optional[Dict[str, Any]]:
    path = jmx_meta_path(project)
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def clear_jmx_import_meta(project: str) -> None:
    path = jmx_meta_path(project)
    if path.is_file():
        path.unlink(missing_ok=True)


def _jmx_meta_is_valid(project: str, meta: Dict[str, Any]) -> bool:
    from core.api_automation.collection_store import list_collections
    from core.api_automation.flow_store import flow_exists
    from core.api_automation.traffic_store import load_scenario

    scenario_ids = [str(s) for s in (meta.get("scenario_ids") or []) if str(s).strip()]
    collection_id = str(meta.get("collection_id") or "").strip()
    flow_id = str(meta.get("flow_id") or "").strip()

    if collection_id:
        collections = {c["id"] for c in list_collections(project)}
        if collection_id not in collections:
            return False

    if scenario_ids:
        for sid in scenario_ids:
            try:
                load_scenario(project, sid)
            except FileNotFoundError:
                return False

    if flow_id and not flow_exists(project, flow_id):
        return False

    return bool(scenario_ids or collection_id or flow_id)


def resolve_jmx_import_meta(project: str) -> Optional[Dict[str, Any]]:
    meta = load_jmx_import_meta(project)
    if not meta:
        return None
    if _jmx_meta_is_valid(project, meta):
        return meta
    clear_jmx_import_meta(project)
    return None


def invalidate_jmx_import_meta_after_api_change(
    project: str,
    *,
    deleted_scenario_ids: Optional[List[str]] = None,
    deleted_collection_id: Optional[str] = None,
) -> bool:
    """Elimina meta/flujo JMX huérfanos tras borrar escenarios o colecciones importadas."""
    meta = load_jmx_import_meta(project)
    if not meta:
        return False

    deleted_ids = {str(s) for s in (deleted_scenario_ids or []) if str(s).strip()}
    meta_ids = {str(s) for s in (meta.get("scenario_ids") or []) if str(s).strip()}
    meta_collection = str(meta.get("collection_id") or "").strip()
    flow_id = str(meta.get("flow_id") or "").strip()

    should_clear = False
    if deleted_collection_id and meta_collection and deleted_collection_id == meta_collection:
        should_clear = True
    elif deleted_ids and meta_ids.intersection(deleted_ids):
        should_clear = True
    elif meta_ids and not _jmx_meta_is_valid(project, meta):
        should_clear = True

    if not should_clear:
        return False

    if flow_id:
        from core.api_automation.flow_store import delete_flow

        delete_flow(project, flow_id)
    clear_jmx_import_meta(project)
    return True


def _count_samplers_in_group(

    plan: ParsedJmxPlan,

    index: int,

    *,

    include_disabled_controllers: bool = False,

) -> int:

    try:

        _, samplers, _ = extract_thread_group_samplers(

            plan,

            index,

            include_disabled_controllers=include_disabled_controllers,

        )

        return len(samplers)

    except ValueError:

        return 0





def _load_suggestion_from_tg(tg) -> Dict[str, Any]:

    try:

        users = max(1, int(float(tg.num_threads or "1")))

    except ValueError:

        users = 1

    try:

        ramp = max(1, int(float(tg.ramp_time or "1")))

    except ValueError:

        ramp = 1

    spawn_rate = max(0.1, round(users / ramp, 2))

    run_time = jmeter_to_elia_text(tg.duration or "60")

    if "${" in (tg.duration or ""):

        run_time = "3600"

    profile = "load"

    if tg.on_sample_error == "stopthread":

        profile = "stress"

    return {

        "profile": profile,

        "users": users,

        "spawn_rate": spawn_rate,

        "run_time": run_time if run_time.isdigit() else f"{run_time}s" if run_time else "60s",

        "ramp_time_sec": ramp,

        "note": "Valores sugeridos desde Thread Group JMeter; ajústalos en Prueba de carga.",

    }





def _first_enabled_csv_basename(csv_refs: List[JmxCsvRef]) -> Optional[str]:

    for cs in csv_refs:

        if cs.enabled and cs.filename:

            return cs.filename

    return None





def _scores(

    http_count: int,

    extractor_count: int,

    jsr223_warnings: int,

    jmeter_func_warnings: int,

    total_nodes: int,

    *,

    groovy_translated: int = 0,

) -> Tuple[int, int]:

    if total_nodes <= 0:

        total_nodes = 1

    imported_nodes = http_count + extractor_count + max(0, len([]))

    structural = min(100, int(round((imported_nodes / total_nodes) * 100)))

    executability = max(5, 100 - jsr223_warnings * 12 - jmeter_func_warnings * 8 + groovy_translated * 6)

    executability = min(100, executability)

    if http_count == 0:

        executability = 0

        structural = 0

    return structural, executability





def build_jmx_import_report(

    data: bytes,

    *,

    source_name: str = "plan.jmx",

    thread_group_index: int = 0,

    include_disabled_controllers: bool = False,

) -> Tuple[JmxImportReport, List[ApiRequest], ParsedJmxPlan]:

    plan = parse_jmx_bytes(data, source_name=source_name)

    tg, samplers, skipped_raw = extract_thread_group_samplers(

        plan,

        thread_group_index,

        include_disabled_controllers=include_disabled_controllers,

    )



    thread_groups = [

        JmxThreadGroupInfo(

            index=tg_item.index,

            name=tg_item.name,

            enabled=tg_item.enabled,

            sampler_count=_count_samplers_in_group(

                plan,

                tg_item.index,

                include_disabled_controllers=include_disabled_controllers,

            ),

        )

        for tg_item in plan.thread_groups

    ]



    variables = {a.name: jmeter_to_elia_text(a.value) for a in plan.arguments}

    csv_refs = [

        JmxCsvRef(

            filename=cs.filename,

            variable_names=cs.variable_names,

            enabled=cs.enabled,

            delimiter=cs.delimiter,

        )

        for cs in plan.csv_datasets

    ]



    report = JmxImportReport(

        source_file=source_name,

        thread_group_index=thread_group_index,

        thread_group_name=tg.name,

        thread_groups=thread_groups,

        imported_variables=variables,

        csv_refs=csv_refs,

        load_suggestion=_load_suggestion_from_tg(tg),

        continue_on_failure=tg.on_sample_error != "stopthread",

        suggested_csv=_first_enabled_csv_basename(csv_refs),

        include_disabled_controllers=include_disabled_controllers,

    )



    requests: List[ApiRequest] = []

    jsr223_count = 0

    groovy_stub_count = 0

    groovy_translated_count = 0

    func_count = 0

    extractor_total = 0

    seen_names: Dict[str, int] = {}



    for idx, sampler in enumerate(samplers, start=1):

        display = sampler.name

        if display in seen_names:

            seen_names[display] += 1

            display = f"{idx:02d}-{display}"

        else:

            seen_names[display] = 1



        extractors: List[ApiExtractor] = []

        for ex in sampler.extractors:

            ref = ex.get("refname") or f"var_{len(extractors)+1}"

            regex = ex.get("regex") or ""

            if regex:

                extractors.append(ApiExtractor(kind="regex", expression=regex, target_var=ref))

                extractor_total += 1



        pre_script: Optional[str] = None

        post_script: Optional[str] = None

        if sampler.jsr223_pre or sampler.jsr223_post:

            translations = translate_groovy_scripts(display, sampler.jsr223_pre, sampler.jsr223_post)

            pre_script, post_script, groovy_extractors, overall, summary = merge_groovy_translations(translations)

            for ex in groovy_extractors:

                target = ex.get("target_var") or ""

                expr = ex.get("expression") or ""

                kind = ex.get("kind") or "jsonpath"

                if target and expr:

                    existing = {(e.target_var, e.expression) for e in extractors}

                    if (target, expr) not in existing:

                        extractors.append(ApiExtractor(kind=kind, expression=expr, target_var=target))

                        extractor_total += 1

            if overall == "translated":

                groovy_translated_count += 1

                report.groovy_translations.append(

                    JmxImportItem(kind="GroovyTranslated", element=display, sampler=display, message=summary)

                )

            elif overall == "stub":

                groovy_stub_count += 1

                jsr223_count += 1

                report.warnings.append(

                    JmxImportItem(kind="GroovyStub", element=display, sampler=display, message=summary)

                )

            else:

                jsr223_count += 1



        for kind, msg in sampler.warnings:

            if kind.startswith("JSR223") or kind.startswith("BeanShell"):

                if not (sampler.jsr223_pre or sampler.jsr223_post):

                    jsr223_count += 1

            if kind == "JMeterFunction":

                func_count += 1

            if kind not in ("JSR223PreProcessor", "JSR223PostProcessor", "BeanShellPreProcessor", "BeanShellPostProcessor"):

                report.warnings.append(JmxImportItem(kind=kind, element=kind, sampler=sampler.name, message=msg))



        req = ApiRequest(

            id=f"jmx-{uuid.uuid4().hex[:8]}",

            name=display,

            method=sampler.method,

            url=jmeter_to_elia_text(sampler.url),

            headers={k: jmeter_to_elia_text(v) for k, v in sampler.headers.items()},

            body=jmeter_to_elia_text(sampler.body) if sampler.body else None,

            extractors=extractors,

            pre_request_script=pre_script,

            post_request_script=post_script,

            source="jmx",

        )

        requests.append(req)

        report.scenario_names.append(display)

        report.imported.append(

            JmxImportItem(

                kind="HTTPSamplerProxy",

                element=display,

                sampler=display,

                message=f"{sampler.method} {req.url[:80]}",

            )

        )



    for kind, name, reason in skipped_raw:

        report.skipped.append(

            JmxImportItem(kind=kind, element=name, message=reason)

        )



    for cs in csv_refs:

        if cs.enabled and cs.filename:

            report.imported.append(

                JmxImportItem(

                    kind="CSVDataSet",

                    element=cs.filename,

                    message=f"Columnas: {', '.join(cs.variable_names[:6])}{'…' if len(cs.variable_names) > 6 else ''}",

                )

            )

        elif cs.filename:

            report.warnings.append(

                JmxImportItem(

                    kind="CSVDataSet",

                    element=cs.filename,

                    message="CSV referenciado pero deshabilitado en JMeter; actívalo o sube el archivo en Datos CSV.",

                )

            )



    for key, val in variables.items():

        report.imported.append(JmxImportItem(kind="Argument", element=key, message=val[:60]))



    report.imported_http = len(requests)

    report.imported_extractors = extractor_total

    total_nodes = len(requests) + len(report.skipped) + jsr223_count + groovy_stub_count + len(csv_refs)

    report.structural_coverage_pct, report.executability_pct = _scores(

        len(requests),

        extractor_total,

        jsr223_count,

        func_count,

        total_nodes,

        groovy_translated=groovy_translated_count,

    )



    if not requests:

        raise ValueError("No hay peticiones HTTP activas para importar en el Thread Group seleccionado")



    return report, requests, plan





def preview_jmx_import(

    data: bytes,

    *,

    source_name: str = "plan.jmx",

    thread_group_index: int = 0,

    include_disabled_controllers: bool = False,

) -> JmxImportReport:

    report, _, _ = build_jmx_import_report(

        data,

        source_name=source_name,

        thread_group_index=thread_group_index,

        include_disabled_controllers=include_disabled_controllers,

    )

    return report





def _create_suite_flow(

    project: str,

    *,

    flow_name: str,

    scenario_ids: List[str],

    continue_on_failure: bool,

    data_file: Optional[str],

) -> str:

    from core.api_automation.flow_store import save_flow



    nodes = [{"type": "request", "scenario_id": sid} for sid in scenario_ids]

    flow = ApiFlow(

        name=flow_name,

        nodes=nodes,

        continue_on_failure=continue_on_failure,

        data_file=data_file,

    )

    safe_stem = re.sub(r'[<>:"/\\|?*]+', "-", flow_name).strip() or "Suite JMX"

    return save_flow(project, flow, flow_id=f"{safe_stem}.json")





def commit_jmx_import(

    project: str,

    data: bytes,

    *,

    source_name: str = "plan.jmx",

    thread_group_index: int = 0,

    include_disabled_controllers: bool = False,

) -> Dict[str, Any]:

    from core.api_automation.project_config import load_environment, load_project_config, save_environment

    from core.api_automation.traffic_store import ensure_api_project, import_requests_as_collection



    report, requests, _ = build_jmx_import_report(

        data,

        source_name=source_name,

        thread_group_index=thread_group_index,

        include_disabled_controllers=include_disabled_controllers,

    )

    ensure_api_project(project)

    stem = os.path.splitext(os.path.basename(source_name))[0] or "plan"

    collection_name = f"Importado .jmx — {stem} ({report.thread_group_name})"

    imported = import_requests_as_collection(

        project,

        requests,

        collection_name=collection_name,

        source="jmx",

    )



    if report.imported_variables:

        cfg = load_project_config(project)

        env_name = cfg.get("default_environment") or "dev"

        try:

            env = load_environment(project, env_name)

        except FileNotFoundError:

            env = {"name": env_name, "variables": {}}

        merged = {**(env.get("variables") or {}), **report.imported_variables}

        save_environment(project, env_name, {"name": env_name, "variables": merged})



    jmx_dir = ensure_api_project(project) / "resources" / "jmeter"

    jmx_dir.mkdir(parents=True, exist_ok=True)

    safe_name = os.path.basename(source_name).replace("..", "").strip() or "plan.jmx"

    if not safe_name.lower().endswith(".jmx"):

        safe_name += ".jmx"

    (jmx_dir / safe_name).write_bytes(data)



    flow_name = f"Suite .jmx — {stem} ({report.thread_group_name})"

    flow_id = _create_suite_flow(

        project,

        flow_name=flow_name,

        scenario_ids=imported["scenario_ids"],

        continue_on_failure=report.continue_on_failure,

        data_file=report.suggested_csv,

    )



    meta_payload = {

        "source_file": source_name,

        "thread_group_index": thread_group_index,

        "thread_group_name": report.thread_group_name,

        "collection_id": imported["collection_id"],

        "collection_name": imported["collection_name"],

        "scenario_ids": imported["scenario_ids"],

        "flow_id": flow_id,

        "flow_name": flow_name,

        "load_suggestion": report.load_suggestion,

        "csv_basename": report.suggested_csv,

        "include_disabled_controllers": include_disabled_controllers,

        "jmx_path": str(jmx_dir / safe_name),

    }

    save_jmx_import_meta(project, meta_payload)



    return {

        "ok": True,

        "report": report.to_dict(),

        "collection_id": imported["collection_id"],

        "collection_name": imported["collection_name"],

        "scenario_ids": imported["scenario_ids"],

        "count": imported["count"],

        "variables_imported": len(report.imported_variables),

        "jmx_path": str(jmx_dir / safe_name),

        "load_suggestion": report.load_suggestion,

        "flow_id": flow_id,

        "flow_name": flow_name,

        "csv_basename": report.suggested_csv,

    }


