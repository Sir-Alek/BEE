"""
Smoke tests de integraciones Jira / Value Edge sin red real.

Los extractores se sustituyen por mocks; se valida resolución de credenciales,
fachada integrations_service y endpoint FastAPI /api/elia/connectors/test.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from core.req_intelligence import integrations_service as svc
from tests.api.support import elia_test_app


JIRA_CREDS = {
    "url": "https://jira.example.com",
    "email": "qa@example.com",
    "api_token": "secret-token",
}

VE_CREDS = {
    "url": "https://ve.example.com",
    "shared_space": "space1",
    "workspace": "ws1",
    "tech_preview_flag": "true",
    "login": "https://ve.example.com/authentication/sign_in",
    "user": "ve_user",
    "password": "ve_pass",
}


class TestCredentialResolution(unittest.TestCase):
    def test_jira_inline_complete(self) -> None:
        out, src = svc.resolve_jira_credentials(inline=True, creds=JIRA_CREDS)
        self.assertEqual(src, "job_payload")
        self.assertEqual(out["url"], JIRA_CREDS["url"])

    def test_jira_inline_missing_token_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            svc.resolve_jira_credentials(
                inline=True,
                creds={"url": "https://jira.example.com", "email": "a@b.c", "api_token": ""},
            )
        self.assertIn("Jira", str(ctx.exception))

    def test_jira_inline_none_raises(self) -> None:
        with self.assertRaises(ValueError):
            svc.resolve_jira_credentials(inline=True, creds=None)

    def test_value_edge_inline_complete(self) -> None:
        out, src = svc.resolve_value_edge_settings(inline=True, creds=VE_CREDS)
        self.assertEqual(src, "job_payload")
        self.assertEqual(out["workspace"], "ws1")

    def test_value_edge_inline_missing_password_raises(self) -> None:
        incomplete = {**VE_CREDS, "password": ""}
        with self.assertRaises(ValueError) as ctx:
            svc.resolve_value_edge_settings(inline=True, creds=incomplete)
        self.assertIn("Value Edge", str(ctx.exception))

    def test_value_edge_builds_login_from_url(self) -> None:
        creds = {**VE_CREDS, "login": ""}
        out, _ = svc.resolve_value_edge_settings(inline=True, creds=creds)
        self.assertEqual(out["login"], "https://ve.example.com/authentication/sign_in")


class TestIntegrationsServiceSmokeMocked(unittest.TestCase):
    @patch.object(svc, "get_jira_extractor")
    def test_jira_smoke_success(self, mock_get: MagicMock) -> None:
        extractor = MagicMock()
        extractor.check_connection.return_value = True
        mock_get.return_value = (extractor, "job_payload")

        out = svc.jira_smoke_test(inline=True, creds=JIRA_CREDS)

        self.assertTrue(out["ok"])
        self.assertEqual(out["source"], "job_payload")
        extractor.check_connection.assert_called_once()

    @patch.object(svc, "get_jira_extractor")
    def test_jira_smoke_connection_failure(self, mock_get: MagicMock) -> None:
        extractor = MagicMock()
        extractor.check_connection.return_value = False
        mock_get.return_value = (extractor, "job_payload")

        out = svc.jira_smoke_test(inline=True, creds=JIRA_CREDS)

        self.assertFalse(out["ok"])

    @patch.object(svc, "get_value_edge_extractor")
    def test_value_edge_smoke_success(self, mock_get: MagicMock) -> None:
        extractor = MagicMock()
        extractor.login.return_value = True
        mock_get.return_value = (extractor, "job_payload")

        out = svc.value_edge_smoke_test(inline=True, creds=VE_CREDS)

        self.assertTrue(out["ok"])
        extractor.login.assert_called_once()

    @patch.object(svc, "get_value_edge_extractor")
    def test_value_edge_smoke_login_failure(self, mock_get: MagicMock) -> None:
        extractor = MagicMock()
        extractor.login.return_value = False
        mock_get.return_value = (extractor, "job_payload")

        out = svc.value_edge_smoke_test(inline=True, creds=VE_CREDS)

        self.assertFalse(out["ok"])


class TestConnectorsApiWithMocks(unittest.TestCase):
    @patch("core.req_intelligence.integrations_service.jira_smoke_test")
    def test_api_jira_connector_test_ok(self, mock_smoke: MagicMock) -> None:
        mock_smoke.return_value = {"ok": True, "source": "job_payload"}
        with elia_test_app() as (api, _):
            code, body = api.post_json(
                "/api/elia/connectors/test",
                {"kind": "jira", "jira": JIRA_CREDS, "value_edge": {}},
            )
            self.assertEqual(code, 200)
            self.assertTrue(body.get("ok"))

    @patch("core.req_intelligence.integrations_service.value_edge_smoke_test")
    def test_api_value_edge_connector_test_ok(self, mock_smoke: MagicMock) -> None:
        mock_smoke.return_value = {"ok": True, "source": "job_payload"}
        with elia_test_app() as (api, _):
            code, body = api.post_json(
                "/api/elia/connectors/test",
                {"kind": "value_edge", "jira": {}, "value_edge": VE_CREDS},
            )
            self.assertEqual(code, 200)
            self.assertTrue(body.get("ok"))

    @patch("core.req_intelligence.integrations_service.jira_smoke_test")
    def test_api_connector_test_propagates_value_error(self, mock_smoke: MagicMock) -> None:
        mock_smoke.side_effect = ValueError("Jira: credenciales inválidas")
        with elia_test_app() as (api, _):
            code, body = api.post_json(
                "/api/elia/connectors/test",
                {"kind": "jira", "jira": JIRA_CREDS, "value_edge": {}},
            )
            self.assertEqual(code, 400)
            self.assertIn("Jira", body.get("detail", ""))


if __name__ == "__main__":
    unittest.main()
