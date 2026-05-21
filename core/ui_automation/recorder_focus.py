"""
Best-effort focus for the automation browser spawned by Puppeteer/Chrome after recording starts.

On Windows we track new chrome.exe / msedge.exe / chromium.exe processes and try SetForegroundWindow.
Other platforms: no-op for now (xdotool could be added later).
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
from ctypes import wintypes
import threading
import time
from typing import Callable, Optional, Set


def chrome_like_pids_snapshot() -> Set[int]:
    """Return PIDs of Chrome/Chromium/Edge processes."""
    names = {
        "chrome.exe",
        "chromium.exe",
        "msedge.exe",
        "chrome",
        "chromium",
        "msedge",
    }
    out: Set[int] = set()
    try:
        import psutil  # type: ignore
    except Exception:
        return out

    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            n = (p.info.get("name") or "").lower()
            if n in names:
                out.add(int(p.info["pid"]))
        except Exception:
            continue
    return out


def chrome_like_top_level_hwnds_snapshot() -> Set[int]:
    """Visible top-level HWNDs owned by Chrome/Chromium/Edge processes."""
    if sys.platform != "win32":
        return set()

    user32 = ctypes.windll.user32
    pids = chrome_like_pids_snapshot()
    if not pids:
        return set()

    out: Set[int] = set()

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    @WNDENUMPROC
    def enum_cb(hwnd, lparam):
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if int(proc_id.value) in pids and user32.IsWindowVisible(hwnd):
            out.add(int(hwnd))
        return True

    user32.EnumWindows(enum_cb, 0)
    return out


def _try_focus_hwnd_windows(hwnd: int, *, maximize: bool = False) -> bool:
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    SW_SHOW = 5
    SW_RESTORE = 9
    SW_MAXIMIZE = 3
    if maximize:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
    elif user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    elif user32.IsZoomed(hwnd):
        pass
    else:
        user32.ShowWindow(hwnd, SW_SHOW)

    fg = user32.GetForegroundWindow()
    dummy_pid = wintypes.DWORD()
    fg_thread_id = user32.GetWindowThreadProcessId(fg, ctypes.byref(dummy_pid))
    cur_tid = kernel32.GetCurrentThreadId()

    user32.AttachThreadInput(cur_tid, fg_thread_id, True)
    try:
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    finally:
        user32.AttachThreadInput(cur_tid, fg_thread_id, False)
    return True


def _hwnd_is_maximized(hwnd: int) -> bool:
    if sys.platform != "win32":
        return True
    return bool(ctypes.windll.user32.IsZoomed(hwnd))


def _pid_top_level_hwnd(pid: int) -> int | None:
    if sys.platform != "win32":
        return None

    user32 = ctypes.windll.user32
    hwnds: list[int] = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    @WNDENUMPROC
    def enum_cb(hwnd, lparam):
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if int(proc_id.value) == pid and user32.IsWindowVisible(hwnd):
            hwnds.append(int(hwnd))
        return True

    user32.EnumWindows(enum_cb, 0)
    if not hwnds:
        return None
    return max(hwnds)


def _try_focus_pid_windows(pid: int, *, maximize: bool = False) -> bool:
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    hwnd = _pid_top_level_hwnd(pid)
    if hwnd is None:
        return False

    SW_SHOW = 5
    SW_RESTORE = 9
    SW_MAXIMIZE = 3
    if maximize:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
    elif user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    elif user32.IsZoomed(hwnd):
        pass
    else:
        user32.ShowWindow(hwnd, SW_SHOW)

    fg = user32.GetForegroundWindow()
    dummy_pid = wintypes.DWORD()
    fg_thread_id = user32.GetWindowThreadProcessId(fg, ctypes.byref(dummy_pid))
    cur_tid = kernel32.GetCurrentThreadId()

    user32.AttachThreadInput(cur_tid, fg_thread_id, True)
    try:
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    finally:
        user32.AttachThreadInput(cur_tid, fg_thread_id, False)
    return True


def _pid_window_is_maximized(pid: int) -> bool:
    if sys.platform != "win32":
        return True
    hwnd = _pid_top_level_hwnd(pid)
    if hwnd is None:
        return False
    return bool(ctypes.windll.user32.IsZoomed(hwnd))


def try_focus_new_automation_browser(
    old_pids: Set[int],
    *,
    delay_sec: float = 2.2,
    maximize: bool = False,
    old_hwnds: Set[int] | None = None,
) -> None:
    time.sleep(delay_sec)
    if sys.platform != "win32":
        return

    attempts = 5 if maximize else 1
    prior_hwnds = old_hwnds if old_hwnds is not None else set()
    for attempt in range(attempts):
        if attempt > 0:
            time.sleep(0.45)

        fresh = chrome_like_pids_snapshot() - old_pids
        for pid in sorted(fresh, reverse=True):
            if not _try_focus_pid_windows(pid, maximize=maximize):
                continue
            if not maximize or _pid_window_is_maximized(pid):
                return

        fresh_hwnds = chrome_like_top_level_hwnds_snapshot() - prior_hwnds
        for hwnd in sorted(fresh_hwnds, reverse=True):
            if not _try_focus_hwnd_windows(hwnd, maximize=maximize):
                continue
            if not maximize or _hwnd_is_maximized(hwnd):
                return


def spawn_focus_thread_for_automation_browser(
    old_pids: Set[int],
    *,
    delay_sec: float = 2.2,
    maximize: bool = False,
    old_hwnds: Set[int] | None = None,
) -> None:
    """Non-blocking: background thread attempts focus after delay."""

    def _run() -> None:
        try:
            try_focus_new_automation_browser(
                old_pids,
                delay_sec=delay_sec,
                maximize=maximize,
                old_hwnds=old_hwnds,
            )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def run_subprocess_with_automation_focus(
    cmd: list[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: Optional[float] = None,
    focus_delay_sec: float = 2.2,
    on_browser_ready: Optional[Callable[[], None]] = None,
) -> subprocess.CompletedProcess:
    """
    Launch a subprocess (e.g. node recorder.js) and try to focus the new automation
    browser window after a short delay while waiting for the process to exit.

    on_browser_ready: optional zero-arg callable called (once, in a daemon thread)
    when the line 'BROWSER_READY' is detected in the subprocess stdout.
    This allows the caller to start video recording only after the browser has
    finished opening and navigating to the target URL.
    """
    old = chrome_like_pids_snapshot()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        env=env,
    )
    spawn_focus_thread_for_automation_browser(old, delay_sec=focus_delay_sec)

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    _ready_fired = threading.Event()

    def _read_stdout() -> None:
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                stdout_lines.append(raw)
                if not _ready_fired.is_set() and "BROWSER_READY" in raw:
                    _ready_fired.set()
                    if on_browser_ready:
                        threading.Thread(target=on_browser_ready, daemon=True).start()
        except Exception:
            pass

    def _read_stderr() -> None:
        try:
            assert proc.stderr is not None
            for raw in proc.stderr:
                stderr_lines.append(raw)
        except Exception:
            pass

    t_out = threading.Thread(target=_read_stdout, daemon=True)
    t_err = threading.Thread(target=_read_stderr, daemon=True)
    t_out.start()
    t_err.start()

    try:
        if timeout is not None:
            proc.wait(timeout=timeout)
        else:
            proc.wait()
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    finally:
        t_out.join(timeout=5.0)
        t_err.join(timeout=5.0)

    return subprocess.CompletedProcess(
        cmd,
        int(proc.returncode or 0),
        "".join(stdout_lines),
        "".join(stderr_lines),
    )
