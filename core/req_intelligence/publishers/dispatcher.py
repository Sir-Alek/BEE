"""Dispatcher multi-destino para publicación Gherkin."""
from __future__ import annotations

from typing import Dict, List, Optional

from core.req_intelligence.connectors_profiles_store import load_profile_by_id
from core.req_intelligence.publishers.azure_devops_publisher import AzureDevOpsPublisher
from core.req_intelligence.publishers.base import PublishContext, PublishResult, PublishTarget
from core.req_intelligence.publishers.git_publisher import GitPublisher
from core.req_intelligence.publishers.jira_vanilla_publisher import JiraVanillaPublisher
from core.req_intelligence.publishers.jira_xray_publisher import JiraXrayPublisher
from core.req_intelligence.publishers.local_file_publisher import LocalFilePublisher
from core.req_intelligence.publishers.value_edge_bdd_publisher import ValueEdgeBddPublisher

_ADAPTERS = {
    "git": GitPublisher(),
    "jira_vanilla": JiraVanillaPublisher(),
    "jira_xray": JiraXrayPublisher(),
    "value_edge": ValueEdgeBddPublisher(),
    "azure_devops": AzureDevOpsPublisher(),
    "local_file": LocalFilePublisher(),
}


class PublisherDispatcher:
    def __init__(self, adapters=None):
        self._adapters = adapters or _ADAPTERS

    def publish(self, target: PublishTarget, ctx: PublishContext) -> PublishResult:
        adapter = self._adapters.get(target)
        if adapter is None:
            return PublishResult(False, target, f"Destino no soportado: {target}")
        return adapter.publish(ctx)

    def smoke_test(self, target: PublishTarget, profile: Dict) -> PublishResult:
        adapter = self._adapters.get(target)
        if adapter is None:
            return PublishResult(False, target, f"Destino no soportado: {target}")
        return adapter.smoke_test(profile)

    def publish_many(
        self,
        targets: List[PublishTarget],
        ctx: PublishContext,
    ) -> List[PublishResult]:
        return [self.publish(t, ctx) for t in targets]


def publish_gherkin(
    *,
    target: PublishTarget,
    gherkin_text: str,
    profile_id: str,
    feature_name: str = "Feature",
    issue_key: str = "",
    requirement_id: str = "",
    work_item_id: str = "",
    file_path: str = "",
    branch: str = "",
    commit_message: str = "",
    output_dir: str = "",
) -> PublishResult:
    profile = load_profile_by_id(profile_id)
    if profile is None:
        return PublishResult(False, target, f"Perfil no encontrado: {profile_id}")
    ctx = PublishContext(
        gherkin_text=gherkin_text,
        feature_name=feature_name,
        profile=profile,
        issue_key=issue_key,
        requirement_id=requirement_id,
        work_item_id=work_item_id,
        file_path=file_path,
        branch=branch,
        commit_message=commit_message,
        output_dir=output_dir,
    )
    return PublisherDispatcher().publish(target, ctx)
