"""Comprobaciones orientativas antes de carga distribuida Locust."""
from __future__ import annotations

import socket
from typing import Any, Dict, List, Optional


def validate_load_preflight(
    *,
    mode: str,
    master_host: str = "127.0.0.1",
    master_port: int = 5557,
) -> Dict[str, Any]:
    """Valida configuración de master/worker. No garantiza workers conectados."""
    mode_norm = (mode or "local").strip().lower()
    checks: List[Dict[str, Any]] = []
    ok = True

    if mode_norm not in ("local", "master", "worker", "distributed"):
        checks.append({"id": "mode", "ok": False, "message": f"Modo no reconocido: {mode}"})
        ok = False
    else:
        checks.append({"id": "mode", "ok": True, "message": f"Modo {mode_norm}"})

    if mode_norm in ("master", "worker", "distributed"):
        host = (master_host or "127.0.0.1").strip() or "127.0.0.1"
        port = int(master_port or 5557)
        if mode_norm == "worker":
            reachable, msg = _probe_tcp(host, port, timeout=2.0)
            checks.append(
                {
                    "id": "master_reachable",
                    "ok": reachable,
                    "message": msg,
                }
            )
            if not reachable:
                ok = False
        elif mode_norm == "master":
            in_use, msg = _port_listening(host, port, timeout=1.0)
            checks.append(
                {
                    "id": "master_port",
                    "ok": not in_use,
                    "message": "Puerto master libre" if not in_use else msg,
                }
            )
            if in_use:
                ok = False

    return {"ok": ok, "checks": checks, "mode": mode_norm}


def _probe_tcp(host: str, port: int, *, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"Master accesible en {host}:{port}"
    except OSError as exc:
        return False, f"No se pudo conectar a {host}:{port} ({exc})"


def _port_listening(host: str, port: int, *, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"Puerto {port} ya en uso en {host}"
    except OSError:
        return False, f"Puerto {port} libre en {host}"
