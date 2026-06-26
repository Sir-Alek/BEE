"""Lanzamiento unificado de Behave / Locust con variables de entorno ELIA."""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from core.elia_paths import behave_projects_dir
from core.test_runner.behave_support import elia_base_dir, ensure_platform_behave_support

BEHAVE_KINDS = frozenset({"behave", "behave_web", "behave_mobile", "behave_legacy", "behave_api"})
LOCUST_KIND = "locust"


def project_path(platform: str, project: str) -> str:
    return str(behave_projects_dir(platform) / project)


def build_run_env(
    platform: str,
    *,
    generate_evidence: bool = True,
    headless: bool = True,
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    env = os.environ.copy()
    env["GENERATE_EVIDENCE"] = "true" if generate_evidence else "false"
    env["HEADLESS"] = "true" if headless else "false"
    env["ELIA_BASE_DIR"] = elia_base_dir()
    env["ELIA_PLATFORM"] = platform
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    logo = os.path.join(elia_base_dir(), "resources", "logo_elia.png")
    if os.path.isfile(logo):
        env["ELIA_LOGO_PATH"] = logo
    if extra:
        env.update({k: str(v) for k, v in extra.items()})
    return env


def prepare_project(platform: str, project: str) -> str:
    path = behave_projects_dir(platform) / project
    if not path.is_dir():
        raise FileNotFoundError(f"Proyecto no encontrado: {platform}/{project}")
    ensure_platform_behave_support(path, platform)
    return str(path)


def build_behave_command(feature: str = "features") -> List[str]:
    return [
        sys.executable,
        "-u",
        "-m",
        "behave",
        "--no-logcapture",
        "--no-capture",
        feature,
    ]


def build_locust_command(
    locustfile: str,
    *,
    users: int = 5,
    spawn_rate: float = 1.0,
    run_time: str = "1m",
    host: str = "",
    csv_prefix: str = "",
    processes: int = 0,
    mode: str = "standalone",
    master_host: str = "",
    master_port: int = 0,
    expect_workers: int = 0,
) -> List[str]:
    """Construye el comando de Locust.

    Carga distribuida:
    - ``processes``: multi-core local. Locust 2.x auto-lanza N workers en la misma
      máquina con ``--processes N`` (aprovecha todos los núcleos pese al GIL).
      Usa -1 para "todos los núcleos".
    - ``mode``: 'standalone' (defecto) | 'master' | 'worker' para carga
      distribuida entre varias máquinas. El 'master' coordina; cada 'worker' se
      conecta a ``master_host:master_port``.
    """
    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        os.path.basename(locustfile),
        "--headless",
    ]

    mode = (mode or "standalone").lower()
    if mode == "worker":
        cmd.append("--worker")
        if master_host:
            cmd.extend(["--master-host", str(master_host)])
        if master_port:
            cmd.extend(["--master-port", str(master_port)])
        # En modo worker, los parámetros de carga (-u/-r/-t) los fija el master.
        return cmd

    if mode == "master":
        cmd.append("--master")
        if master_port:
            cmd.extend(["--master-bind-port", str(master_port)])
        if expect_workers > 0:
            cmd.extend(["--expect-workers", str(expect_workers)])

    cmd.extend(["-u", str(users), "-r", str(spawn_rate), "-t", run_time])

    # Multi-core local (solo si no estamos ya en modo master/worker explícito).
    if processes and mode == "standalone":
        cmd.extend(["--processes", str(processes)])

    if host:
        cmd.extend(["--host", host])
    if csv_prefix:
        cmd.extend(["--csv", csv_prefix])
    return cmd


def validate_distributed_load_options(
    *,
    mode: str = "standalone",
    master_host: str = "",
    master_port: int = 0,
    processes: int = 0,
) -> tuple[bool, str]:
    """Valida parámetros de carga distribuida antes de lanzar Locust."""
    normalized = (mode or "standalone").lower()
    if normalized not in ("standalone", "master", "worker"):
        return False, "Modo de carga inválido: use standalone, master o worker."

    if normalized == "worker":
        if not (master_host or "").strip():
            return False, "Modo worker requiere la IP o hostname del master."
        if master_port <= 0:
            return False, "Modo worker requiere master_port (por defecto 5557)."

    if normalized != "standalone" and processes:
        return False, "No combine procesos Locust (--processes) con modo master/worker en red."

    return True, ""


def normalize_kind(platform: str, kind: str) -> str:
    k = (kind or "behave").lower()
    if k == "behave":
        return f"behave_{platform}" if platform != "web" else "behave_web"
    return k
