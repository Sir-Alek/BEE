"""Generación opt-in de evidencias PDF/JSON para el módulo API directo."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from core.api_automation.traffic_store import ensure_api_project


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


class _ApiEvidencePdf(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="C")

    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin


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
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(pdf.content_width, 5, _pdf_text(f"Metodo: {req.get('method', 'GET')}"))
    pdf.multi_cell(pdf.content_width, 5, _pdf_text(f"URL: {req.get('url', '')}"))
    headers = req.get("headers") or {}
    if headers:
        pdf.multi_cell(pdf.content_width, 5, _pdf_text("Headers: " + json.dumps(headers, ensure_ascii=True)[:1200]))
    body = req.get("body")
    if body:
        pdf.multi_cell(pdf.content_width, 5, _pdf_text("Body: " + str(body)[:1500]))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Respuesta", ln=True)
    pdf.set_font("Helvetica", "", 9)
    status = result.get("status_code", "?")
    elapsed = result.get("elapsed_ms", "?")
    ok = result.get("ok", False)
    pdf.multi_cell(pdf.content_width, 5, _pdf_text(f"Estado: {'OK' if ok else 'FALLO'} - HTTP {status} ({elapsed} ms)"))
    if assertions:
        pdf.multi_cell(pdf.content_width, 5, "Aserciones:")
        for item in assertions:
            mark = "OK" if item.get("passed") else "FAIL"
            pdf.multi_cell(pdf.content_width, 5, _pdf_text(f"  [{mark}] {item.get('message', '')}"))
    resp_body = str(result.get("body") or "")[:4000]
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Cuerpo de respuesta (truncado):", ln=True)
    pdf.set_font("Courier", "", 8)
    pdf.multi_cell(pdf.content_width, 4, _pdf_text(resp_body or "(vacio)"))

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
) -> str:
    """PDF enriquecido con percentiles (opt-in post-carga)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = _reports_dir(project) / f"ApiLoadTest_{ts}_enriched.pdf"
    summary = _metrics_summary(metrics)

    pdf = _ApiEvidencePdf()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "ELIA - Reporte de carga API (enriquecido)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _pdf_text(f"Proyecto: {project}"), ln=True)
    if run_id:
        pdf.cell(0, 6, _pdf_text(f"Run ID: {run_id}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True)
    pdf.cell(0, 6, _pdf_text(f"Usuarios: {users} | Duracion: {run_time} | Escenarios: {scenario_count}"), ln=True)
    if host:
        pdf.cell(0, 6, _pdf_text(f"Host: {host}"), ln=True)
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
) -> str:
    """HTML enriquecido con percentiles (opt-in post-carga)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = _reports_dir(project) / f"ApiLoadTest_{ts}_enriched.html"
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
<p><b>Proyecto:</b> {project} | <b>Run:</b> {run_id or 'n/a'} | <b>Fecha:</b> {datetime.now():%Y-%m-%d %H:%M:%S}</p>
<p>Usuarios: {users} | Duración: {run_time} | Escenarios: {scenario_count} | Host: {host or 'n/a'}</p>
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
