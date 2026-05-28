"""Publicación Gherkin en Azure DevOps Work Items."""
from __future__ import annotations

import base64
from typing import Any, Dict, List

import requests

from core.req_intelligence.publishers.base import PublishContext, PublishResult


class AzureDevOpsPublisher:
    target = "azure_devops"

    def publish(self, ctx: PublishContext) -> PublishResult:
        profile = ctx.profile or {}
        az = profile.get("azure_devops") or {}
        org = str(az.get("org") or "").strip()
        project = str(az.get("project") or "").strip()
        pat = str(az.get("pat") or "").strip()
        work_item_id = (ctx.work_item_id or az.get("default_work_item_id") or "").strip()
        target_field = str(az.get("target_field") or "System.Description").strip()
        if not all([org, project, pat, work_item_id]):
            return PublishResult(False, "azure_devops", "Perfil Azure incompleto (org, project, pat, work_item_id)")

        html = f"<pre><code>{_escape_html(ctx.gherkin_text)}</code></pre>"
        patch: List[Dict[str, Any]] = [
            {"op": "add", "path": f"/fields/{target_field}", "value": html},
        ]
        url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{work_item_id}?api-version=7.0"
        token = base64.b64encode(f":{pat}".encode()).decode()
        r = requests.patch(
            url,
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/json-patch+json"},
            json=patch,
            timeout=30,
        )
        if r.status_code in (200, 201):
            wi_url = f"https://dev.azure.com/{org}/{project}/_workitems/edit/{work_item_id}"
            return PublishResult(
                True,
                "azure_devops",
                f"Work item {work_item_id} actualizado",
                external_id=work_item_id,
                url=wi_url,
            )
        return PublishResult(False, "azure_devops", f"Azure {r.status_code}: {r.text[:300]}")

    def smoke_test(self, profile: Dict[str, Any]) -> PublishResult:
        az = profile.get("azure_devops") or {}
        org = str(az.get("org") or "").strip()
        project = str(az.get("project") or "").strip()
        pat = str(az.get("pat") or "").strip()
        if not all([org, project, pat]):
            return PublishResult(False, "azure_devops", "Faltan org, project o pat")
        url = f"https://dev.azure.com/{org}/{project}/_apis/projects/{project}?api-version=7.0"
        token = base64.b64encode(f":{pat}".encode()).decode()
        r = requests.get(url, headers={"Authorization": f"Basic {token}"}, timeout=15)
        if r.status_code == 200:
            return PublishResult(True, "azure_devops", f"Proyecto Azure {project} accesible")
        return PublishResult(False, "azure_devops", f"Azure smoke {r.status_code}")


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
