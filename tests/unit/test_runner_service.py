"""Tests del servicio de ejecución Behave/Locust."""
from __future__ import annotations

import os
import sys
import time
import unittest

from core.test_runner.runner_service import TestRunnerService


class TestRunnerServiceTests(unittest.TestCase):
    def test_successful_run_completes_with_done_state(self) -> None:
        svc = TestRunnerService()
        run_id = svc.start(
            kind="test",
            command=[sys.executable, "-u", "-c", "print('hello-elia')"],
            cwd=os.getcwd(),
        )
        run = self._wait_for_finish(svc, run_id)
        self.assertIsNotNone(run)
        assert run is not None
        self.assertEqual(run.state, "done")
        self.assertEqual(run.return_code, 0)
        self.assertIn("hello-elia", "\n".join(run.lines))

    def test_failed_run_completes_with_error_state(self) -> None:
        svc = TestRunnerService()
        run_id = svc.start(
            kind="test",
            command=[sys.executable, "-u", "-c", "print('step-failed'); import sys; sys.exit(1)"],
            cwd=os.getcwd(),
        )
        run = self._wait_for_finish(svc, run_id)
        self.assertIsNotNone(run)
        assert run is not None
        self.assertEqual(run.state, "error")
        self.assertEqual(run.return_code, 1)
        self.assertIn("step-failed", "\n".join(run.lines))

    def _wait_for_finish(self, svc: TestRunnerService, run_id: str, timeout: float = 15.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            run = svc.get(run_id)
            if run is not None and run.state != "running":
                return run
            time.sleep(0.05)
        return svc.get(run_id)


if __name__ == "__main__":
    unittest.main()
