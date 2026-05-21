"""
Integración Jira / Value Edge con red real (opt-in).

Ejecutar:
  set ELIA_RUN_INTEGRATION=1
  set ELIA_JIRA_URL=https://...
  set ELIA_JIRA_EMAIL=...
  set ELIA_JIRA_TOKEN=...
  set ELIA_VE_URL=https://...
  set ELIA_VE_SHARED_SPACE=...
  set ELIA_VE_WORKSPACE=...
  set ELIA_VE_USER=...
  set ELIA_VE_PASSWORD=...
  python tests/run_integration.py
"""
from __future__ import annotations

import os
import unittest

from core.req_intelligence import integrations_service as svc
from tests.support.markers import integration_enabled


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _jira_creds_from_env() -> dict[str, str] | None:
    url, email, token = _env("ELIA_JIRA_URL"), _env("ELIA_JIRA_EMAIL"), _env("ELIA_JIRA_TOKEN")
    if not (url and email and token):
        return None
    return {"url": url, "email": email, "api_token": token}


def _ve_creds_from_env() -> dict[str, str] | None:
    url = _env("ELIA_VE_URL")
    if not url:
        return None
    login = _env("ELIA_VE_LOGIN") or f"{url.rstrip('/')}/authentication/sign_in"
    creds = {
        "url": url,
        "shared_space": _env("ELIA_VE_SHARED_SPACE"),
        "workspace": _env("ELIA_VE_WORKSPACE"),
        "tech_preview_flag": _env("ELIA_VE_TECH_PREVIEW") or "true",
        "login": login,
        "user": _env("ELIA_VE_USER"),
        "password": _env("ELIA_VE_PASSWORD"),
    }
    if not all(str(creds[k]).strip() for k in ("shared_space", "workspace", "user", "password")):
        return None
    return creds


@unittest.skipUnless(integration_enabled(), "Requiere ELIA_RUN_INTEGRATION=1")
class TestJiraLiveIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.creds = _jira_creds_from_env()
        if cls.creds is None:
            raise unittest.SkipTest(
                "Faltan ELIA_JIRA_URL, ELIA_JIRA_EMAIL o ELIA_JIRA_TOKEN",
            )

    def test_jira_check_connection_live(self) -> None:
        out = svc.jira_smoke_test(inline=True, creds=self.creds)
        self.assertEqual(out["source"], "job_payload")
        self.assertTrue(out["ok"], "Jira check_connection falló — revisa credenciales/red")


@unittest.skipUnless(integration_enabled(), "Requiere ELIA_RUN_INTEGRATION=1")
class TestValueEdgeLiveIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.creds = _ve_creds_from_env()
        if cls.creds is None:
            raise unittest.SkipTest(
                "Faltan variables ELIA_VE_* (url, shared_space, workspace, user, password)",
            )

    def test_value_edge_login_live(self) -> None:
        out = svc.value_edge_smoke_test(inline=True, creds=self.creds)
        self.assertEqual(out["source"], "job_payload")
        self.assertTrue(out["ok"], "Value Edge login falló — revisa credenciales/red")


if __name__ == "__main__":
    unittest.main()
