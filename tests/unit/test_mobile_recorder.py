"""Pruebas de configuración Appium para grabación móvil."""
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.paths import REPO_ROOT

ROOT = REPO_ROOT


def _load_mobile_recorder_py():
    path = ROOT / "core" / "ui_automation" / "mobile_recorder.py"
    spec = importlib.util.spec_from_file_location("mobile_recorder_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mr = _load_mobile_recorder_py()


class TestMobileRecorderCapabilities(unittest.TestCase):
    def test_apk_path_on_pc(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tmp:
            tmp.write(b"fake")
            apk = tmp.name
        try:
            caps: dict = {}
            err = mr._apply_android_app_capabilities(
                caps,
                apk_path=apk,
                app_package="",
                app_activity="",
                device_id="emulator-5554",
            )
            self.assertIsNone(err)
            self.assertEqual(caps.get("appium:app"), apk)
            self.assertNotIn("appium:appPackage", caps)
        finally:
            os.unlink(apk)

    def test_installed_app_package_and_activity(self) -> None:
        caps: dict = {}
        err = mr._apply_android_app_capabilities(
            caps,
            apk_path="",
            app_package="com.example.app",
            app_activity=".MainActivity",
            device_id="device1",
        )
        self.assertIsNone(err)
        self.assertEqual(caps["appium:appPackage"], "com.example.app")
        self.assertEqual(caps["appium:appActivity"], ".MainActivity")

    @patch.object(mr, "_resolve_main_activity", return_value=".Launcher")
    def test_resolves_activity_when_missing(self, _mock: object) -> None:
        caps: dict = {}
        err = mr._apply_android_app_capabilities(
            caps,
            apk_path="",
            app_package="com.example.app",
            app_activity="",
            device_id="device1",
        )
        self.assertIsNone(err)
        self.assertEqual(caps["appium:appActivity"], ".Launcher")

    def test_missing_apk_and_package_errors(self) -> None:
        caps: dict = {}
        err = mr._apply_android_app_capabilities(
            caps,
            apk_path="",
            app_package="",
            app_activity="",
            device_id="device1",
        )
        self.assertIsNotNone(err)

    def test_import_appium_client(self) -> None:
        if importlib.util.find_spec("appium") is None:
            self.skipTest("Appium-Python-Client no instalado")
        webdriver_mod, options_cls = mr._import_appium_client()
        self.assertTrue(callable(getattr(webdriver_mod, "Remote", None)))
        self.assertTrue(callable(options_cls))


if __name__ == "__main__":
    unittest.main()
