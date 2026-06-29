"""Tests for ELIA memory learning helpers."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from core import elia_memory as mem


class TestEliaMemoryLearning(unittest.TestCase):
    def test_should_learn_respects_preferences(self) -> None:
        with patch("core.ai_policy.load_preferences", return_value={"memory_auto_learn": False}):
            self.assertFalse(mem.should_learn_correction(edited=True, content_changed=True))
        with patch(
            "core.ai_policy.load_preferences",
            return_value={"memory_auto_learn": True, "memory_learn_after_retry": False},
        ):
            self.assertTrue(mem.should_learn_correction(edited=True, content_changed=False))
            self.assertFalse(mem.should_learn_correction(edited=False, content_changed=False, attempt=2))
        with patch(
            "core.ai_policy.load_preferences",
            return_value={"memory_auto_learn": True, "memory_learn_after_retry": True},
        ):
            self.assertTrue(mem.should_learn_correction(edited=False, content_changed=False, attempt=2))

    def test_memory_status_includes_prompt_limit(self) -> None:
        status = mem.memory_status()
        self.assertEqual(status["prompt_examples_limit"], 3)
        self.assertEqual(status["max_entries"], 80)


if __name__ == "__main__":
    unittest.main()
