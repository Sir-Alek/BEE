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


def configure_execution_logging() -> Path:
    """Configura elia_execution.log bajo Documents/ELIA/logs (rotativo, idempotente)."""
    global _CONFIGURED
    log_path = execution_log_path()
    if _CONFIGURED:
        return log_path

    logs_dir().mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    has_file = any(
        isinstance(h, RotatingFileHandler)
        and getattr(h, "baseFilename", "").endswith("elia_execution.log")
        for h in root.handlers
    )
    if not has_file:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        root.addHandler(handler)

    _CONFIGURED = True
    logging.getLogger(__name__).info("ELIA execution logging initialized at %s", log_path)
    return log_path


def _tail_execution_log(max_lines: int = 40) -> str:
    path = execution_log_path()
    if not path.is_file():
        return "(no execution log yet)"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        return sanitize_text("\n".join(tail))
    except OSError:
        return "(could not read execution log)"


def _format_events(events: List[Dict[str, Any]], limit: int = 12) -> str:
    if not events:
        return "(no job events)"
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
ELIA BETA BUG REPORT - OFFLINE DIAGNOSTIC
======================================================================
App Version: {elia_version_display()} ({ELIA_VERSION})
Job ID: {job_id}
Module/Mode: {mode}
OS Platform: {os_label}
Python Version: {py_ver}
Log directory: ELIA://USER_DATA/logs/
----------------------------------------------------------------------
ERROR SUMMARY:
{msg_clean}
----------------------------------------------------------------------
STACK TRACE (SANITIZED):
{trace_clean or "(no stack trace captured)"}
----------------------------------------------------------------------
RECENT JOB EVENTS:
{_format_events(events or [])}
----------------------------------------------------------------------
EXECUTION LOG (TAIL):
{_tail_execution_log()}
----------------------------------------------------------------------
PRIVACY NOTICE (LOCAL-FIRST):
This report was sanitized locally. It does not include credentials,
connector tokens, or business prompts. Review before sharing outside
your organization.
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
    logging.getLogger(__name__).error(
        "Job %s failed (%s): %s", job_id[:8], mode, sanitize_text(error_msg)[:200]
    )
    return out_path


def load_job_error_report(job_id: str) -> Optional[str]:
    path = error_reports_dir() / f"{job_id}.txt"
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None
    return None


def beta_feedback_url() -> str:
    return (os.environ.get("ELIA_BETA_FEEDBACK_URL") or "").strip()
