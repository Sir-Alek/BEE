"""Tests for OpenAPI import."""
from __future__ import annotations

import unittest

from core.api_automation.openapi_import import import_openapi_spec


class TestOpenApiImport(unittest.TestCase):
    def test_empty_paths_returns_tuple(self) -> None:
        reqs, title = import_openapi_spec({"openapi": "3.0.0", "info": {"title": "Demo"}, "paths": None})
        self.assertEqual(title, "Demo")
        self.assertEqual(reqs, [])

    def test_resolve_ref_body_example(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Pet"},
            "paths": {
                "/pets": {
                    "post": {
                        "summary": "Create pet",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Pet"},
                                }
                            }
                        },
                    }
                }
            },
            "components": {
                "schemas": {
                    "Pet": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                }
            },
        }
        reqs, _ = import_openapi_spec(spec)
        self.assertEqual(len(reqs), 1)
        self.assertIn("name", reqs[0].body or "")


if __name__ == "__main__":
    unittest.main()
