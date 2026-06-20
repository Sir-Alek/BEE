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


class TestCanonicalEmulatorExe(unittest.TestCase):
    def test_maps_qemu_binary_to_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as sdk:
            emulator_dir = os.path.join(sdk, "emulator")
            qemu_dir = os.path.join(emulator_dir, "qemu", "windows-x86_64")
            os.makedirs(qemu_dir, exist_ok=True)
            wrapper = os.path.join(emulator_dir, "emulator.exe")
            qemu = os.path.join(qemu_dir, "qemu-system-x86_64.exe")
            open(wrapper, "wb").close()
            open(qemu, "wb").close()
            got = ma._canonical_emulator_exe(qemu)
            self.assertEqual(got, wrapper)

    def test_accepts_wrapper_path(self) -> None:
        with tempfile.TemporaryDirectory() as emulator_dir:
            wrapper = os.path.join(emulator_dir, "emulator.exe")
            open(wrapper, "wb").close()
            self.assertEqual(ma._canonical_emulator_exe(wrapper), wrapper)

    def test_rejects_unknown_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            other = os.path.join(tmp, "foo.exe")
            open(other, "wb").close()
            self.assertIsNone(ma._canonical_emulator_exe(other))


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
    @patch.object(ma, "resolve_appium")
    @patch.object(ma, "list_avds", return_value=(["Pixel_7"], None))
    @patch.object(ma, "list_devices", return_value=([], None))
    @patch.object(ma, "resolve_emulator")
    @patch.object(ma, "resolve_adb")
    @patch.object(ma, "resolve_android_sdk")
    def test_preflight_fails_without_appium_installed(
        self,
        mock_sdk,
        mock_adb,
        mock_emulator,
        _list_dev,
        _list_avd,
        mock_resolve_appium,
        _appium,
    ) -> None:
        mock_sdk.return_value = (r"C:\Android\Sdk", "android_home")
        mock_adb.return_value = ma.AndroidTool(name="adb", path=r"C:\adb.exe")
        mock_emulator.return_value = ma.AndroidTool(name="emulator", path=r"C:\emu.exe")
        mock_resolve_appium.return_value = ma.AndroidTool(name="appium", path=None)
        result = ma.run_preflight()
        self.assertFalse(result.ok)
        self.assertTrue(any("Appium no instalado" in e for e in result.errors))

    @patch.object(ma, "check_appium_server", return_value=False)
    @patch.object(ma, "resolve_appium")
    @patch.object(ma, "list_avds", return_value=(["Pixel_7"], None))
    @patch.object(ma, "list_devices", return_value=([], None))
    @patch.object(ma, "resolve_emulator")
    @patch.object(ma, "resolve_adb")
    @patch.object(ma, "resolve_android_sdk")
    def test_preflight_ok_when_appium_installed_but_stopped(
        self,
        mock_sdk,
        mock_adb,
        mock_emulator,
        _list_dev,
        _list_avd,
        mock_resolve_appium,
        _appium,
    ) -> None:
        mock_sdk.return_value = (r"C:\Android\Sdk", "android_home")
        mock_adb.return_value = ma.AndroidTool(name="adb", path=r"C:\adb.exe")
        mock_emulator.return_value = ma.AndroidTool(name="emulator", path=r"C:\emu.exe")
        mock_resolve_appium.return_value = ma.AndroidTool(name="appium", path=r"C:\appium.cmd")
        result = ma.run_preflight()
        self.assertTrue(result.ok)
        self.assertTrue(any("instalado pero no responde" in w for w in result.warnings))

    @patch.object(ma, "check_appium_server", return_value=True)
    @patch.object(ma, "resolve_appium")
    @patch.object(ma, "list_avds", return_value=([], "emulator no encontrado. Instala Android Emulator o define ANDROID_HOME."))
    @patch.object(ma, "list_devices", return_value=([], None))
    @patch.object(ma, "resolve_emulator")
    @patch.object(ma, "resolve_adb")
    @patch.object(ma, "resolve_android_sdk")
    def test_preflight_emulator_missing_warning_is_unified(
        self,
        mock_sdk,
        mock_adb,
        mock_emulator,
        _list_dev,
        _list_avd,
        mock_resolve_appium,
        _appium,
    ) -> None:
        mock_sdk.return_value = (r"C:\Android\Sdk", "android_home")
        mock_adb.return_value = ma.AndroidTool(name="adb", path=r"C:\adb.exe")
        mock_emulator.return_value = ma.AndroidTool(name="emulator", path=None)
        mock_resolve_appium.return_value = ma.AndroidTool(name="appium", path=r"C:\appium.cmd")
        result = ma.run_preflight()
        self.assertTrue(result.ok)
        emulator_warnings = [w for w in result.warnings if "Android Emulator" in w]
        self.assertEqual(len(emulator_warnings), 1)
        self.assertIn("No se detectó Android Emulator", emulator_warnings[0])


class TestAppiumServer(unittest.TestCase):
    @patch.object(ma, "check_appium_server", return_value=True)
    def test_start_appium_reuses_running_server(self, _check) -> None:
        res = ma.start_appium_server()
        self.assertTrue(res["ok"])
        self.assertTrue(res["reused"])


class TestDetectForegroundPackage(unittest.TestCase):
    def test_parse_top_resumed_activity(self) -> None:
        text = (
            "topResumedActivity=ActivityRecord{abc u0 com.sec.android.app.popupcalculator/.CalcActivity t123}"
        )
        picked = ma._pick_foreground_candidate(ma._parse_focus_candidates(text))
        assert picked is not None
        self.assertEqual(picked[0], "com.sec.android.app.popupcalculator")
        self.assertEqual(picked[1], ".CalcActivity")

    def test_skips_launcher_when_app_also_present(self) -> None:
        text = (
            "topResumedActivity=ActivityRecord{a u0 com.sec.android.app.launcher/.Launcher t1}\n"
            "mResumedActivity: ActivityRecord{b u0 com.example.app/.MainActivity t2}"
        )
        picked = ma._pick_foreground_candidate(ma._parse_focus_candidates(text))
        assert picked is not None
        self.assertEqual(picked[0], "com.example.app")


if __name__ == "__main__":
    unittest.main()
