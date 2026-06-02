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


def _browser_launch_snapshots() -> tuple[Set[int], Set[int]]:
    try:
        from core.ui_automation.recorder_focus import (
            chrome_like_pids_snapshot,
            chrome_like_top_level_hwnds_snapshot,
        )

        return chrome_like_pids_snapshot(), chrome_like_top_level_hwnds_snapshot()
    except Exception:
        return set(), set()


def _focus_new_browser_window_later(
    old_pids: Set[int],
    *,
    delay_sec: float = 1.2,
    maximize: bool = False,
    old_hwnds: Set[int] | None = None,
) -> None:
    """
    Trae al frente la ventana del navegador recién abierta.

    Con ``maximize=True`` (UI de ELIA), fuerza SW_MAXIMIZE en esa ventana nueva;
    Chrome/Edge a menudo ignoran ``--start-maximized`` si ya hay otra instancia abierta.
    """
    try:
        from core.ui_automation.recorder_focus import spawn_focus_thread_for_automation_browser

        spawn_focus_thread_for_automation_browser(
            old_pids,
            delay_sec=delay_sec,
            maximize=maximize,
            old_hwnds=old_hwnds,
        )
    except Exception:
        pass


def _candidate_executables() -> List[str]:
    out: List[str] = []
    if sys.platform == "win32":
        try:
            from core.ui_automation.chrome_resolver import candidate_chrome_executables

            out.extend(candidate_chrome_executables())
        except Exception:
            pass

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


def elia_browser_profile_dir() -> str:
    """
    Perfil Chromium dedicado a ELIA (no el perfil personal del usuario).
    Permite persistir preferencias de la UI (p. ej. tema) sin heredar historial
    ni la opción «continuar donde lo dejé» del navegador principal.
    """
    override = (os.environ.get("ELIA_BROWSER_USER_DATA_DIR") or "").strip()
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "ELIA", "browser-profile")
    os.makedirs(path, exist_ok=True)
    return path


def _chromium_elia_launch_argv(urls: Sequence[str], *, new_window: bool) -> List[str]:
    profile = elia_browser_profile_dir()
    flags: List[str] = [
        f"--user-data-dir={profile}",
        "--disable-restore-session-state",
        "--no-first-run",
        "--disable-session-crashed-bubble",
        "--no-default-browser-check",
    ]
    if new_window:
        flags.extend(["--new-window", "--start-maximized"])
    return [*flags, *list(urls)]


def _launch_chromium(executables: Iterable[str], argv_tail: Sequence[str], *, focus: bool = True) -> bool:
    old_pids: Set[int] = set()
    old_hwnds: Set[int] | None = None
    if focus:
        old_pids, old_hwnds = _browser_launch_snapshots()
    for exe in executables:
        if not os.path.isfile(exe):
            continue
        try:
            subprocess.Popen(
                [exe, *argv_tail],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=sys.platform != "win32",
            )
            if focus:
                _focus_new_browser_window_later(old_pids, maximize=True, old_hwnds=old_hwnds)
            return True
        except Exception:
            continue
    return False


def open_elia_home_url(url: str) -> None:
    """
    Abre la UI de ELIA en una ventana limpia con perfil aislado (solo ELIA).
    """
    argv = _chromium_elia_launch_argv([url], new_window=True)
    if _launch_chromium(_candidate_executables(), argv):
        return
    open_url_in_new_browser_window(url)


def _try_chromium_new_window(url: str, executables: Iterable[str]) -> bool:
    argv = _chromium_elia_launch_argv([url], new_window=True)
    return _launch_chromium(executables, argv)


def open_url_in_new_browser_window(url: str) -> None:
    """
    Prefer launching Chromium/Chrome/Edge in a new OS window for the given URL.
    """
    if _try_chromium_new_window(url, _candidate_executables()):
        return
    old_pids, old_hwnds = _browser_launch_snapshots()
    try:
        webbrowser.open_new(url)
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            return
    _focus_new_browser_window_later(old_pids, maximize=True, old_hwnds=old_hwnds)


def open_url_in_browser_tab(url: str) -> None:
    """
    Abre la URL en una pestaña del perfil ELIA (sin --new-window).
    Usado al re-enlazar una segunda instancia de ELIA al servidor ya activo.
    """
    argv = _chromium_elia_launch_argv([url], new_window=False)
    if _launch_chromium(_candidate_executables(), argv, focus=False):
        return
    try:
        webbrowser.open(url, new=0)
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass


def _try_chromium_open_urls(urls: Sequence[str], executables: Iterable[str]) -> bool:
    """Open multiple URLs as tabs in one Chromium instance (order preserved)."""
    if not urls:
        return False
    argv = _chromium_elia_launch_argv(list(urls), new_window=True)
    return _launch_chromium(executables, argv)


def open_home_and_job_in_browser(home_url: str, job_url: str) -> bool:
    """
    Ensure the user always has a fixed home tab: open home URL first, then job URL,
    as tabs in the same browser instance (typical Chromium behavior when passing
    multiple URLs on the command line).

    Returns True if a Chromium-based launch was attempted successfully.
    """
    return _try_chromium_open_urls((home_url, job_url), _candidate_executables())
