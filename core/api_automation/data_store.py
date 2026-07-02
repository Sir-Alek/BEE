"""CSV data-driven bajo behave/api/{proyecto}/resources/data/."""
from __future__ import annotations

import csv
import io
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.api_automation.traffic_store import _project_root, ensure_api_project

MAX_DATA_FILE_BYTES = 10 * 1024 * 1024
MAX_CSV_ROWS = 50_000

_DATA_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-. ]{0,62}[A-Za-z0-9]$|^[A-Za-z0-9]$")


def data_dir(project: str) -> Path:
    root = ensure_api_project(project)
    d = root / "resources" / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_data_files(project: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for path in sorted(data_dir(project).glob("*.csv")):
        out.append({"name": path.name, "path": str(path)})
    return out


def _safe_csv_name(name: str) -> str:
    base = os.path.basename(name).strip()
    if not base.lower().endswith(".csv"):
        base += ".csv"
    if ".." in base or "/" in base or "\\" in base:
        raise ValueError("Nombre CSV no válido")
    stem = base[:-4] if base.lower().endswith(".csv") else base
    if stem and not _DATA_NAME_RE.match(stem):
        raise ValueError("Nombre CSV no válido: use letras, números, guiones o espacios")
    return base


def _normalize_upload_name(filename: str) -> Tuple[str, str]:
    """Devuelve (nombre_base, extensión) con ext .csv o .xlsx."""
    base = os.path.basename((filename or "").strip())
    if not base:
        raise ValueError("Nombre de archivo requerido")
    if ".." in base or "/" in base or "\\" in base:
        raise ValueError("Nombre de archivo no válido")
    lower = base.lower()
    if lower.endswith(".xlsx"):
        return base[: -5], ".xlsx"
    if lower.endswith(".csv"):
        return base[: -4], ".csv"
    return base, ".csv"


def read_csv_rows(project: str, filename: str) -> List[Dict[str, str]]:
    path = data_dir(project) / _safe_csv_name(filename)
    if not path.is_file():
        raise FileNotFoundError(filename)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = []
        for row in reader:
            rows.append({str(k): str(v or "") for k, v in row.items() if k})
        return rows


def read_csv_text(project: str, filename: str) -> str:
    path = data_dir(project) / _safe_csv_name(filename)
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path.read_text(encoding="utf-8")


def preview_csv(project: str, filename: str, *, limit: int = 5) -> Dict[str, Any]:
    rows = read_csv_rows(project, filename)
    columns = list(rows[0].keys()) if rows else []
    return {"name": _safe_csv_name(filename), "columns": columns, "rows": rows[:limit], "total": len(rows)}


def _validate_csv_text(content: str) -> List[Dict[str, str]]:
    text = (content or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ValueError("El archivo está vacío")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not any(str(h or "").strip() for h in reader.fieldnames):
        raise ValueError("El CSV debe incluir una fila de cabeceras")
    rows: List[Dict[str, str]] = []
    for row in reader:
        rows.append({str(k): str(v or "") for k, v in row.items() if k})
        if len(rows) > MAX_CSV_ROWS:
            raise ValueError(f"Máximo {MAX_CSV_ROWS} filas de datos por archivo")
    return rows


def _xlsx_bytes_to_csv_text(data: bytes) -> str:
    from io import BytesIO

    last_err: Optional[Exception] = None
    try:
        import openpyxl

        wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
        try:
            ws = wb.active
            if ws is None:
                raise ValueError("El libro Excel no tiene hojas")
            buf = io.StringIO()
            writer: Optional[csv.writer] = None
            for row in ws.iter_rows(values_only=True):
                values = ["" if cell is None else str(cell) for cell in row]
                if writer is None:
                    writer = csv.writer(buf, lineterminator="\n")
                writer.writerow(values)
            text = buf.getvalue()
            if not text.strip():
                raise ValueError("La hoja Excel está vacía")
            return text
        finally:
            wb.close()
    except ImportError as e:
        last_err = e
    except Exception as e:
        last_err = e

    try:
        import pandas as pd

        df = pd.read_excel(BytesIO(data), sheet_name=0, dtype=str)
        df = df.fillna("")
        if df.empty:
            raise ValueError("La hoja Excel está vacía")
        return df.to_csv(index=False, lineterminator="\n")
    except ImportError as e:
        raise ValueError(
            "No se pudo leer Excel: instale openpyxl o pandas en el entorno ELIA"
        ) from (last_err or e)
    except Exception as e:
        raise ValueError(f"No se pudo convertir Excel a CSV: {e}") from e


def save_csv_content(project: str, filename: str, content: str) -> str:
    _validate_csv_text(content)
    path = data_dir(project) / _safe_csv_name(filename)
    path.write_text(content.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")
    return str(path)


def import_data_file(
    project: str,
    filename: str,
    data: bytes,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]:
    if len(data) > MAX_DATA_FILE_BYTES:
        raise ValueError(f"Archivo demasiado grande (máx. {MAX_DATA_FILE_BYTES // (1024 * 1024)} MB)")
    _stem, ext = _normalize_upload_name(filename)
    source_format = "csv"
    if ext == ".xlsx":
        csv_content = _xlsx_bytes_to_csv_text(data)
        out_name = _safe_csv_name(f"{_stem}.csv")
        source_format = "xlsx"
    else:
        try:
            csv_content = data.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise ValueError("El CSV debe estar en UTF-8") from e
        out_name = _safe_csv_name(f"{_stem}.csv")

    _validate_csv_text(csv_content)
    dest = data_dir(project) / out_name
    if dest.exists() and not overwrite:
        raise FileExistsError(out_name)

    dest.write_text(csv_content.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")
    preview = preview_csv(project, out_name)
    return {
        "ok": True,
        "path": str(dest),
        "name": out_name,
        "source_format": source_format,
        "converted_from_xlsx": source_format == "xlsx",
        "preview": preview,
    }
