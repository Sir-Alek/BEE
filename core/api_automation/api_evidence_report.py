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
