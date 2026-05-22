"""Tests for encrypted ELIA AI memory store."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from core import elia_memory as mem
from core import elia_paths
from core.elia_memory_crypto import (
    EXPORT_FORMAT,
    decrypt_local_blob,
    decrypt_team_import,
    encrypt_local_document,
    encrypt_team_export,
)


class TestEliaMemoryCrypto(unittest.TestCase):
    def test_local_round_trip(self) -> None:
        doc = {"version": 1, "entries": [{"ts": 1.0, "script_fp": "abc", "script": "s", "feature": "f"}]}
        blob = encrypt_local_document(doc)
        restored = decrypt_local_blob(blob)
        self.assertEqual(restored["entries"][0]["feature"], "f")

    def test_team_export_import_round_trip(self) -> None:
        doc = {"version": 1, "entries": [{"ts": 2.0, "script_fp": "xyz", "script": "click", "feature": "When x"}]}
        exported = encrypt_team_export(doc, "EquipoQA")
        restored = decrypt_team_import(exported, "EquipoQA")
        self.assertEqual(len(restored["entries"]), 1)
        wrapper = json.loads(exported.decode("utf-8"))
        self.assertEqual(wrapper["format"], EXPORT_FORMAT)

    def test_team_wrong_passphrase_fails(self) -> None:
        exported = encrypt_team_export({"version": 1, "entries": []}, "good")
        with self.assertRaises(Exception):
            decrypt_team_import(exported, "bad")


class TestEliaMemoryStore(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = self._tmpdir.name

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _paths(self):
        return patch.object(elia_paths, "ensure_user_data_root", return_value=__import__("pathlib").Path(self._root))

    def test_migrates_legacy_json_to_enc(self) -> None:
        root = __import__("pathlib").Path(self._root)
        legacy = root / "elia_memory.json"
        legacy.write_text(
            json.dumps({"version": 1, "entries": [{"ts": 1, "script_fp": "a", "script": "s", "feature": "f"}]}),
            encoding="utf-8",
        )
        with self._paths():
            st = mem.memory_status()
        self.assertTrue(st["encrypted"])
        self.assertEqual(st["entries"], 1)
        self.assertFalse(legacy.is_file())
        self.assertTrue((root / "elia_memory.json.bak").is_file())

    def test_merge_prefers_imported_on_conflict(self) -> None:
        with self._paths():
            mem.append_correction(script_snippet="same script", feature_text="local feature")
            local_fp = mem.memory_status()["entries"]
            self.assertEqual(local_fp, 1)
            doc = {
                "version": 1,
                "entries": [
                    {
                        "ts": 99,
                        "script_fp": mem._fingerprint("same script"),  # type: ignore[attr-defined]
                        "script": "same script",
                        "feature": "imported feature",
                    },
                    {"ts": 100, "script_fp": "newfp1234567890", "script": "other", "feature": "other f"},
                ],
            }
            blob = encrypt_team_export(doc, "team")
            result = mem.import_from_team(blob, "team", "merge")
            self.assertEqual(result["updated"], 1)
            self.assertEqual(result["added"], 1)
            examples = mem.recent_examples_for_prompt(limit=5)
            features = {e["feature"] for e in examples}
            self.assertIn("imported feature", features)
            self.assertIn("other f", features)

    def test_replace_overwrites_all(self) -> None:
        with self._paths():
            mem.append_correction(script_snippet="old", feature_text="old f")
            doc = {"version": 1, "entries": [{"ts": 1, "script_fp": "n1", "script": "n", "feature": "only"}]}
            blob = encrypt_team_export(doc, "team")
            mem.import_from_team(blob, "team", "replace")
            examples = mem.recent_examples_for_prompt(limit=5)
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0]["feature"], "only")


if __name__ == "__main__":
    unittest.main()
