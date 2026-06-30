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

    @patch("core.ui_automation.mobile_android.get_appium_status")
    def test_mobile_appium_status_endpoint(self, mock_status) -> None:
        mock_status.return_value = {
            "ok": True,
            "running": True,
            "installed": True,
            "managed_by_elia": False,
            "url": "http://127.0.0.1:4723",
            "host": "127.0.0.1",
            "port": 4723,
            "android_only": True,
        }
        with elia_test_app() as (api, _jm):
            code, body = api.get_json("/api/mobile/appium/status")
        self.assert_status(code, 200, body)
        self.assertTrue(body.get("running"))

    @patch("core.ui_automation.mobile_avd_wizard.wizard_capabilities")
    def test_avd_wizard_capabilities(self, mock_caps) -> None:
        mock_caps.return_value = {
            "orchestration_allowed": False,
            "orchestration_tier": "architect",
            "cmdline_tools_ok": True,
            "avd_count": 0,
            "avds": [],
            "has_online_emulator": False,
            "studio_available": True,
            "disk_ok": True,
            "templates": [],
            "job": {"active": False, "done": False, "ok": False, "phase": "", "message": ""},
        }
        with elia_test_app() as (api, _jm):
            code, body = api.get_json("/api/mobile/avd/wizard/capabilities")
        self.assert_status(code, 200, body)
        self.assertTrue(body.get("ok"))
        self.assertFalse(body.get("orchestration_allowed"))

    @patch("core.elia_license.get_license_status")
    @patch("core.ui_automation.mobile_avd_wizard.start_orchestration")
    def test_avd_wizard_start_forbidden_for_tester(self, mock_start, mock_st) -> None:
        mock_st.return_value = type(
            "S",
            (),
            {"tier_name": "tester", "is_beta": False},
        )()
        with elia_test_app() as (api, _jm):
            code, body = api.post_json("/api/mobile/avd/wizard/start", {"template_id": "standard"})
        self.assertEqual(code, 403)
        mock_start.assert_not_called()

    @patch("core.ui_automation.mobile_avd_wizard.open_android_studio")
    def test_avd_open_studio(self, mock_open) -> None:
        mock_open.return_value = {"ok": True, "message": "Android Studio abierto."}
        with elia_test_app() as (api, _jm):
            code, body = api.post_json("/api/mobile/avd/wizard/open-studio", {})
        self.assert_status(code, 200, body)
        self.assertTrue(body.get("ok"))
        mock_open.assert_called_once_with(path=None, save=False)


if __name__ == "__main__":
    unittest.main()
