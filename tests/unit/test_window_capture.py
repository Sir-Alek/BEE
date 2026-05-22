"""Tests for window_capture helpers."""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from core.ui_automation.window_capture import (
    _emulator_port_hint,
    find_android_emulator_hwnd,
    find_legacy_app_hwnd,
    hwnd_to_monitor,
    is_emulator_device_id,
)


class TestWindowCapture(unittest.TestCase):
    def test_is_emulator_device_id(self) -> None:
        self.assertTrue(is_emulator_device_id("emulator-5554"))
        self.assertFalse(is_emulator_device_id("R58M123ABC"))
        self.assertFalse(is_emulator_device_id(""))

    def test_emulator_port_hint(self) -> None:
        self.assertEqual(_emulator_port_hint("emulator-5554"), "5554")
        self.assertIsNone(_emulator_port_hint("device-1"))

    def test_hwnd_to_monitor_non_windows(self) -> None:
        with patch.object(sys, "platform", "linux"):
            self.assertIsNone(hwnd_to_monitor(12345))

    def test_find_legacy_app_hwnd_non_windows(self) -> None:
        with patch.object(sys, "platform", "darwin"):
            self.assertIsNone(find_legacy_app_hwnd("Notepad"))

    def test_find_android_emulator_hwnd_non_windows(self) -> None:
        with patch.object(sys, "platform", "linux"):
            self.assertIsNone(find_android_emulator_hwnd("emulator-5554"))


if __name__ == "__main__":
    unittest.main()
