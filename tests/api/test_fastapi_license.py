"""
License API lifecycle: activation, status, module gating, expiry simulation.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from core import elia_license as lic
from tests.api.support import ApiTestCase, elia_test_app, isolated_license


class TestLicenseApiFlow(ApiTestCase):
    FP = "d" * 32

    def test_status_reflects_activation(self) -> None:
        with elia_test_app(fingerprint=self.FP) as (api, _):
            code, body = api.get_json("/api/license/status")
            self.assertEqual(code, 200)
            self.assertTrue(body.get("activated"))
            self.assertTrue(body.get("can_run_jobs"))
            self.assertEqual(body.get("machine_fingerprint"), self.FP)

    def test_activate_valid_key_via_api(self) -> None:
        key = lic.build_activation_key(self.FP, lic.DURATION_PERM, issue_ts=1_700_000_000)
        with elia_test_app(licensed=False, fingerprint=self.FP) as (api, _):
            code, body = api.post_json("/api/license/activate", {"key": key})
            self.assertEqual(code, 200)
            self.assertTrue(body.get("ok"))
            self.assertTrue(body.get("can_run_jobs"))

    def test_activate_wrong_machine_key_rejected(self) -> None:
        other_fp = "e" * 32
        key = lic.build_activation_key(other_fp, lic.DURATION_PERM, issue_ts=1_700_000_000)
        with elia_test_app(licensed=False, fingerprint=self.FP) as (api, _):
            code, body = api.post_json("/api/license/activate", {"key": key})
            self.assertEqual(code, 200)
            self.assertFalse(body.get("ok"))

    def test_modules_status_tracks_license_flags(self) -> None:
        key_ml = lic.build_activation_key(
            self.FP,
            lic.DURATION_PERM,
            tier="enterprise",
            issue_ts=1_700_000_000,
        )
        with isolated_license(self.FP, activate=False):
            with patch.object(lic, "get_machine_fingerprint", return_value=self.FP):
                lic.activate_with_key(key_ml)
                from webui.fastapi_app import create_app

                from fastapi.testclient import TestClient

                app = create_app()
                with TestClient(app) as client:
                    res = client.get("/api/modules/status")
                    body = res.json()
                    self.assertTrue(body["mobile_recording"])
                    self.assertTrue(body["legacy_recording"])
                    self.assertTrue(body["doc_to_bdd"])

    def test_expired_license_blocks_jobs_via_api(self) -> None:
        key_15d = lic.build_activation_key(self.FP, lic.DURATION_15D, issue_ts=1_700_000_000)
        with isolated_license(self.FP, activate=False):
            with patch.object(lic, "get_machine_fingerprint", return_value=self.FP):
                lic.activate_with_key(key_15d)
                past = 1_700_000_000 + 20 * 86400
                with patch.object(lic.time, "time", return_value=past):
                    from webui.fastapi_app import create_app
                    from fastapi.testclient import TestClient

                    app = create_app()
                    with TestClient(app) as client:
                        res = client.post("/api/jobs/convert", json={"mode": "demo"})
                        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
