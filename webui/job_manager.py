from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Respuesta especial del UI para volver al paso anterior del flujo de prompts.
PROMPT_ANSWER_BACK = "__elia_back__"


class JobCancelledError(Exception):
    pass


@dataclass
class Prompt:
    prompt_id: str
    type: str
    title: str
    message: str
    # Optional structured fields (bdd preview, etc.)
    payload: Optional[Dict[str, Any]] = None
    # message_ack: info | warning | error (modal OK, like Tk messagebox)
    severity: str = "info"
    # UI payload
    options: Optional[List[Dict[str, str]]] = None  # [{value,label}]
    actions: Optional[List[Dict[str, Any]]] = None  # [{type, description, original_line}]
    # Response
    status: str = "pending"  # pending | answered | dismissed | cancelled
    answer: Any = None
    created_at: float = field(default_factory=time.time)
    answered_at: Optional[float] = None


@dataclass
class JobState:
    job_id: str
    mode: str
    state: str = "queued"  # queued | running | waiting_user | done | error | cancelled
    progress: Dict[str, Any] = field(default_factory=dict)
    active_prompt: Optional[Prompt] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # Synchronization primitive for waiting user prompts
    lock: threading.Lock = field(default_factory=threading.Lock)
    cond: threading.Condition = field(init=False)

    def __post_init__(self) -> None:
        self.cond = threading.Condition(self.lock)


class JobManager:
    """
    Job/prompt coordinator intended for "one prompt at a time".

    Design:
    - The core runs in a worker thread.
    - When it needs UI input, it calls WebUIAdapter -> create_prompt_and_wait.
    - create_prompt_and_wait blocks until answer_prompt is called by the API/UI.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, JobState] = {}
        self._global_lock = threading.Lock()

    def create_job(self, *, mode: str) -> str:
        job_id = str(uuid.uuid4())
        job = JobState(job_id=job_id, mode=mode, state="running")
        job.events.append({"type": "job_started", "ts": time.time()})
        with self._global_lock:
            self._jobs[job_id] = job
        try:
            from webui.error_reporting import log_execution

            log_execution("job_started", job_id=job_id, mode=mode)
        except Exception:
            pass
        return job_id

    def get_job(self, job_id: str) -> JobState:
        with self._global_lock:
            return self._jobs[job_id]

    def cancel_job(self, job_id: str) -> None:
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return
        with job.lock:
            job.state = "cancelled"
            job.updated_at = time.time()
            if job.active_prompt and job.active_prompt.status == "pending":
                job.active_prompt.status = "cancelled"
                job.active_prompt.answered_at = time.time()
            job.cond.notify_all()

        self._emit_event(job_id, {"type": "job_cancelled"})
        try:
            from webui.error_reporting import log_execution

            log_execution("job_cancelled", job_id=job_id, mode=job.mode)
        except Exception:
            pass

    def _emit_event(self, job_id: str, event: Dict[str, Any]) -> None:
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return
        with job.lock:
            event = {"ts": time.time(), **event}
            job.events.append(event)
            job.updated_at = time.time()

    def add_event(self, job_id: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self._emit_event(job_id, {"type": event_type, "payload": payload or {}})

    def create_prompt_and_wait(self, job_id: str, *, prompt: Prompt) -> Any:
        """
        Registers `prompt` as active and blocks until answered.
        Returns prompt.answer (can be bool/None/string/list... depending on prompt.type).
        """
        with self._global_lock:
            job = self._jobs[job_id]

        with job.lock:
            if job.state in ("done", "error", "cancelled"):
                raise JobCancelledError(f"Job {job_id} is in state {job.state}")
            if job.active_prompt and job.active_prompt.status == "pending":
                # one-at-a-time enforced
                raise RuntimeError(f"Job {job_id} already has a pending prompt")

            job.active_prompt = prompt
            job.state = "waiting_user"
            job.updated_at = time.time()
            # Avoid calling _emit_event() while holding job.lock to prevent deadlocks.
            job.events.append(
                {
                    "ts": time.time(),
                    "type": "prompt_created",
                    "prompt_id": prompt.prompt_id,
                    "prompt_type": prompt.type,
                }
            )

            # Wait until prompt gets answered/cancelled/dismissed
            while job.active_prompt is not None and job.active_prompt.status in ("pending",):
                job.cond.wait(timeout=0.25)

            if job.state == "cancelled" or (job.active_prompt and job.active_prompt.status == "cancelled"):
                raise JobCancelledError(f"Job {job_id} cancelled while waiting for prompt {prompt.prompt_id}")

            # By spec: answered or dismissed
            if job.active_prompt is None:
                # Shouldn't happen in one-at-a-time, but guard anyway.
                raise RuntimeError(f"Job {job_id} active prompt disappeared")

            return job.active_prompt.answer

    def answer_prompt(self, job_id: str, *, prompt_id: str, answer: Any) -> None:
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return

        with job.lock:
            if job.active_prompt is None or job.active_prompt.prompt_id != prompt_id:
                # stale prompt_id or out-of-order response; ignore
                return
            if job.active_prompt.status != "pending":
                return

            job.active_prompt.answer = answer
            job.active_prompt.status = "answered"
            job.active_prompt.answered_at = time.time()
            job.state = "running"
            job.updated_at = time.time()
            job.cond.notify_all()

        self._emit_event(job_id, {"type": "prompt_answered", "prompt_id": prompt_id})

    def dismiss_prompt(self, job_id: str, *, prompt_id: str) -> None:
        """
        Optional: treat a dismissed UI as cancellation for that prompt.
        """
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return

        with job.lock:
            if job.active_prompt is None or job.active_prompt.prompt_id != prompt_id:
                return
            if job.active_prompt.status != "pending":
                return
            job.active_prompt.status = "dismissed"
            job.active_prompt.answer = None
            job.active_prompt.answered_at = time.time()
            job.state = "running"
            job.updated_at = time.time()
            job.cond.notify_all()

        self._emit_event(job_id, {"type": "prompt_dismissed", "prompt_id": prompt_id})

    def mark_done(self, job_id: str) -> None:
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return
        with job.lock:
            job.state = "done"
            job.updated_at = time.time()
            if job.active_prompt and job.active_prompt.status == "pending":
                job.active_prompt.status = "answered"
                job.active_prompt.answer = job.active_prompt.answer
            job.cond.notify_all()
        self._emit_event(job_id, {"type": "job_done"})

        try:
            from webui.error_reporting import log_execution

            log_execution("job_done", job_id=job_id, mode=job.mode)
        except Exception:
            pass

    def mark_error(self, job_id: str, *, message: str, details: Optional[str] = None) -> None:
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return
        with job.lock:
            job.state = "error"
            job.updated_at = time.time()
            job.error = {"message": message, "details": details}
            if job.active_prompt and job.active_prompt.status == "pending":
                job.active_prompt.status = "cancelled"
                job.active_prompt.answer = None
                job.active_prompt.answered_at = time.time()
            job.cond.notify_all()
            mode = job.mode
            events_snapshot = list(job.events)
        self._emit_event(job_id, {"type": "job_error", "message": message})
        try:
            from webui.error_reporting import persist_job_error_snapshot

            persist_job_error_snapshot(
                job_id=job_id,
                mode=mode,
                error_msg=message,
                traceback_str=details,
                events=events_snapshot,
            )
        except Exception:
            pass

    def update_progress(self, job_id: str, progress: Dict[str, Any]) -> None:
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return

        with job.lock:
            job.progress = {**job.progress, **progress}
            job.updated_at = time.time()
        # No emit_event here: polling reads job.progress directly.

    def request_recording_stop(self, job_id: str) -> None:
        """Señal desde la UI para finalizar grabación móvil/legacy sin cancelar el job."""
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return
        with job.lock:
            job.progress = {**job.progress, "stop_requested": True}
            job.updated_at = time.time()

    def should_stop_recording(self, job_id: str) -> bool:
        with self._global_lock:
            job = self._jobs.get(job_id)
        if not job:
            return True
        with job.lock:
            if job.state == "cancelled":
                return True
            return bool(job.progress.get("stop_requested"))

    def get_job_summary(self, job_id: str) -> Dict[str, Any]:
        job = self.get_job(job_id)
        with job.lock:
            prompt = job.active_prompt
            if prompt is None or prompt.status != "pending":
                active_prompt = None
            else:
                active_prompt = {
                    "prompt_id": prompt.prompt_id,
                    "type": prompt.type,
                    "title": prompt.title,
                    "message": prompt.message,
                    "payload": getattr(prompt, "payload", None),
                    "severity": getattr(prompt, "severity", "info") or "info",
                    "options": prompt.options,
                    "actions": prompt.actions,
                }

            error_out = None
            if job.error:
                error_out = {"message": job.error.get("message", "Unknown error")}

            return {
                "job_id": job.job_id,
                "mode": job.mode,
                "state": job.state,
                "progress": job.progress,
                "error": error_out,
                "active_prompt": active_prompt,
                "events_count": len(job.events),
            }

    def get_job_events(
        self,
        job_id: str,
        *,
        limit: int = 200,
        since: int = 0,
    ) -> Dict[str, Any]:
        job = self.get_job(job_id)
        with job.lock:
            start = max(0, since)
            chunk = list(job.events[start : start + limit])
            return {
                "events": chunk,
                "next_index": start + len(chunk),
                "total": len(job.events),
            }

