"""Contratos de publicación Gherkin (generación ≠ publicación)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional, Protocol

PublishTarget = Literal["git", "jira_vanilla", "jira_xray", "value_edge", "azure_devops", "local_file"]


@dataclass
class PublishContext:
    """Contexto común para todos los adaptadores."""

    gherkin_text: str
    feature_name: str = "Feature"
    profile: Optional[Dict[str, Any]] = None
    issue_key: str = ""
    requirement_id: str = ""
    work_item_id: str = ""
    file_path: str = ""
    branch: str = ""
    commit_message: str = ""
    output_dir: str = ""


@dataclass
class PublishResult:
    ok: bool
    target: PublishTarget
    message: str
    external_id: str = ""
    url: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class Publisher(Protocol):
    target: PublishTarget

    def publish(self, ctx: PublishContext) -> PublishResult: ...

    def smoke_test(self, profile: Dict[str, Any]) -> PublishResult: ...
