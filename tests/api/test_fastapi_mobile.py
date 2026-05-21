"""Pruebas HTTP de endpoints /api/mobile/*."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.api.support import ApiTestCase, elia_test_app


class TestFastApiMobile(ApiTestCase):
    @patch("core.ui_automation.mobile_android.list_devices")
    def test_mobile_devices_endpoint(self, mock_list) -> None:
        from core.ui_automation.mobile_android import MobileDevice

        mock_list.return_value = (
            [MobileDevice(id="emulator-5554", state="device", kind="emulator")],
            None,
        )
        with elia_test_app() as (api, _jm):
            code, body = api.get_json("/api/mobile/devices")
        self.assert_status(code, 200, body)
        self.assertTrue(body.get("ok"))
        self.assertEqual(body["devices"][0]["id"], "emulator-5554")
        self.assertTrue(body.get("android_only"))

    @patch("core.ui_automation.mobile_android.run_preflight")
    def test_mobile_preflight_endpoint(self, mock_pf) -> None:
        from core.ui_automation.mobile_android import MobilePreflightResult

        mock_pf.return_value = MobilePreflightResult(ok=True, items=[], warnings=[], errors=[])
        with elia_test_app() as (api, _jm):
            code, body = api.get_json("/api/mobile/preflight")
        self.assert_status(code, 200, body)
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("android_only"))

    @patch("core.elia_license.can_run_jobs", return_value=False)
    def test_mobile_endpoints_require_license(self, _mock_can) -> None:
        with elia_test_app(licensed=False) as (api, _jm):
            code, body = api.get_json("/api/mobile/devices")
        self.assert_forbidden_license(code, body)


if __name__ == "__main__":
    unittest.main()
