"""Tests para CHANGELOG.md y versión mostrada al usuario."""
from __future__ import annotations

import os
import unittest

from core._version import ELIA_VERSION, elia_version_display
from core.changelog import load_changelog, parse_changelog_markdown


class TestChangelogParser(unittest.TestCase):
    def test_parse_sections_and_order(self) -> None:
        text = """
# Changelog

## [0.6.61] - 2026-05-22

### Añadido
- Primera novedad.

### Corregido
- Un arreglo.

## [0.6.5] - 2026-05-21

### Cambiado
- Un cambio.
"""
        entries = parse_changelog_markdown(text)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["version"], "0.6.61")
        self.assertEqual(entries[0]["date"], "2026-05-22")
        self.assertEqual(entries[0]["added"], ["Primera novedad."])
        self.assertEqual(entries[0]["fixed"], ["Un arreglo."])
        self.assertEqual(entries[1]["changed"], ["Un cambio."])

    def test_load_repo_changelog(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        entries = load_changelog(repo_root)
        self.assertGreaterEqual(len(entries), 6)
        versions = [entry["version"] for entry in entries]
        self.assertIn("0.6.61", versions)
        self.assertIn("0.5.0", versions)


class TestVersionDisplay(unittest.TestCase):
    def test_beta_suffix_before_1_0(self) -> None:
        display = elia_version_display()
        self.assertTrue(display.endswith("-beta"))
        self.assertTrue(display.startswith(ELIA_VERSION))


if __name__ == "__main__":
    unittest.main()
