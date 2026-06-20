"""Utilidades para analizar y preparar flujos API con nodos anidados."""
from __future__ import annotations

from typing import Any, Dict, Iterator, List

from core.api_automation.models import ApiFlow


def walk_nodes(nodes: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        yield node
        for key in ("then", "else", "body"):
            yield from walk_nodes(node.get(key) or [])


def count_node_types(nodes: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for node in walk_nodes(nodes):
        ntype = str(node.get("type") or "request").lower()
        counts[ntype] = counts.get(ntype, 0) + 1
    return counts


def collect_nodes_by_type(nodes: List[Dict[str, Any]], ntype: str) -> List[Dict[str, Any]]:
    target = ntype.lower()
    return [n for n in walk_nodes(nodes) if str(n.get("type") or "").lower() == target]


def build_sql_setup_flow(nodes: List[Dict[str, Any]], *, name: str = "Setup SQL pre-carga") -> ApiFlow:
    """Flujo lineal con solo nodos SQL (orden depth-first) para preparación pre-carga."""
    sql_nodes = collect_nodes_by_type(nodes, "sql")
    return ApiFlow(name=name, nodes=sql_nodes, continue_on_failure=False)
