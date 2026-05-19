"""Tests para ingesta Word/Excel → DocChunk."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.req_intelligence.doc_ingestion import ExcelIngester


class TestExcelIngester(unittest.TestCase):
    def test_skips_summary_sheet_like_pronosticos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matriz.xlsx"
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                pd.DataFrame(
                    {
                        "Unnamed: 0": [None, None, "Estatus"],
                        "Unnamed: 1": [None, "Cuenta de Nombre del Caso", 8],
                        "Unnamed: 2": [None, "Aprobado", 12],
                    }
                ).to_excel(writer, sheet_name="Resumen", index=False)
                pd.DataFrame(
                    {
                        "ID_Caso": ["CP001"],
                        "Nombre del Caso": ["Filtro por ETV"],
                        "Descripción": ["Validar filtrado"],
                        "Precondiciones": ["ATM con ETV"],
                        "Pasos de Ejecución": ["Seleccionar ETV"],
                        "Resultado Esperado": ["Solo ATM de la ETV"],
                    }
                ).to_excel(writer, sheet_name="Casos de prueba", index=False)

            chunks = ExcelIngester().ingest(str(path))
            sheets = {(c.row_data or {}).get("sheet") for c in chunks}
            self.assertNotIn("Resumen", sheets)
            self.assertIn("Casos de prueba", sheets)
            cp = next(c for c in chunks if (c.row_data or {}).get("id") == "CP001")
            self.assertIn("Filtro por ETV", cp.title)
            self.assertIn("Seleccionar ETV", cp.content)
            self.assertIn("ATM con ETV", cp.content)

    def test_multi_sheet_matrix_on_second_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matriz.xlsx"
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                pd.DataFrame({"Nota": ["Portada del documento"]}).to_excel(
                    writer, sheet_name="Portada", index=False
                )
                pd.DataFrame(
                    {
                        "ID": ["TC-01", "TC-02"],
                        "Descripción": ["Login válido", "Login inválido"],
                        "Pasos": ["Ir a login", "Ir a login"],
                        "Resultado esperado": ["Entra al home", "Muestra error"],
                    }
                ).to_excel(writer, sheet_name="Matriz", index=False)

            chunks = ExcelIngester().ingest(str(path))
            self.assertGreaterEqual(len(chunks), 2)
            self.assertTrue(any("TC-01" in c.title or "Login válido" in c.content for c in chunks))
            self.assertTrue(any(c.row_data and c.row_data.get("sheet") == "Matriz" for c in chunks))

    def test_header_not_on_first_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "offset.xlsx"
            raw = pd.DataFrame(
                [
                    ["Matriz de pruebas", "", "", ""],
                    ["", "", "", ""],
                    ["ID", "Descripción", "Pasos", "Resultado esperado"],
                    ["1", "Caso A", "Paso 1", "OK"],
                ]
            )
            raw.to_excel(path, index=False, header=False)
            chunks = ExcelIngester().ingest(str(path))
            self.assertGreaterEqual(len(chunks), 1)
            self.assertIn("Caso A", chunks[0].content)


if __name__ == "__main__":
    unittest.main()
