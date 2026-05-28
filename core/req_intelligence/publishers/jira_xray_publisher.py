"""Publicación Gherkin vía Xray (import/feature)."""
from __future__ import annotations

from typing import Any, Dict

import requests

from core.req_intelligence.integrations_service import resolve_jira_credentials
from core.req_intelligence.publishers.base import PublishContext, PublishResult


class JiraXrayPublisher:
    target = "jira_xray"

    def publish(self, ctx: PublishContext) -> PublishResult:
        profile = ctx.profile or {}
        jira_cfg = profile.get("jira") or {}
        project_key = str(jira_cfg.get("project_key") or "").strip()
        if not project_key:
            return PublishResult(False, "jira_xray", "project_key requerido en perfil Jira")
        try:
            creds, _ = resolve_jira_credentials(inline=True, creds=jira_cfg)
        except ValueError as e:
            return PublishResult(False, "jira_xray", str(e))

        base = str(jira_cfg.get("xray_base_url") or creds["url"]).rstrip("/")
        url = f"{base}/rest/raven/1.0/import/feature"
        auth = (creds["email"], creds["api_token"])
        files = {"file": (f"{ctx.feature_name or 'feature'}.feature", ctx.gherkin_text.encode("utf-8"))}
        params = {"projectKey": project_key}
        if ctx.issue_key.strip():
            params["testEnvironments"] = ctx.issue_key.strip()

        r = requests.post(url, auth=auth, params=params, files=files, timeout=60)
        if r.status_code in (200, 201):
            return PublishResult(
                True,
                "jira_xray",
                f"Feature importado en Xray ({project_key})",
                external_id=project_key,
                details={"response": r.text[:500]},
            )
        return PublishResult(False, "jira_xray", f"Xray {r.status_code}: {r.text[:300]}")

    def smoke_test(self, profile: Dict[str, Any]) -> PublishResult:
        jira_cfg = profile.get("jira") or {}
        project_key = str(jira_cfg.get("project_key") or "").strip()
        if not project_key:
            return PublishResult(False, "jira_xray", "Configure project_key para Xray")
        try:
            creds, _ = resolve_jira_credentials(inline=True, creds=jira_cfg)
        except ValueError as e:
            return PublishResult(False, "jira_xray", str(e))
        base = str(jira_cfg.get("xray_base_url") or creds["url"]).rstrip("/")
        r = requests.get(
            f"{base}/rest/api/2/project/{project_key}",
            auth=(creds["email"], creds["api_token"]),
            timeout=15,
        )
        if r.status_code == 200:
            return PublishResult(True, "jira_xray", f"Proyecto Xray/Jira {project_key} accesible")
        return PublishResult(False, "jira_xray", f"Xray smoke {r.status_code}")
