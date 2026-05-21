"""
AI preferences and capabilities API — mode validation and round-trip persistence.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.api.support import ApiTestCase, elia_test_app


class TestAiPreferencesApi(ApiTestCase):
    def test_capabilities_returns_resolution_shape(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.get_json("/api/ai/capabilities")
            self.assertEqual(code, 200)
            self.assertIn("preferences", body)
            self.assertIn("capability", body)
            self.assertIn("resolution", body)
            self.assertIn(body["preferences"]["mode"], ("auto", "on", "off"))

    def test_preferences_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prefs_file = Path(tmp) / "ai_preferences.json"
            with patch("core.ai_policy._preferences_file", return_value=prefs_file):
                with elia_test_app() as (api, _):
                    for mode in ("off", "on", "auto"):
                        code, body = api.put_json("/api/ai/preferences", {"mode": mode})
                        self.assertEqual(code, 200, body)
                        self.assertEqual(body["preferences"]["mode"], mode)

                    stored = json.loads(prefs_file.read_text(encoding="utf-8"))
                    self.assertEqual(stored["mode"], "auto")

    def test_status_legacy_endpoint_still_works(self) -> None:
        with elia_test_app() as (api, _):
            code, body = api.get_json("/api/ai/status")
            self.assertEqual(code, 200)
            # May include model info or import_error — must not 500
            self.assertIsInstance(body, dict)


if __name__ == "__main__":
    unittest.main()
