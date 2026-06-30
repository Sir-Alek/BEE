"""Pruebas de tool_paths.json y validación."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import tool_paths as tp


class TestValidateStudio(unittest.TestCase):
    def test_validate_studio_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(bin_dir)
            exe = os.path.join(bin_dir, "studio64.exe")
            open(exe, "wb").close()
            ok, resolved, _msg = tp.validate_studio_path(tmp)
            self.assertTrue(ok)
            self.assertEqual(resolved, exe)

    def test_validate_studio_exe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "studio64.exe")
            open(exe, "wb").close()
            ok, resolved, _msg = tp.validate_studio_path(exe)
            self.assertTrue(ok)
            self.assertEqual(resolved, exe)


class TestSaveLoad(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(tp.elia_paths, "ensure_user_data_root", return_value=root):
                tp._cache = None
                tp.save_tool_paths({"android_studio": r"D:\Studio\bin\studio64.exe"})
                loaded = tp.load_tool_paths(force=True)
            self.assertEqual(loaded.get("android_studio"), r"D:\Studio\bin\studio64.exe")
            data = json.loads((root / "tool_paths.json").read_text(encoding="utf-8"))
            self.assertEqual(data["android_studio"], r"D:\Studio\bin\studio64.exe")
