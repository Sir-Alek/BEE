"""Publicación Gherkin en Jira vanilla (descripción / criterios ADF)."""
from __future__ import annotations

from typing import Any, Dict, List

import requests

from core.req_intelligence.integrations_service import get_jira_extractor
from core.req_intelligence.publishers.base import PublishContext, PublishResult


def _adf_code_block(text: str, title: str = "BDD Feature") -> Dict[str, Any]:
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": title}],
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "gherkin"},
                "content": [{"type": "text", "text": text}],
            },
        ],
    }


class JiraVanillaPublisher:
    target = "jira_vanilla"

    def publish(self, ctx: PublishContext) -> PublishResult:
        profile = ctx.profile or {}
        jira_cfg = profile.get("jira") or {}
        issue_key = (ctx.issue_key or jira_cfg.get("default_issue_key") or "").strip()
        if not issue_key:
            return PublishResult(False, "jira_vanilla", "Issue key requerido (ej. QA-104)")
        try:
            ex, _ = get_jira_extractor(inline=True, creds=jira_cfg)
        except ValueError as e:
            return PublishResult(False, "jira_vanilla", str(e))

        target_field = str(jira_cfg.get("target_field") or "description").strip().lower()
        field_id = "description" if target_field != "acceptance" else None
        adf = _adf_code_block(ctx.gherkin_text, ctx.feature_name or "Feature BDD")

        if field_id == "description":
            payload = {"fields": {"description": adf}}
        else:
            payload = {
                "fields": {
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Criterios BDD (ELIA):"}],
                            },
                            adf["content"][1],
                        ],
                    }
                }
            }

        url = f"{ex.url}/rest/api/3/issue/{issue_key}"
        r = ex.session.put(
            url,
            headers={"Authorization": ex.auth_header, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if r.status_code in (200, 204):
            browse = f"{ex.url}/browse/{issue_key}"
            return PublishResult(
                True,
                "jira_vanilla",
                f"Historia {issue_key} actualizada",
                external_id=issue_key,
                url=browse,
            )
        return PublishResult(False, "jira_vanilla", f"Jira {r.status_code}: {r.text[:300]}")

    def smoke_test(self, profile: Dict[str, Any]) -> PublishResult:
        from core.req_intelligence.integrations_service import jira_smoke_test

        out = jira_smoke_test(inline=True, creds=profile.get("jira"))
        return PublishResult(bool(out.get("ok")), "jira_vanilla", "Jira OK" if out.get("ok") else "Jira falló")
