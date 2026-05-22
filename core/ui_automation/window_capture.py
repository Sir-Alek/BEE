"""Utilidades para localizar ventanas Windows y convertirlas a región de captura (mss)."""
from __future__ import annotations

import re
import sys
from typing import Any, Callable, Dict, List, Optional

_EMULATOR_PROCESS_NAMES = {
    "emulator.exe",
    "qemu-system-x86_64.exe",
    "qemu-system-i386.exe",
    "qemu-system-aarch64.exe",
    "qemu-system-armel.exe",
}


def hwnd_to_monitor(hwnd: int) -> Optional[Dict[str, int]]:
    """Convierte un HWND a dict compatible con mss: top, left, width, height."""
    if sys.platform != "win32" or not hwnd:
        return None
    import ctypes
    from ctypes import wintypes

    rect = wintypes.RECT()
    if not ctypes.windll.user32.GetWindowRect(wintypes.HWND(int(hwnd)), ctypes.byref(rect)):
        return None
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        return None
    return {"top": int(rect.top), "left": int(rect.left), "width": width, "height": height}


def _enum_visible_windows(
    predicate: Callable[[int, str, str], bool],
) -> List[int]:
    if sys.platform != "win32":
        return []

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    matches: List[int] = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    @WNDENUMPROC
    def enum_cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""

        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        proc_name = _process_name(int(proc_id.value))

        if predicate(int(hwnd), title, proc_name):
            matches.append(int(hwnd))
        return True

    user32.EnumWindows(enum_cb, 0)
    return matches


def _process_name(pid: int) -> str:
    if pid <= 0:
        return ""
    try:
        import psutil  # type: ignore

        return (psutil.Process(pid).name() or "").lower()
    except Exception:
        return ""


def resolve_hwnd(window_ref: Any) -> Optional[int]:
    """Normaliza pywinauto window, hwnd int u otros wrappers a HWND."""
    if window_ref is None:
        return None
    if isinstance(window_ref, int):
        return int(window_ref)
    for attr in ("handle", "_hWnd", "hwnd"):
        val = getattr(window_ref, attr, None)
        if val:
            return int(val)
    return None


def find_hwnd_by_title_substring(
    substring: str,
    *,
    min_width: int = 120,
    min_height: int = 120,
) -> Optional[int]:
    needle = (substring or "").strip().lower()
    if not needle or sys.platform != "win32":
        return None

    def pred(_hwnd: int, title: str, _proc: str) -> bool:
        if needle not in title.lower():
            return False
        mon = hwnd_to_monitor(_hwnd)
        if not mon:
            return False
        return mon["width"] >= min_width and mon["height"] >= min_height

    matches = _enum_visible_windows(pred)
    return matches[0] if matches else None


def find_legacy_app_hwnd(window_name: str) -> Optional[int]:
    """Busca la ventana de la app legacy por título (parcial)."""
    name = (window_name or "").strip()
    if not name:
        return None

    if sys.platform != "win32":
        return None

    try:
        from pywinauto import Desktop

        app = Desktop(backend="uia")
        wins = app.windows(title_re=f".*{re.escape(name)}.*")
        if wins:
            return resolve_hwnd(wins[0])
    except ImportError:
        pass

    try:
        import win32gui  # type: ignore

        hwnd = win32gui.FindWindow(None, name)
        if hwnd:
            return int(hwnd)
    except ImportError:
        pass

    return find_hwnd_by_title_substring(name)


def _emulator_port_hint(device_id: str) -> Optional[str]:
    dev = (device_id or "").strip()
    m = re.match(r"emulator-(\d+)$", dev, re.I)
    if not m:
        return None
    return m.group(1)


def find_android_emulator_hwnd(device_id: str = "") -> Optional[int]:
    """
    Localiza la ventana del emulador Android en el escritorio Windows.
    Prioriza ventanas del proceso emulator/qemu cuyo título contiene «Emulator».
    """
    if sys.platform != "win32":
        return None

    port_hint = _emulator_port_hint(device_id)

    def base_pred(hwnd: int, title: str, proc: str) -> bool:
        if proc not in _EMULATOR_PROCESS_NAMES:
            return False
        lower = title.lower()
        if "emulator" not in lower and "android" not in lower:
            return False
        mon = hwnd_to_monitor(hwnd)
        if not mon or mon["width"] < 200 or mon["height"] < 200:
            return False
        return True

    if port_hint:
        def pred_with_port(hwnd: int, title: str, proc: str) -> bool:
            return base_pred(hwnd, title, proc) and port_hint in title

        matches = _enum_visible_windows(pred_with_port)
        if matches:
            return matches[0]

    matches = _enum_visible_windows(base_pred)
    if matches:
        return matches[0]

    for needle in ("Android Emulator", "Emulator"):
        hwnd = find_hwnd_by_title_substring(needle, min_width=200, min_height=200)
        if hwnd:
            return hwnd
    return None


def is_emulator_device_id(device_id: str) -> bool:
    return (device_id or "").strip().lower().startswith("emulator-")
