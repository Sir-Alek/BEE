"""Tests for web UI runtime registry."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webui import web_runtime as wr


class TestWebRuntime(unittest.TestCase):
    def test_write_and_read_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "web_runtime.json"
            with patch.object(wr, "_runtime_path", return_value=path):
                wr.write_runtime(host="127.0.0.1", port=8765, pid=999, session_id="abc")
                data = wr.read_runtime()
            self.assertIsNotNone(data)
            assert data is not None
            self.assertEqual(data["port"], 8765)
            self.assertIn("elia_sid=abc", data["url"])

    def test_runtime_server_alive_false_when_unreachable(self) -> None:
        data = {"host": "127.0.0.1", "port": 1, "url": "http://127.0.0.1:1/api/app/about"}
        self.assertFalse(wr.runtime_server_alive(data))

    def test_try_attach_false_without_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            with patch.object(wr, "_runtime_path", return_value=path):
                self.assertFalse(wr.try_attach_to_running_instance())
                self.assertFalse(wr.try_attach_to_running_instance(open_browser=False))

    def test_build_ui_url_includes_session(self) -> None:
        url = wr.build_ui_url(host="127.0.0.1", port=8765, session_id="sid-1")
        self.assertEqual(url, "http://127.0.0.1:8765/?elia_sid=sid-1")

    def test_elia_ui_port_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ELIA_UI_PORT", None)
            self.assertEqual(wr.elia_ui_port(), wr.DEFAULT_ELIA_UI_PORT)

    def test_write_runtime_resets_pid_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "web_runtime.json"
            with patch.object(wr, "_runtime_path", return_value=path):
                wr.write_runtime(host="127.0.0.1", port=11111, pid=10, session_id="s1")
                wr.write_runtime(host="127.0.0.1", port=22222, pid=20, session_id="s2")
                data = wr.read_runtime()
            self.assertIsNotNone(data)
            assert data is not None
            self.assertEqual(data["port"], 22222)
            self.assertEqual(data["all_pids"], [20])
            self.assertEqual(data["session_id"], "s2")

    def test_terminate_sibling_skips_keep_pid(self) -> None:
        with patch.object(wr, "_collect_elia_process_pids", return_value=[10, 20, 30]), patch.object(
            wr, "_kill_pid"
        ) as kill:
            wr.terminate_sibling_elia_processes(keep_pid=20)
        kill.assert_any_call(10)
        kill.assert_any_call(30)
        self.assertEqual(kill.call_count, 2)


if __name__ == "__main__":
    unittest.main()
