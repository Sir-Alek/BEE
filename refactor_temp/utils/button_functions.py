# button_functions.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import uuid
import logging
from time import sleep
from typing import Optional, Literal, Tuple
import re
import time
import subprocess
import csv
from pathlib import Path
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui
import pygetwindow as gw
import ctypes
from ctypes import wintypes
from selenium.webdriver.support.ui import Select
import glob
from utils.evidence import GetEvidence
import pandas as pd
from python_calamine import CalamineWorkbook

BASE_DIR = os.getcwd()

# ---> VARIABLES GLOBALES PARA EVIDENCIAS
GLOBAL_TAKE_EVIDENCE = False
GLOBAL_EVIDENCE_DIR = ""
GLOBAL_EVIDENCE_FUNC = None

# ---> FOTÓGRAFO GLOBAL PARA TODAS LAS FUNCIONES <---
def take_global_evidence(driver, default_step: str, nombre_elemento: str, usar_create_screenshot: bool, screenshot_step: str = None):
    # Evaluamos si tomarla por parámetro explícito o por variable global
    should_take = usar_create_screenshot or GLOBAL_TAKE_EVIDENCE
    if not should_take:
        return None

    step = screenshot_step or default_step
    label = nombre_elemento or "Elemento"
    dir_name = GLOBAL_EVIDENCE_DIR
    
    fn = GLOBAL_EVIDENCE_FUNC or globals().get("create_screenshot")

    if callable(fn):
        try:
            return fn(step=step, label=label, dir_name=dir_name, web_driver=driver)
        except TypeError:
            try:
                return fn(step, label, dir_name, driver)
            except Exception:
                pass
        except Exception as ex:
            logging.warning(f"Evidencia falló: {ex}")
    return None

# Cache PID->image name to avoid repeated tasklist/psutil calls
_PID_IMAGE_CACHE: dict[int, str] = {}

def _get_pid_for_hwnd(hwnd: int) -> int:
    """Obtiene PID del proceso dueño de una ventana (hWnd)."""
    try:
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(wintypes.HWND(int(hwnd)), ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0

def _image_name_for_pid(pid: int) -> str:
    """Devuelve el nombre de imagen (exe) para un PID (best-effort)."""
    pid = int(pid or 0)
    if pid <= 0:
        return ""
    cached = _PID_IMAGE_CACHE.get(pid)
    if cached:
        return cached
    # Intento 1: psutil (si está disponible)
    try:
        import psutil  # type: ignore
        name = (psutil.Process(pid).name() or "").strip()
        if name:
            _PID_IMAGE_CACHE[pid] = name
            return name
    except Exception:
        pass
    # Intento 2: tasklist (sin dependencia)
    try:
        cp = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (cp.stdout or "").strip()
        if out:
            row = next(csv.reader(out.splitlines()), None)
            if row and len(row) >= 1:
                name = (row[0] or "").strip()
                if name:
                    _PID_IMAGE_CACHE[pid] = name
                    return name
    except Exception:
        pass
    return ""

from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)

from selenium.webdriver.common.keys import Keys
from datetime import datetime

BASE_DIR = os.getcwd()


# ============================================================
# EVIDENCIAS: carpeta por caso en ejecución + screenshots
# ============================================================

_EVIDENCE_CONTEXT = {
    "case_name": None,   # nombre lógico del caso (p.ej. test_OA_CP001...)
    "run_id": None,      # identificador de ejecución (timestamp)
    "dir_path": None,    # ruta absoluta a la carpeta de evidencias del caso
}

def _sanitize_fs_name(name: str, max_len: int = 90) -> str:
    """Sanitiza un nombre para usarlo como carpeta/archivo (cross-platform)."""
    name = (name or "").strip()
    if not name:
        return "_unnamed"
    safe = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in name)
    safe = safe.strip("._")
    return (safe or "_unnamed")[:max_len]

def set_evidence_case(
    case_name: str,
    *,
    run_id: Optional[str] = None,
    base_dir: str = BASE_DIR,
    parent_rel: str = os.path.join("outputs", "evidences"),
    add_timestamp: bool = True,
) -> str:
    """
    Inicializa la carpeta de evidencias del *caso en ejecución* y deja el contexto listo
    para que ui_interact (y/o create_screenshot) guarde ahí.

    Ejemplo de carpeta resultante:
      outputs/evidences/<case_name>_2026-01-08_10-15-22

    Retorna la ruta absoluta creada.
    """
    safe_case = _sanitize_fs_name(case_name, max_len=120)
    ts = run_id or (datetime.now().strftime("%Y-%m-%d_%H-%M-%S") if add_timestamp else "")
    folder = f"{safe_case}_{ts}" if ts else safe_case

    dir_path = os.path.join(base_dir, parent_rel, folder)
    os.makedirs(dir_path, exist_ok=True)

    _EVIDENCE_CONTEXT["case_name"] = safe_case
    _EVIDENCE_CONTEXT["run_id"] = ts or None
    _EVIDENCE_CONTEXT["dir_path"] = dir_path
    return dir_path

def get_evidence_dir() -> Optional[str]:
    """Devuelve la ruta absoluta actual de evidencias (si se inicializó)."""
    return _EVIDENCE_CONTEXT.get("dir_path")

def resolve_evidence_dir(
    dir_name: str = "",
    *,
    base_dir: str = BASE_DIR,
    parent_rel: str = os.path.join("outputs", "evidences"),
) -> str:
    """
    Resuelve la carpeta destino para evidencias.

    Prioridad:
      1) dir_name absoluto -> se usa tal cual
      2) dir_name relativo -> base_dir/parent_rel/dir_name
      3) contexto inicializado vía set_evidence_case -> se usa ese
      4) carpeta default no-escopada -> outputs/evidences/_unscoped_<timestamp>
    """
    if dir_name:
        if os.path.isabs(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            return dir_name
        p = os.path.join(base_dir, parent_rel, dir_name)
        os.makedirs(p, exist_ok=True)
        return p

    ctx = get_evidence_dir()
    if ctx:
        os.makedirs(ctx, exist_ok=True)
        return ctx

    # Default (si el caller no inicializó caso)
    return set_evidence_case("_unscoped", base_dir=base_dir, parent_rel=parent_rel, add_timestamp=True)

def create_screenshot(
    *,
    step: str,
    label: str,
    dir_name: str = "",
    web_driver: Optional[WebDriver] = None,
) -> Optional[str]:
    """
    Toma una evidencia (screenshot) y la guarda en la carpeta del caso en ejecución.

    - Si `dir_name` viene vacío, usa el contexto de `set_evidence_case(...)`.
    - Retorna la ruta del archivo PNG o None si falla.
    """
    if web_driver is None:
        raise ValueError("create_screenshot requiere web_driver")

    try:
        target_dir = resolve_evidence_dir(dir_name)
        safe_step = _sanitize_fs_name(step, max_len=30)
        safe_label = _sanitize_fs_name(label, max_len=70)
        filename = f"{safe_step}_{safe_label}_{uuid.uuid4().hex[:8]}.png"
        fpath = os.path.join(target_dir, filename)
        ok = web_driver.save_screenshot(fpath)
        return fpath if ok else None
    except Exception as ex:
        logging.warning(f"create_screenshot falló ({type(ex).__name__}): {ex}")
        return None



# ============================================================
# EVIDENCIAS (SO): screenshots de Explorer/Excel (no DOM)
# ============================================================

def _pick_window_by_title_contains(
    title_substr: str,
    *,
    process_image_names: Optional[set[str]] = None,
):
    """Regresa la ventana más grande cuyo título contiene `title_substr` (case-insensitive).

    Si `process_image_names` se proporciona, filtra por nombre de proceso (p.ej. {'explorer.exe'} o {'excel.exe'}).
    """
    key = (title_substr or "").strip().lower()
    if not key:
        return None

    allowed = {p.lower() for p in (process_image_names or set())} if process_image_names else None

    wins = []
    for w in gw.getAllWindows():
        try:
            if not w.title or key not in w.title.lower():
                continue
            if allowed:
                hwnd = int(getattr(w, "_hWnd", 0) or 0)
                pid = _get_pid_for_hwnd(hwnd)
                img = _image_name_for_pid(pid).lower()
                if not img or img not in allowed:
                    continue
            wins.append(w)
        except Exception:
            continue

    if not wins:
        return None

    wins.sort(key=lambda w: (w.width * w.height), reverse=True)
    return wins[0]


def _window_hwnds_by_title_contains(
    title_substr: str,
    *,
    process_image_names: Optional[set[str]] = None,
) -> set[int]:
    """Handles (hWnd) de ventanas cuyo título contiene el texto (case-insensitive), opcionalmente filtradas por proceso."""
    key = (title_substr or "").strip().lower()
    if not key:
        return set()

    allowed = {p.lower() for p in (process_image_names or set())} if process_image_names else None

    hwnds: set[int] = set()
    for w in gw.getAllWindows():
        try:
            if not w.title or key not in w.title.lower():
                continue
            hwnd = int(getattr(w, "_hWnd", 0) or 0)
            if not hwnd:
                continue
            if allowed:
                pid = _get_pid_for_hwnd(hwnd)
                img = _image_name_for_pid(pid).lower()
                if not img or img not in allowed:
                    continue
            hwnds.add(hwnd)
        except Exception:
            continue

    return hwnds


def activate_window_by_title_contains(
    title_substr: str,
    *,
    timeout: float = 8.0,
    wait_activate: float = 0.35,
    process_image_names: Optional[set[str]] = None,
) -> bool:
    """Intenta poner en primer plano una ventana cuyo título contiene `title_substr`.

    Importante: si `process_image_names` se proporciona, SOLO considerará ventanas de ese proceso
    (p.ej. {'explorer.exe'} o {'excel.exe'}) para evitar activar el navegador u otras apps con títulos similares.
    """
    key = (title_substr or "").strip()
    if not key:
        return False

    end = time.time() + float(timeout)
    while time.time() < end:
        w = _pick_window_by_title_contains(key, process_image_names=process_image_names)
        if not w:
            time.sleep(0.25)
            continue

        try:
            if getattr(w, "isMinimized", False):
                w.restore()
        except Exception:
            pass

        try:
            w.activate()
        except Exception:
            pass

        time.sleep(float(wait_activate))

        # Click suave en la BARRA DE TITULO (no en el centro) para asegurar foco real sin interactuar con celdas/archivos
        try:
            x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
            y = int(w.top) + 15
            if x >= 0 and y >= 0:
                pyautogui.click(x, y)
                time.sleep(0.12)
        except Exception:
            pass

        # Validación best-effort
        try:
            aw = gw.getActiveWindow()
            if aw and aw.title and key.lower() in aw.title.lower():
                return True
            # Si filtramos por proceso, a veces el título puede variar; asumimos ok tras activar.
            if process_image_names:
                return True
        except Exception:
            return True

        time.sleep(0.25)

    return False

    end = time.time() + float(timeout)
    while time.time() < end:
        w = _pick_window_by_title_contains(key)
        if not w:
            time.sleep(0.25)
            continue

        try:
            if getattr(w, 'isMinimized', False):
                w.restore()
        except Exception:
            pass

        try:
            w.activate()
        except Exception:
            pass

        time.sleep(float(wait_activate))

        # click en el centro para forzar foco real (Windows)
        try:
            cx = int(w.left) + max(10, int(w.width) // 2)
            cy = int(w.top) + max(10, int(w.height) // 2)
            if cx > 0 and cy > 0:
                pyautogui.click(cx, cy)
                time.sleep(0.15)
        except Exception:
            pass

        try:
            aw = gw.getActiveWindow()
            if aw and aw.title and key.lower() in aw.title.lower():
                return True
        except Exception:
            # Si no podemos validar ventana activa, asumimos ok tras activar.
            return True

        time.sleep(0.25)

    return False


def close_windows_by_title_contains(
    title_substr: str,
    *,
    timeout: float = 6.0,
    max_to_close: int = 1,
    prefer_hwnds: set[int] | None = None,
    process_image_names: Optional[set[str]] = None,
) -> int:
    """Cierra ventanas cuyo título contiene `title_substr` (best-effort).

    Si `process_image_names` se proporciona, solo cerrará ventanas de ese proceso (evita cerrar el navegador por error).
    """
    key = (title_substr or "").strip().lower()
    if not key:
        return 0

    allowed = {p.lower() for p in (process_image_names or set())} if process_image_names else None

    def _find_wins():
        wins = []
        for w in gw.getAllWindows():
            try:
                if not w.title or key not in w.title.lower():
                    continue
                if allowed:
                    hwnd = int(getattr(w, "_hWnd", 0) or 0)
                    pid = _get_pid_for_hwnd(hwnd)
                    img = _image_name_for_pid(pid).lower()
                    if not img or img not in allowed:
                        continue
                wins.append(w)
            except Exception:
                continue

        # preferir handles específicos si se proporcionan
        if prefer_hwnds:
            wins.sort(
                key=lambda w: (
                    0 if int(getattr(w, "_hWnd", 0) or 0) in prefer_hwnds else 1,
                    -(w.width * w.height),
                )
            )
        else:
            wins.sort(key=lambda w: (w.width * w.height), reverse=True)
        return wins

    end = time.time() + float(timeout)
    closed = 0
    while time.time() < end and closed < int(max_to_close):
        wins = _find_wins()
        if not wins:
            break

        w = wins[0]
        try:
            if getattr(w, "isMinimized", False):
                w.restore()
        except Exception:
            pass

        try:
            w.activate()
        except Exception:
            pass
        time.sleep(0.2)

        # Click en barra de título para evitar abrir archivos/elementos
        try:
            x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
            y = int(w.top) + 15
            if x >= 0 and y >= 0:
                pyautogui.click(x, y)
                time.sleep(0.10)
        except Exception:
            pass

        # Cierre best-effort: WM_CLOSE -> fallback Alt+F4
        try:
            w.close()
        except Exception:
            try:
                pyautogui.hotkey("alt", "f4")
            except Exception:
                pass

        time.sleep(0.6)
        closed += 1

    return closed


def _list_excel_pids() -> set[int]:
    """Lista PIDs de EXCEL.EXE (Windows). Devuelve set vacío si falla."""
    try:
        cp = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq EXCEL.EXE", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (cp.stdout or "").strip()
        pids: set[int] = set()
        if not out:
            return pids
        for row in csv.reader(out.splitlines()):
            if not row:
                continue
            # Formato típico: "EXCEL.EXE","1234","Console","1","54,328 K"
            if len(row) >= 2 and (row[0] or "").upper() == "EXCEL.EXE":
                try:
                    pids.add(int(row[1]))
                except Exception:
                    pass
        return pids
    except Exception:
        return set()


def create_screenshot_download(
    *,
    step: str,
    label: str,
    urlEvidences: str = "",
    web_driver: Optional[WebDriver] = None,   # compatibilidad (no se usa en OS shot)
    window_title_contains: Optional[str] = None,
    pre_capture_wait: float = 3.0,
    wait_activate: float = 0.35,
    process_image_names: Optional[set[str]] = None,
) -> Optional[str]:
    """
    Screenshot a nivel SO (Explorer/Excel), guardado en urlEvidences.

    - urlEvidences puede ser ruta absoluta o relativa (se resuelve con resolve_evidence_dir)
    - Si window_title_contains se proporciona, intenta recortar a esa ventana;
      si no la encuentra, hace fullscreen.
    - pre_capture_wait: espera extra antes de capturar (por defecto 3s)
    """
    try:
        target_dir = resolve_evidence_dir(urlEvidences)
        os.makedirs(target_dir, exist_ok=True)

        safe_step = _sanitize_fs_name(step, max_len=30)
        safe_label = _sanitize_fs_name(label, max_len=70)
        filename = f"{safe_step}_{safe_label}_{uuid.uuid4().hex[:8]}.png"
        fpath = os.path.join(target_dir, filename)

        region = None
        if window_title_contains:
            w = _pick_window_by_title_contains(window_title_contains, process_image_names=process_image_names)
            if w:
                try:
                    if w.isMinimized:
                        w.restore()
                    w.activate()
                    time.sleep(wait_activate)                    # Click suave en la barra de título para asegurar foco real sin interactuar con celdas/archivos
                    try:
                        x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
                        y = int(w.top) + 15
                        if x >= 0 and y >= 0:
                            pyautogui.click(x, y)
                            time.sleep(0.12)
                    except Exception:
                        pass

                    # Evitar coords negativas (multimonitor): fallback a fullscreen
                    if int(w.left) >= 0 and int(w.top) >= 0 and int(w.width) > 0 and int(w.height) > 0:
                        region = (int(w.left), int(w.top), int(w.width), int(w.height))
                except Exception:
                    region = None

        if pre_capture_wait and pre_capture_wait > 0:
            time.sleep(float(pre_capture_wait))

        img = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
        img.save(fpath)
        return fpath

    except Exception as ex:
        logging.warning(f"create_screenshot_download falló ({type(ex).__name__}): {ex}")
        return None


def close_excel_opened(
    *,
    window_title_contains: str,
    timeout: int = 20,
    force_kill_excel: bool = False,
    kill_only_if_no_excel_was_running: bool = True,
    excel_pids_before: Optional[set[int]] = None,
    spawned_pids: Optional[set[int]] = None,
) -> bool:
    """Cierre robusto de Excel minimizando efectos colaterales (foco/teclas).

    Problema típico: si el foco se pierde, los atajos/teclas pueden caer en Explorer/Chrome y abrir archivos o pestañas.
    Esta versión:
      - Filtra ventanas por proceso (EXCEL.EXE)
      - Da foco haciendo click en la BARRA DE TITULO
      - Si el Excel fue "spawned" por el script (pids nuevos), prefiere cerrarlo por PID (sin enviar teclas)
    """
    key = (window_title_contains or "").strip().lower()
    if not key:
        logging.warning("close_excel_opened: window_title_contains vacío.")
        return False

    pids_before = excel_pids_before if excel_pids_before is not None else set()
    spawned = set(spawned_pids or set())

    def _find_excel_wins():
        wins = []
        for w in gw.getAllWindows():
            try:
                if not w.title or key not in w.title.lower():
                    continue
                hwnd = int(getattr(w, "_hWnd", 0) or 0)
                pid = _get_pid_for_hwnd(hwnd)
                img = _image_name_for_pid(pid).lower()
                if img != "excel.exe":
                    continue
                wins.append(w)
            except Exception:
                continue
        wins.sort(key=lambda w: (w.width * w.height), reverse=True)
        return wins

    def _active_is_excel() -> bool:
        try:
            aw = gw.getActiveWindow()
            if not aw:
                return False
            hwnd = int(getattr(aw, "_hWnd", 0) or 0)
            pid = _get_pid_for_hwnd(hwnd)
            return _image_name_for_pid(pid).lower() == "excel.exe"
        except Exception:
            return False

    def _taskkill_pids(pids: set[int]) -> bool:
        ok_any = False
        for pid in sorted({int(p) for p in pids if int(p) > 0}):
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, check=False)
                ok_any = True
            except Exception:
                pass
        return ok_any

    # Si NO había Excel antes y este Excel fue abierto por el script, la vía más segura es cerrar por PID (sin teclas).
    if kill_only_if_no_excel_was_running and not pids_before and spawned:
        _taskkill_pids(spawned)
        time.sleep(1.0)
        return True

    end = time.time() + int(timeout)
    while time.time() < end:
        wins = _find_excel_wins()
        if not wins:
            return True

        w = wins[0]
        try:
            if getattr(w, "isMinimized", False):
                w.restore()
        except Exception:
            pass

        try:
            w.activate()
        except Exception:
            pass
        time.sleep(0.25)

        # Click en barra de título para asegurar foco real
        try:
            x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
            y = int(w.top) + 15
            if x >= 0 and y >= 0:
                pyautogui.click(x, y)
                time.sleep(0.12)
        except Exception:
            pass

        # 1) Intento sin teclas: WM_CLOSE
        try:
            w.close()
        except Exception:
            pass

        time.sleep(0.8)
        if not _find_excel_wins():
            return True

        # 2) Si apareció diálogo de guardado, intenta "No guardar" (ES) / "Don't Save" (EN) con atajos
        # Solo si el foco realmente está en Excel
        if _active_is_excel():
            try:
                aw = gw.getActiveWindow()
                aw_title = (aw.title or "").lower() if aw else ""
                # El diálogo suele titularse "Microsoft Excel" y NO contiene el nombre del archivo.
                is_dialog = ("microsoft excel" in aw_title) and (key not in aw_title)
            except Exception:
                is_dialog = False

            if is_dialog:
                try:
                    pyautogui.hotkey("alt", "n")  # No guardar (ES)
                    time.sleep(0.25)
                except Exception:
                    pass
                try:
                    pyautogui.hotkey("alt", "d")  # Don't Save (EN)
                    time.sleep(0.25)
                except Exception:
                    pass
                try:
                    pyautogui.press("enter")
                    time.sleep(0.25)
                except Exception:
                    pass

        time.sleep(0.5)

    # Fallback final: si conocemos PIDs spawned, cerramos por PID sin afectar otras instancias
    if spawned:
        _taskkill_pids(spawned)
        time.sleep(1.0)
        if not _find_excel_wins():
            return True

    # Ultimísimo recurso: matar EXCEL.EXE completo (solo si se permite)
    if force_kill_excel or (kill_only_if_no_excel_was_running and not pids_before):
        try:
            subprocess.run(["taskkill", "/IM", "EXCEL.EXE", "/F"], capture_output=True, text=True, check=False)
            time.sleep(1.0)
            return True
        except Exception as ex:
            logging.warning(f"taskkill EXCEL.EXE falló: {ex}")

    logging.warning("No se logró cerrar Excel de forma segura; considera force_kill_excel=True.")
    return False

    def _find():
        wins = [w for w in gw.getAllWindows() if w.title and key in w.title.lower()]
        wins.sort(key=lambda w: (w.width * w.height), reverse=True)
        return wins

    def _focus(w):
        try:
            if w.isMinimized:
                w.restore()
            w.activate()
            time.sleep(0.35)
            cx = w.left + max(10, int(w.width) // 2)
            cy = w.top + max(10, int(w.height) // 2)
            if cx > 0 and cy > 0:
                pyautogui.click(cx, cy)
                time.sleep(0.15)
        except Exception:
            pass

    def _dont_save():
        # ES/EN por atajos del diálogo de Excel
        pyautogui.hotkey("alt", "n")
        time.sleep(0.25)
        pyautogui.press("enter")
        time.sleep(0.25)
        pyautogui.hotkey("alt", "d")
        time.sleep(0.25)
        pyautogui.press("enter")
        time.sleep(0.25)
        # Fallback por letras
        pyautogui.press("n")
        pyautogui.press("enter")
        time.sleep(0.2)
        pyautogui.press("d")
        pyautogui.press("enter")
        time.sleep(0.2)

    end = time.time() + timeout
    while time.time() < end:
        wins = _find()
        if not wins:
            return True

        w = wins[0]
        _focus(w)

        # 1) cerrar libro
        pyautogui.hotkey("ctrl", "w")
        time.sleep(0.8)
        _dont_save()

        # 2) si sigue la ventana, intenta cerrar app
        wins = _find()
        if not wins:
            return True

        _focus(wins[0])
        pyautogui.hotkey("alt", "f4")
        time.sleep(0.8)
        _dont_save()

        if not _find():
            return True

        time.sleep(0.5)

    # Fallback: force kill
    pids_before = excel_pids_before if excel_pids_before is not None else set()
    if force_kill_excel or (kill_only_if_no_excel_was_running and not pids_before):
        try:
            subprocess.run(["taskkill", "/IM", "EXCEL.EXE", "/F"], capture_output=True, text=True)
            time.sleep(1.0)
            return True
        except Exception as ex:
            logging.warning(f"taskkill EXCEL.EXE falló: {ex}")

    logging.warning("No se logró cerrar Excel por ventana; considera force_kill_excel=True.")
    return False

# ============================================================
# Helpers GENERALES
# ============================================================

def _screenshot(driver: WebDriver, prefix: str) -> Optional[str]:
    """Guarda screenshot en carpeta ./screens y devuelve la ruta, o None si falla."""
    try:
        os.makedirs("screens", exist_ok=True)
        path = os.path.join("screens", f"{prefix}_{uuid.uuid4().hex}.png")
        driver.save_screenshot(path)
        return path
    except Exception:
        return None

# def _wait_overlays(driver: WebDriver, timeout_overlays: float = 5.0) -> None:
#     """Espera desaparición de overlays/backdrops/spinners comunes (Angular/Material)."""
#     try:
#         WebDriverWait(driver, timeout_overlays).until(
#             EC.invisibility_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-backdrop.cdk-overlay-backdrop-showing"))
#         )
#     except TimeoutException:
#         pass
#     try:
#         WebDriverWait(driver, timeout_overlays).until_not(
#             lambda d: len(d.find_elements(By.CSS_SELECTOR, ".cdk-overlay-pane")) > 0
#         )
#     except TimeoutException:
#         pass
#     # Spinners típicos (ajusta según tu app)
#     for sel in [".mat-progress-spinner", ".mdc-linear-progress", ".spinner", ".loading"]:
#         try:
#             WebDriverWait(driver, 2).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, sel)))
#         except TimeoutException:
#             pass

def _wait_overlays(driver: WebDriver, timeout_overlays: float = 15.0) -> None:
    """Espera desaparición de overlays/backdrops/spinners comunes."""
    try:
        WebDriverWait(driver, timeout_overlays).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-backdrop.cdk-overlay-backdrop-showing"))
        )
    except TimeoutException:
        pass
        
    try:
        WebDriverWait(driver, timeout_overlays).until_not(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, ".cdk-overlay-pane")) > 0
        )
    except TimeoutException:
        pass
        
    # Spinners típicos
    spinners_css = [
        ".mat-progress-spinner", ".mdc-linear-progress", ".spinner", 
        ".loading", ".loader", "[role='progressbar']"
    ]
    
    for sel in spinners_css:
        try:
            WebDriverWait(driver, timeout_overlays).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, sel))
            )
        except TimeoutException:
            # Si después de 15 segundos sigue ahí, lo registramos pero no detenemos todo
            logging.warning(f"El overlay {sel} tardó más de {timeout_overlays}s en desaparecer.")
            
    # Un pequeño respiro de medio segundo para que las gráficas terminen de renderizar
    time.sleep(0.5)

def _switch_into_iframe_if_needed(driver: WebDriver, wait: WebDriverWait, iframe_xpath: Optional[str]) -> None:
    """Si se proporciona iframe_xpath, espera y entra al iframe."""
    if iframe_xpath:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframe_xpath)))

def _topmost_ok(driver: WebDriver, el) -> bool:
    """Comprueba si el centro del elemento está libre (no cubierto por otro)."""
    return driver.execute_script("""
        const el=arguments[0], r=el.getBoundingClientRect();
        const x=Math.floor(r.left + r.width/2), y=Math.floor(r.top + r.height/2);
        const t=document.elementFromPoint(x,y);
        return el===t || (t && (el.contains(t)||t.contains(el)));
    """, el)

def _restore_outline(driver: WebDriver, el, prev: Optional[str]) -> None:
    """Restaura el outline previo si es posible."""
    if el is None:
        return
    try:
        driver.execute_script("arguments[0].style.outline=arguments[1];", el, prev)
    except Exception:
        pass

# ============================================================
# Limpieza de estado (neutralizar mouse y cerrar menús)
# ============================================================

def ui_cleanup_state(driver: WebDriver, timeout: int = 3) -> None:
    """
    1) Mueve el mouse a un área neutra (arriba-izquierda).
    2) Click al body para cerrar menús.
    3) Espera a que se oculten overlays/menus de Angular Material.
    """
    try:
        ActionChains(driver).move_by_offset(-10_000, -10_000).perform()
        ActionChains(driver).move_by_offset(1, 1).perform()
        body = driver.find_element(By.TAG_NAME, "body")
        ActionChains(driver).move_to_element_with_offset(body, 5, 5).click().perform()
    except Exception:
        try:
            driver.execute_script("document.body.click();")
        except Exception:
            pass

    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, ".cdk-overlay-backdrop.cdk-overlay-backdrop-showing")
            )
        )
    except Exception:
        pass
    try:
        WebDriverWait(driver, timeout).until_not(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, ".cdk-overlay-pane")) > 0
        )
    except Exception:
        pass

# ============================================================
# Helpers STALE-SAFE (rebuscar y reintentar)
# ============================================================

def _refind(wait: WebDriverWait, xpath: str, visible: bool):
    """Re-encuentra el elemento tras un stale. visible=True usa visibility_of..., si no presence_of..."""
    cond = EC.visibility_of_element_located if visible else EC.presence_of_element_located
    return wait.until(cond((By.XPATH, xpath)))

def _do_with_refetch(driver: WebDriver, wait: WebDriverWait, xpath: str, visible: bool, func, max_retries: int = 3):
    """
    Ejecuta `func(el)` y, si el elemento se vuelve stale, lo reencuentra y reintenta.
    Devuelve el resultado de func o lanza la excepción real en el último intento.
    """
    el = _refind(wait, xpath, visible=visible)
    for _ in range(max_retries):
        try:
            return func(el)
        except StaleElementReferenceException:
            el = _refind(wait, xpath, visible=visible)
    return func(el)  # último intento, deja propagar si falla

def _center_and_highlight_stalesafe(
    driver: WebDriver,
    wait: WebDriverWait,
    xpath: str,
    outline_css: str = "4px solid #00FF00",
    pause: float = 0.1,
    visible: bool = True
):
    """
    Scroll + highlight con reintento si el elemento queda 'stale' durante la operación.
    Devuelve (element, prev_outline).
    """
    def _op(el):
        driver.execute_script("arguments[0].scrollIntoView({block:'center',inline:'center'})", el)
        prev = driver.execute_script(
            "const el=arguments[0]; const prev=el.style.outline; el.style.outline=arguments[1]; return prev;",
            el, outline_css
        )
        if pause > 0:
            sleep(pause)
        return el, prev

    return _do_with_refetch(driver, wait, xpath, visible=visible, func=_op, max_retries=3)

def ui_navigate(
    driver: WebDriver,
    url: str,
    nombre_pagina: str = "Pagina_Web",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
):
    """
    Navega a una URL, espera a que desaparezcan pantallas de carga 
    y toma la evidencia global estandarizada.
    """
    # 1. Navegamos a la URL
    driver.get(url)
    
    # 2. Esperamos a que la página asiente y los spinners iniciales desaparezcan
    try:
        _wait_overlays(driver)
    except Exception:
        pass
        
    # 3. Tomamos la foto panorámica de la página recién cargada
    take_global_evidence(driver, "goto_url", nombre_pagina, usar_create_screenshot, screenshot_step)

def ui_clear_downloads():
    """
    Limpia la carpeta de descargas antes de una nueva prueba 
    para evitar falsos positivos con archivos viejos.
    """
    download_dir = os.path.join(os.getcwd(), 'outputs', 'downloads')
    
    # Si la carpeta existe, borramos todo lo que hay adentro
    if os.path.exists(download_dir):
        archivos = glob.glob(os.path.join(download_dir, "*"))
        for archivo in archivos:
            try:
                os.remove(archivo)
            except Exception as e:
                pass # Si el archivo está bloqueado por el sistema, lo ignoramos
    else:
        # Si no existe, la creamos limpia
        os.makedirs(download_dir, exist_ok=True)

def ui_validate_download(
    extension: str = (".csv",),
    timeout: int = 30,
    nombre_elemento: str = "Archivo_Descargado",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
) -> bool:
    """
    Espera a que un archivo con la extensión dada aparezca en la carpeta de descargas.
    Genera un recibo visual estandarizado si la evidencia está activada.
    """
    download_dir = os.path.join(os.getcwd(), 'outputs', 'downloads')
    os.makedirs(download_dir, exist_ok=True)
    
    # 1. Normalizamos la entrada: si nos mandaron un string, lo hacemos lista
    if isinstance(extension, str):
        extensiones = [extension]
    else:
        extensiones = extension
        
    # 2. Preparamos los patrones de búsqueda (ej: ["*.xlsx", "*.xlsb"])
    patrones = [f"*{ext}" if ext.startswith(".") else f"*.{ext}" for ext in extensiones]
    
    start_time = time.time()
    archivo_descargado = None
    
    while time.time() - start_time < timeout:
        archivos_encontrados = []
        
        # 3. Buscamos TODOS los patrones permitidos en la carpeta
        for patron in patrones:
            archivos_encontrados.extend(glob.glob(os.path.join(download_dir, patron)))
            
        if archivos_encontrados:
            # Si encontró algo (sea xlsx o xlsb), nos quedamos con el más reciente
            archivo_descargado = max(archivos_encontrados, key=os.path.getctime)
            
            # Verificamos que el archivo ya tenga peso (>0 bytes)
            if os.path.getsize(archivo_descargado) > 0:
                break
                
        time.sleep(1) # Polling
        
    if archivo_descargado:
        tiempo_total = time.time() - start_time
        peso_bytes = os.path.getsize(archivo_descargado)
        
        if usar_create_screenshot:
            # Usamos la variable global de button_functions
            if GLOBAL_EVIDENCE_DIR:
                GetEvidence.create_download_receipt(
                    step=screenshot_step, 
                    label=nombre_elemento, 
                    dir_name=GLOBAL_EVIDENCE_DIR, 
                    file_path=archivo_descargado, 
                    file_size_bytes=peso_bytes, 
                    download_time_sec=tiempo_total
                )
        return archivo_descargado
    else:
        ext_str = " o ".join(extensiones)
        raise AssertionError(f"Ningún archivo con extensión {ext_str} llegó a descargas en {timeout}s.")  


def ui_validate_txt_content(
    file_path: str,
    textos_esperados: list = None,
    nombre_elemento: str = "Contenido_TXT",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
) -> bool:
    """
    Lee un archivo de texto plano (.txt), valida que no esté vacío,
    busca cadenas de texto específicas y genera un recibo visual de las primeras líneas.
    """
    try:
        # 1. Pausa de seguridad
        time.sleep(2.0)
        
        contenido_texto = ""
        
        # 2. Lectura nativa ultra rápida (soporta acentos y caracteres especiales con utf-8)
        with open(file_path, 'r', encoding='utf-8', errors='replace') as archivo:
            contenido_texto = archivo.read()
            
        # 3. Validar que no esté vacío
        if not contenido_texto or contenido_texto.strip() == "":
            raise AssertionError(f"El archivo {os.path.basename(file_path)} se descargó, pero está VACÍO.")
            
        # 4. Validar Textos Esperados (en lugar de columnas)
        if textos_esperados:
            for texto in textos_esperados:
                if texto not in contenido_texto:
                    raise AssertionError(f"No se encontró el texto esperado '{texto}' en el archivo .txt")
                    
        # 5. Generar el recibo visual (Foto oscura para el PDF)
        if usar_create_screenshot and GLOBAL_EVIDENCE_DIR:
            # Tomamos solo las primeras 20 líneas para no hacer una imagen kilométrica
            lineas = contenido_texto.split('\n')
            texto_preview = '\n'.join(lineas[:20])
            
            # Si el archivo tiene más de 20 líneas, le ponemos un aviso al final
            if len(lineas) > 20:
                texto_preview += "\n... [MÁS DATOS OCULTOS PARA LA VISTA PREVIA] ..."
                
            GetEvidence.create_data_preview_receipt(
                step=screenshot_step,
                label=nombre_elemento,
                dir_name=GLOBAL_EVIDENCE_DIR,
                file_path=file_path,
                data_string=texto_preview
            )
            
        return True
        
    except Exception as e:
        raise AssertionError(f"Error crítico al validar el contenido del TXT: {str(e)}")

def ui_validate_excel_content(
    file_path: str,
    columnas_esperadas: list = None,
    nombre_elemento: str = "Contenido_Excel",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
) -> bool:
    """
    Lee un archivo Excel/CSV en memoria (Headless-safe), valida que no esté vacío,
    verifica columnas específicas y genera un recibo visual de los datos.
    """
    
    try:
        # 1. Pausa de seguridad para el File System
        time.sleep(2.0)
        
        # 2. Variable para guardar la tabla que sí tenga datos
        df_final = pd.DataFrame()
        hoja_con_datos = ""
        
        # 3. Lógica de lectura inteligente
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
            df = df.dropna(how='all').dropna(axis=1, how='all') # Limpiamos filas/columnas 100% vacías
            if not df.empty:
                df_final = df
                
        else:
            # Es un Excel (.xlsx o .xlsb)
            engine_to_use = 'calamine' 
            
            # Leemos el archivo completo (todas las hojas)
            hojas = pd.read_excel(file_path, engine=engine_to_use, sheet_name=None)
            
            # Buscamos la primera hoja que realmente contenga información
            for nombre_hoja, df_hoja in hojas.items():
                # Limpiamos filas y columnas decorativas que estén 100% en blanco
                df_limpio = df_hoja.dropna(how='all').dropna(axis=1, how='all')
                
                if not df_limpio.empty and len(df_limpio.columns) > 0:
                    df_final = df_limpio
                    hoja_con_datos = nombre_hoja
                    break # Encontramos los datos, dejamos de buscar
                    
        # 4. Validar que encontramos datos o al menos la estructura de columnas
        if df_final is None or len(df_final.columns) == 0:
            raise AssertionError(f"El archivo {os.path.basename(file_path)} está totalmente VACÍO (Ni siquiera tiene columnas).")
            
        # 5. Validar columnas esperadas
        if columnas_esperadas:
            for col in columnas_esperadas:
                if col not in df_final.columns:
                    raise AssertionError(
                        f"Falta la columna '{col}'. \n"
                        f"Hoja leída: '{hoja_con_datos}' \n"
                        f"Columnas encontradas: {df_final.columns.tolist()}"
                    )
        
        # 6. Generar el recibo visual
        if usar_create_screenshot and GLOBAL_EVIDENCE_DIR:
            logging.info(f"\n[RADAR] Columnas detectadas: {df_final.columns.tolist()}\n")
            # Obligamos a Pandas a no colapsar las columnas
            with pd.option_context('display.max_columns', None, 'display.width', 2000, 'display.max_colwidth', None):
                # Imprimimos las primeras 15 filas
                tabla_texto = df_final.head(15).to_string(index=False)
            
            # Si leímos de un Excel con varias hojas, lo mencionamos en el recibo
            titulo_recibo = nombre_elemento if not hoja_con_datos else f"{nombre_elemento}_({hoja_con_datos})"
            
            GetEvidence.create_data_preview_receipt(
                step=screenshot_step,
                label=titulo_recibo,
                dir_name=GLOBAL_EVIDENCE_DIR,
                file_path=file_path,
                data_string=tabla_texto
            )
            
        return True
        
    except Exception as e:
        raise AssertionError(f"Error crítico al validar el contenido del archivo: {str(e)}")

# ============================================================
# FUNCIÓN PRINCIPAL: ui_interact
# ============================================================

ActionType = Literal["click", "insertTxt", "getValue", "highlight", "assertNotVisible"]

def ui_interact(
    driver: WebDriver,
    xPath_elemento: str,
    accion: ActionType,
    nombre_elemento: str = "Elemento",
    valor: Optional[str] = None,                # Para insertTxt
    iframe_xpath: Optional[str] = None,
    timeout: int = 15,
    borde_css: str = "4px solid #00FF00",
    usar_click_js_si_falla: bool = True,
    usar_js_para_input: bool = True,            # Para insertTxt: set value + eventos (React/Angular)
    restaurar_borde: bool = True,
    cleanup_al_final: bool = True,

    # Evidencia (opcional)
    usar_create_screenshot: bool = False,
    # wait_for_xpath: Optional[str] = None,       # Espera a que este XPath sea visible antes de tomar la evidencia
    screenshot_step: Optional[str] = None,      # Número de evidencia (p.ej. "STEP_01")
    screenshot_dir_name: str = "",              # Carpeta donde se guardará la evidencia
    create_screenshot_fn=None,                  # Inyecta create_screenshot si vive en otro módulo
):
    wait = WebDriverWait(driver, timeout)
    el = None
    prev_outline = None

    try:
        _switch_into_iframe_if_needed(driver, wait, iframe_xpath)

        # if wait_for_xpath:
        #     wait.until(EC.presence_of_element_located((By.XPATH, wait_for_xpath)))
        
        # Validar que un elemento NO esté en pantalla 
        if accion == "assertNotVisible":
            _wait_overlays(driver) # Esperamos a que terminen de cargar los datos normales
            
            # Buscamos si el popup de error existe y está visible
            elementos = driver.find_elements(By.XPATH, xPath_elemento)
            visibles = [e for e in elementos if e.is_displayed()]
            
            if visibles:
                el_error = visibles[0]
                # ¡Lo atrapamos! Lo enmarcamos en ROJO para la foto de evidencia
                try:
                    driver.execute_script("arguments[0].style.outline='6px solid #FF0000';", el_error)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el_error)
                except Exception:
                    pass
                
                # Forzamos la captura de pantalla aunque la bandera general esté apagada
                # snap = take_global_evidence(driver, "FALLO_POPUP", nombre_elemento, True, screenshot_step)
                
                msg = f"FALLO DEL TEST: Apareció el mensaje/pop-up inesperado '{nombre_elemento}'. XPATH: {xPath_elemento}"
                logging.error(msg)
                raise AssertionError(msg) # Esto detiene el test de inmediato y lo marca como Fallido
            
            else:
                # Todo bien, el elemento no apareció. Tomamos foto de éxito si nos la pidieron.
                take_global_evidence(driver, accion, nombre_elemento, usar_create_screenshot, screenshot_step)
                return True

        if accion in ["click", "insertTxt"]:
            wait.until(EC.element_to_be_clickable((By.XPATH, xPath_elemento)))
        else:
            wait.until(EC.visibility_of_element_located((By.XPATH, xPath_elemento)))

        _wait_overlays(driver)

        # 1. Enmarcamos y optimizamos la pausa a 0.1s
        el, prev_outline = _center_and_highlight_stalesafe(
            driver, wait, xPath_elemento, outline_css=borde_css, pause=0.1, visible=True
        )

        if accion == "click":
            # Para el clic, tomamos la foto ANTES de hacer clic
            take_global_evidence(driver, accion, nombre_elemento, usar_create_screenshot, screenshot_step)
            try:
                _do_with_refetch(driver, wait, xPath_elemento, visible=True, func=lambda e: e.click(), max_retries=2)
                return el
            except (ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException):
                try:
                    _do_with_refetch(
                        driver, wait, xPath_elemento, visible=True,
                        func=lambda e: ActionChains(driver).move_to_element(e).pause(0.1).click(e).perform(),
                        max_retries=2
                    )
                    return el
                except Exception:
                    if usar_click_js_si_falla:
                        _do_with_refetch(
                            driver, wait, xPath_elemento, visible=True,
                            func=lambda e: driver.execute_script("arguments[0].click();", e),
                            max_retries=2
                        )
                        return el

                    # Corregido: Removida la variable 'accion' que sobraba en los argumentos
                    snap = take_global_evidence(driver, "click_error", nombre_elemento, usar_create_screenshot, screenshot_step) or _screenshot(driver, "click_error")
                    msg = (f'No se pudo hacer clic en "{nombre_elemento}". XPATH: {xPath_elemento}\n'
                           f'Screenshot: {snap or "no disponible"}')
                    logging.error(msg)
                    raise AssertionError(msg)

        elif accion == "insertTxt":
            if valor is None:
                raise AssertionError(f'Para "insertTxt" debes proporcionar `valor` para "{nombre_elemento}".')

            def _clear_and_type(e):
                try:
                    if e.tag_name and e.tag_name.lower() in ("input", "textarea"):
                        e.clear()
                except Exception:
                    pass
                e.send_keys(valor)
                return True

            _do_with_refetch(driver, wait, xPath_elemento, visible=True, func=_clear_and_type, max_retries=3)

            if usar_js_para_input:
                _do_with_refetch(
                    driver, wait, xPath_elemento, visible=True,
                    func=lambda e: driver.execute_script("""
                        const el=arguments[0], v=arguments[1];
                        const isInput = el.tagName==='INPUT' || el.tagName==='TEXTAREA';
                        if (isInput) {
                            const desc = Object.getOwnPropertyDescriptor(el.__proto__, 'value');
                            if (desc && desc.set) { desc.set.call(el, v); } else { el.value = v; }
                            el.dispatchEvent(new Event('input', {bubbles:true}));
                            el.dispatchEvent(new Event('change', {bubbles:true}));
                        } else {
                            el.textContent = v;
                            el.dispatchEvent(new Event('input', {bubbles:true}));
                            el.dispatchEvent(new Event('change', {bubbles:true}));
                        }
                    """, e, valor),
                    max_retries=3
                )
            
            # Tomamos la foto DESPUÉS de escribir, pero con el recuadro verde aún activo
            take_global_evidence(driver, accion, nombre_elemento, usar_create_screenshot, screenshot_step)
            return el

        elif accion == "getValue":
            def _get_value(e):
                val = e.get_attribute("value")
                if val is None or val == "":
                    val = e.get_attribute("textContent") or e.get_attribute("innerText") or ""
                    val = val.strip()
                return val

            value = _do_with_refetch(driver, wait, xPath_elemento, visible=True, func=_get_value, max_retries=2)
            take_global_evidence(driver, accion, nombre_elemento, usar_create_screenshot, screenshot_step)
            return value
        
        elif accion == "highlight":
            # Para validaciones visuales: Solo enmarca y toma la foto
            take_global_evidence(driver, accion, nombre_elemento, usar_create_screenshot, screenshot_step)
            return el

        else:
            raise AssertionError(f"Acción no soportada: {accion}")

    except TimeoutException as e:
        # Corregido: Removida la variable 'accion' que sobraba en los argumentos
        take_global_evidence(driver, "timeout", nombre_elemento, usar_create_screenshot, screenshot_step)
        raise AssertionError(
            f'El elemento "{nombre_elemento}" no estuvo disponible para "{accion}" tras {timeout}s. XPATH: {xPath_elemento}'
        ) from e

    finally:
        try:
            if restaurar_borde:
                _restore_outline(driver, el, prev_outline)
        except Exception:
            pass
        if cleanup_al_final:
            ui_cleanup_state(driver)

def ui_menu_action(
    driver: WebDriver,
    menu_xpath: str,
    submenu_text: Optional[str] = None,
    submenu_xpath: Optional[str] = None,
    nombre_menu: str = "Menú acciones",
    nombre_opcion: str = "Opción",
    iframe_xpath: Optional[str] = None,
    timeout: int = 15,
    open_method: Literal["hover", "click"] = "hover",
    borde_css: str = "4px solid #00FF00",
    restaurar_borde: bool = True,
):
    """
    Abre un menú (hover o click) y selecciona una opción del menú.
    Pensado para Angular/Material donde el menú aparece en .cdk-overlay-pane.
    """
    wait = WebDriverWait(driver, timeout)
    el_menu = None
    prev_outline_menu = None
    prev_outline_item = None

    try:
        _switch_into_iframe_if_needed(driver, wait, iframe_xpath)

        wait.until(EC.element_to_be_clickable((By.XPATH, menu_xpath)))
        _wait_overlays(driver)

        el_menu, prev_outline_menu = _center_and_highlight_stalesafe(
            driver, wait, menu_xpath, outline_css=borde_css, pause=0.2, visible=True
        )

        if open_method == "hover":
            _do_with_refetch(
                driver, wait, menu_xpath, visible=True,
                func=lambda e: ActionChains(driver).move_to_element(e).pause(0.2).perform(),
                max_retries=2
            )
        else:
            _do_with_refetch(driver, wait, menu_xpath, visible=True, func=lambda e: e.click(), max_retries=2)

        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".cdk-overlay-pane")) > 0)
        _wait_overlays(driver, timeout_overlays=2)

        if submenu_xpath:
            target_xpath = submenu_xpath
        else:
            if not submenu_text:
                raise AssertionError("Debes proporcionar submenu_text o submenu_xpath.")
            target_xpath = (
                "//div[contains(@class,'cdk-overlay-pane')]"
                "//button[.//span[normalize-space(.)=$text] or normalize-space(.)=$text]"
            ).replace("$text", submenu_text.replace("'", "\\'"))

        el_item, prev_outline_item = _center_and_highlight_stalesafe(
            driver, wait, target_xpath, outline_css=borde_css, pause=0.2, visible=True
        )

        _do_with_refetch(driver, wait, target_xpath, visible=True, func=lambda e: e.click(), max_retries=2)

        return el_item

    except TimeoutException as e:
        raise AssertionError(
            f'No fue posible abrir "{nombre_menu}" o encontrar la opción "{nombre_opcion}" en {timeout}s.'
        ) from e
    except Exception as e:
        snap = _screenshot(driver, "menu_action_error")
        msg = (f'Fallo al seleccionar "{nombre_opcion}" en "{nombre_menu}". '
               f'Detalle: {type(e).__name__}: {e}\nScreenshot: {snap or "no disponible"}')
        logging.error(msg)
        raise AssertionError(msg)
    finally:
        if restaurar_borde:
            try:
                _restore_outline(driver, el_menu, prev_outline_menu)
                _restore_outline(driver, el_item, prev_outline_item)
            except Exception:
                pass

# ============================================================
# NUEVO: Movimiento de mouse y click “en pantalla”
# ============================================================

def ui_mouse_move(
    driver: WebDriver,
    *,
    xpath: Optional[str] = None,
    offset: Tuple[int, int] = (0, 0),
    x_abs: Optional[int] = None,
    y_abs: Optional[int] = None,
    iframe_xpath: Optional[str] = None,
    timeout: int = 10,
    wait_for_xpath: Optional[str] = None,
    scroll_block: str = "center",
    nombre_elemento: str = "Hover_Area",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
) -> None:
    """
    Mueve el mouse a un ELEMENTO (por XPATH) o coordenadas absolutas.
    """
    wait = WebDriverWait(driver, timeout)

    if xpath:
        _switch_into_iframe_if_needed(driver, wait, iframe_xpath)
        
        # 1. Esperar a que desaparezcan los spinners de carga globales
        try:
            _wait_overlays(driver) 
        except Exception:
            pass

        # 2. Espera opcional por un elemento interno (ej. esperar a que carguen las filas //tr)
        if wait_for_xpath:
            wait.until(EC.presence_of_element_located((By.XPATH, wait_for_xpath)))

        # 3. Esperar a que el elemento principal sea visible
        el = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        
        # 4. Scroll automático y seguro (PRIMERO, para que el elemento esté en pantalla)
        try:
            driver.execute_script(f"arguments[0].scrollIntoView({{behavior: 'instant', block: '{scroll_block}', inline: 'center'}});", el) 
            time.sleep(0.15) 
        except Exception:
            pass

        # Dibujamos el cuadro verde temporalmente
        try:
            driver.execute_script("arguments[0].style.outline='2px solid #00A000';", el)
        except Exception:
            pass

        # 5. Ejecutar el movimiento final del mouse
        ActionChains(driver).move_to_element_with_offset(el, offset[0], offset[1]).perform()
        
    
        # Tomamos la foto con el elemento ya centrado y verde
        take_global_evidence(driver, "hover", nombre_elemento, usar_create_screenshot, screenshot_step)

        # Quitamos el cuadro verde para no dejar rastro
        try:
            driver.execute_script("arguments[0].style.outline='';", el)
        except Exception:
            pass
        
        return
    
    if x_abs is not None and y_abs is not None:
        # Emular absoluto: reset a (0,0) aprox y luego offset hasta (x_abs, y_abs)
        ActionChains(driver).move_by_offset(-10_000, -10_000).perform()
        ActionChains(driver).move_by_offset(x_abs, y_abs).perform()
        return

    raise AssertionError("Debes proporcionar xpath+offset o x_abs+y_abs para mover el mouse.")


def ui_mouse_move_pixels(
    driver: WebDriver,
    dx: int = 0,
    dy: int = 0,
    *,
    anchor_to_body: bool = True,
    timeout: int = 10
) -> None:
    """
    Mueve el "puntero" de Selenium (no siempre el cursor del SO) por offset en pixeles.

    - dy > 0 mueve hacia abajo; dy < 0 mueve hacia arriba.
    - Si anchor_to_body=True, primero ancla el puntero al <body> para evitar offsets
      relativos a una posición desconocida.

    Nota importante:
      Selenium mueve un puntero virtual dentro del viewport. Si el offset final cae
      fuera del viewport, el driver puede ignorar la acción o lanzar MoveTargetOutOfBoundsException.
    """
    wait = WebDriverWait(driver, timeout)

    if anchor_to_body:
        body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # Anclar a una zona "segura" (centro del viewport) para maximizar margen de movimiento.
        vw = driver.execute_script("return Math.max(document.documentElement.clientWidth, window.innerWidth || 0);")
        vh = driver.execute_script("return Math.max(document.documentElement.clientHeight, window.innerHeight || 0);")
        # Centro con un pequeño margen para evitar bordes.
        cx = max(2, int(vw // 2))
        cy = max(2, int(vh // 2))
        ActionChains(driver).move_to_element_with_offset(body, cx, cy).perform()

    if dx == 0 and dy == 0:
        return

    # Clamp básico: evita intentar terminar fuera del viewport cuando el movimiento es muy grande.
    # Esto no es perfecto (porque el driver no expone la posición actual del puntero), pero reduce fallos comunes.
    vw = driver.execute_script("return Math.max(document.documentElement.clientWidth, window.innerWidth || 0);")
    vh = driver.execute_script("return Math.max(document.documentElement.clientHeight, window.innerHeight || 0);")
    max_dx = int(vw // 2) - 3
    max_dy = int(vh // 2) - 3
    dx = int(max(-max_dx, min(max_dx, dx)))
    dy = int(max(-max_dy, min(max_dy, dy)))

    ActionChains(driver).move_by_offset(dx, dy).perform()


def ui_mouse_move_vertical_pixels(
    driver: WebDriver,
    pixels: int,
    *,
    direction: str = "down",
    anchor_to_body: bool = True,
    timeout: int = 10
) -> None:
    """
    Wrapper para mover el puntero arriba/abajo en pixeles.

    direction:
      - "down" / "abajo"  => dy positivo
      - "up"   / "arriba" => dy negativo
    """
    direction_norm = (direction or "").strip().lower()
    if direction_norm in ("down", "abajo", "bottom"):
        dy = abs(int(pixels))
    elif direction_norm in ("up", "arriba", "top"):
        dy = -abs(int(pixels))
    else:
        raise AssertionError("direction debe ser 'down/abajo' o 'up/arriba'.")

    ui_mouse_move_pixels(driver, dx=0, dy=dy, anchor_to_body=anchor_to_body, timeout=timeout)


def ui_scroll_vertical_pixels(driver: WebDriver, pixels: int) -> None:
    """
    Hace scroll del viewport (rueda/página), NO mueve el puntero.
    Útil cuando la intención era 'bajar la página' por N pixeles.
    """
    driver.execute_script("window.scrollBy(0, arguments[0]);", int(pixels))


def ui_click_screen(
    driver: WebDriver,
    *,
    x_abs: Optional[int] = None,
    y_abs: Optional[int] = None,
    click_body_fallback: bool = True
) -> None:
    """
    Hace clic en “la pantalla”:
      - Si x_abs/y_abs se indican: emula clic en ese punto de la ventana.
      - Si no: intenta clic en el <body> (útil para cerrar menús/overlays).
    """
    if x_abs is not None and y_abs is not None:
        ActionChains(driver).move_by_offset(-10_000, -10_000).perform()
        ActionChains(driver).move_by_offset(x_abs, y_abs).click().perform()
        # opcional: regresar a esquina
        ActionChains(driver).move_by_offset(-x_abs, -y_abs).perform()
        return

    if click_body_fallback:
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            ActionChains(driver).move_to_element_with_offset(body, 5, 5).click().perform()
            return
        except Exception:
            try:
                driver.execute_script("document.body.click();")
                return
            except Exception:
                pass

    raise AssertionError("No fue posible hacer click en pantalla con los parámetros dados.")

def ui_get_value_raw(driver, xPath_elemento: str, nombre_elemento: str = "Elemento"):
    """
    Obtiene el valor/texto de un elemento SIN hacer scroll, highlight ni click.
    Útil para inputs que cambian al ganar/perder foco.
    """
    try:
        el = driver.find_element("xpath", xPath_elemento)
        val = el.get_attribute("value")
        if not val:
            val = el.get_attribute("textContent") or el.get_attribute("innerText") or ""
        return val.strip()
    except Exception as e:
        raise AssertionError(f'No se pudo obtener valor de "{nombre_elemento}". Detalle: {e}')
    
#####---------Manejo de Dropdowns --------####
def select_dropdown_option(driver, dropdown_label_text, option_text, timeout=10):
    wait = WebDriverWait(driver, timeout)

    # 1. Click en el label del dropdown
    dropdown_label = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//*[@data-testid='select-label' and text()='{dropdown_label_text}']")
        )
    )
    dropdown_label.click()

    # # 2. Esperar a que el contenedor se abra (aria-hidden='false')
    # dropdown_container = wait.until(
    #     EC.visibility_of_element_located(
    #         (By.XPATH, "//div[@data-testid='select-items' and @aria-hidden='false']")
    #     )
    # )

    # 3. Click en la opción
    option = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//div[@class='select-items--option'][contains(.,'{option_text}')]")
        )
    )
    option.click()   


    #--------------------------------------------------------------------------------

def select_date_control(
    driver: WebDriver,
    input_xpath: str,
    date_str: str,
    nombre_elemento: str = "Fecha",
    date_format: Optional[str] = None,
    timeout: float = 15.0,
    open_button_xpath: Optional[str] = None,
    prefer_iso_for_type_date: bool = True,
) -> str:
    """
    Selecciona/establece una fecha en un control de fecha.

    Soporta 2 escenarios comunes:
      1) Input editable (incluye <input type="date">): establece el valor por JS (input/change) y como respaldo con send_keys.
      2) Datepicker con overlay: opcionalmente abre el calendario con `open_button_xpath` y hace clic en el día como fallback.

    Retorna el valor final del atributo `value`.
    """
    wait = WebDriverWait(driver, timeout)

    def _parse_date(s: str) -> datetime:
        s = (s or "").strip()
        if not s:
            raise ValueError("date_str vacío")
        if date_format:
            return datetime.strptime(s, date_format)

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
        raise ValueError(f"No pude interpretar date_str='{s}'. Proporciona date_format, ej. '%d/%m/%Y'.")

    dt = _parse_date(date_str)
    iso_value = dt.strftime("%Y-%m-%d")
    day_num = str(dt.day)

    # 1) Intento: setear por JS + disparar eventos
    def _set_value_js(e):
        _wait_overlays(driver)
        typ = (e.get_attribute("type") or "").lower()
        target = iso_value if (prefer_iso_for_type_date and typ == "date") else date_str

        driver.execute_script("""
            const el=arguments[0], v=arguments[1];
            el.focus();
            el.value = v;
            el.dispatchEvent(new Event('input',  {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
        """, e, target)

        try:
            e.send_keys(Keys.TAB)
        except Exception:
            pass
        return True

    try:
        _do_with_refetch(driver, wait, input_xpath, visible=True, func=_set_value_js, max_retries=3)
    except Exception as ex:
        logging.warning(f"select_date_control: set_value_js falló ({type(ex).__name__}): {ex}")

    def _read_value(e):
        return (e.get_attribute("value") or "").strip()

    current_val = _do_with_refetch(driver, wait, input_xpath, visible=True, func=_read_value, max_retries=2)

    # Si es type=date, normalmente debe quedar ISO
    try:
        el_tmp = _refind(wait, input_xpath, visible=True)
        typ = (el_tmp.get_attribute("type") or "").lower()
    except Exception:
        typ = ""

    expected = iso_value if (prefer_iso_for_type_date and typ == "date") else None

    if expected and current_val == expected:
        return current_val
    if (not expected) and current_val:
        return current_val

    # 2) Respaldo: send_keys vía ui_interact
    try:
        ui_interact(
            driver,
            input_xpath,
            "insertTxt",
            nombre_elemento=nombre_elemento,
            valor=(iso_value if (prefer_iso_for_type_date and typ == "date") else date_str),
            timeout=timeout,
            usar_js_para_input=True,
        )
        current_val = _do_with_refetch(driver, wait, input_xpath, visible=True, func=_read_value, max_retries=2)
        if current_val:
            return current_val
    except Exception as ex:
        logging.warning(f"select_date_control: send_keys fallback falló ({type(ex).__name__}): {ex}")

    # 3) Fallback final: abrir datepicker y seleccionar el día (best-effort)
    if open_button_xpath:
        try:
            ui_interact(driver, open_button_xpath, "click", nombre_elemento="Abrir calendario", timeout=timeout)
        except Exception as ex:
            logging.warning(f"select_date_control: abrir calendario falló ({type(ex).__name__}): {ex}")

    candidates = [
        f"//mat-calendar//*[self::button or self::div or self::span][normalize-space()='{day_num}'][not(ancestor-or-self::*[@disabled])]",
        f"//div[contains(@class,'react-datepicker')]//div[contains(@class,'react-datepicker__day') and not(contains(@class,'outside-month')) and normalize-space()='{day_num}']",
        f"//*[contains(@class,'cdk-overlay-container') or contains(@class,'cdk-overlay-pane')]//*[self::button or self::div or self::span][normalize-space()='{day_num}']",
        f"//*[self::button or self::div or self::span][normalize-space()='{day_num}']",
    ]

    clicked = False
    for xp in candidates:
        try:
            _wait_overlays(driver)
            el_day = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
            el_day.click()
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        raise AssertionError(
            f'No se pudo establecer la fecha en "{nombre_elemento}". '
            f'Input XPATH: {input_xpath}. Si usas datepicker, proporciona open_button_xpath o ajusta selectores.'
        )

    current_val = _do_with_refetch(driver, wait, input_xpath, visible=True, func=_read_value, max_retries=2)
    return current_val

def set_flatpickr_date(
    driver,
    date_str: str,
    input_locator=(By.ID, "fecha"),
    flatpickr_format: str = "Y-m-d",
    timeout: float = 10.0,
    restore_readonly: bool = True,
    nombre_elemento: str = "Fecha_Flatpickr",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
) -> str:
    """
    Establece una fecha en un input Flatpickr readonly y dispara onchange (updatetodo()).

    - date_str: fecha a establecer (por ejemplo '2026-01-07' si flatpickr_format='Y-m-d')
    - flatpickr_format: formato Flatpickr (tokens: Y, m, d, etc.)
    Retorna el value final del input.
    """
    wait = WebDriverWait(driver, timeout)
    el = wait.until(EC.presence_of_element_located(input_locator))

    # Asegura visibilidad para evitar clicks/JS sobre elementos fuera de viewport
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    
    try:
        driver.execute_script("arguments[0].style.outline='2px solid #00A000';", el)
    except Exception:
        pass
        
    take_global_evidence(driver, "set_date", nombre_elemento, usar_create_screenshot, screenshot_step)
    
    try:
        driver.execute_script("arguments[0].style.outline='';", el)
    except Exception:
        pass

    # 1) Camino ideal: usar la instancia Flatpickr (dispara change si triggerChange=true)
    used_fp = driver.execute_script(
        """
        const el = arguments[0];
        const dateStr = arguments[1];
        const fmt = arguments[2];
        const fp = el._flatpickr;

        if (fp && typeof fp.setDate === 'function') {
            // 2do parámetro true = triggerChange (debe disparar onchange="updatetodo();")
            fp.setDate(dateStr, true, fmt);
            return true;
        }
        return false;
        """,
        el, date_str, flatpickr_format
    )

    if used_fp:
        return (el.get_attribute("value") or "").strip()

    # 2) Fallback: remover readonly, set value y disparar eventos (input/change)
    driver.execute_script(
        """
        const el = arguments[0];
        const v  = arguments[1];
        const restore = arguments[2];

        const hadReadonly = el.hasAttribute('readonly');
        if (hadReadonly) el.removeAttribute('readonly');

        el.focus();
        el.value = v;
        el.dispatchEvent(new Event('input',  {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));

        if (restore && hadReadonly) el.setAttribute('readonly','readonly');
        """,
        el, date_str, restore_readonly
    )

    return (el.get_attribute("value") or "").strip()

#Click sobre menu desplegable Raiz, Submenu , Sub-SubMenu

def _mark_element(driver, el):
    driver.execute_script(
        "arguments[0].style.outline='2px solid #00A000';"
        "arguments[0].style.outlineOffset='2px';",
        el
    )

def _mark_by_xpath(driver, xpath: str, timeout: int = 3):
    # Marca re-localizando por xpath (evita referencias stale)
    el = WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.XPATH, xpath)))
    _mark_element(driver, el)
    return el

def select_menu_option(
    driver,
    root_xpath: str,
    submenu_hover_xpath: str,
    subsubmenu_click_xpath: str,
    timeout: int = 15,
    mark_root: bool = True,
    mark_submenu: bool = True,
    mark_subsubmenu: bool = True,
    pause: float = 0.20,
    scroll_to_top: bool = False,
    nombre_elemento: str = "Menu_Opcion",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
):
    """
    Click raíz -> hover submenú -> click sub-submenú.
    Nota: el sub-submenú suele desaparecer tras el click, por eso se marca ANTES de click.
    """
    wait = WebDriverWait(driver, timeout)

    try:
        # 1) Reseteo visual opcional para evitar "Sticky Headers" cruzados
        if scroll_to_top:
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
        # 2) Click raíz
        root = wait.until(EC.element_to_be_clickable((By.XPATH, root_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", root)

        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, root_xpath))).click()
        except Exception:
            driver.execute_script("arguments[0].click();", root)

        if mark_root:
            try:
                _mark_element(driver, root)
            except StaleElementReferenceException:
                # si la vista re-renderiza, re-marcar por xpath
                _mark_by_xpath(driver, root_xpath, timeout=2)

        # 3) Hover submenú
        submenu = wait.until(EC.element_to_be_clickable((By.XPATH, submenu_hover_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", submenu)

        ActionChains(driver).move_to_element(submenu).pause(pause).perform()
        driver.execute_script(
            "arguments[0].dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));",
            submenu
        )

        if mark_submenu:
            try:
                _mark_element(driver, submenu)
            except StaleElementReferenceException:
                _mark_by_xpath(driver, submenu_hover_xpath, timeout=2)

        # 4) Sub-submenú: MARCAR ANTES + CLICK
        subsubmenu = wait.until(EC.element_to_be_clickable((By.XPATH, subsubmenu_click_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", subsubmenu)

        if mark_subsubmenu:
            # marcar ANTES del click para evitar stale
            try:
                _mark_element(driver, subsubmenu)
            except StaleElementReferenceException:
                # re-locate y marcar
                subsubmenu = _mark_by_xpath(driver, subsubmenu_click_xpath, timeout=2)
                take_global_evidence(driver, "click_menu", nombre_elemento, usar_create_screenshot, screenshot_step)
        
        # Toma Captura de evidencia        
        take_global_evidence(driver, "select_menu", nombre_elemento, usar_create_screenshot, screenshot_step)        

        # click final
        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, subsubmenu_click_xpath))).click()
        except Exception:
            try:
                ActionChains(driver).move_to_element(subsubmenu).pause(0.05).click(subsubmenu).perform()
            except Exception:
                driver.execute_script("arguments[0].click();", subsubmenu)

        return True

    except TimeoutException:
        raise AssertionError(
            "No se pudo completar el flujo root->click, submenu->hover, subsubmenu->click. "
            f"root_xpath={root_xpath} submenu_hover_xpath={submenu_hover_xpath} subsubmenu_click_xpath={subsubmenu_click_xpath}"
        )

def click_root_and_click_submenu(
    driver,
    root_xpath: str,
    submenu_click_xpath: str,
    timeout: int = 15,
    mark_root: bool = True,
    mark_submenu: bool = True,
    nombre_elemento: str = "Submenu_Opcion",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
):
    """
    Click raíz -> Click opción de submenú (2 niveles).
    """
    wait = WebDriverWait(driver, timeout)

    try:
        # 1) Click raíz
        root = wait.until(EC.element_to_be_clickable((By.XPATH, root_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", root)
        time.sleep(0.3)
        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, root_xpath))).click()
        except Exception:
            driver.execute_script("arguments[0].click();", root)

        if mark_root:
            try:
                _mark_element(driver, root)
            except StaleElementReferenceException:
                pass

        # 2) Click submenú
        sub = wait.until(EC.element_to_be_clickable((By.XPATH, submenu_click_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", sub)
        if mark_submenu:
            try:
                _mark_element(driver, sub)  # marcar ANTES del click
            except StaleElementReferenceException:
                pass
        take_global_evidence(driver, "click_submenu", nombre_elemento, usar_create_screenshot, screenshot_step)

        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, submenu_click_xpath))).click()
        except Exception:
            driver.execute_script("arguments[0].click();", sub)

        return True

    except TimeoutException:
        raise AssertionError(
            f"No se pudo ejecutar click raíz y click submenú. root_xpath={root_xpath} submenu_click_xpath={submenu_click_xpath}"
        )

def ui_select_native_dropdown(
    driver: WebDriver,
    xPath_elemento: str,
    valor_seleccion: str,
    tipo_seleccion: Literal["value", "text", "index"] = "value",
    nombre_elemento: str = "Dropdown Nativo",
    timeout: int = 15,
    borde_css: str = "4px solid #00FF00",
    restaurar_borde: bool = True,
    usar_create_screenshot: bool = False,
    screenshot_step: Optional[str] = None,
    screenshot_dir_name: str = ""
):
    """
    Interactúa con un elemento <select> nativo de HTML de forma robusta.
    Permite seleccionar por 'value' (por defecto), texto visible ('text'), o índice numérico ('index').
    """
    wait = WebDriverWait(driver, timeout)
    el = None
    prev_outline = None

    try:
        # 1. Esperamos a que el select sea visible e interactuable
        el = wait.until(EC.element_to_be_clickable((By.XPATH, xPath_elemento)))
        _wait_overlays(driver) # Usamos tu helper existente para evitar bloqueos
        
        # 2. Hacemos scroll y resaltamos el elemento (stale-safe)
        el, prev_outline = _center_and_highlight_stalesafe(
            driver, wait, xPath_elemento, outline_css=borde_css, pause=0.4, visible=True
        )
        
        # 3. Usamos la clase Select nativa de Selenium
        select_obj = Select(el)
        
        # 4. Ejecutamos la selección según el tipo solicitado
        if tipo_seleccion == "value":
            select_obj.select_by_value(str(valor_seleccion))
        elif tipo_seleccion == "text":
            select_obj.select_by_visible_text(str(valor_seleccion))
        elif tipo_seleccion == "index":
            select_obj.select_by_index(int(valor_seleccion))
        else:
            raise ValueError(f"El tipo_seleccion '{tipo_seleccion}' no es válido. Usa 'value', 'text' o 'index'.")
            
        # 5. Disparamos eventos JS por si la app los necesita
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """, el)

        # 6. Captura de evidencia 
        take_global_evidence(driver, "select_dropdown", nombre_elemento, usar_create_screenshot, screenshot_step)
        return el

    except TimeoutException as e:
        raise AssertionError(
            f'El dropdown "{nombre_elemento}" no estuvo disponible tras {timeout}s. XPATH: {xPath_elemento}'
        ) from e
    except Exception as e:
        raise AssertionError(f"Fallo al seleccionar '{valor_seleccion}' en '{nombre_elemento}'. Detalles: {e}")
    finally:
        if restaurar_borde:
            try:
                _restore_outline(driver, el, prev_outline)
            except Exception:
                pass

def descargar_abrir_evidenciar_y_cerrar_excel(
    web_driver,
    fecha_consulta: str,                           # "YYYY-MM-DD"
    nameExcel: str,                                # prefijo exacto del archivo (puede incluir espacios/paréntesis)
    download_dir: str | Path = "outputs/downloads",
    evidence_dir: str | Path = "outputs/evidences",
    step: str = "STEP_05",
    label_folder: str = "1_folder_downloads",
    label_excel: str = "2_open_excel",
    timeout_download: int = 180,
    explorer_wait: float = 1.5,
    excel_wait: float = 4.0,
    excel_window_hint: str | None = None,
    explorer_window_hint: str | None = None,
    pre_capture_wait: float = 6.0,
    force_kill_excel: bool = False,
) -> dict:
    """
    Espera y abre: download_dir / (nameExcel + fecha_consulta + '*.xlsx')

    Ejemplo:
      nameExcel="Deposito 5) Cajeros sin Journal (TRX solo stat)"
      fecha_consulta="2025-05-05"
      => "Deposito 5) Cajeros sin Journal (TRX solo stat)2025-05-05*.xlsx"

    Flujo:
      1) Espera descarga
      2) Abre carpeta (Explorer) + screenshot OS
      3) Abre Excel + screenshot OS
      4) Cierra Excel (Ctrl+W/Alt+N/Alt+F4) y, si NO había Excel abierto antes, puede forzar cierre.
    """
    download_dir = Path(download_dir).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    nameExcel = (nameExcel or "").rstrip()
    target_prefix = f"{nameExcel}{fecha_consulta}".lower()

    # Regex: ^<nameExcel><YYYY-MM-DD>.*\.xlsx$
    pattern = re.compile(rf"^{re.escape(nameExcel)}{re.escape(fecha_consulta)}.*\.xlsx$", re.IGNORECASE)

    # 1) Esperar XLSX terminado
    end = time.time() + timeout_download
    last_size = -1
    stable_ticks = 0
    xlsx_path: Path | None = None

    while time.time() < end:
        files = [
            p for p in download_dir.glob("*.xlsx")
            if p.name.lower().startswith(target_prefix) and pattern.match(p.name)
        ]

        if files:
            candidate = max(files, key=lambda p: p.stat().st_mtime)
            size = candidate.stat().st_size

            if size == last_size and size > 0:
                stable_ticks += 1
            else:
                stable_ticks = 0
                last_size = size

            if stable_ticks >= 2:
                xlsx_path = candidate
                break

        time.sleep(0.5)

    if not xlsx_path:
        raise TimeoutError(
            f"No apareció/terminó el XLSX esperado. Prefijo: '{nameExcel}{fecha_consulta}' en {download_dir}"
        )

    # 2) Abrir Explorer en la ruta download_dir (seleccionando el XLSX) y tomar screenshot (OS)
    #    /select, asegura que Explorer abra la carpeta correcta y muestre el archivo descargado.
    folder_hint = (explorer_window_hint or download_dir.name).strip() if (explorer_window_hint or download_dir.name) else download_dir.name

    hwnds_before = _window_hwnds_by_title_contains(folder_hint, process_image_names={'explorer.exe'})

    try:
        subprocess.run(["explorer", "/select,", str(xlsx_path)], check=False)
    except Exception:
        # fallback: al menos abrir la carpeta
        try:
            os.startfile(str(download_dir))
        except Exception:
            subprocess.run(["explorer", str(download_dir)], check=False)

    time.sleep(explorer_wait)

    shot_folder = create_screenshot_download(
        step=step,
        label=label_folder,
        web_driver=web_driver,
        urlEvidences=str(evidence_dir),
        window_title_contains=folder_hint,
        pre_capture_wait=pre_capture_wait,
        process_image_names={'explorer.exe'},
    )

    # Cerrar Explorer después de evidenciar la carpeta de descargas
    try:
        hwnds_after = _window_hwnds_by_title_contains(folder_hint, process_image_names={'explorer.exe'})
        prefer = (hwnds_after - hwnds_before) or hwnds_after
        close_windows_by_title_contains(
            folder_hint,
            timeout=6.0,
            max_to_close=1,
            prefer_hwnds=set(prefer),
            process_image_names={'explorer.exe'},
        )
    except Exception:
        pass

    # 3) Abrir Excel + screenshot
    excel_pids_before = _list_excel_pids()

    os.startfile(str(xlsx_path))
    time.sleep(excel_wait)

    excel_pids_after = _list_excel_pids()
    spawned_pids = set(excel_pids_after) - set(excel_pids_before)

    hint = ((excel_window_hint or xlsx_path.stem).strip() or xlsx_path.stem)
    # Poner Excel al frente antes del screenshot (evita que quede detrás de otras ventanas)
    if not activate_window_by_title_contains(hint, timeout=10.0, process_image_names={'excel.exe'}):
        # fallback genérico
        activate_window_by_title_contains("excel", timeout=6.0, process_image_names={'excel.exe'})

    shot_excel = create_screenshot_download(
        step=step,
        label=label_excel,
        web_driver=web_driver,
        urlEvidences=str(evidence_dir),
        window_title_contains=hint,
        pre_capture_wait=pre_capture_wait,
        process_image_names={'excel.exe'},
    )

    # 4) Cerrar Excel sin guardar (robusto)
    closed = close_excel_opened(
        window_title_contains=hint,
        timeout=20,
        force_kill_excel=force_kill_excel,
        kill_only_if_no_excel_was_running=True,
        excel_pids_before=excel_pids_before,
        spawned_pids=spawned_pids,
    )

    return {
        "xlsx_path": str(xlsx_path),
        "screenshot_folder": shot_folder,
        "screenshot_excel": shot_excel,
        "download_dir": str(download_dir),
        "evidence_dir": str(evidence_dir),
        "excel_closed": bool(closed),
    }

def scroll_horizontal_to_end(driver, locator, highlight=True, usar_create_screenshot: bool = False, screenshot_step: Optional[str] = None, nombre_elemento: str = "Tabla"):
    """
    Espera a que la tabla sea interactuable, la centra, realiza scroll horizontal al final y toma evidencia.
    """
    # 1. Definimos el tiempo de espera (timeout) consistente con ui_interact
    wait = WebDriverWait(driver, 20)
    
    try:
        # 2. ESPERA CRÍTICA: Aseguramos que los spinners/overlays desaparezcan antes de buscar el elemento
        _wait_overlays(driver)
        
        # 3. ESPERA CRÍTICA: Esperamos a que la tabla sea visible e interactuable
        element = wait.until(EC.visibility_of_element_located((By.XPATH, locator)))
        
        # 4. Centrar la tabla en el viewport (Scroll Vertical)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5) 
        
        # 5. Highlight (Enmarcar de verde)
        if highlight:
            driver.execute_script("arguments[0].style.outline = '3px solid #28a745';", element)
        
        # 6. Acción de Scroll Horizontal mediante JS
        script = """
            var container = arguments[0].closest('.table-responsive') || arguments[0].parentNode;
            if (container) {
                container.scrollLeft = container.scrollWidth;
            }
        """
        driver.execute_script(script, element)
        
        # 7. Pausa breve para estabilidad visual antes de la captura
        time.sleep(0.8)
        
        # 8. CAPTURA DE EVIDENCIA: Usamos el fotógrafo global para asegurar que se guarde en la ruta correcta[cite: 1]
        # Esto es lo que faltaba para que detectara tus banderas globales y la carpeta del caso
        take_global_evidence(
            driver=driver, 
            default_step="scroll_horizontal", 
            nombre_elemento=nombre_elemento, 
            usar_create_screenshot=usar_create_screenshot, 
            screenshot_step=screenshot_step
        )
            
    except Exception as e:
        logging.error(f"Error crítico en scroll_horizontal_to_end para {locator}: {e}")
        