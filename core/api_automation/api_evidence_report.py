"""Generación opt-in de evidencias PDF/JSON para el módulo API directo."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from core.api_automation.load_test_profiles import PROFILE_LABELS
from core.api_automation.traffic_store import ensure_api_project


def _profile_label(profile: str) -> str:
    pid = (profile or "load").strip().lower()
    return PROFILE_LABELS.get(pid, pid)


def _sla_lines(sla_result: Optional[Dict[str, Any]]) -> List[str]:
    if not sla_result or not sla_result.get("checks"):
        return []
    status = "PASS" if sla_result.get("ok") else "FAIL"
    lines = [f"SLA: {status}"]
    for check in sla_result.get("checks") or []:
        mark = "OK" if check.get("passed") else "FAIL"
        lines.append(
            f"  [{mark}] {check.get('metric')}: actual={check.get('actual')} "
            f"umbral={check.get('threshold')}"
        )
    return lines


def _stage_lines(stages: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not stages:
        return []
    return [
        f"  Escalón {idx + 1}: {st.get('duration', '?')}s → {st.get('users', '?')} usuarios "
        f"(spawn {st.get('spawn_rate', '?')})"
        for idx, st in enumerate(stages)
    ]


def _reports_dir(project: str) -> Path:
    root = ensure_api_project(project)
    out = root / "outputs" / "pdfReports"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _evidence_dir(project: str) -> Path:
    root = ensure_api_project(project)
    out = root / "outputs" / "evidences"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _safe_slug(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^\w\-]+", "_", (text or "api").strip())[:limit].strip("_")
    return slug or "api"


def _pdf_text(text: Any) -> str:
    """Normaliza texto para fuentes core Helvetica (latin-1)."""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def _split_long_tokens(text: str, max_len: int = 96) -> str:
    """Parte tokens largos (URL, HTML) para que multi_cell respete el ancho."""
    lines: List[str] = []
    for raw_line in str(text or "").splitlines() or [""]:
        if len(raw_line) <= max_len:
            lines.append(raw_line)
            continue
        chunks: List[str] = []
        buf = ""
        for ch in raw_line:
            buf += ch
            if len(buf) >= max_len:
                chunks.append(buf)
                buf = ""
        if buf:
            chunks.append(buf)
        lines.append("\n".join(chunks))
    return "\n".join(lines)


def _looks_like_html(body: str) -> bool:
    lowered = str(body or "").lstrip().lower()
    return lowered.startswith("<!doctype") or lowered.startswith("<html") or "<html" in lowered[:300]


def _format_body_for_pdf(body: Any, *, limit: int = 4000) -> str:
    """Cuerpo tal cual (JSON indentado si aplica), truncado para el PDF."""
    text = str(body or "").strip()
    if not text:
        return "(vacio)"
    try:
        parsed = json.loads(text)
        text = json.dumps(parsed, ensure_ascii=True, indent=2)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    if len(text) > limit:
        return f"{text[:limit]}\n... (truncado, {len(text)} caracteres totales)"
    return text


def _header_content_type(headers: Any) -> str:
    if not isinstance(headers, dict):
        return ""
    for key, value in headers.items():
        if str(key).lower() == "content-type":
            return str(value)
    return ""


class _ApiEvidencePdf(FPDF):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="C")

    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def write_wrapped(
        self,
        text: str,
        *,
        font: str = "Helvetica",
        style: str = "",
        size: int = 9,
        line_h: float = 5,
    ) -> None:
        self.set_x(self.l_margin)
        self.set_font(font, style, size)
        self.multi_cell(
            self.content_width,
            line_h,
            _pdf_text(_split_long_tokens(text)),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )


def write_request_evidence_json(project: str, payload: Dict[str, Any]) -> str:
    """Guarda evidencia JSON de una petición individual."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = _safe_slug(str(payload.get("name") or "request"))
    path = _evidence_dir(project) / f"ApiRequest_{name}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)


def write_request_evidence_pdf(project: str, payload: Dict[str, Any]) -> str:
    """Genera PDF de evidencia para una petición HTTP individual."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = _safe_slug(str(payload.get("name") or "request"))
    out_path = _reports_dir(project) / f"ApiRequest_{name}_{ts}.pdf"

    req = payload.get("request") or {}
    result = payload.get("result") or {}
    assertions = result.get("assertions") or []

    pdf = _ApiEvidencePdf()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "ELIA - Evidencia API", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _pdf_text(f"Proyecto: {project}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Entorno: {payload.get('environment', 'dev')}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Peticion", ln=True)
    pdf.write_wrapped(f"Metodo: {req.get('method', 'GET')}")
    pdf.write_wrapped(f"URL: {req.get('url', '')}")
    headers = req.get("headers") or {}
    if headers:
        pdf.write_wrapped("Headers: " + json.dumps(headers, ensure_ascii=True)[:1200])
    body = req.get("body")
    if body:
        pdf.write_wrapped("Body: " + str(body)[:1500])
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Respuesta", ln=True)
    status = result.get("status_code", "?")
    elapsed = result.get("elapsed_ms", "?")
    ok = result.get("ok", False)
    pdf.write_wrapped(f"Estado: {'OK' if ok else 'FALLO'} - HTTP {status} ({elapsed} ms)")
    resp_headers = result.get("headers") or {}
    if resp_headers:
        pdf.write_wrapped("Headers: " + json.dumps(resp_headers, ensure_ascii=True)[:1200])
    content_type = _header_content_type(resp_headers)
    if content_type:
        pdf.write_wrapped(f"Content-Type: {content_type}")
    if assertions:
        pdf.write_wrapped("Aserciones:")
        for item in assertions:
            mark = "OK" if item.get("passed") else "FAIL"
            pdf.write_wrapped(f"  [{mark}] {item.get('message', '')}")
    raw_body = str(result.get("body") or "")
    if _looks_like_html(raw_body):
        pdf.write_wrapped(
            "Nota: la respuesta es HTML (pagina web), no JSON de API. "
            "Compruebe que la URL apunte al endpoint REST y no a la UI de Swagger."
        )
    resp_body = _format_body_for_pdf(raw_body)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Cuerpo de respuesta:", ln=True)
    pdf.write_wrapped(resp_body, font="Courier", size=8, line_h=4)

    pdf.output(str(out_path))
    return str(out_path)


def write_load_test_evidence_pdf(
    project: str,
    *,
    lines: List[str],
    users: int = 0,
    run_time: str = "",
    host: str = "",
    scenario_count: int = 0,
) -> str:
    """Genera PDF consolidado a partir de la salida de Locust (opt-in al finalizar)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = _reports_dir(project) / f"ApiLoadTest_{ts}.pdf"

    summary_lines = _extract_locust_summary(lines)

    pdf = _ApiEvidencePdf()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "ELIA - Reporte de carga API", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _pdf_text(f"Proyecto: {project}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Usuarios: {users} | Duracion: {run_time} | Escenarios: {scenario_count}"), ln=True)
    if host:
        pdf.cell(0, 6, _pdf_text(f"Host: {host}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Resumen Locust", ln=True)
    pdf.set_font("Courier", "", 8)
    if summary_lines:
        for line in summary_lines[:40]:
            pdf.multi_cell(pdf.content_width, 4, _pdf_text(line[:120]))
    else:
        pdf.multi_cell(pdf.content_width, 4, "Sin metricas parseables. Ver consola de ejecucion.")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Salida (ultimas lineas):", ln=True)
    pdf.set_font("Courier", "", 7)
    tail = lines[-30:] if lines else ["(sin salida)"]
    for line in tail:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.content_width, 3, _pdf_text(line[:140]))

    pdf.output(str(out_path))
    return str(out_path)


def _metrics_summary(metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not metrics:
        return {}
    live = metrics.get("live") or {}
    csv_block = metrics.get("csv") or {}
    agg = csv_block.get("aggregated") or csv_block.get("summary") or {}
    return {
        "total_requests": live.get("total_requests") or agg.get("requests") or 0,
        "total_failures": live.get("total_failures") or agg.get("failures") or 0,
        "error_rate_pct": live.get("error_rate_pct") or 0,
        "current_rps": live.get("current_rps") or agg.get("rps") or 0,
        "avg_ms": live.get("avg_ms") or agg.get("avg_ms") or 0,
        "p50_ms": live.get("p50_ms") or agg.get("p50_ms") or 0,
        "p95_ms": live.get("p95_ms") or agg.get("p95_ms") or 0,
        "p99_ms": live.get("p99_ms") or agg.get("p99_ms") or 0,
        "endpoints": csv_block.get("endpoints") or live.get("endpoints") or [],
    }


def write_enriched_load_test_evidence_pdf(
    project: str,
    *,
    lines: List[str],
    metrics: Optional[Dict[str, Any]] = None,
    users: int = 0,
    run_time: str = "",
    host: str = "",
    scenario_count: int = 0,
    run_id: str = "",
    profile: str = "load",
    sla_result: Optional[Dict[str, Any]] = None,
    stages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """PDF enriquecido con percentiles (opt-in post-carga)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_slug = re.sub(r"[^a-z0-9]+", "_", (profile or "load").lower()).strip("_")
    out_path = _reports_dir(project) / f"ApiLoadTest_{profile_slug}_{ts}_enriched.pdf"
    summary = _metrics_summary(metrics)

    pdf = _ApiEvidencePdf()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "ELIA - Reporte de carga API (enriquecido)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _pdf_text(f"Proyecto: {project}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Tipo de prueba: {_profile_label(profile)}"), ln=True)
    if run_id:
        pdf.cell(0, 6, _pdf_text(f"Run ID: {run_id}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Usuarios: {users} | Duracion: {run_time} | Escenarios: {scenario_count}"), ln=True)
    if host:
        pdf.cell(0, 6, _pdf_text(f"Host: {host}"), ln=True)
    for line in _sla_lines(sla_result):
        pdf.cell(0, 5, _pdf_text(line), ln=True)
    if profile == "scalability" and stages:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Escalones de escalabilidad:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for line in _stage_lines(stages):
            pdf.cell(0, 5, _pdf_text(line), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Metricas agregadas", ln=True)
    pdf.set_font("Helvetica", "", 9)
    rows = [
        ("Peticiones", summary.get("total_requests", 0)),
        ("Fallos", summary.get("total_failures", 0)),
        ("Tasa error %", summary.get("error_rate_pct", 0)),
        ("RPS", summary.get("current_rps", 0)),
        ("Avg ms", summary.get("avg_ms", 0)),
        ("p50 ms", summary.get("p50_ms", 0)),
        ("p95 ms", summary.get("p95_ms", 0)),
        ("p99 ms", summary.get("p99_ms", 0)),
    ]
    for label, value in rows:
        pdf.cell(0, 5, _pdf_text(f"  {label}: {value}"), ln=True)

    endpoints = summary.get("endpoints") or []
    if endpoints:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Por endpoint (CSV):", ln=True)
        pdf.set_font("Courier", "", 7)
        for ep in endpoints[:15]:
            if str(ep.get("name", "")).lower() == "aggregated":
                continue
            pdf.multi_cell(
                pdf.content_width,
                3,
                _pdf_text(
                    f"{ep.get('name', '?')}: req={ep.get('requests', 0)} "
                    f"p95={ep.get('p95_ms', 0)}ms rps={ep.get('rps', 0)}"
                ),
            )

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Resumen consola Locust:", ln=True)
    pdf.set_font("Courier", "", 7)
    for line in _extract_locust_summary(lines)[:25]:
        pdf.multi_cell(pdf.content_width, 3, _pdf_text(line[:140]))

    pdf.output(str(out_path))
    return str(out_path)


def write_enriched_load_test_evidence_html(
    project: str,
    *,
    lines: List[str],
    metrics: Optional[Dict[str, Any]] = None,
    users: int = 0,
    run_time: str = "",
    host: str = "",
    scenario_count: int = 0,
    run_id: str = "",
    profile: str = "load",
    sla_result: Optional[Dict[str, Any]] = None,
    stages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """HTML enriquecido con percentiles (opt-in post-carga)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_slug = re.sub(r"[^a-z0-9]+", "_", (profile or "load").lower()).strip("_")
    out_path = _reports_dir(project) / f"ApiLoadTest_{profile_slug}_{ts}_enriched.html"
    summary = _metrics_summary(metrics)
    endpoints = summary.get("endpoints") or []
    endpoint_rows = ""
    for ep in endpoints[:20]:
        if str(ep.get("name", "")).lower() == "aggregated":
            continue
        endpoint_rows += (
            f"<tr><td>{ep.get('name', '')}</td><td>{ep.get('requests', 0)}</td>"
            f"<td>{ep.get('p50_ms', 0)}</td><td>{ep.get('p95_ms', 0)}</td>"
            f"<td>{ep.get('p99_ms', 0)}</td><td>{ep.get('rps', 0)}</td></tr>"
        )
    console = "<br>".join(_pdf_text(line) for line in _extract_locust_summary(lines)[:30])
    sla_html = ""
    if sla_result and sla_result.get("checks"):
        status = "PASS" if sla_result.get("ok") else "FAIL"
        color = "#1b7f3a" if sla_result.get("ok") else "#b00020"
        rows = "".join(
            f"<tr><td>{c.get('metric')}</td><td>{c.get('actual')}</td>"
            f"<td>{c.get('threshold')}</td><td>{'OK' if c.get('passed') else 'FAIL'}</td></tr>"
            for c in sla_result.get("checks") or []
        )
        sla_html = (
            f'<h2 style="color:{color}">SLA: {status}</h2>'
            f"<table><tr><th>Métrica</th><th>Actual</th><th>Umbral</th><th>Estado</th></tr>{rows}</table>"
        )
    stages_html = ""
    if profile == "scalability" and stages:
        stage_rows = "".join(
            f"<tr><td>{idx + 1}</td><td>{st.get('duration', '')}</td>"
            f"<td>{st.get('users', '')}</td><td>{st.get('spawn_rate', '')}</td></tr>"
            for idx, st in enumerate(stages)
        )
        stages_html = (
            "<h2>Escalones de escalabilidad</h2>"
            "<table><tr><th>#</th><th>Duración (s)</th><th>Usuarios</th><th>Spawn rate</th></tr>"
            f"{stage_rows}</table>"
        )
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>ELIA Carga API</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}}
table{{border-collapse:collapse;width:100%;margin:12px 0}}
th,td{{border:1px solid #ccc;padding:6px 8px;text-align:left;font-size:13px}}
th{{background:#f4f4f4}}
.metric{{display:inline-block;margin:6px 12px 6px 0;padding:8px 12px;background:#f8f8f8;border-radius:8px}}
pre{{background:#111;color:#eee;padding:12px;border-radius:8px;font-size:12px;overflow:auto}}
</style></head><body>
<h1>ELIA — Reporte de carga API</h1>
<p><b>Proyecto:</b> {project} | <b>Tipo:</b> {_profile_label(profile)} | <b>Run:</b> {run_id or 'n/a'} | <b>Fecha:</b> {datetime.now():%Y-%m-%d %H:%M:%S}</p>
<p>Usuarios: {users} | Duración: {run_time} | Escenarios: {scenario_count} | Host: {host or 'n/a'}</p>
{sla_html}
{stages_html}
<div>
<span class="metric">Req: {summary.get('total_requests', 0)}</span>
<span class="metric">Fallos: {summary.get('total_failures', 0)}</span>
<span class="metric">Error %: {summary.get('error_rate_pct', 0)}</span>
<span class="metric">RPS: {summary.get('current_rps', 0)}</span>
<span class="metric">p50: {summary.get('p50_ms', 0)} ms</span>
<span class="metric">p95: {summary.get('p95_ms', 0)} ms</span>
<span class="metric">p99: {summary.get('p99_ms', 0)} ms</span>
</div>
<h2>Por endpoint</h2>
<table><tr><th>Nombre</th><th>Req</th><th>p50</th><th>p95</th><th>p99</th><th>RPS</th></tr>{endpoint_rows or '<tr><td colspan="6">Sin CSV</td></tr>'}</table>
<h2>Consola Locust</h2>
<pre>{console or 'Sin salida parseable'}</pre>
</body></html>"""
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def write_suite_evidence_json(project: str, payload: Dict[str, Any]) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = _safe_slug(str(payload.get("name") or "suite"))
    path = _evidence_dir(project) / f"ApiSuite_{name}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)


def write_suite_evidence_pdf(project: str, payload: Dict[str, Any]) -> str:
    """PDF consolidado de suite funcional (opt-in)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = _safe_slug(str(payload.get("name") or "suite"))
    out_path = _reports_dir(project) / f"ApiSuite_{name}_{ts}.pdf"
    suite = payload.get("suite") or {}
    runs = suite.get("runs") or []

    pdf = _ApiEvidencePdf()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "ELIA - Evidencia suite API", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _pdf_text(f"Proyecto: {project}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Entorno: {payload.get('environment', 'dev')}"), ln=True)
    pdf.cell(0, 6, _pdf_text("Formato: evidencia suite funcional (auditoría ELIA)"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
    pdf.cell(0, 6, _pdf_text(
        f"Resultado: {'OK' if suite.get('ok') else 'FALLOS'} — "
        f"{suite.get('passed_steps', 0)} OK / {suite.get('failed_steps', 0)} fallos"
    ), ln=True)
    pdf.ln(4)

    for run_idx, run in enumerate(runs):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, _pdf_text(f"Iteracion {run_idx + 1}"), ln=True)
        pdf.set_font("Helvetica", "", 9)
        for step in run.get("steps") or []:
            mark = "OK" if step.get("ok") else "FAIL"
            result = step.get("result") or {}
            pdf.multi_cell(
                pdf.content_width,
                5,
                _pdf_text(
                    f"[{mark}] {step.get('name', '?')} — HTTP {result.get('status_code', '?')} "
                    f"({result.get('elapsed_ms', '?')} ms)"
                ),
            )
    pdf.output(str(out_path))
    return str(out_path)


def _extract_locust_summary(lines: List[str]) -> List[str]:
    """Extrae líneas de tabla/resumen típicas de Locust headless."""
    out: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if (
            "aggregated" in lower
            or stripped.startswith("|")
            or "req/s" in lower
            or "failures" in lower
            or "percentile" in lower
            or "total" in lower and "requests" in lower
        ):
            out.append(stripped)
    return out
