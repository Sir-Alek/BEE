"""Tipos del informe de importación JMeter → ELIA."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class JmxThreadGroupInfo:
    index: int
    name: str
    enabled: bool
    sampler_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JmxImportItem:
    kind: str
    element: str
    sampler: Optional[str] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JmxCsvRef:
    filename: str
    variable_names: List[str]
    enabled: bool
    delimiter: str = ","

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JmxImportReport:
    source_file: str
    thread_group_index: int
    thread_group_name: str
    thread_groups: List[JmxThreadGroupInfo] = field(default_factory=list)
    imported_http: int = 0
    imported_extractors: int = 0
    imported_variables: Dict[str, str] = field(default_factory=dict)
    csv_refs: List[JmxCsvRef] = field(default_factory=list)
    load_suggestion: Dict[str, Any] = field(default_factory=dict)
    continue_on_failure: bool = False
    suggested_csv: Optional[str] = None
    include_disabled_controllers: bool = False
    groovy_translations: List[JmxImportItem] = field(default_factory=list)
    imported: List[JmxImportItem] = field(default_factory=list)
    warnings: List[JmxImportItem] = field(default_factory=list)
    skipped: List[JmxImportItem] = field(default_factory=list)
    structural_coverage_pct: int = 0
    executability_pct: int = 0
    scenario_names: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file,
            "thread_group_index": self.thread_group_index,
            "thread_group_name": self.thread_group_name,
            "thread_groups": [tg.to_dict() for tg in self.thread_groups],
            "imported_http": self.imported_http,
            "imported_extractors": self.imported_extractors,
            "imported_variables": self.imported_variables,
            "csv_refs": [c.to_dict() for c in self.csv_refs],
            "load_suggestion": self.load_suggestion,
            "continue_on_failure": self.continue_on_failure,
            "suggested_csv": self.suggested_csv,
            "include_disabled_controllers": self.include_disabled_controllers,
            "groovy_translations": [g.to_dict() for g in self.groovy_translations],
            "imported": [i.to_dict() for i in self.imported],
            "warnings": [w.to_dict() for w in self.warnings],
            "skipped": [s.to_dict() for s in self.skipped],
            "structural_coverage_pct": self.structural_coverage_pct,
            "executability_pct": self.executability_pct,
            "scenario_names": self.scenario_names,
        }
