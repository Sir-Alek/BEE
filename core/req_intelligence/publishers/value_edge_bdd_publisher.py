"""Publicación Gherkin como entidad bdd_spec en Value Edge."""
from __future__ import annotations

from typing import Any, Dict

import requests

from core.req_intelligence.integrations_service import get_value_edge_extractor
from core.req_intelligence.publishers.base import PublishContext, PublishResult


class ValueEdgeBddPublisher:
    target = "value_edge"

    def publish(self, ctx: PublishContext) -> PublishResult:
        profile = ctx.profile or {}
        ve_cfg = profile.get("value_edge") or {}
        req_id = (ctx.requirement_id or ve_cfg.get("default_requirement_id") or "").strip()
        if not req_id:
            return PublishResult(False, "value_edge", "ID de requerimiento/story VE requerido")
        try:
            ex, _ = get_value_edge_extractor(inline=True, creds=ve_cfg)
        except ValueError as e:
            return PublishResult(False, "value_edge", str(e))
        if not ex.login():
            return PublishResult(False, "value_edge", "Login Value Edge falló")

        url = (
            f"{ex.url}/api/shared_spaces/{ex.shared_space}/workspaces/{ex.workspace}/bdd_specs"
        )
        name = ctx.feature_name or "Feature BDD"
        payload = {
            "data": [
                {
                    "name": name,
                    "script": ctx.gherkin_text,
                    "parent": {"type": "story", "id": req_id},
                }
            ]
        }
        r = ex.session.post(url, headers=ex.headers, json=payload, timeout=60)
        if r.status_code in (200, 201):
            data = r.json()
            spec_id = ""
            if isinstance(data.get("data"), list) and data["data"]:
                spec_id = str(data["data"][0].get("id") or "")
            return PublishResult(
                True,
                "value_edge",
                f"BDD spec creado/actualizado en VE (story {req_id})",
                external_id=spec_id or req_id,
            )
        return PublishResult(False, "value_edge", f"VE {r.status_code}: {r.text[:300]}")

    def smoke_test(self, profile: Dict[str, Any]) -> PublishResult:
        from core.req_intelligence.integrations_service import value_edge_smoke_test

        out = value_edge_smoke_test(inline=True, creds=profile.get("value_edge"))
        return PublishResult(bool(out.get("ok")), "value_edge", "Value Edge OK" if out.get("ok") else "VE falló")
