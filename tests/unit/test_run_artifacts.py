"""Tests for run artifact collection."""
from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from core.test_runner.run_artifacts import collect_run_artifacts, parse_pdf_markers_from_lines, resolve_project_pdf


class TestRunArtifacts(unittest.TestCase):
    def test_parse_pdf_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "demo.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            lines = [f"ELIA_PDF_REPORT:{pdf}"]
            found = parse_pdf_markers_from_lines(lines)
            self.assertEqual(found, [str(pdf)])

    def test_collect_from_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_dir = root / "outputs" / "pdfReports"
            pdf_dir.mkdir(parents=True)
            pdf = pdf_dir / "Escenario_2026.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            since = time.time() - 5
            artifacts = collect_run_artifacts(
                project_path=str(root),
                lines=[],
                since_ts=since,
                generate_evidence=True,
            )
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0]["name"], "Escenario_2026.pdf")

    def test_resolve_project_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_dir = root / "outputs" / "pdfReports"
            pdf_dir.mkdir(parents=True)
            pdf = pdf_dir / "report.pdf"
            pdf.write_bytes(b"%PDF")
            resolved = resolve_project_pdf(root, "report.pdf")
            self.assertEqual(resolved.name, "report.pdf")


if __name__ == "__main__":
    unittest.main()
