"""
Open ELIA UI URLs preferring a dedicated browser window (--new-window) instead of
reusing an existing tab when possible. Falls back to webbrowser.open_new.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from typing import Iterable, List, Sequence, Set


def _focus_new_browser_window_later(old_pids: Set[int], *, delay_sec: float = 1.2) -> None:
    """
    Trae al frente la ventana del navegador recién abierta (sin maximizar todas
    las ventanas Chrome/Edge del usuario, que provocaba parpadeos y minimizado).
    """
    try:
        from core.ui_automation.recorder_focus import spawn_focus_thread_for_automation_browser

        spawn_focus_thread_for_automation_browser(old_pids, delay_sec=delay_sec)
    except Exception:
        pass


def _candidate_executables() -> List[str]:
    out: List[str] = []
    env_path = (os.environ.get("ELIA_BROWSER_PATH") or os.environ.get("CHROME_PATH") or "").strip()
    if env_path:
        out.append(env_path)

    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        out.extend(
            [
                os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
                os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
                os.path.join(local, r"Google\Chrome\Application\chrome.exe") if local else "",
                os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
                os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
            ]
        )
    elif sys.platform == "darwin":
        out.extend(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
        )

    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        p = shutil.which(name)
        if p:
            out.append(p)

    # de-dupe while preserving order
    seen: set[str] = set()
    uniq: List[str] = []
    for x in out:
        x = (x or "").strip()
        if not x or x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq


def _try_chromium_new_window(url: str, executables: Iterable[str]) -> bool:
    try:
        from core.ui_automation.recorder_focus import chrome_like_pids_snapshot

        old_pids = chrome_like_pids_snapshot()
    except Exception:
        old_pids = set()

    for exe in executables:
        if not os.path.isfile(exe):
            continue
        try:
            subprocess.Popen(
                [exe, "--new-window", "--start-maximized", "--window-size=1920,1080", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=sys.platform != "win32",
            )
            _focus_new_browser_window_later(old_pids)
            return True
        except Exception:
            continue
    return False


def open_url_in_new_browser_window(url: str) -> None:
    """
    Prefer launching Chromium/Chrome/Edge in a new OS window for the given URL.
    """
    if _try_chromium_new_window(url, _candidate_executables()):
        return
    try:
        webbrowser.open_new(url)
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        from core.ui_automation.recorder_focus import chrome_like_pids_snapshot

        _focus_new_browser_window_later(chrome_like_pids_snapshot())
    except Exception:
        pass


def _try_chromium_open_urls(urls: Sequence[str], executables: Iterable[str]) -> bool:
    """Open multiple URLs as tabs in one Chromium instance (order preserved)."""
    if not urls:
        return False
    try:
        from core.ui_automation.recorder_focus import chrome_like_pids_snapshot

        old_pids = chrome_like_pids_snapshot()
    except Exception:
        old_pids = set()
    argv = list(urls)
    for exe in executables:
        if not os.path.isfile(exe):
            continue
        try:
            subprocess.Popen(
                [exe, "--new-window", "--start-maximized", "--window-size=1920,1080", *argv],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=sys.platform != "win32",
            )
            _focus_new_browser_window_later(old_pids)
            return True
        except Exception:
            continue
    return False


def open_home_and_job_in_browser(home_url: str, job_url: str) -> bool:
    """
    Ensure the user always has a fixed home tab: open home URL first, then job URL,
    as tabs in the same browser instance (typical Chromium behavior when passing
    multiple URLs on the command line).

    Returns True if a Chromium-based launch was attempted successfully.
    """
    return _try_chromium_open_urls((home_url, job_url), _candidate_executables())
