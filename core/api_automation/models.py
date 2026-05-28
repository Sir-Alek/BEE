"""Modelos canónicos para tráfico y escenarios API."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ApiAssertion:
    kind: str  # status | jsonpath | header | body_contains | regex | duration
    expression: str = ""
    expected: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiAssertion":
        return cls(
            kind=str(data.get("kind") or "status"),
            expression=str(data.get("expression") or ""),
            expected=str(data.get("expected") or ""),
        )


@dataclass
class ApiExtractor:
    kind: str  # jsonpath | regex | header | status
    expression: str = ""
    target_var: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiExtractor":
        return cls(
            kind=str(data.get("kind") or "jsonpath"),
            expression=str(data.get("expression") or ""),
            target_var=str(data.get("target_var") or ""),
        )


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
    extractors: List[ApiExtractor] = field(default_factory=list)
    max_duration_ms: Optional[int] = None
    weight: int = 1
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[str] = None
    source: str = "manual"  # manual | capture | ai

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["assertions"] = [a.to_dict() if isinstance(a, ApiAssertion) else a for a in self.assertions]
        d["extractors"] = [e.to_dict() if isinstance(e, ApiExtractor) else e for e in self.extractors]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiRequest":
        assertions_raw = data.get("assertions") or []
        assertions: List[ApiAssertion] = []
        for item in assertions_raw:
            if isinstance(item, ApiAssertion):
                assertions.append(item)
            elif isinstance(item, dict):
                assertions.append(ApiAssertion.from_dict(item))

        extractors_raw = data.get("extractors") or []
        extractors: List[ApiExtractor] = []
        for item in extractors_raw:
            if isinstance(item, ApiExtractor):
                extractors.append(item)
            elif isinstance(item, dict):
                extractors.append(ApiExtractor.from_dict(item))

        max_dur = data.get("max_duration_ms")
        weight = int(data.get("weight") or 1)
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or "Petición API"),
            method=str(data.get("method") or "GET").upper(),
            url=str(data.get("url") or ""),
            headers={str(k): str(v) for k, v in (data.get("headers") or {}).items()},
            body=data.get("body"),
            expected_status=int(data.get("expected_status") or 200),
            assertions=assertions,
            extractors=extractors,
            max_duration_ms=int(max_dur) if max_dur is not None else None,
            weight=max(1, weight),
            response_status=data.get("response_status"),
            response_headers={str(k): str(v) for k, v in (data.get("response_headers") or {}).items()},
            response_body=data.get("response_body"),
            source=str(data.get("source") or "manual"),
        )


@dataclass
class ApiFlowStep:
    scenario_id: Optional[str] = None
    request: Optional[Dict[str, Any]] = None
    extractors: List[ApiExtractor] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "request": self.request,
            "extractors": [e.to_dict() for e in self.extractors],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiFlowStep":
        extractors = [ApiExtractor.from_dict(e) for e in (data.get("extractors") or []) if isinstance(e, dict)]
        return cls(
            scenario_id=data.get("scenario_id"),
            request=data.get("request") if isinstance(data.get("request"), dict) else None,
            extractors=extractors,
        )


@dataclass
class ApiFlow:
    name: str
    steps: List[ApiFlowStep] = field(default_factory=list)
    continue_on_failure: bool = False
    data_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "continue_on_failure": self.continue_on_failure,
            "data_file": self.data_file,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiFlow":
        steps = [ApiFlowStep.from_dict(s) for s in (data.get("steps") or []) if isinstance(s, dict)]
        return cls(
            name=str(data.get("name") or "Flujo API"),
            steps=steps,
            continue_on_failure=bool(data.get("continue_on_failure")),
            data_file=data.get("data_file"),
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
