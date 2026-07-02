"""Tests para collection_store (registro de colecciones API)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.api_automation import collection_store as cs


class TestEnsureDefaultCollection(unittest.TestCase):
    def test_does_not_wipe_existing_registry_on_read_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_behave_projects_dir(plat: str) -> Path:
                return root / plat

            project = "DemoProj"
            proj_dir = root / "api" / project
            proj_dir.mkdir(parents=True)
            registry_path = proj_dir / "collections.json"
            original = {
                "collections": [
                    {"id": "_default", "name": "General", "source": "template"},
                    {"id": "demo", "name": "Demo ELIA", "source": "template"},
                ]
            }
            registry_path.write_text(json.dumps(original), encoding="utf-8")

            with patch.object(cs, "behave_projects_dir", side_effect=fake_behave_projects_dir):
                with patch.object(cs, "_load_registry", return_value={"collections": []}):
                    cs.ensure_default_collection(project)

            data = json.loads(registry_path.read_text(encoding="utf-8"))
            ids = [c["id"] for c in data["collections"]]
            self.assertIn("demo", ids)
            self.assertIn("_default", ids)

    def test_creates_default_when_registry_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_behave_projects_dir(plat: str) -> Path:
                return root / plat

            project = "NewProj"
            with patch.object(cs, "behave_projects_dir", side_effect=fake_behave_projects_dir):
                cid = cs.ensure_default_collection(project)

            self.assertEqual(cid, "_default")
            registry_path = root / "api" / project / "collections.json"
            self.assertTrue(registry_path.is_file())
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(data["collections"][0]["id"], "_default")


if __name__ == "__main__":
    unittest.main()
