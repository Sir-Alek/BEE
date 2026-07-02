"""Tests para data_store (import CSV/XLSX)."""
from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from core.api_automation import data_store as ds


class TestDataStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_path = Path(self.tmp.name) / "resources" / "data"
        self.data_path.mkdir(parents=True)
        self.project = "TestProj"
        self.patcher = patch.object(ds, "data_dir", return_value=self.data_path)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self.tmp.cleanup()

    def test_import_csv(self) -> None:
        content = b"email,password\nuser1@test.com,pass1\n"
        result = ds.import_data_file(self.project, "users.csv", content)
        self.assertTrue(result["ok"])
        self.assertEqual(result["name"], "users.csv")
        self.assertEqual(result["source_format"], "csv")
        rows = ds.read_csv_rows(self.project, "users.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["email"], "user1@test.com")

    def test_import_empty_csv_fails(self) -> None:
        with self.assertRaises(ValueError):
            ds.import_data_file(self.project, "empty.csv", b"")

    def test_import_csv_without_headers_fails(self) -> None:
        with self.assertRaises(ValueError):
            ds.import_data_file(self.project, "bad.csv", b",,\n1,2,3\n")

    def test_import_invalid_name_fails(self) -> None:
        with self.assertRaises(ValueError):
            ds.import_data_file(self.project, "***.csv", b"a,b\n1,2\n")

    def test_import_overwrite(self) -> None:
        ds.import_data_file(self.project, "d.csv", b"x,y\n1,2\n")
        with self.assertRaises(FileExistsError):
            ds.import_data_file(self.project, "d.csv", b"x,y\n3,4\n")
        ds.import_data_file(self.project, "d.csv", b"x,y\n3,4\n", overwrite=True)
        rows = ds.read_csv_rows(self.project, "d.csv")
        self.assertEqual(rows[0]["x"], "3")

    def test_xlsx_conversion(self) -> None:
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl not installed")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["col1", "col2"])
        ws.append(["a", "b"])
        buf = BytesIO()
        wb.save(buf)
        result = ds.import_data_file(self.project, "data.xlsx", buf.getvalue())
        self.assertTrue(result["converted_from_xlsx"])
        self.assertEqual(result["name"], "data.csv")
        rows = ds.read_csv_rows(self.project, "data.csv")
        self.assertEqual(rows[0]["col1"], "a")

    def test_save_csv_content_validates(self) -> None:
        with self.assertRaises(ValueError):
            ds.save_csv_content(self.project, "x.csv", "")

    def test_read_csv_text(self) -> None:
        ds.import_data_file(self.project, "t.csv", b"h,v\n1,2\n")
        text = ds.read_csv_text(self.project, "t.csv")
        self.assertIn("h,v", text)
