"""Tests for API assertion heuristics."""
from __future__ import annotations

import unittest

from core.api_automation.api_assertion_ai import infer_api_assertions
from core.api_automation.models import ApiRequest


class TestApiAssertionAi(unittest.TestCase):
    def test_heuristic_status_only(self) -> None:
        req = ApiRequest(id="r1", name="GET", method="GET", url="https://api.test/x", expected_status=404)
        assertions = infer_api_assertions(req, use_ai=False)
        self.assertGreaterEqual(len(assertions), 1)
        self.assertEqual(assertions[0].kind, "status")
        self.assertEqual(assertions[0].expected, "404")

    def test_heuristic_json_keys(self) -> None:
        req = ApiRequest(
            id="r2",
            name="POST",
            method="POST",
            url="https://api.test/items",
            response_body='{"id": 1, "name": "x"}',
            expected_status=201,
        )
        assertions = infer_api_assertions(req, use_ai=False)
        kinds = {a.kind for a in assertions}
        self.assertIn("status", kinds)
        self.assertIn("jsonpath", kinds)
