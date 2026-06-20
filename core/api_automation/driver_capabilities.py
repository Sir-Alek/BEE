"""Detección de drivers SQL/gRPC opcionales (import perezoso)."""
from __future__ import annotations

from typing import Any, Dict, List


def _try_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def sql_driver_status() -> Dict[str, Any]:
    return {
        "sqlite": True,
        "postgres": _try_import("psycopg2"),
        "mysql": _try_import("mysql.connector"),
        "sqlserver": _try_import("pyodbc"),
    }


def grpc_driver_status() -> Dict[str, Any]:
    ok = _try_import("grpc") and _try_import("google.protobuf")
    reflection = _try_import("grpc_reflection")
    missing: List[str] = []
    if not _try_import("grpc"):
        missing.append("grpcio")
    if not _try_import("google.protobuf"):
        missing.append("protobuf")
    if not reflection:
        missing.append("grpcio-reflection")
    return {"available": ok and reflection, "missing": missing}


def get_driver_capabilities() -> Dict[str, Any]:
    sql = sql_driver_status()
    grpc = grpc_driver_status()
    return {
        "sql": sql,
        "grpc": grpc,
        "install_hint": "pip install -r requirements-api-extras.txt",
    }
