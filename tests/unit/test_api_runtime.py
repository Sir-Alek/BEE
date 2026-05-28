"""Tests for API runtime: interpolation, merge, executor, assertions."""
from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from core.api_automation.models import ApiAssertion, ApiRequest
from core.api_automation.openapi_import import import_openapi_spec
from core.api_automation.postman_import import import_postman_collection
from core.api_automation.runtime.assertion_engine import evaluate_assertions
from core.api_automation.runtime.context_merge import build_effective_request
from core.api_automation.runtime.interpolation import interpolate_text


class TestApiRuntime(unittest.TestCase):
    def test_interpolate_variables(self) -> None:
        text = interpolate_text("{{base_url}}/users/{{id}}", {"base_url": "https://api.test", "id": "42"})
        self.assertEqual(text, "https://api.test/users/42")

    def test_build_effective_request_merges_headers(self) -> None:
        req = ApiRequest(
            id="r1",
            name="GET",
            method="GET",
            url="{{base_url}}/health",
            headers={"X-Custom": "1"},
        )
        effective = build_effective_request(
            req,
            global_headers={"Authorization": "Bearer {{token}}", "X-Custom": "global"},
            variables={"base_url": "https://api.test", "token": "abc"},
        )
        self.assertEqual(effective["url"], "https://api.test/health")
        self.assertEqual(effective["headers"]["Authorization"], "Bearer abc")
        self.assertEqual(effective["headers"]["X-Custom"], "1")

    def test_evaluate_status_assertion(self) -> None:
        req = ApiRequest(id="r1", name="GET", method="GET", url="https://x", expected_status=200)
        results = evaluate_assertions(req, status_code=404, response_headers={}, response_body="{}", elapsed_ms=0)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["passed"])

    def test_postman_import_minimal(self) -> None:
        requests = import_postman_collection(
            {
                "info": {"name": "Demo"},
                "item": [
                    {
                        "name": "Health",
                        "request": {
                            "method": "GET",
                            "url": "{{base_url}}/health",
                        },
                    }
                ],
            }
        )
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].method, "GET")

    def test_openapi_import_minimal(self) -> None:
        requests = import_openapi_spec(
            {
                "openapi": "3.0.0",
                "info": {"title": "Demo API"},
                "servers": [{"url": "https://api.test"}],
                "paths": {
                    "/items": {
                        "get": {"summary": "List items"},
                    }
                },
            }
        )
        self.assertEqual(len(requests), 1)
        self.assertIn("/items", requests[0].url)

    @patch("core.api_automation.runtime.request_executor.httpx.Client")
    def test_execute_request(self, client_cls: MagicMock) -> None:
        from core.api_automation.runtime.request_executor import execute_request

        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Type": "application/json"}
        response.text = '{"ok":true}'
        client = MagicMock()
        client.request.return_value = response
        client.__enter__.return_value = client
        client.__exit__.return_value = None
        client_cls.return_value = client

        req = ApiRequest(id="r1", name="GET", method="GET", url="https://api.test/ok", expected_status=200)
        result = execute_request(req)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status_code"], 200)


if __name__ == "__main__":
    unittest.main()
