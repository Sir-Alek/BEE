"""Plantillas de prueba de carga (Load, Stress, Spike, Soak, Scalability)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

PROFILE_IDS = ("load", "stress", "spike", "soak", "scalability", "volume")

PROFILE_LABELS: Dict[str, str] = {
    "load": "Carga sostenida",
    "stress": "Estrés (rampa hasta techo)",
    "spike": "Spike (pico abrupto)",
    "soak": "Soak / resistencia",
    "scalability": "Escalabilidad por escalones",
    "volume": "Volumen (carga + CSV)",
}


def parse_run_time_seconds(run_time: str) -> int:
    raw = (run_time or "1m").strip().lower()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([smh])?$", raw)
    if not m:
        try:
            return max(60, int(float(raw)))
        except (TypeError, ValueError):
            return 60
    value = float(m.group(1))
    unit = m.group(2) or "s"
    if unit == "m":
        return int(value * 60)
    if unit == "h":
        return int(value * 3600)
    return int(value)


def resolve_load_profile(
    profile: Optional[str],
    *,
    users: int,
    spawn_rate: float,
    run_time: str,
    think_time: Optional[Dict[str, Any]] = None,
    stages: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]], str]:
    """Devuelve (profile_id, stages, think_time, run_time_effective).

    Si `stages` viene explícito, se respeta y solo se normaliza el profile_id.
    """
    pid = (profile or "load").strip().lower()
    if pid not in PROFILE_IDS:
        pid = "load"
    if stages:
        return pid, stages, think_time, run_time

    total = parse_run_time_seconds(run_time)
    users = max(1, int(users))
    spawn = max(0.1, float(spawn_rate))

    if pid == "load":
        return pid, None, think_time or {"kind": "between", "min": 0.5, "max": 2.0}, run_time

    if pid == "stress":
        # Cuatro escalones hasta el 100 % de usuarios configurados
        q = max(1, users // 4)
        stage_secs = max(30, total // 4)
        resolved = [
            {"duration": stage_secs, "users": q, "spawn_rate": spawn},
            {"duration": stage_secs * 2, "users": q * 2, "spawn_rate": spawn},
            {"duration": stage_secs * 3, "users": q * 3, "spawn_rate": spawn},
            {"duration": total, "users": users, "spawn_rate": spawn},
        ]
        return pid, resolved, think_time or {"kind": "between", "min": 0.2, "max": 1.0}, run_time

    if pid == "spike":
        baseline = max(1, users // 10 or 1)
        spike_start = max(30, int(total * 0.4))
        spike_end = max(spike_start + 30, int(total * 0.55))
        resolved = [
            {"duration": spike_start, "users": baseline, "spawn_rate": spawn},
            {"duration": spike_end, "users": users, "spawn_rate": max(spawn, users / 10)},
            {"duration": total, "users": baseline, "spawn_rate": spawn},
        ]
        return pid, resolved, think_time or {"kind": "constant", "value": 0.5}, run_time

    if pid == "soak":
        # Carga moderada sostenida (70 % usuarios), think-time más realista
        soak_users = max(1, int(users * 0.7))
        resolved = [{"duration": total, "users": soak_users, "spawn_rate": spawn}]
        return pid, resolved, think_time or {"kind": "between", "min": 1.0, "max": 3.0}, run_time

    if pid == "scalability":
        steps = 5
        step_secs = max(30, total // steps)
        resolved: List[Dict[str, Any]] = []
        for i in range(1, steps + 1):
            step_users = max(1, int(users * i / steps))
            resolved.append(
                {"duration": step_secs * i, "users": step_users, "spawn_rate": spawn}
            )
        return pid, resolved, think_time or {"kind": "between", "min": 0.3, "max": 1.5}, run_time

    if pid == "volume":
        return pid, None, think_time or {"kind": "between", "min": 0.1, "max": 0.5}, run_time

    return "load", None, think_time, run_time


def list_profiles() -> List[Dict[str, str]]:
    return [{"id": pid, "label": PROFILE_LABELS[pid]} for pid in PROFILE_IDS]
