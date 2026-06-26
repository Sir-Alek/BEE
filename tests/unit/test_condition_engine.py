"""Tests for API flow condition engine."""
from __future__ import annotations

import unittest

from core.api_automation.runtime.condition_engine import evaluate_condition


class TestConditionEngine(unittest.TestCase):
    def test_always(self) -> None:
        self.assertTrue(evaluate_condition({"kind": "always"}, variables={}))

    def test_status(self) -> None:
        last = {"status_code": 200}
        self.assertTrue(evaluate_condition({"kind": "status", "expected": "200"}, variables={}, last_result=last))
        self.assertFalse(evaluate_condition({"kind": "status", "expected": "404"}, variables={}, last_result=last))

    def test_var_equals(self) -> None:
        self.assertTrue(
            evaluate_condition(
                {"kind": "var_equals", "expression": "token", "expected": "abc"},
                variables={"token": "abc"},
            )
        )

    def test_negate(self) -> None:
        self.assertFalse(
            evaluate_condition(
                {"kind": "status", "expected": "200", "negate": True},
                variables={},
                last_result={"status_code": 200},
            )
        )

    def test_body_contains(self) -> None:
        self.assertTrue(
            evaluate_condition(
                {"kind": "body_contains", "expected": "ok"},
                variables={},
                last_result={"body": '{"status":"ok"}'},
            )
        )


if __name__ == "__main__":
    unittest.main()
