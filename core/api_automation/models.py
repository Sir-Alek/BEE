"""Modelos canónicos para tráfico y escenarios API."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ApiAssertion:
    kind: str  # status | jsonpath | header
    expression: str = ""
    expected: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApiRequest:
    """Petición HTTP normalizada (origen: sniffer, UI manual o conversor)."""

    id: str
    name: str
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    expected_status: int = 200
    assertions: List[ApiAssertion] = field(default_factory=list)
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[str] = None
    source: str = "manual"  # manual | capture | ai

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["assertions"] = [a.to_dict() if isinstance(a, ApiAssertion) else a for a in self.assertions]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiRequest":
        assertions_raw = data.get("assertions") or []
        assertions: List[ApiAssertion] = []
        for item in assertions_raw:
            if isinstance(item, ApiAssertion):
                assertions.append(item)
            elif isinstance(item, dict):
                assertions.append(
                    ApiAssertion(
                        kind=str(item.get("kind") or "status"),
                        expression=str(item.get("expression") or ""),
                        expected=str(item.get("expected") or ""),
                    )
                )
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or "Petición API"),
            method=str(data.get("method") or "GET").upper(),
            url=str(data.get("url") or ""),
            headers={str(k): str(v) for k, v in (data.get("headers") or {}).items()},
            body=data.get("body"),
            expected_status=int(data.get("expected_status") or 200),
            assertions=assertions,
            response_status=data.get("response_status"),
            response_headers={str(k): str(v) for k, v in (data.get("response_headers") or {}).items()},
            response_body=data.get("response_body"),
            source=str(data.get("source") or "manual"),
        )


@dataclass
class ApiTrafficCapture:
    version: int = 1
    captured_at: str = ""
    source_url: str = ""
    entries: List[ApiRequest] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "captured_at": self.captured_at,
            "source_url": self.source_url,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiTrafficCapture":
        entries = [ApiRequest.from_dict(e) for e in (data.get("entries") or []) if isinstance(e, dict)]
        return cls(
            version=int(data.get("version") or 1),
            captured_at=str(data.get("captured_at") or ""),
            source_url=str(data.get("source_url") or ""),
            entries=entries,
        )
