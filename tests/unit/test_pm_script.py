"""Tests for Postman-style script runner."""
from __future__ import annotations

import unittest

from core.api_automation.models import ApiRequest
from core.api_automation.runtime.pm_script import run_post_request_script, run_pre_request_script


class TestPmScript(unittest.TestCase):
    def test_pre_request_sets_variable_and_header(self) -> None:
        req = ApiRequest(id="x", name="t", method="GET", url="{{base}}/ok", headers={})
        variables = {"token": "abc"}
        script = (
            'pm.request.headers.add({key: "Authorization", value: "Bearer " + pm.environment.get("token")});'
        )
        result = run_pre_request_script(script, req, variables)
        self.assertTrue(result.ok)
        self.assertEqual(req.headers.get("Authorization"), "Bearer abc")

    def test_post_request_json_binding_and_test(self) -> None:
        req = ApiRequest(id="x", name="t", method="GET", url="/", headers={})
        variables: dict[str, str] = {}
        script = "\n".join(
            [
                "const data = pm.response.json();",
                'pm.environment.set("id", data.id);',
                'pm.test("HTTP 200", function () { pm.response.to.have.status(200); });',
            ]
        )
        result = run_post_request_script(
            script,
            req,
            variables,
            status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"id": "42"}',
        )
        self.assertTrue(result.ok)
        self.assertEqual(variables.get("id"), "42")
        self.assertTrue(any(t.get("passed") for t in result.script_tests))


if __name__ == "__main__":
    unittest.main()
