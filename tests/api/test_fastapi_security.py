"""
Security hardening tests for ELIA FastAPI surface.

Vectors: localhost-only gate, path traversal in uploads and gherkin paths,
injection payloads in JSON bodies, invalid AI mode, oversized inputs.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from tests.api.support import ApiTestCase, elia_test_app
from webui.fastapi_app import _require_localhost, _safe_under_user_data, create_app


async def _asgi_get_status(app: Any, path: str, client_host: str) -> int:
    status_code = 500

    async def send(message: dict) -> None:
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": (client_host, 12345),
        "server": ("127.0.0.1", 8765),
        "scheme": "http",
        "root_path": "",
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    await app(scope, receive, send)
    return status_code


class TestLocalhostGate(ApiTestCase):
    def test_testclient_host_allowed(self) -> None:
        scope = {"type": "http", "client": ("testclient", 50000), "headers": []}
        req = Request(scope)
        _require_localhost(req)  # must not raise

    def test_remote_host_rejected(self) -> None:
        scope = {"type": "http", "client": ("203.0.113.50", 443), "headers": []}
        req = Request(scope)
        with self.assertRaises(HTTPException) as ctx:
            _require_localhost(req)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("localhost", ctx.exception.detail.lower())

    def test_loopback_variants_allowed(self) -> None:
        for host in ("127.0.0.1", "::1", "localhost"):
            scope = {"type": "http", "client": (host, 8080), "headers": []}
            _require_localhost(Request(scope))


class TestStaticAssetLocalhostGate(ApiTestCase):
    """Rutas estáticas SPA y logos deben aplicar _require_localhost (no solo el catchall)."""

    def test_static_paths_reject_remote_client(self) -> None:
        app = create_app()
        for path in ("/", "/logo.png", "/logo-icon.png", "/logo-letters.png", "/favicon.ico"):
            status = asyncio.run(_asgi_get_status(app, path, "203.0.113.50"))
            self.assertEqual(status, 403, path)

    def test_static_paths_allow_loopback(self) -> None:
        app = create_app()
        for path in ("/", "/favicon.ico"):
            status = asyncio.run(_asgi_get_status(app, path, "127.0.0.1"))
            self.assertIn(status, (200, 404), path)


class TestPathTraversalGuards(ApiTestCase):
    def test_safe_under_user_data_blocks_escape(self) -> None:
        with patch("webui.fastapi_app._user_data_root", return_value=tempfile.mkdtemp()):
            root = os.path.abspath(tempfile.gettempdir())
            with patch("webui.fastapi_app._user_data_root", return_value=root):
                escaped = _safe_under_user_data("..", "..", "etc", "passwd")
                self.assertTrue(
                    escaped == root or escaped.startswith(root + os.sep),
                    "Path escape must fall back to user data root",
                )

    def test_upload_rejects_path_traversal_filename(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.upload_files(
                "/api/req/upload-docs",
                [("files", b"fake", "../../../evil.docx")],
            )
            self.assertEqual(code, 200)
            # Server normalizes dest; saved files must stay under tmp upload dir
            for entry in body.get("files", []):
                path = entry.get("path", "")
                self.assertNotIn("..", path)
                self.assertTrue(path.endswith(".docx") or path.endswith("evil.docx"))

    def test_upload_skips_disallowed_extensions(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.upload_files(
                "/api/req/upload-docs",
                [
                    ("files", b"<?php echo 1; ?>", "shell.php"),
                    ("files", b"<script>alert(1)</script>", "xss.html"),
                    ("files", b'{"injection": true}', "payload.json"),
                ],
            )
            self.assertEqual(code, 200)
            saved = body.get("files", [])
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["ext"], ".json")


class TestInjectionAndEdgePayloads(ApiTestCase):
    def test_license_activate_xss_key_does_not_crash(self) -> None:
        with elia_test_app(licensed=False) as (api, _):
            payload = {"key": "<script>alert('xss')</script>"}
            code, body = api.post_json("/api/license/activate", payload)
            self.assertEqual(code, 200)
            self.assertFalse(body.get("ok"))

    def test_connectors_put_sql_injection_profile_id(self) -> None:
        with elia_test_app() as (api, _):
            doc = {
                "version": 1,
                "profiles": [
                    {
                        "id": "'; DROP TABLE profiles; --",
                        "name": "Robert'); DROP TABLE students;--",
                        "jira": {"url": "http://jira.local", "email": "a@b.c", "api_token": "tok"},
                        "value_edge": {
                            "url": "",
                            "shared_space": "",
                            "workspace": "",
                            "tech_preview_flag": "true",
                            "login": "",
                            "user": "",
                            "password": "",
                        },
                    }
                ],
            }
            code, body = api.put_json("/api/elia/connectors", doc)
            self.assertEqual(code, 200)
            self.assertTrue(body.get("ok"))
            code2, loaded = api.get_json("/api/elia/connectors")
            self.assertEqual(code2, 200)
            self.assertEqual(loaded["profiles"][0]["id"], doc["profiles"][0]["id"])

    def test_ai_preferences_rejects_invalid_mode(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.put_json("/api/ai/preferences", {"mode": "supercharged"})
            self.assertEqual(code, 400)
            self.assertIn("mode", body.get("detail", ""))

    def test_job_convert_unknown_mode_eventually_errors(self) -> None:
        # Pydantic rejects unknown modes at validation layer before job starts.
        with elia_test_app() as (api, _):
            res = api.client.post("/api/jobs/convert", json={"mode": "not_a_real_mode"})
            self.assertEqual(res.status_code, 422)


class TestUnlicensedAccess(ApiTestCase):
    def test_jobs_blocked_without_license(self) -> None:
        with elia_test_app(licensed=False) as (api, _):
            code, body = api.post_json("/api/jobs/convert", {"mode": "demo"})
            self.assert_forbidden_license(code, body)

    def test_license_status_available_without_activation(self) -> None:
        with elia_test_app(licensed=False) as (api, _):
            code, body = api.get_json("/api/license/status")
            self.assertEqual(code, 200)
            self.assertFalse(body.get("can_run_jobs"))


if __name__ == "__main__":
    unittest.main()
