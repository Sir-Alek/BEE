"""Tests del escáner de grabaciones."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from core.req_intelligence.recording_scanner import scan_project_recordings


class TestRecordingScanner(unittest.TestCase):
    def test_scan_json_mobile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = os.path.join(tmp, "scripts")
            os.makedirs(scripts)
            path = os.path.join(scripts, "flow.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"platform": "mobile", "events": []}, f)
            refs = scan_project_recordings(tmp, "Proj")
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].platform, "mobile")
            self.assertEqual(refs[0].file_name, "flow.json")


if __name__ == "__main__":
    unittest.main()
