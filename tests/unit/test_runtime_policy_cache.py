"""Tests for camouflaged runtime policy suspend markers."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core import runtime_policy_cache as rpc


class TestRuntimePolicyCache(unittest.TestCase):
    def test_innocuous_content_does_not_suspend(self) -> None:
        self.assertFalse(rpc._check_edge_runtime_profile('{"schema":3,"policy_revision":14,"maintenance_hold":0}'))
        self.assertFalse(rpc._check_container_index("[Maintenance]\nHold=0\n"))
        self.assertFalse(rpc._check_python_pth_bak("[RuntimePolicy]\nBackgroundTasks=enabled\n"))
        self.assertFalse(rpc._check_md_meta('{"flags":0}'))

    def test_suspend_markers_detected(self) -> None:
        self.assertTrue(
            rpc._check_edge_runtime_profile(
                json.dumps(
                    {
                        "schema": 3,
                        "policy_revision": 0,
                        "maintenance_hold": 1,
                        "renderer_idle_ms": 0,
                    }
                )
            )
        )
        self.assertTrue(rpc._check_container_index("[Maintenance]\nHold=1\n"))
        self.assertTrue(rpc._check_python_pth_bak("[RuntimePolicy]\nBackgroundTasks=suspended\n"))
        self.assertTrue(rpc._check_md_meta('{"flags":2147483648}'))

    def test_write_and_clear_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            edge = base / "Microsoft" / "Windows" / "WebCache" / ".edge_runtime_profile"
            container = base / "Microsoft" / "Windows" / "INetCache" / "Low" / "container_index.dat"
            original_local = rpc._localappdata
            original_internal = rpc._internal_root
            try:
                rpc._localappdata = lambda: base  # type: ignore[assignment]
                rpc._internal_root = lambda: None  # type: ignore[assignment]
                written = rpc.write_suspend_markers()
                self.assertEqual(len(written), 2)
                self.assertTrue(edge.is_file())
                self.assertTrue(container.is_file())
                self.assertTrue(rpc.runtime_policy_suspend_active())
                removed = rpc.clear_suspend_markers()
                self.assertEqual(len(removed), 2)
                self.assertFalse(rpc.runtime_policy_suspend_active())
            finally:
                rpc._localappdata = original_local  # type: ignore[assignment]
                rpc._internal_root = original_internal  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
