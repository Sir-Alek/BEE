"""Estilo Gherkin: sin prefijos redundantes Verificar / el contexto es."""
from __future__ import annotations

import unittest

from core.req_intelligence.bdd_doc_converter import _heuristic_gherkin, _sanitize_gherkin_text
from core.req_intelligence.doc_ingestion import DocChunk


class TestGherkinStyle(unittest.TestCase):
    def test_heuristic_matrix_without_redundant_prefixes(self) -> None:
        chunk = DocChunk(
            id="t_1",
            source_file="matriz.xlsx",
            title="Caso CP001: Filtro por ETV",
            content="...",
            chunk_type="test_matrix",
            row_data={
                "id": "CP001",
                "name": "Filtro por ETV",
                "description": "Validar filtrado por empresa de valores",
                "preconditions": "ATM con ETV asignada",
                "steps": "Seleccionar ETV > Aplicar filtro",
                "expected": "Solo ATM de la ETV seleccionada",
            },
        )
        gherkin = _heuristic_gherkin(chunk)
        self.assertIn("Scenario: Filtro por ETV", gherkin)
        self.assertNotIn("Verificar:", gherkin)
        self.assertNotIn("el contexto es:", gherkin)
        self.assertIn("Given ATM con ETV asignada", gherkin)
        self.assertIn("When Seleccionar ETV", gherkin)

    def test_sanitize_llm_like_output(self) -> None:
        raw = (
            "Feature: X\n"
            "  Scenario: Verificar: Caso CP001: Filtro por ETV\n"
            "    Given el contexto es: Validar filtrado\n"
            "    When hacer algo\n"
            "    Then resultado\n"
        )
        clean = _sanitize_gherkin_text(raw)
        self.assertIn("Scenario: Filtro por ETV", clean)
        self.assertIn("Given Validar filtrado", clean)
        self.assertNotIn("Verificar:", clean)
        self.assertNotIn("el contexto es:", clean)

    def test_sanitize_normalizes_spanish_keywords(self) -> None:
        raw = (
            "Feature: X\n"
            "  Scenario: Demo\n"
            "    Dado el usuario autenticado\n"
            "    Cuando abre el módulo\n"
            "    Entonces ve el panel\n"
        )
        clean = _sanitize_gherkin_text(raw)
        self.assertIn("Given el usuario autenticado", clean)
        self.assertIn("When abre el módulo", clean)
        self.assertIn("Then ve el panel", clean)


if __name__ == "__main__":
    unittest.main()
