"""Adaptadores de publicación Gherkin multi-destino."""
from core.req_intelligence.publishers.base import PublishContext, PublishResult, PublishTarget
from core.req_intelligence.publishers.dispatcher import PublisherDispatcher, publish_gherkin

__all__ = [
    "PublishContext",
    "PublishResult",
    "PublishTarget",
    "PublisherDispatcher",
    "publish_gherkin",
]
