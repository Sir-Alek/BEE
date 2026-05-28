"""Tests unitarios de publicación BDD multi-destino (sin red real)."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from core.req_intelligence.connectors_profiles_store import (
    load_profile_by_id,
    normalize_document,
    normalize_profile,
)
from core.req_intelligence.publishers.base import PublishContext
from core.req_intelligence.publishers.dispatcher import PublisherDispatcher, publish_gherkin
from core.req_intelligence.publishers.local_file_publisher import LocalFilePublisher


PROFILE = normalize_profile(
    {
        "id": "p1",
        "name": "Test",
        "jira": {
            "url": "https://jira.example.com",
            "email": "qa@example.com",
            "api_token": "tok",
            "project_key": "QA",
            "default_issue_key": "QA-1",
        },
        "value_edge": {
            "url": "https://ve.example.com",
            "shared_space": "s1",
            "workspace": "w1",
            "tech_preview_flag": "true",
            "login": "https://ve.example.com/authentication/sign_in",
            "user": "u",
            "password": "p",
            "default_requirement_id": "1001",
        },
        "git": {
            "repo_url": "https://github.com/acme/repo",
            "token": "ghp_test",
            "branch": "main",
            "base_path": "features/",
        },
        "azure_devops": {
            "org": "org",
            "project": "proj",
            "pat": "pat",
            "default_work_item_id": "42",
        },
    }
)


class TestConnectorsNormalize(unittest.TestCase):
    def test_normalize_v1_profile_adds_publish_fields(self) -> None:
        raw = {
            "version": 1,
            "profiles": [
                {
                    "id": "x",
                    "name": "Legacy",
                    "jira": {"url": "https://jira.example.com", "email": "a@b.c", "api_token": "t"},
                    "value_edge": {"url": "https://ve.example.com", "shared_space": "s", "workspace": "w"},
                }
            ],
        }
        doc = normalize_document(raw)
        self.assertEqual(doc["version"], 2)
        prof = doc["profiles"][0]
        self.assertIn("git", prof)
        self.assertEqual(prof["jira"]["mode"], "vanilla")

    @patch("core.req_intelligence.connectors_profiles_store.load_document")
    def test_load_profile_by_id(self, mock_load: MagicMock) -> None:
        mock_load.return_value = normalize_document({"version": 2, "profiles": [PROFILE]})
        found = load_profile_by_id("p1")
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "Test")


class TestLocalFilePublisher(unittest.TestCase):
    def test_publish_writes_feature_file(self) -> None:
        pub = LocalFilePublisher()
        with tempfile.TemporaryDirectory() as tmp:
            ctx = PublishContext(
                gherkin_text="Feature: Demo\n  Scenario: S\n    Given x",
                feature_name="Demo",
                output_dir=tmp,
            )
            result = pub.publish(ctx)
            self.assertTrue(result.ok)
            path = os.path.join(tmp, "Demo.feature")
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as f:
                self.assertIn("Feature: Demo", f.read())


class TestJiraVanillaPublisher(unittest.TestCase):
    @patch("core.req_intelligence.publishers.jira_vanilla_publisher.get_jira_extractor")
    def test_publish_puts_issue(self, mock_get: MagicMock) -> None:
        from core.req_intelligence.publishers.jira_vanilla_publisher import JiraVanillaPublisher

        extractor = MagicMock()
        extractor.url = "https://jira.example.com"
        extractor.auth_header = "Basic x"
        extractor.session.put.return_value = MagicMock(status_code=204, text="")
        mock_get.return_value = (extractor, "inline")

        ctx = PublishContext(
            gherkin_text="Feature: X\n  Scenario: Y",
            profile=PROFILE,
            issue_key="QA-99",
        )
        result = JiraVanillaPublisher().publish(ctx)
        self.assertTrue(result.ok)
        self.assertEqual(result.external_id, "QA-99")
        extractor.session.put.assert_called_once()


class TestDispatcher(unittest.TestCase):
    def test_unknown_target(self) -> None:
        d = PublisherDispatcher(adapters={})
        ctx = PublishContext(gherkin_text="Feature: A")
        result = d.publish("git", ctx)
        self.assertFalse(result.ok)

    @patch("core.req_intelligence.publishers.dispatcher.load_profile_by_id")
    def test_publish_gherkin_missing_profile(self, mock_load: MagicMock) -> None:
        mock_load.return_value = None
        result = publish_gherkin(target="local_file", gherkin_text="Feature: A", profile_id="missing")
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
