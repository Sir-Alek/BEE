"""Reporte de errores offline-first: logging local, sanitización y exportación."""
from __future__ import annotations

import logging
import os
import platform
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.elia_paths import error_reports_dir, execution_log_path, logs_dir

_CONFIGURED = False
EXECUTION_LOGGER_NAME = "elia.execution"

# Rotación por defecto: 5 MB × 4 archivos (activo + 3 backups) ≈ 20 MB máximo.
_DEFAULT_MAX_MB = 5
_DEFAULT_BACKUPS = 3
_DEFAULT_ERROR_REPORTS_MAX = 50
_DEFAULT_LOG_LEVEL = logging.INFO

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


def _rotation_limits() -> tuple[int, int]:
    max_bytes = _env_int("ELIA_EXEC_LOG_MAX_MB", _DEFAULT_MAX_MB, lo=1, hi=50) * 1024 * 1024
    backup_count = _env_int("ELIA_EXEC_LOG_BACKUPS", _DEFAULT_BACKUPS, lo=1, hi=10)
    return max_bytes, backup_count


def execution_log_retention_label() -> str:
    max_mb = _env_int("ELIA_EXEC_LOG_MAX_MB", _DEFAULT_MAX_MB, lo=1, hi=50)
    backups = _env_int("ELIA_EXEC_LOG_BACKUPS", _DEFAULT_BACKUPS, lo=1, hi=10)
    return f"rotación ~{max_mb} MB × {backups + 1} archivos (máx. ~{max_mb * (backups + 1)} MB)"


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


def configure_execution_logging() -> Path:
    """Configura elia_execution.log bajo Documents/ELIA/logs (rotativo, idempotente)."""
    global _CONFIGURED
    log_path = execution_log_path()
    logger = logging.getLogger(EXECUTION_LOGGER_NAME)
    logger.setLevel(_execution_log_level())
    logger.propagate = False

    logs_dir().mkdir(parents=True, exist_ok=True)
    max_bytes, backup_count = _rotation_limits()

    has_rotating = any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
    if not has_rotating:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)

    if not _CONFIGURED:
        max_mb = max_bytes // (1024 * 1024)
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
