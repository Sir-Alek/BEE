"""Reporte de errores offline-first: logging local, sanitización y exportación."""
from __future__ import annotations

import logging
import os
import platform
import re
import sys
import time
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.elia_paths import error_reports_dir, execution_log_path, logs_dir

_CONFIGURED = False
EXECUTION_LOGGER_NAME = "elia.execution"
FOLDER_OPEN_HINT = (
    "Si no ves la ventana del explorador de archivos, revísala en la barra de tareas."
)

# Rotación diaria; conservar como máximo 7 días de historial.
_DEFAULT_RETENTION_DAYS = 7
_DEFAULT_ERROR_REPORTS_MAX = 50
_DEFAULT_LOG_LEVEL = logging.INFO
_LOG_TS_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

# Patrones de redacción (Infosec / local-first). Orden importa.
_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer ***REDACTED***"),
    (
        re.compile(r"(?i)(password|passwd|token|api[_-]?key|secret|authorization)\s*[:=]\s*\S+"),
        r"\1=***REDACTED***",
    ),
    (re.compile(r"(?:[cC]:[\\/][uU]sers|[hH]ome)[\\/][^\"'\s]+", re.IGNORECASE), "ELIA://USER_HOME"),
    (re.compile(r"[cC]:[\\/][^\"'\s]+"), "ELIA://PATH"),
    (
        re.compile(r"(?i)(jira|valueedge|value_edge)[^\s]*\s+(password|token|api_key)\s*[:=]\s*\S+"),
        r"\1 \2=***REDACTED***",
    ),
]


def sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    out = text
    for pattern, repl in _REDACTIONS:
        out = pattern.sub(repl, out)
    return out


def _env_int(name: str, default: int, *, lo: int, hi: int) -> int:
    try:
        value = int((os.environ.get(name) or "").strip() or default)
    except ValueError:
        value = default
    return max(lo, min(value, hi))


def _retention_days() -> int:
    return _env_int("ELIA_EXEC_LOG_MAX_DAYS", _DEFAULT_RETENTION_DAYS, lo=1, hi=90)


def execution_log_retention_label() -> str:
    days = _retention_days()
    return f"rotación diaria, conservando como máximo {days} días"


def execution_log_about_hint() -> str:
    """Texto breve para Acerca de: ruta del log y para qué sirve."""
    return (
        "Registro local de diagnóstico y errores: "
        "Documents/ELIA/logs/"
    )


def _execution_log_level() -> int:
    raw = (os.environ.get("ELIA_EXEC_LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, raw, None)
    if isinstance(level, int):
        return level
    return _DEFAULT_LOG_LEVEL


def log_execution(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Registro estructurado en elia_execution.log (sanitizado, sin secretos)."""
    configure_execution_logging()
    logger = get_execution_logger()
    if not logger.isEnabledFor(level):
        return
    parts = [f"[{event}]"]
    for key in sorted(fields):
        value = fields[key]
        if value is None or value == "":
            continue
        safe = sanitize_text(str(value))
        if len(safe) > 500:
            safe = safe[:497] + "..."
        parts.append(f"{key}={safe}")
    logger.log(level, " ".join(parts))


def get_execution_logger() -> logging.Logger:
    """Logger dedicado a ELIA; no captura uvicorn/fastapi en el archivo."""
    configure_execution_logging()
    return logging.getLogger(EXECUTION_LOGGER_NAME)


def prune_stale_execution_logs(*, max_age_days: int | None = None) -> int:
    """Elimina copias rotadas de elia_execution.log más antiguas que max_age_days."""
    max_age = max_age_days or _retention_days()
    cutoff = time.time() - max_age * 86400
    removed = 0
    for path in logs_dir().glob("elia_execution.log*"):
        if path.name == "elia_execution.log":
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def trim_execution_log_by_age(*, max_age_days: int | None = None) -> bool:
    """Recorta el log activo dejando solo entradas dentro del periodo de retención."""
    log_path = execution_log_path()
    if not log_path.is_file() or log_path.stat().st_size == 0:
        return False
    max_age = max_age_days or _retention_days()
    cutoff = datetime.now() - timedelta(days=max_age)
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    kept: list[str] = []
    for line in lines:
        match = _LOG_TS_PATTERN.match(line)
        if not match:
            kept.append(line)
            continue
        try:
            ts = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            kept.append(line)
            continue
        if ts >= cutoff:
            kept.append(line)
    if len(kept) == len(lines):
        return False
    try:
        log_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    except OSError:
        return False
    return True


def configure_execution_logging() -> Path:
    """Configura elia_execution.log bajo Documents/ELIA/logs (rotativo, idempotente)."""
    global _CONFIGURED
    log_path = execution_log_path()
    logger = logging.getLogger(EXECUTION_LOGGER_NAME)
    logger.setLevel(_execution_log_level())
    logger.propagate = False

    logs_dir().mkdir(parents=True, exist_ok=True)
    backup_count = _retention_days()

    has_timed = any(isinstance(h, TimedRotatingFileHandler) for h in logger.handlers)
    if not has_timed:
        handler = TimedRotatingFileHandler(
            log_path,
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)

    if not _CONFIGURED:
        prune_stale_execution_logs()
        trim_execution_log_by_age()
        logger.info(
            "Log de ejecución ELIA iniciado en ELIA://USER_DATA/logs/elia_execution.log "
            "(%s)",
            execution_log_retention_label(),
        )
        _CONFIGURED = True
    return log_path


def prune_error_reports(*, max_files: int | None = None) -> int:
    """Elimina snapshots antiguos en error_reports/ para acotar uso de disco."""
    if max_files is None:
        max_files = _env_int("ELIA_ERROR_REPORTS_MAX", _DEFAULT_ERROR_REPORTS_MAX, lo=5, hi=500)
    report_dir = error_reports_dir()
    if not report_dir.is_dir():
        return 0
    files = sorted(report_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for stale in files[max_files:]:
        try:
            stale.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def _tail_execution_log(max_lines: int = 40) -> str:
    path = execution_log_path()
    if not path.is_file():
        return "(aún no hay log de ejecución)"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        return sanitize_text("\n".join(tail))
    except OSError:
        return "(no se pudo leer el log de ejecución)"


def _format_events(events: List[Dict[str, Any]], limit: int = 12) -> str:
    if not events:
        return "(sin eventos del trabajo)"
    lines: list[str] = []
    for ev in events[-limit:]:
        et = ev.get("type", "event")
        payload = ev.get("payload") or {}
        safe_payload = sanitize_text(str({k: v for k, v in payload.items() if k not in ("feature_text", "script_excerpt")}))
        lines.append(f"- {et}: {safe_payload}" if safe_payload else f"- {et}")
    return "\n".join(lines)


def build_error_report(
    *,
    job_id: str,
    mode: str,
    error_msg: str,
    traceback_str: Optional[str] = None,
    events: Optional[List[Dict[str, Any]]] = None,
) -> str:
    from core._version import ELIA_VERSION, elia_version_display

    msg_clean = sanitize_text(error_msg)
    trace_clean = sanitize_text(traceback_str or "")
    py_ver = sys.version.split()[0]
    os_label = f"{platform.system()} {platform.release()}"

    report = f"""======================================================================
ELIA — REPORTE DE ERROR BETA (DIAGNÓSTICO LOCAL)
======================================================================
Versión: {elia_version_display()} ({ELIA_VERSION})
Job ID: {job_id}
Modo: {mode}
Sistema operativo: {os_label}
Python: {py_ver}
Directorio de logs: ELIA://USER_DATA/logs/ ({execution_log_retention_label()})
----------------------------------------------------------------------
RESUMEN DEL ERROR:
{msg_clean}
----------------------------------------------------------------------
TRAZA (SANITIZADA):
{trace_clean or "(no se capturó traza de pila)"}
----------------------------------------------------------------------
EVENTOS RECIENTES DEL TRABAJO:
{_format_events(events or [])}
----------------------------------------------------------------------
LOG DE EJECUCIÓN (ÚLTIMAS LÍNEAS):
{_tail_execution_log()}
----------------------------------------------------------------------
AVISO DE PRIVACIDAD (LOCAL-FIRST):
Este reporte ha sido sanitizado localmente. No incluye credenciales,
tokens de conectores ni prompts de negocio. Revísalo antes de
compartirlo fuera de tu organización.
======================================================================"""
    return report


def persist_job_error_snapshot(
    *,
    job_id: str,
    mode: str,
    error_msg: str,
    traceback_str: Optional[str] = None,
    events: Optional[List[Dict[str, Any]]] = None,
) -> Path:
    configure_execution_logging()
    content = build_error_report(
        job_id=job_id,
        mode=mode,
        error_msg=error_msg,
        traceback_str=traceback_str,
        events=events,
    )
    out_dir = error_reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{job_id}.txt"
    out_path.write_text(content, encoding="utf-8")
    log_execution(
        "job_error",
        level=logging.ERROR,
        job_id=job_id,
        mode=mode,
        message=error_msg,
    )
    prune_error_reports()
    return out_path


def open_logs_folder_in_os() -> Path:
    """Abre la carpeta de logs ELIA en el explorador del sistema."""
    import subprocess
    import sys

    configure_execution_logging()
    folder = logs_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = str(folder.resolve())
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)
    return folder


def load_job_error_report(job_id: str) -> Optional[str]:
    path = error_reports_dir() / f"{job_id}.txt"
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None
    return None


def beta_feedback_url() -> str:
    from core._version import ELIA_BETA_FEEDBACK_URL

    override = (os.environ.get("ELIA_BETA_FEEDBACK_URL") or "").strip()
    if override:
        return override
    return (ELIA_BETA_FEEDBACK_URL or "").strip()
