"""Rutas de publicación BDD multi-destino."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core.req_intelligence.connectors_profiles_store import load_profile_by_id
from core.req_intelligence.publishers.base import PublishContext, PublishTarget
from core.req_intelligence.publishers.dispatcher import PublisherDispatcher


class ReqPublishRequest(BaseModel):
    target: PublishTarget
    profile_id: str
    gherkin_text: str = Field(min_length=1)
    feature_name: str = "Feature"
    issue_key: str = ""
    requirement_id: str = ""
    work_item_id: str = ""
    file_path: str = ""
    branch: str = ""
    commit_message: str = ""
    output_dir: str = ""


class ReqPublishTestRequest(BaseModel):
    target: PublishTarget
    profile_id: str


def _require_doc_module() -> None:
    from core.modules_config import is_module_enabled

    if not is_module_enabled("doc_to_bdd"):
        raise HTTPException(status_code=403, detail="Inteligencia de Requerimientos requiere ELIA Tester")


def _require_publisher_target(target: PublishTarget) -> None:
    from core.modules_config import is_feature_enabled

    standard = {"local_file", "git", "jira_vanilla"}
    enterprise = {"jira_xray", "value_edge", "azure_devops"}
    if target in standard:
        if target != "local_file" and not is_feature_enabled("publishers_standard"):
            raise HTTPException(
                status_code=403,
                detail="Publishers Git/Jira requieren ELIA Tester",
            )
        return
    if target in enterprise:
        if not is_feature_enabled("publishers_enterprise"):
            raise HTTPException(
                status_code=403,
                detail="Publishers Xray/Value Edge/Azure DevOps requieren ELIA Architect",
            )
        return
    raise HTTPException(status_code=400, detail=f"Destino de publicación no soportado: {target}")


def register_req_publish_routes(app, *, require_localhost, require_active_license) -> None:
    dispatcher = PublisherDispatcher()

    @app.post("/api/req/publish")
    def req_publish(
        body: ReqPublishRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_doc_module()
        _require_publisher_target(body.target)
        profile = load_profile_by_id(body.profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Perfil de conector no encontrado")
        ctx = PublishContext(
            gherkin_text=body.gherkin_text,
            feature_name=body.feature_name,
            profile=profile,
            issue_key=body.issue_key,
            requirement_id=body.requirement_id,
            work_item_id=body.work_item_id,
            file_path=body.file_path,
            branch=body.branch,
            commit_message=body.commit_message,
            output_dir=body.output_dir,
        )
        result = dispatcher.publish(body.target, ctx)
        if not result.ok:
            raise HTTPException(status_code=502, detail=result.message)
        return {
            "ok": True,
            "target": result.target,
            "message": result.message,
            "external_id": result.external_id,
            "url": result.url,
            "details": result.details,
        }

    @app.post("/api/req/publish/test")
    def req_publish_test(
        body: ReqPublishTestRequest,
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_doc_module()
        _require_publisher_target(body.target)
        profile = load_profile_by_id(body.profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Perfil de conector no encontrado")
        result = dispatcher.smoke_test(body.target, profile)
        return {"ok": result.ok, "target": result.target, "message": result.message}

    @app.get("/api/req/publish/targets")
    def req_publish_targets(
        _: None = Depends(require_localhost),
        __: None = Depends(require_active_license),
    ) -> Dict[str, Any]:
        _require_doc_module()
        return {
            "targets": [
                {"id": "local_file", "label": "Guardar .feature local"},
                {"id": "git", "label": "Commit a Git"},
                {"id": "jira_vanilla", "label": "Jira (descripción/criterios)"},
                {"id": "jira_xray", "label": "Jira + Xray import"},
                {"id": "value_edge", "label": "ValueEdge bdd_spec"},
                {"id": "azure_devops", "label": "Azure DevOps Work Item"},
            ]
        }
