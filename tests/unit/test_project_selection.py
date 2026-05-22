"""Tests for webui.project_selection."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from webui.job_manager import PROMPT_ANSWER_BACK, JobManager
from webui.project_selection import prompt_project_path


class TestProjectSelection(unittest.TestCase):
    def test_back_from_pick_returns_to_yes_no(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "ExistingProject"))
            jm = JobManager()
            job_id = jm.create_job(mode="test")
            answers = [False, PROMPT_ANSWER_BACK, True, "MyNew"]
            answer_idx = 0
            lock = threading.Lock()

            original = jm.create_prompt_and_wait

            def fake_wait(jid: str, *, prompt):
                nonlocal answer_idx
                with lock:
                    ans = answers[answer_idx]
                    answer_idx += 1
                jm.answer_prompt(jid, prompt_id=prompt.prompt_id, answer=ans)
                return ans

            with patch.object(jm, "create_prompt_and_wait", side_effect=fake_wait):
                path = prompt_project_path(jm, job_id, projects_dir=tmp)

            self.assertEqual(path, os.path.join(tmp, "MyNew"))
            self.assertEqual(answer_idx, 4)

    def test_back_from_new_project_input_returns_to_yes_no(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "ExistingProject"))
            jm = JobManager()
            job_id = jm.create_job(mode="test")
            answers = [True, PROMPT_ANSWER_BACK, False, "ExistingProject"]
            answer_idx = 0
            lock = threading.Lock()

            def fake_wait(jid: str, *, prompt):
                nonlocal answer_idx
                with lock:
                    ans = answers[answer_idx]
                    answer_idx += 1
                jm.answer_prompt(jid, prompt_id=prompt.prompt_id, answer=ans)
                return ans

            with patch.object(jm, "create_prompt_and_wait", side_effect=fake_wait):
                path = prompt_project_path(jm, job_id, projects_dir=tmp)

            self.assertEqual(path, os.path.join(tmp, "ExistingProject"))
            self.assertEqual(answer_idx, 4)


if __name__ == "__main__":
    unittest.main()
