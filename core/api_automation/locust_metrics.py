"""Parser de métricas Locust (stdout + CSV) en memoria."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class LocustMetricsAccumulator:
    total_requests: int = 0
    total_failures: int = 0
    current_rps: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    lines_seen: int = 0
    endpoints: List[Dict[str, Any]] = field(default_factory=list)

    def ingest_line(self, line: str) -> None:
        self.lines_seen += 1
        stripped = line.strip()
        if not stripped:
            return
        rps_match = re.search(r"Aggregated\s+.*?(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)", stripped)
        if rps_match:
            self.total_requests = int(rps_match.group(1))
            self.total_failures = int(rps_match.group(2))
            self.avg_ms = float(rps_match.group(6))
            self.p50_ms = float(rps_match.group(8))
            self.p95_ms = float(rps_match.group(9))
            self.p99_ms = float(rps_match.group(10))
        req_match = re.search(r"(\d+\.?\d*)\s+req/s", stripped, re.I)
        if req_match:
            self.current_rps = float(req_match.group(1))

    def to_dict(self) -> Dict[str, Any]:
        error_rate = (self.total_failures / self.total_requests * 100) if self.total_requests else 0.0
        return {
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "error_rate_pct": round(error_rate, 2),
            "current_rps": self.current_rps,
            "avg_ms": self.avg_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "endpoints": self.endpoints,
        }


def accumulate_from_lines(lines: List[str]) -> Dict[str, Any]:
    acc = LocustMetricsAccumulator()
    for line in lines:
        acc.ingest_line(line)
    return acc.to_dict()


def parse_locust_stats_csv(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {}
    endpoints: List[Dict[str, Any]] = []
    aggregated: Dict[str, Any] = {}
    with open(p, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or row.get("name") or "").strip()
            if not name:
                continue
            entry = {
                "name": name,
                "requests": _int(row.get("Request Count") or row.get("# requests")),
                "failures": _int(row.get("Failure Count") or row.get("# failures")),
                "avg_ms": _float(row.get("Average Response Time") or row.get("Average (ms)")),
                "p50_ms": _float(row.get("50%") or row.get("50% (ms)")),
                "p95_ms": _float(row.get("95%") or row.get("95% (ms)")),
                "p99_ms": _float(row.get("99%") or row.get("99% (ms)")),
                "rps": _float(row.get("Requests/s") or row.get("RPS")),
            }
            if name.lower() == "aggregated":
                aggregated = entry
            else:
                endpoints.append(entry)
    out = aggregated or (endpoints[0] if endpoints else {})
    return {
        "aggregated": aggregated,
        "endpoints": endpoints,
        "summary": out,
    }


def parse_locust_failures_csv(path: str) -> List[Dict[str, Any]]:
    """Desglose de errores por endpoint desde `<prefix>_failures.csv`."""
    p = Path(path)
    if not p.is_file():
        return []
    failures: List[Dict[str, Any]] = []
    with open(p, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or row.get("name") or "").strip()
            if not name:
                continue
            failures.append(
                {
                    "method": (row.get("Method") or "").strip(),
                    "name": name,
                    "error": (row.get("Error") or row.get("error") or "").strip(),
                    "occurrences": _int(row.get("Occurrences") or row.get("Occurrence")),
                }
            )
    return failures


def evaluate_load_sla(metrics: Dict[str, Any], sla: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Evalúa umbrales de SLA contra las métricas resueltas.

    `sla` admite: max_p95_ms, max_p99_ms, max_avg_ms, max_error_pct, min_rps.
    Devuelve {ok, checks:[{metric, threshold, actual, passed}]}.
    """
    if not sla:
        return {"ok": True, "checks": []}
    summary = (metrics.get("csv") or {}).get("summary") or {}
    live = metrics.get("live") or {}

    def _val(key_csv: str, key_live: str) -> float:
        if summary.get(key_csv) is not None:
            return _float(summary.get(key_csv))
        return _float(live.get(key_live))

    error_pct = _float(live.get("error_rate_pct"))
    checks: List[Dict[str, Any]] = []

    def _add(metric, threshold, actual, passed):
        checks.append(
            {"metric": metric, "threshold": threshold, "actual": actual, "passed": passed}
        )

    if "max_p95_ms" in sla:
        a = _val("p95_ms", "p95_ms")
        _add("p95_ms", sla["max_p95_ms"], a, a <= _float(sla["max_p95_ms"]))
    if "max_p99_ms" in sla:
        a = _val("p99_ms", "p99_ms")
        _add("p99_ms", sla["max_p99_ms"], a, a <= _float(sla["max_p99_ms"]))
    if "max_avg_ms" in sla:
        a = _val("avg_ms", "avg_ms")
        _add("avg_ms", sla["max_avg_ms"], a, a <= _float(sla["max_avg_ms"]))
    if "max_error_pct" in sla:
        _add("error_pct", sla["max_error_pct"], error_pct, error_pct <= _float(sla["max_error_pct"]))
    if "min_rps" in sla:
        a = _val("rps", "current_rps")
        _add("rps", sla["min_rps"], a, a >= _float(sla["min_rps"]))

    return {"ok": all(c["passed"] for c in checks), "checks": checks}


def resolve_metrics(project_path: str, lines: List[str], csv_prefix: str = "elia_load") -> Dict[str, Any]:
    live = accumulate_from_lines(lines)
    stats_path = Path(project_path) / f"{csv_prefix}_stats.csv"
    failures_path = Path(project_path) / f"{csv_prefix}_failures.csv"
    csv_data = parse_locust_stats_csv(str(stats_path)) if stats_path.is_file() else {}
    failures = parse_locust_failures_csv(str(failures_path)) if failures_path.is_file() else []
    return {
        "live": live,
        "csv": csv_data,
        "csv_path": str(stats_path) if stats_path.is_file() else None,
        "failures": failures,
    }


def _int(value: Any) -> int:
    try:
        return int(float(str(value or 0)))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(str(value or 0))
    except (TypeError, ValueError):
        return 0.0
