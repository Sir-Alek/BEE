"""
Shared helpers for ELIA FastAPI integration tests.

Pattern: lightweight Screenplay actors — each helper encapsulates one concern
(API transport, license fixtures, job polling) so test modules stay DRY.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, Optional, Tuple
from unittest.mock import patch

from fastapi.testclient import TestClient

from core import elia_license as lic
from webui.fastapi_app import create_app
from webui.job_manager import JobManager


class EliaApiActor:
    """HTTP actor: wraps TestClient with JSON helpers and dynamic job polling."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def get_json(self, path: str) -> Tuple[int, Dict[str, Any]]:
        res = self.client.get(path)
        return res.status_code, self._parse_json(res)

    def post_json(self, path: str, body: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
        res = self.client.post(path, json=body or {})
        return res.status_code, self._parse_json(res)

    def put_json(self, path: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        res = self.client.put(path, json=body)
        return res.status_code, self._parse_json(res)

    def upload_files(
        self, path: str, files: Iterable[Tuple[str, bytes, str]]
    ) -> Tuple[int, Dict[str, Any]]:
        """files: iterable of (field_name, content, filename)."""
        multipart = [("files", (filename, content)) for _, content, filename in files]
        res = self.client.post(path, files=multipart)
        return res.status_code, self._parse_json(res)

    def answer_prompt(self, job_id: str, prompt_id: str, answer: Any) -> Tuple[int, Dict[str, Any]]:
        return self.post_json(
            f"/api/jobs/{job_id}/prompts/{prompt_id}/response",
            {"answer": answer},
        )

    def answer_active_prompt(self, job_id: str, answer: Any) -> bool:
        """Responde el prompt pendiente del job, si existe. Devuelve True si respondió."""
        _, body = self.get_json(f"/api/jobs/{job_id}")
        prompt = body.get("active_prompt")
        if not prompt or not prompt.get("prompt_id"):
            return False
        self.answer_prompt(job_id, prompt["prompt_id"], answer)
        return True

    def wait_for_job(
        self,
        job_id: str,
        *,
        timeout: float = 15.0,
        poll_interval: float = 0.05,
        terminal_states: Tuple[str, ...] = ("done", "error", "cancelled"),
        auto_answer: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Poll GET /api/jobs/{id} until a terminal state or timeout.
        If auto_answer is set, responds to pending prompts (e.g. demo pick_project).
        """
        deadline = time.monotonic() + timeout
        last: Dict[str, Any] = {}
        while time.monotonic() < deadline:
            status, body = self.get_json(f"/api/jobs/{job_id}")
            if status == 200:
                last = body
                if body.get("state") in terminal_states:
                    return body
                if auto_answer is not None and body.get("active_prompt"):
                    self.answer_active_prompt(job_id, auto_answer)
            time.sleep(poll_interval)
        raise AssertionError(
            f"Job {job_id} did not reach {terminal_states} within {timeout}s; last={last!r}"
        )

    def drive_demo_jobs_to_completion(
        self,
        job_ids: Iterable[str],
        *,
        choice: str = "Proyecto A",
        timeout: float = 20.0,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Poll multiple demo jobs and answer pick_project prompts until all finish.
        TestClient is not thread-safe; use this from a single thread for concurrency tests.
        """
        pending = set(job_ids)
        results: Dict[str, Dict[str, Any]] = {}
        deadline = time.monotonic() + timeout
        while pending and time.monotonic() < deadline:
            for jid in list(pending):
                _, body = self.get_json(f"/api/jobs/{jid}")
                state = body.get("state")
                if state in ("done", "error", "cancelled"):
                    results[jid] = body
                    pending.discard(jid)
                elif body.get("active_prompt"):
                    self.answer_active_prompt(jid, choice)
            time.sleep(0.05)
        if pending:
            raise AssertionError(f"Jobs still pending after {timeout}s: {pending}")
        return results

    def drive_job_prompts(
        self,
        job_id: str,
        answers: Iterable[Any],
        *,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Responde prompts en orden hasta estado terminal (done/error/cancelled)."""
        answers_list = list(answers)
        idx = 0
        deadline = time.monotonic() + timeout
        last: Dict[str, Any] = {}
        answered_ids: set[str] = set()
        while time.monotonic() < deadline:
            status, body = self.get_json(f"/api/jobs/{job_id}")
            if status == 200:
                last = body
                state = body.get("state")
                if state in ("done", "error", "cancelled"):
                    return body
                prompt = body.get("active_prompt") or {}
                pid = prompt.get("prompt_id")
                if pid and pid not in answered_ids and idx < len(answers_list):
                    self.answer_prompt(job_id, pid, answers_list[idx])
                    answered_ids.add(pid)
                    idx += 1
            time.sleep(0.05)
        raise AssertionError(
            f"Job {job_id} did not finish within {timeout}s; answered={idx}/{len(answers_list)} last={last!r}"
        )

    @staticmethod
    def _parse_json(res) -> Dict[str, Any]:
        try:
            return res.json()
        except Exception:
            return {"_raw": res.text}


@contextmanager
def isolated_license(
    fingerprint: str = "c" * 32,
    *,
    activate: bool = True,
    key_builder=None,
) -> Generator[Path, None, None]:
    """
    Temporary license_state.json under a temp dir; optionally activates a perm key.
    """
    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / "license_state.json"
        patches = [
            patch.dict(
                os.environ,
                {"ELIA_SKIP_LICENSE": "", "ELIA_ACTIVATION_KEY": ""},
                clear=False,
            ),
            patch.object(lic, "_state_path", return_value=state_file),
            patch.object(lic, "get_machine_fingerprint", return_value=fingerprint),
        ]
        for p in patches:
            p.start()
        try:
            if activate:
                builder = key_builder or (
                    lambda fp: lic.build_activation_key(fp, lic.DURATION_PERM, issue_ts=1_700_000_000)
                )
                lic.activate_with_key(builder(fingerprint))
            yield state_file
        finally:
            for p in reversed(patches):
                p.stop()


@contextmanager
def elia_test_app(
    *,
    licensed: bool = True,
    fingerprint: str = "c" * 32,
    job_manager: Optional[JobManager] = None,
) -> Generator[Tuple[EliaApiActor, JobManager], None, None]:
    """
    Yields (api_actor, job_manager) with a fresh FastAPI app per test.
    License is isolated unless licensed=False.
    """
    jm = job_manager or JobManager()
    with tempfile.TemporaryDirectory() as user_data:
        env_patch = patch.dict(
            os.environ,
            {"ELIA_USER_DATA": user_data},
            clear=False,
        )
        env_patch.start()
        try:
            if licensed:
                with isolated_license(fingerprint):
                    app = create_app(job_manager=jm)
                    with TestClient(app) as client:
                        yield EliaApiActor(client), jm
            else:
                with isolated_license(fingerprint, activate=False):
                    app = create_app(job_manager=jm)
                    with TestClient(app) as client:
                        yield EliaApiActor(client), jm
        finally:
            env_patch.stop()


class ApiTestCase(unittest.TestCase):
    """Base with small assertion helpers for HTTP responses."""

    def assert_status(self, code: int, expected: int, body: Dict[str, Any], msg: str = "") -> None:
        prefix = f"{msg}: " if msg else ""
        self.assertEqual(code, expected, f"{prefix}body={body!r}")

    def assert_forbidden_license(self, code: int, body: Dict[str, Any]) -> None:
        self.assertEqual(code, 403)
        detail = body.get("detail", "")
        self.assertIn("Licencia", detail)
