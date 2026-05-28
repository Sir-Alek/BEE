"""Ejecución de subprocesos de prueba con streaming de logs."""
from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class RunState:
    run_id: str
    kind: str
    command: List[str]
    cwd: str
    state: str = "running"
    return_code: Optional[int] = None
    lines: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    error: Optional[str] = None
    platform: str = ""
    project: str = ""
    project_path: str = ""
    generate_evidence: bool = False
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "kind": self.kind,
            "state": self.state,
            "return_code": self.return_code,
            "lines": list(self.lines[-500:]),
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "platform": self.platform,
            "project": self.project,
            "project_path": self.project_path,
            "artifacts": list(self.artifacts),
            "meta": dict(self.meta),
        }


class TestRunnerService:
    def __init__(self) -> None:
        self._runs: Dict[str, RunState] = {}
        self._lock = threading.Lock()
        self._line_cond = threading.Condition(self._lock)

    def start(
        self,
        *,
        kind: str,
        command: List[str],
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        on_line: Optional[Callable[[str], None]] = None,
        platform: str = "",
        project: str = "",
        project_path: str = "",
        generate_evidence: bool = False,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        run = RunState(
            run_id=run_id,
            kind=kind,
            command=list(command),
            cwd=cwd,
            platform=platform,
            project=project,
            project_path=project_path or cwd,
            generate_evidence=generate_evidence,
            meta=dict(meta or {}),
        )
        with self._lock:
            self._runs[run_id] = run

        def _worker() -> None:
            try:
                proc = subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=env or os.environ.copy(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                assert proc.stdout is not None
                for raw in proc.stdout:
                    line = raw.rstrip("\n")
                    with self._line_cond:
                        run.lines.append(line)
                        self._line_cond.notify_all()
                    if on_line:
                        on_line(line)
                proc.wait()
                run.return_code = int(proc.returncode or 0)
                run.state = "done" if run.return_code == 0 else "error"
            except Exception as e:
                run.error = str(e)
                run.state = "error"
            finally:
                run.finished_at = time.time()
                if run.generate_evidence and run.project_path:
                    from core.test_runner.run_artifacts import collect_run_artifacts

                    run.artifacts = collect_run_artifacts(
                        project_path=run.project_path,
                        lines=run.lines,
                        since_ts=run.created_at,
                        generate_evidence=True,
                    )
                with self._line_cond:
                    self._line_cond.notify_all()

        threading.Thread(target=_worker, daemon=True).start()
        return run_id

    def get(self, run_id: str) -> Optional[RunState]:
        with self._lock:
            return self._runs.get(run_id)

    def wait_lines(self, run_id: str, since: int, timeout: float = 30.0) -> List[str]:
        deadline = time.time() + timeout
        with self._line_cond:
            while True:
                run = self._runs.get(run_id)
                if run is None:
                    return []
                if since < len(run.lines):
                    return run.lines[since:]
                if run.state != "running":
                    return run.lines[since:]
                remaining = deadline - time.time()
                if remaining <= 0:
                    return []
                self._line_cond.wait(timeout=min(1.0, remaining))


test_runner_service = TestRunnerService()
