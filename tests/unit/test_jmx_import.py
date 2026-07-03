"""Tests importador JMeter (.jmx)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.api_automation.jmx_import.groovy_translate import translate_groovy_scripts
from core.api_automation.jmx_import.mapper import (
    commit_jmx_import,
    load_jmx_import_meta,
    preview_jmx_import,
    resolve_jmx_import_meta,
)
from core.api_automation.jmx_import.parser import parse_jmx_bytes

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "jmx" / "minimal.jmx"
DOMICILIACION = Path(r"c:\Users\APPEQP146\Desktop\proyects\Performance\DOMICILIACION.jmx")
SEGURIDAD = Path(r"c:\Users\APPEQP146\Desktop\proyects\Performance\Seguridad.jmx")


class TestJmxImport(unittest.TestCase):
    def test_parse_minimal_fixture(self) -> None:
        data = FIXTURE.read_bytes()
        plan = parse_jmx_bytes(data, source_name="minimal.jmx")
        self.assertEqual(len(plan.thread_groups), 1)
        self.assertEqual(plan.arguments[0].name, "URL")
        self.assertEqual(len(plan.csv_datasets), 1)

    def test_preview_minimal(self) -> None:
        report = preview_jmx_import(FIXTURE.read_bytes(), source_name="minimal.jmx")
        self.assertEqual(report.imported_http, 2)
        self.assertEqual(report.imported_extractors, 1)
        self.assertIn("URL", report.imported_variables)
        self.assertGreaterEqual(report.executability_pct, 5)
        self.assertTrue(any(g.kind == "GroovyTranslated" for g in report.groovy_translations))

    def test_groovy_simple_put_translation(self) -> None:
        translations = translate_groovy_scripts("demo", ["vars.put('x','1')"], [])
        self.assertEqual(translations[0].status, "translated")
        self.assertIn('pm.variables.set("x", "1")', translations[0].pre_script or "")

    def test_commit_minimal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_behave(plat: str) -> Path:
                return root / plat

            project = "JmxTest"
            with patch("core.api_automation.traffic_store.behave_projects_dir", side_effect=fake_behave):
                result = commit_jmx_import(project, FIXTURE.read_bytes(), source_name="minimal.jmx")
                self.assertTrue(result["ok"])
                self.assertEqual(result["count"], 2)
                self.assertTrue(Path(result["jmx_path"]).is_file())
                self.assertTrue(result["flow_id"])
                meta = load_jmx_import_meta(project)
                self.assertIsNotNone(meta)
                assert meta is not None
                self.assertEqual(meta["flow_id"], result["flow_id"])
                self.assertIn("load_suggestion", meta)
                from core.api_automation.traffic_store import delete_scenarios
                from core.api_automation.jmx_import.mapper import invalidate_jmx_import_meta_after_api_change

                delete_scenarios(project, result["scenario_ids"])
                cleared = invalidate_jmx_import_meta_after_api_change(
                    project,
                    deleted_scenario_ids=result["scenario_ids"],
                )
                self.assertTrue(cleared)
                self.assertIsNone(resolve_jmx_import_meta(project))

    def test_include_disabled_controllers_increases_count_on_seguridad(self) -> None:
        if not SEGURIDAD.is_file():
            self.skipTest("Seguridad.jmx no disponible")
        data = SEGURIDAD.read_bytes()
        normal = preview_jmx_import(data, source_name="Seguridad.jmx")
        forced = preview_jmx_import(data, source_name="Seguridad.jmx", include_disabled_controllers=True)
        self.assertGreaterEqual(forced.imported_http, normal.imported_http)

    @unittest.skipUnless(DOMICILIACION.is_file(), "DOMICILIACION.jmx no disponible")
    def test_preview_domiciliacion(self) -> None:
        report = preview_jmx_import(DOMICILIACION.read_bytes(), source_name="DOMICILIACION.jmx", thread_group_index=0)
        self.assertGreaterEqual(report.imported_http, 6)
        self.assertIn("URL", report.imported_variables)
        self.assertGreaterEqual(len(report.thread_groups), 3)

    @unittest.skipUnless(SEGURIDAD.is_file(), "Seguridad.jmx no disponible")
    def test_preview_seguridad(self) -> None:
        report = preview_jmx_import(SEGURIDAD.read_bytes(), source_name="Seguridad.jmx")
        self.assertGreaterEqual(report.imported_http, 6)
        self.assertGreaterEqual(report.imported_extractors, 8)


if __name__ == "__main__":
    unittest.main()
