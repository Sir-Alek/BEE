"""Tests para manifest de modelos Qwen."""
from __future__ import annotations

import unittest

from core.ai.manifest import list_models, load_manifest, profile_roles


class TestAiManifest(unittest.TestCase):
    def test_manifest_loads(self) -> None:
        data = load_manifest()
        self.assertEqual(data.get("version"), 1)
        self.assertGreaterEqual(len(data.get("models") or []), 3)

    def test_lite_has_single_role(self) -> None:
        roles = profile_roles("lite")
        self.assertEqual(roles, ["lite_unified"])

    def test_standard_has_two_roles(self) -> None:
        roles = profile_roles("standard")
        self.assertIn("analysis", roles)
        self.assertIn("codegen", roles)

    def test_list_models_standard(self) -> None:
        models = list_models(profile="standard")
        self.assertEqual(len(models), 2)


if __name__ == "__main__":
    unittest.main()
