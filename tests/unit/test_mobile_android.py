"""Pruebas de descubrimiento Android (adb, AVD, preflight)."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from core.ui_automation import mobile_android as ma


class TestParseAdbDevices(unittest.TestCase):
    def test_parses_physical_and_emulator(self) -> None:
        text = (
            "List of devices attached\n"
            "R5CXA1DQPFX            device product:o1s model:SM_S921B device:o1s transport_id:1\n"
            "emulator-5554          device product:sdk_gphone model:sdk_gphone device:generic transport_id:2\n"
        )
        devices = ma.parse_adb_devices_output(text)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].kind, "physical")
        self.assertEqual(devices[0].id, "R5CXA1DQPFX")
        self.assertEqual(devices[1].kind, "emulator")
        self.assertEqual(devices[1].id, "emulator-5554")


class TestResolveAndroidSdk(unittest.TestCase):
    def test_reads_elia_android_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"ELIA_ANDROID_HOME": tmp}, clear=False):
                sdk, src = ma.resolve_android_sdk()
            self.assertEqual(sdk, tmp)
            self.assertEqual(src, "elia_android_home")


class TestAssertDeviceOnline(unittest.TestCase):
    @patch.object(ma, "device_boot_completed", return_value=True)
    @patch.object(ma, "list_devices")
    @patch.object(ma, "resolve_adb")
    def test_online_emulator_ok(self, mock_adb, mock_list, _boot) -> None:
        mock_adb.return_value = ma.AndroidTool(name="adb", path=r"C:\adb.exe")
        mock_list.return_value = (
            [ma.MobileDevice(id="emulator-5554", state="device", kind="emulator")],
            None,
        )
        self.assertIsNone(ma.assert_device_online("emulator-5554"))

    @patch.object(ma, "list_devices")
    @patch.object(ma, "resolve_adb")
    def test_missing_device_errors(self, mock_adb, mock_list) -> None:
        mock_adb.return_value = ma.AndroidTool(name="adb", path=r"C:\adb.exe")
        mock_list.return_value = ([], None)
        err = ma.assert_device_online("missing")
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("no encontrado", err[0].lower())


class TestPreflight(unittest.TestCase):
    @patch.object(ma, "check_appium_server", return_value=False)
    @patch.object(ma, "list_avds", return_value=(["Pixel_7"], None))
    @patch.object(ma, "list_devices", return_value=([], None))
    @patch.object(ma, "resolve_emulator")
    @patch.object(ma, "resolve_adb")
    @patch.object(ma, "resolve_android_sdk")
    def test_preflight_fails_without_appium(
        self,
        mock_sdk,
        mock_adb,
        mock_emulator,
        _list_dev,
        _list_avd,
        _appium,
    ) -> None:
        mock_sdk.return_value = (r"C:\Android\Sdk", "android_home")
        mock_adb.return_value = ma.AndroidTool(name="adb", path=r"C:\adb.exe")
        mock_emulator.return_value = ma.AndroidTool(name="emulator", path=r"C:\emu.exe")
        result = ma.run_preflight()
        self.assertFalse(result.ok)
        self.assertTrue(any("Appium" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
