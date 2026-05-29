"""Tests para respuestas JSON Doc-to-BDD (Gemma GBNF + render Python)."""
from __future__ import annotations

import json
import os
import unittest

from core.bdd_llm_response import (
    normalize_bdd_steps,
    parse_bdd_llm_text,
    render_gherkin_from_bdd_response,
)
from core.gemma_inference import ai_cot_mode


class TestBddLlmResponse(unittest.TestCase):
    def _fixture(self, name: str) -> dict:
        path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "gemma", name)
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_normalize_steps_valid_structure(self) -> None:
        data = self._fixture("bdd_response_sample.json")
        steps = normalize_bdd_steps(data["steps"])
        self.assertIsNotNone(steps)
        assert steps is not None
        self.assertEqual([k for k, _ in steps], ["given", "when", "then"])

    def test_render_gherkin_from_json(self) -> None:
        data = self._fixture("bdd_response_sample.json")
        gherkin = render_gherkin_from_bdd_response(data, feature_name="Login")
        self.assertIsNotNone(gherkin)
        assert gherkin is not None
        self.assertIn("Feature: Login", gherkin)
        self.assertIn("Scenario: Login exitoso", gherkin)
        self.assertIn("Given el usuario", gherkin)

    def test_parse_bdd_llm_text_from_json_string(self) -> None:
        raw = json.dumps(self._fixture("bdd_response_sample.json"), ensure_ascii=False)
        gherkin = parse_bdd_llm_text(raw, feature_name="Login")
        self.assertIsNotNone(gherkin)

    def test_ai_cot_mode_default_single(self) -> None:
        old = os.environ.pop("ELIA_AI_COT_MODE", None)
        try:
            self.assertEqual(ai_cot_mode(), "single")
        finally:
            if old is not None:
                os.environ["ELIA_AI_COT_MODE"] = old


if __name__ == "__main__":
    unittest.main()
