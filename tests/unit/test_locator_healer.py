"""Tests para locator_healer (estrategias tipadas, sin LLM)."""
from __future__ import annotations

import json
import os
import unittest

from core.ui_automation.locator_healer import (
    _algorithmic_heal,
    _parse_gemma_locator_response,
    heal_locator,
)


class TestLocatorHealer(unittest.TestCase):
    def _fixture(self, name: str) -> dict:
        path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "gemma", name)
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_parse_typed_strategies(self) -> None:
        data = self._fixture("locator_response_sample.json")
        parsed = _parse_gemma_locator_response(data)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["primary"], "#login-submit")
        self.assertEqual(len(parsed["strategies"]), 3)
        self.assertEqual(parsed["strategies"][0]["type"], "id")

    def test_algorithmic_heal_data_testid(self) -> None:
        record = {
            "selector": "div:nth-child(3) > button",
            "xpath": "//button[3]",
            "tag": "button",
            "id": "",
            "fingerprint": {
                "data_attrs": {"data-testid": "submit-login"},
                "role": "button",
            },
        }
        result = _algorithmic_heal(record)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("data-testid", result["primary"])
        self.assertGreaterEqual(len(result.get("strategies") or []), 1)

    def test_heal_locator_no_ai_fallback(self) -> None:
        record = {"selector": "#ok", "xpath": "//*[@id='ok']", "tag": "button", "id": "ok"}
        result = heal_locator(record, use_ai=False)
        self.assertEqual(result["primary"], "#ok")
        self.assertIn("strategies", result)


if __name__ == "__main__":
    unittest.main()
