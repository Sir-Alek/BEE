"""Tests de vinculación BDD y merge de pasos."""
from __future__ import annotations

import os
import tempfile
import unittest

from core.req_intelligence.feature_scanner import merge_steps_into_scenario
from core.ui_automation.recording_linkage import (
    apply_grouped_link_to_scenario,
    apply_link_to_existing_scenario,
    decode_scenario_link,
    encode_scenario_link,
    extract_all_scenario_steps,
)


class TestScenarioLink(unittest.TestCase):
    def test_encode_decode(self) -> None:
        raw = encode_scenario_link("/proj/features/a.feature", "Login ok")
        self.assertEqual(decode_scenario_link(raw), ("/proj/features/a.feature", "Login ok"))

    def test_extract_all_scenarios(self) -> None:
        text = (
            "Feature: X\n\n"
            "  Scenario: Uno\n"
            "    Given a\n"
            "    When b\n"
            "  Scenario: Dos\n"
            "    Then c\n"
        )
        steps = extract_all_scenario_steps(text)
        self.assertEqual(steps, ["Given a", "When b", "Then c"])


class TestMergeSteps(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "f.feature")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(
                "Feature: Demo\n"
                "  Scenario: Target\n"
                "    Given existente\n"
            )

    def test_append_mode(self) -> None:
        ok = merge_steps_into_scenario(
            self.path,
            "Target",
            ["When nuevo paso"],
            mode="append",
        )
        self.assertTrue(ok)
        with open(self.path, encoding="utf-8") as f:
            body = f.read()
        self.assertIn("Given existente", body)
        self.assertIn("When nuevo paso", body)
        self.assertTrue(body.index("Given existente") < body.index("When nuevo paso"))

    def test_replace_mode(self) -> None:
        merge_steps_into_scenario(
            self.path, "Target", ["Then solo"], mode="replace"
        )
        with open(self.path, encoding="utf-8") as f:
            body = f.read()
        self.assertNotIn("existente", body)
        self.assertIn("Then solo", body)

    def test_apply_grouped_link(self) -> None:
        generated = (
            "Feature: Agrupado\n"
            "  Scenario: Flujo A\n"
            "    When hace A\n"
            "  Scenario: Flujo B\n"
            "    Then ve B\n"
        )
        self.assertTrue(
            apply_grouped_link_to_scenario(generated, self.path, "Target", mode="append")
        )
        with open(self.path, encoding="utf-8") as f:
            body = f.read()
        self.assertIn("When hace A", body)
        self.assertIn("Then ve B", body)


if __name__ == "__main__":
    unittest.main()
