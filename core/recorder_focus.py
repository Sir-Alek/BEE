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
from typing import Optional, Set


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


def _try_focus_pid_windows(pid: int) -> bool:
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

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
        return False

    hwnd = max(hwnds)  # often the top-level window has the largest HWND

    # SW_RESTORE demaximizes a maximized window (MSDN). Only restore if minimized;
    # if already maximized, skip ShowWindow and only bring to foreground.
    SW_SHOW = 5
    SW_RESTORE = 9
    if user32.IsIconic(hwnd):
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


def try_focus_new_automation_browser(old_pids: Set[int], *, delay_sec: float = 2.2) -> None:
    time.sleep(delay_sec)
    if sys.platform != "win32":
        return

    fresh = chrome_like_pids_snapshot() - old_pids
    if not fresh:
        return

    for pid in sorted(fresh, reverse=True):
        if _try_focus_pid_windows(pid):
            return


def spawn_focus_thread_for_automation_browser(old_pids: Set[int], *, delay_sec: float = 2.2) -> None:
    """Non-blocking: background thread attempts focus after delay."""

    def _run() -> None:
        try:
            try_focus_new_automation_browser(old_pids, delay_sec=delay_sec)
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
) -> subprocess.CompletedProcess:
    """
    Launch a subprocess (e.g. node recorder.js) and try to focus the new automation
    browser window after a short delay while waiting for the process to exit.
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
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        raise
    return subprocess.CompletedProcess(cmd, int(proc.returncode or 0), out, err)
