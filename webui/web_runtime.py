"""Registro de la instancia Web UI activa (puerto, PID) para evitar procesos duplicados."""
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_ELIA_UI_PORT = 8765
_INSTANCE_LOCK_HANDLE: Any = None


def elia_ui_port() -> int:
    raw = os.environ.get("ELIA_UI_PORT", str(DEFAULT_ELIA_UI_PORT))
    try:
        port = int(str(raw).strip())
    except ValueError:
        port = DEFAULT_ELIA_UI_PORT
    return max(1, min(port, 65535))


def elia_ui_host() -> str:
    return (os.environ.get("ELIA_UI_HOST") or "127.0.0.1").strip() or "127.0.0.1"


def acquire_single_instance_lock() -> bool:
    """
    True si este proceso debe levantar el servidor.
    False si ya hay otra instancia arrancando o en ejecución (solo re-enlazar UI).
    """
    global _INSTANCE_LOCK_HANDLE
    if _INSTANCE_LOCK_HANDLE is not None:
        return True
    if sys.platform == "win32":
        import ctypes

        error_already_exists = 183
        handle = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\ELIA_WEB_UI_SINGLE_INSTANCE")
        _INSTANCE_LOCK_HANDLE = handle
        return int(ctypes.windll.kernel32.GetLastError()) != error_already_exists
    lock_path = _runtime_path().parent / "elia_instance.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    try:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _INSTANCE_LOCK_HANDLE = fd
        return True
    except (ImportError, OSError, BlockingIOError):
        try:
            os.close(fd)
        except OSError:
            pass
        return False


def release_single_instance_lock() -> None:
    global _INSTANCE_LOCK_HANDLE
    if _INSTANCE_LOCK_HANDLE is None:
        return
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.kernel32.CloseHandle(int(_INSTANCE_LOCK_HANDLE))
        else:
            import fcntl

            fcntl.flock(int(_INSTANCE_LOCK_HANDLE), fcntl.LOCK_UN)
            os.close(int(_INSTANCE_LOCK_HANDLE))
    except (OSError, ValueError, AttributeError):
        pass
    _INSTANCE_LOCK_HANDLE = None


def build_ui_url(*, host: Optional[str] = None, port: Optional[int] = None, session_id: Optional[str] = None) -> str:
    h = host or elia_ui_host()
    p = int(port if port is not None else elia_ui_port())
    base = f"http://{h}:{p}/"
    sid = str(session_id or "").strip()
    if not sid:
        return base
    return f"{base}?elia_sid={sid}"


def _runtime_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    elia = Path(base) / "ELIA"
    elia.mkdir(parents=True, exist_ok=True)
    return elia / "web_runtime.json"


def read_runtime() -> Optional[Dict[str, Any]]:
    path = _runtime_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _read_all_pids(data: Optional[Dict[str, Any]]) -> List[int]:
    if not data:
        return []
    raw = data.get("all_pids")
    if not isinstance(raw, list):
        pid = data.get("pid")
        return [int(pid)] if pid is not None else []
    out: List[int] = []
    for item in raw:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def iter_registered_pids() -> Iterable[int]:
    data = read_runtime()
    seen: set[int] = set()
    for pid in _read_all_pids(data):
        if pid in seen:
            continue
        seen.add(pid)
        yield pid


def write_runtime(
    *,
    host: str,
    port: int,
    pid: Optional[int] = None,
    session_id: Optional[str] = None,
) -> None:
    pid_val = int(pid if pid is not None else os.getpid())
    sid = str(session_id or "")
    payload = {
        "host": host,
        "port": int(port),
        "pid": pid_val,
        "all_pids": [pid_val],
        "url": build_ui_url(host=host, port=int(port), session_id=sid),
        "started_at": time.time(),
        "session_id": sid,
    }
    _runtime_path().write_text(json.dumps(payload, indent=0), encoding="utf-8")


def clear_runtime() -> None:
    try:
        _runtime_path().unlink(missing_ok=True)
    except OSError:
        pass


def _runtime_base_url(data: Dict[str, Any]) -> str:
    host = str(data.get("host") or "127.0.0.1")
    port = data.get("port")
    if port is None:
        raise ValueError("runtime sin puerto")
    return str(data.get("url") or f"http://{host}:{int(port)}/").rstrip("/")


def runtime_server_alive(data: Optional[Dict[str, Any]] = None) -> bool:
    return runtime_server_healthy(data)


def runtime_server_healthy(data: Optional[Dict[str, Any]] = None) -> bool:
    row = data if data is not None else read_runtime()
    if not row:
        return False
    try:
        base = _runtime_base_url(row)
    except ValueError:
        return False
    about_url = f"{base}/api/app/about"
    ping_url = f"{base}/api/app/ping"
    try:
        req = urllib.request.Request(about_url, method="GET")
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            if not (200 <= int(getattr(resp, "status", 200) or 200) < 500):
                return False
            body = resp.read()
        about = json.loads(body.decode("utf-8"))
        if not isinstance(about, dict) or about.get("app_name") != "ELIA":
            return False
        expected_session = str(row.get("session_id") or "").strip()
        if expected_session:
            if str(about.get("session_id") or "") != expected_session:
                return False
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False
    try:
        ping_req = urllib.request.Request(
            ping_url,
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(ping_req, timeout=1.2) as resp:
            if not (200 <= int(getattr(resp, "status", 200) or 200) < 500):
                return False
            ping_body = json.loads(resp.read().decode("utf-8"))
        return isinstance(ping_body, dict) and ping_body.get("ok") is True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False


def try_attach_to_running_instance(*, open_browser: bool = True) -> bool:
    """
    Si ya hay un servidor ELIA sano en el puerto canónico, opcionalmente abre su URL.
    """
    data = read_runtime()
    if not data or not runtime_server_healthy(data):
        return False
    if not open_browser:
        return True
    url = str(data.get("url") or build_ui_url(session_id=str(data.get("session_id") or "")))
    try:
        from webui.browser_launch import open_url_in_browser_tab

        open_url_in_browser_tab(url)
    except Exception:
        try:
            import webbrowser

            webbrowser.open(url, new=0)
        except Exception:
            return False
    return True


def _kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(int(pid)), "/F", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                check=False,
            )
            return
        os.kill(int(pid), signal.SIGTERM)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass


def _win_pids_by_image_name(image_name: str) -> List[int]:
    if sys.platform != "win32" or not image_name:
        return []
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    pids: List[int] = []
    for line in (proc.stdout or "").splitlines():
        row = line.strip()
        if not row or row.startswith("INFO:"):
            continue
        parts = [p.strip('"') for p in row.split('","')]
        if len(parts) < 2:
            continue
        try:
            pids.append(int(parts[1]))
        except ValueError:
            continue
    return pids


def _win_pids_listening_on_port(port: int, host: str = "127.0.0.1") -> List[int]:
    if sys.platform != "win32":
        return _unix_pids_listening_on_port(port, host)
    needle = f"{host}:{int(port)}"
    try:
        proc = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    pids: set[int] = set()
    for line in (proc.stdout or "").splitlines():
        upper = line.upper()
        if "LISTENING" not in upper:
            continue
        if needle not in line and f"0.0.0.0:{int(port)}" not in line and f"[::1]:{int(port)}" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pids.add(int(parts[-1]))
        except ValueError:
            continue
    return sorted(pids)


def _unix_pids_listening_on_port(port: int, host: str = "127.0.0.1") -> List[int]:
    try:
        proc = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{int(port)}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, FileNotFoundError):
        return []
    pids: List[int] = []
    for line in (proc.stdout or "").splitlines():
        try:
            pids.append(int(line.strip()))
        except ValueError:
            continue
    return sorted(set(pids))


def free_local_ui_port(*, host: Optional[str] = None, port: Optional[int] = None) -> None:
    """Libera el puerto UI matando procesos que lo ocupen (instancias zombie)."""
    h = host or elia_ui_host()
    p = int(port if port is not None else elia_ui_port())
    keep = os.getpid()
    for pid in _win_pids_listening_on_port(p, h):
        if pid == keep:
            continue
        _kill_pid(pid)
    if sys.platform != "win32":
        time.sleep(0.15)
        return
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind((h if h != "0.0.0.0" else "127.0.0.1", p))
                return
        except OSError:
            time.sleep(0.1)


def _win_pids_by_commandline_fragment(fragment: str) -> List[int]:
    if sys.platform != "win32" or not fragment:
        return []
    try:
        proc = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                f"CommandLine like '%{fragment}%'",
                "get",
                "ProcessId",
                "/FORMAT:CSV",
            ],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    pids: List[int] = []
    for line in (proc.stdout or "").splitlines():
        if not line.strip() or line.lower().startswith("node,"):
            continue
        match = re.search(r",(\d+)\s*$", line.strip())
        if match:
            try:
                pids.append(int(match.group(1)))
            except ValueError:
                continue
    return pids


def _collect_elia_process_pids() -> List[int]:
    found: set[int] = set()
    for pid in iter_registered_pids():
        found.add(int(pid))
    if getattr(sys, "frozen", False):
        exe_name = os.path.basename(sys.executable)
        for pid in _win_pids_by_image_name(exe_name):
            found.add(int(pid))
    else:
        try:
            root = str(Path(__file__).resolve().parents[1])
            for pid in _win_pids_by_commandline_fragment(root):
                found.add(int(pid))
        except Exception:
            pass
    return sorted(found)


def terminate_sibling_elia_processes(*, keep_pid: Optional[int] = None) -> None:
    """Termina otras instancias ELIA.exe (zombies) dejando viva la actual por defecto."""
    keep = int(keep_pid if keep_pid is not None else os.getpid())
    for pid in _collect_elia_process_pids():
        if pid == keep:
            continue
        _kill_pid(pid)


def cleanup_stale_elia_processes() -> None:
    """
    Elimina instancias ELIA zombie y libera el puerto UI antes de un arranque nuevo.
    """
    data = read_runtime()
    if data and runtime_server_healthy(data):
        return
    terminate_sibling_elia_processes(keep_pid=os.getpid())
    free_local_ui_port()
    clear_runtime()


def prepare_exclusive_new_instance() -> None:
    """Arranque exclusivo: mata hermanos, libera puerto fijo y limpia runtime."""
    terminate_sibling_elia_processes(keep_pid=os.getpid())
    free_local_ui_port()
    clear_runtime()


def shutdown_elia_cluster() -> None:
    """Cierre completo: hermanos/zombies, libera registro y puerto."""
    terminate_sibling_elia_processes(keep_pid=os.getpid())
    clear_runtime()
