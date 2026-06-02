"""Terminación de procesos ELIA huérfanos (misma build / registro runtime)."""
from __future__ import annotations

import os
import sys
import time
from typing import Iterable, Optional, Set

from webui.web_runtime import clear_runtime, iter_registered_pids, read_runtime


def _norm_exe(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        return os.path.normcase(os.path.abspath(path))
    except OSError:
        return None


def _current_executable() -> Optional[str]:
    return _norm_exe(sys.executable)


def _terminate_pids(pids: Iterable[int], *, grace_sec: float = 1.5) -> int:
    try:
        import psutil
    except ImportError:
        return 0

    targets: list[psutil.Process] = []
    for pid in pids:
        if pid <= 0:
            continue
        try:
            targets.append(psutil.Process(int(pid)))
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            continue

    killed = 0
    for proc in targets:
        try:
            proc.terminate()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not targets:
        return 0

    deadline = time.time() + grace_sec
    while time.time() < deadline:
        alive = False
        for proc in targets:
            try:
                if proc.is_running():
                    alive = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not alive:
            break
        time.sleep(0.1)

    for proc in targets:
        try:
            if proc.is_running():
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


def _collect_same_executable_pids(include_current: bool) -> Set[int]:
    exe = _current_executable()
    if not exe:
        return set()
    try:
        import psutil
    except ImportError:
        return set()

    me = os.getpid()
    found: Set[int] = set()
    for proc in psutil.process_iter(["pid", "exe"]):
        try:
            pid = int(proc.info.get("pid") or 0)
            if pid <= 0:
                continue
            if pid == me and not include_current:
                continue
            proc_exe = _norm_exe(proc.info.get("exe"))
            if proc_exe != exe:
                continue
            found.add(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, TypeError):
            continue
    return found


def _collect_dev_main_pids(include_current: bool) -> Set[int]:
    """Desarrollo (python main.py): solo PIDs registrados en web_runtime."""
    me = os.getpid()
    found: Set[int] = set(iter_registered_pids())
    if not include_current and me in found:
        found.discard(me)
    return found


def terminate_all_elia_web_processes(*, include_current: bool = True) -> int:
    """
    Termina procesos ELIA del mismo ejecutable (release) o PIDs registrados (dev).
    Usar al cerrar la UI para eliminar instancias zombie en otros puertos.
    """
    if getattr(sys, "frozen", False):
        pids = _collect_same_executable_pids(include_current=include_current)
    else:
        pids = _collect_dev_main_pids(include_current=include_current)

    killed = _terminate_pids(pids)
    clear_runtime()
    return killed


def cleanup_stale_elia_on_startup() -> int:
    """Al arrancar: elimina instancias registradas cuyo HTTP ya no responde."""
    from webui.web_runtime import runtime_server_alive

    data = read_runtime()
    if data and runtime_server_alive(data):
        return 0

    pids = list(iter_registered_pids())
    if not pids and getattr(sys, "frozen", False):
        pids = list(_collect_same_executable_pids(include_current=False))
    killed = _terminate_pids(pids)
    clear_runtime()
    return killed
