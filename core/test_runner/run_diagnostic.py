"""Diagnóstico estructurado tras una ejecución Behave/Locust (iniciativa P2)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_FAIL_SCENARIO_RE = re.compile(r"^\s*(features/[^\s]+\.feature):(\d+)\s+(.+)$")
_HOOK_ERROR_RE = re.compile(r"HOOK-ERROR in (\w+):\s*(.+)$")
_FAILED_SCENARIO_RE = re.compile(r"ERROR:.*Escenario FALLIDO:\s*(.+)$")
_RESULT_FAILED_RE = re.compile(r"Resultado:\s*FAILED", re.IGNORECASE)
_DIAGNOSTIC_ISSUE_RE = re.compile(
    r"(?:DIAGNOSTIC \| |WARNING: )Problema en diagnóstico(?: general)?:\s*(.+)$",
    re.IGNORECASE,
)
_STEP_FAILED_MARKER = "[Step] FALLIDO:"
_STEP_FAILED_FULL_RE = re.compile(
    r"^\s*(Given|When|Then|And)\s+(.+?)\s*-\s*(.+)$",
    re.IGNORECASE,
)
_GHERKIN_KEYWORDS = {"given": "Given", "when": "When", "then": "Then", "and": "And"}
_EXCEPTION_TYPE_RE = re.compile(r"^([A-Za-z_]+(?:Exception|Error))(?::|\s|$)")

# Historial local por proyecto: conservar como máximo las N ejecuciones más recientes.
RUN_HISTORY_MAX = 5


def _sanitize_filename(name: str) -> str:
    return (
        str(name)
        .replace(" ", "")
        .replace("/", "")
        .replace("\\", "")
        .replace(":", "")
        .replace("*", "")
        .replace("?", "")
    )


def _rel_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _extract_exception_type(message: Optional[str]) -> Optional[str]:
    if not message:
        return None
    text = str(message).strip()
    match = _EXCEPTION_TYPE_RE.match(text)
    if match:
        return match.group(1)
    if "Message:" in text:
        return _extract_exception_type(text.split("Message:", 1)[1].strip())
    return None


def _parse_step_failed_line(line: str) -> Optional[Dict[str, str]]:
    if _STEP_FAILED_MARKER not in line:
        return None
    part = line.split(_STEP_FAILED_MARKER, 1)[1].strip()
    match = _STEP_FAILED_FULL_RE.match(part)
    if match:
        keyword = _GHERKIN_KEYWORDS.get(match.group(1).lower(), match.group(1))
        step_text = match.group(2).strip()
        error = match.group(3).strip()
        return {
            "failed_step": f"{keyword} {step_text}",
            "failed_step_keyword": keyword,
            "failed_step_text": step_text,
            "step_error": error,
        }
    if " - " in part:
        left, error = part.split(" - ", 1)
        return {"failed_step": left.strip(), "step_error": error.strip()}
    return {"step_error": part}


def _list_recent_logs(root: Path, *, since_ts: float) -> List[Dict[str, Any]]:
    logs_dir = root / "outputs" / "logs"
    if not logs_dir.is_dir():
        return []
    items: List[Dict[str, Any]] = []
    for log_file in logs_dir.glob("*.txt"):
        try:
            mtime = log_file.stat().st_mtime
        except OSError:
            continue
        if mtime >= since_ts - 2.0:
            items.append(
                {
                    "name": log_file.name,
                    "path": _rel_path(root, log_file),
                    "modified_at": mtime,
                }
            )
    items.sort(key=lambda x: x["modified_at"], reverse=True)
    return items


def _list_recent_evidences(root: Path, *, since_ts: float) -> List[Dict[str, Any]]:
    evidence_root = root / "outputs" / "evidences"
    if not evidence_root.is_dir():
        return []
    items: List[Dict[str, Any]] = []
    for path in evidence_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".png", ".json"}:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= since_ts - 2.0:
            items.append(
                {
                    "name": path.name,
                    "path": _rel_path(root, path),
                    "kind": "screenshot" if path.suffix.lower() == ".png" else "json",
                    "modified_at": mtime,
                }
            )
    items.sort(key=lambda x: x["modified_at"], reverse=True)
    return items


def parse_behave_failures(lines: List[str]) -> List[Dict[str, Any]]:
    """Extrae escenarios fallidos y errores de hook a partir de la salida Behave."""
    hook_errors: List[Dict[str, str]] = []
    failing: List[Dict[str, Any]] = []
    failed_names: List[str] = []

    for line in lines:
        hook_match = _HOOK_ERROR_RE.search(line)
        if hook_match:
            hook_errors.append({"phase": hook_match.group(1), "message": hook_match.group(2).strip()})
            continue
        fail_match = _FAIL_SCENARIO_RE.match(line.strip())
        if fail_match:
            failing.append(
                {
                    "feature_file": fail_match.group(1),
                    "feature_line": int(fail_match.group(2)),
                    "scenario": fail_match.group(3).strip(),
                    "hook_error": None,
                    "step_error": None,
                }
            )
            continue
        failed_match = _FAILED_SCENARIO_RE.search(line)
        if failed_match:
            failed_names.append(failed_match.group(1).strip())

    if failing:
        if hook_errors and failing:
            failing[0]["hook_error"] = hook_errors[0]["message"]
        return failing

    if failed_names or hook_errors:
        scenario = failed_names[0] if failed_names else "Escenario"
        return [
            {
                "feature_file": "",
                "feature_line": None,
                "scenario": scenario,
                "hook_error": hook_errors[0]["message"] if hook_errors else None,
                "step_error": None,
            }
        ]
    return []


def _collect_failure_signals(lines: List[str]) -> Dict[str, Any]:
    step_errors: List[str] = []
    diagnostic_notes: List[str] = []
    failed_steps: List[Dict[str, str]] = []
    for line in lines:
        parsed = _parse_step_failed_line(line)
        if parsed:
            if parsed.get("step_error"):
                step_errors.append(parsed["step_error"])
            failed_steps.append(parsed)
        diag_match = _DIAGNOSTIC_ISSUE_RE.search(line)
        if diag_match:
            diagnostic_notes.append(diag_match.group(1).strip())
    return {
        "step_errors": step_errors,
        "diagnostic_notes": diagnostic_notes,
        "failed_steps": failed_steps,
    }


def _failure_reason(
    *,
    hook_error: Optional[str],
    step_error: Optional[str],
    diagnostic_notes: List[str],
) -> Optional[str]:
    if hook_error:
        return hook_error
    if step_error:
        return step_error
    if diagnostic_notes:
        return diagnostic_notes[-1]
    return None


def _apply_step_signals(failure: Dict[str, Any], signals: Dict[str, Any]) -> None:
    failed_steps = signals.get("failed_steps") or []
    if failed_steps:
        last = failed_steps[-1]
        if last.get("failed_step"):
            failure["failed_step"] = last["failed_step"]
        if last.get("failed_step_keyword"):
            failure["failed_step_keyword"] = last["failed_step_keyword"]
        if last.get("failed_step_text"):
            failure["failed_step_text"] = last["failed_step_text"]
    if signals["step_errors"]:
        failure["step_error"] = signals["step_errors"][-1]
        failure["exception_type"] = _extract_exception_type(failure["step_error"])
    if signals["diagnostic_notes"]:
        failure["diagnostic_notes"] = signals["diagnostic_notes"]
    failure["failure_reason"] = _failure_reason(
        hook_error=failure.get("hook_error"),
        step_error=failure.get("step_error"),
        diagnostic_notes=signals["diagnostic_notes"],
    )
    if not failure.get("exception_type"):
        failure["exception_type"] = _extract_exception_type(failure.get("failure_reason"))


def _enrich_failure(failure: Dict[str, Any], lines: List[str], log_path: Optional[Path] = None) -> None:
    signals = _collect_failure_signals(lines)
    if log_path and log_path.is_file():
        try:
            log_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            log_lines = []
        log_signals = _collect_failure_signals(log_lines)
        if log_signals["step_errors"] and not signals["step_errors"]:
            signals["step_errors"] = log_signals["step_errors"]
        if log_signals["failed_steps"] and not signals["failed_steps"]:
            signals["failed_steps"] = log_signals["failed_steps"]
        if log_signals["diagnostic_notes"]:
            signals["diagnostic_notes"].extend(log_signals["diagnostic_notes"])
    _apply_step_signals(failure, signals)


def _attach_screenshots(failure: Dict[str, Any], evidences: List[Dict[str, Any]]) -> None:
    related = [e for e in evidences if "FAIL_" in e.get("name", "")]
    failure["screenshots"] = related[:5]
    if related:
        failure["primary_screenshot"] = related[0]


def build_run_diagnostic(
    *,
    project_path: str,
    lines: List[str],
    since_ts: float,
    return_code: Optional[int],
    kind: str,
    run_id: Optional[str] = None,
    platform: str = "",
    project: str = "",
    finished_at: Optional[float] = None,
) -> Dict[str, Any]:
    root = Path(project_path)
    failures = parse_behave_failures(lines) if kind.startswith("behave") else []
    if kind.startswith("behave") and not failures:
        signals = _collect_failure_signals(lines)
        if signals["step_errors"] or signals["diagnostic_notes"] or signals["failed_steps"]:
            failure: Dict[str, Any] = {
                "feature_file": "",
                "feature_line": None,
                "scenario": "Escenario",
                "hook_error": None,
            }
            _apply_step_signals(failure, signals)
            failures = [failure]
    logs = _list_recent_logs(root, since_ts=since_ts)
    evidences = _list_recent_evidences(root, since_ts=since_ts)

    for failure in failures:
        scenario = str(failure.get("scenario") or "")
        log_name = f"{_sanitize_filename(scenario)}.txt"
        log_path = root / "outputs" / "logs" / log_name
        failure["log_path"] = f"outputs/logs/{log_name}" if log_name else ""
        failure["log_exists"] = log_path.is_file()
        _attach_screenshots(failure, evidences)
        _enrich_failure(failure, lines, log_path if log_path.is_file() else None)

    summary = "passed" if return_code == 0 else "failed"
    for line in reversed(lines):
        if _RESULT_FAILED_RE.search(line):
            summary = "failed"
            break

    diagnostic: Dict[str, Any] = {
        "ok": return_code == 0,
        "return_code": return_code,
        "kind": kind,
        "summary": summary,
        "failures": failures,
        "logs": logs,
        "evidences": evidences,
        "project_path": str(root.resolve()) if root.is_dir() else project_path,
        "run_id": run_id,
        "platform": platform,
        "project": project,
        "finished_at": finished_at or time.time(),
    }
    return diagnostic


def persist_run_manifest(project_path: str, run_id: str, diagnostic: Dict[str, Any]) -> Optional[Path]:
    """Guarda manifest local para historial del proyecto (base P4)."""
    if not project_path or not run_id:
        return None
    root = Path(project_path)
    out_dir = root / "outputs" / ".elia" / "runs"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = dict(diagnostic)
        payload["run_id"] = run_id
        out_path = out_dir / f"{run_id}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        prune_project_run_history(project_path, max_files=RUN_HISTORY_MAX)
        return out_path
    except OSError:
        return None


def prune_project_run_history(project_path: str, *, max_files: int | None = None) -> int:
    """Elimina manifests antiguos dejando solo las max_files ejecuciones más recientes."""
    cap = max_files if max_files is not None else RUN_HISTORY_MAX
    cap = max(1, min(cap, RUN_HISTORY_MAX))
    root = Path(project_path)
    hist_dir = root / "outputs" / ".elia" / "runs"
    if not hist_dir.is_dir():
        return 0
    files = sorted(hist_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for stale in files[cap:]:
        try:
            stale.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def list_project_run_history(project_path: str, *, limit: int | None = None) -> List[Dict[str, Any]]:
    cap = RUN_HISTORY_MAX if limit is None else max(1, min(limit, RUN_HISTORY_MAX))
    root = Path(project_path)
    hist_dir = root / "outputs" / ".elia" / "runs"
    if not hist_dir.is_dir():
        return []
    entries: List[Dict[str, Any]] = []
    files = sorted(hist_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files[:cap]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        failure = (data.get("failures") or [{}])[0] if data.get("failures") else {}
        entries.append(
            {
                "run_id": data.get("run_id") or path.stem,
                "finished_at": data.get("finished_at") or path.stat().st_mtime,
                "summary": data.get("summary") or ("passed" if data.get("ok") else "failed"),
                "kind": data.get("kind") or "",
                "scenario": failure.get("scenario") if isinstance(failure, dict) else None,
                "failure_reason": failure.get("failure_reason") if isinstance(failure, dict) else None,
                "failed_step": failure.get("failed_step") if isinstance(failure, dict) else None,
            }
        )
    return entries


def load_project_run_manifest(project_path: str, run_id: str) -> Optional[Dict[str, Any]]:
    root = Path(project_path)
    path = root / "outputs" / ".elia" / "runs" / f"{run_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None
