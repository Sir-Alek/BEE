"""Tests for gRPC step helpers (preflight, lazy deps)."""
from __future__ import annotations

import unittest

from core.api_automation.driver_capabilities import grpc_driver_status
from core.api_automation.runtime.grpc_step import grpc_preflight, run_grpc_step


class TestGrpcStep(unittest.TestCase):
    def test_grpc_preflight_requires_target(self) -> None:
        result = grpc_preflight({}, variables={})
        self.assertFalse(result["ok"])
        self.assertIn("target", str(result.get("error", "")).lower())

    def test_run_grpc_step_requires_fields(self) -> None:
        result = run_grpc_step({}, variables={})
        self.assertFalse(result["ok"])
        self.assertIn("target", str(result.get("error", "")).lower())

    def test_grpc_driver_status_shape(self) -> None:
        status = grpc_driver_status()
        self.assertIn("available", status)
        self.assertIn("missing", status)
        self.assertIsInstance(status["missing"], list)
