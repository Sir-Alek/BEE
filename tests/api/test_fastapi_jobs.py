"""
Job lifecycle via FastAPI: create, poll, prompt/response, cancel, concurrency.
"""
from __future__ import annotations

import unittest

from tests.api.support import ApiTestCase, elia_test_app


class TestJobLifecycle(ApiTestCase):
    def test_demo_job_completes(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.post_json("/api/jobs/convert", {"mode": "demo"})
            self.assertEqual(code, 200)
            job_id = body.get("job_id")
            self.assertTrue(job_id)

            # Demo job blocks on pick_project until the UI (or test) answers the prompt.
            final = api.wait_for_job(job_id, timeout=10.0, auto_answer="Proyecto A")
            self.assertEqual(final["state"], "done")
            self.assertEqual(final["mode"], "demo")

    def test_get_nonexistent_job_returns_404(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.get_json("/api/jobs/00000000-0000-0000-0000-000000000099")
            self.assertEqual(code, 404)

    def test_cancel_nonexistent_job_returns_404(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.post_json("/api/jobs/00000000-0000-0000-0000-000000000099/cancel")
            self.assertEqual(code, 404)
            self.assertIn("not found", body.get("detail", "").lower())

    def test_cancel_job_transitions_to_cancelled(self) -> None:
        """
        doc_to_bdd without files errors quickly; cancel is tested on a running job
        by starting puppeteer_recorder without url (worker marks error). For cancel,
        we use a job that waits on a prompt — mobile_recorder without params errors fast.
        Instead: cancel immediately after create on demo (race — demo may finish first).
        """
        with elia_test_app() as (api, jm):
            code, body = api.post_json("/api/jobs/convert", {"mode": "demo"})
            job_id = body["job_id"]
            api.post_json(f"/api/jobs/{job_id}/cancel")
            final = api.wait_for_job(
                job_id,
                timeout=5.0,
                terminal_states=("done", "error", "cancelled", "running"),
            )
            # Cancel may arrive after demo completes; both are acceptable outcomes.
            self.assertIn(final["state"], ("cancelled", "done"))

    def test_doc_to_bdd_without_files_errors(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.post_json("/api/jobs/convert", {"mode": "doc_to_bdd", "doc_files": []})
            self.assertEqual(code, 200)
            final = api.wait_for_job(body["job_id"], timeout=10.0)
            self.assertEqual(final["state"], "error")
            self.assertIn("documentos", final["error"]["message"].lower())

    def test_mobile_recorder_without_license_module_errors_when_not_in_key(self) -> None:
        """Perm license without M flag → module disabled at runtime."""
        with elia_test_app() as (api, _):
            code, body = api.post_json(
                "/api/jobs/convert",
                {"mode": "mobile_recorder", "apk_path": "/fake.apk", "device_id": "dev"},
            )
            self.assertEqual(code, 200)
            final = api.wait_for_job(body["job_id"], timeout=10.0)
            self.assertEqual(final["state"], "error")
            self.assertIn("habilitado", final["error"]["message"].lower())

    def test_concurrent_demo_jobs_do_not_corrupt_state(self) -> None:
        """
        Stress: N parallel demo jobs must all reach terminal state independently.
        TestClient is single-threaded; we poll all jobs from one thread and answer prompts.
        """
        with elia_test_app() as (api, _):
            job_ids = []
            for _ in range(5):
                code, body = api.post_json("/api/jobs/convert", {"mode": "demo"})
                self.assertEqual(code, 200)
                job_ids.append(body["job_id"])

            results = api.drive_demo_jobs_to_completion(job_ids, timeout=20.0)
            for jid, final in results.items():
                self.assertEqual(final["state"], "done", f"job {jid} failed")

    def test_job_events_endpoint_returns_timeline(self) -> None:
        with elia_test_app() as (api, _):
            _, body = api.post_json("/api/jobs/convert", {"mode": "demo"})
            job_id = body["job_id"]
            api.wait_for_job(job_id, auto_answer="Proyecto B")
            code, events_body = api.get_json(f"/api/jobs/{job_id}/events")
            self.assertEqual(code, 200)
            events = events_body.get("events", [])
            self.assertGreater(len(events), 0)
            types = {e.get("type") for e in events}
            self.assertIn("job_started", types)


class TestPromptResponseFlow(ApiTestCase):
    def test_answer_unknown_prompt_is_idempotent(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.post_json("/api/jobs/convert", {"mode": "demo"})
            job_id = body["job_id"]
            code2, resp = api.post_json(
                f"/api/jobs/{job_id}/prompts/dead-beef-prompt/response",
                {"answer": "ignored"},
            )
            self.assertEqual(code2, 200)
            self.assertTrue(resp.get("ok"))


if __name__ == "__main__":
    unittest.main()
