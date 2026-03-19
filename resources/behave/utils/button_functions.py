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
import threading

from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.keys import Keys

import pyautogui
import pygetwindow as gw
import ctypes
from ctypes import wintypes
import glob
import pandas as pd
from python_calamine import CalamineWorkbook

from utils.evidence import GetEvidence

BASE_DIR = os.getcwd()

# ============================================================
# ESTADO SEGURO PARA CONCURRENCIA (Reemplaza a las globales)
# ============================================================
class EvidenceState(threading.local):
    def __init__(self):
        self.take_evidence = False
        self.dir_name = ""
        self.func = None

_evidence_state = EvidenceState()

def set_global_evidence_config(take=False, dir_name="", func=None):
    """Permite actualizar el estado de las evidencias de forma segura por hilo."""
    _evidence_state.take_evidence = take
    _evidence_state.dir_name = dir_name
    _evidence_state.func = func

# ---> FOTÓGRAFO GLOBAL PARA TODAS LAS FUNCIONES <---
def take_global_evidence(driver, default_step: str, nombre_elemento: str, usar_create_screenshot: bool, screenshot_step: str = None):
    # Evaluamos si tomarla por parámetro explícito o por el estado del hilo actual
    should_take = usar_create_screenshot or getattr(_evidence_state, 'take_evidence', False)
    if not should_take:
        return None

    step = screenshot_step or default_step
    label = nombre_elemento or "Elemento"
    dir_name = getattr(_evidence_state, 'dir_name', "")
    
    fn = getattr(_evidence_state, 'func', None) or globals().get("create_screenshot")

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

# ============================================================
# CACHE & PID HELPERS (Sistema Operativo)
# ============================================================
_PID_IMAGE_CACHE: dict[int, str] = {}

def _get_pid_for_hwnd(hwnd: int) -> int:
    try:
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(wintypes.HWND(int(hwnd)), ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0

def _image_name_for_pid(pid: int) -> str:
    pid = int(pid or 0)
    if pid <= 0:
        return ""
    cached = _PID_IMAGE_CACHE.get(pid)
    if cached:
        return cached
    try:
        import psutil  # type: ignore
        name = (psutil.Process(pid).name() or "").strip()
        if name:
            _PID_IMAGE_CACHE[pid] = name
            return name
    except Exception:
        pass
    try:
        cp = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, check=False,
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


# ============================================================
# EVIDENCIAS: carpeta por caso en ejecución + screenshots
# ============================================================

_EVIDENCE_CONTEXT = {
    "case_name": None,
    "run_id": None,
    "dir_path": None,
}

def _sanitize_fs_name(name: str, max_len: int = 90) -> str:
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
    return _EVIDENCE_CONTEXT.get("dir_path")

def resolve_evidence_dir(
    dir_name: str = "",
    *,
    base_dir: str = BASE_DIR,
    parent_rel: str = os.path.join("outputs", "evidences"),
) -> str:
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

    return set_evidence_case("_unscoped", base_dir=base_dir, parent_rel=parent_rel, add_timestamp=True)

def create_screenshot(
    *,
    step: str,
    label: str,
    dir_name: str = "",
    web_driver: Optional[WebDriver] = None,
) -> Optional[str]:
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

        try:
            x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
            y = int(w.top) + 15
            if x >= 0 and y >= 0:
                pyautogui.click(x, y)
                time.sleep(0.12)
        except Exception:
            pass

        try:
            aw = gw.getActiveWindow()
            if aw and aw.title and key.lower() in aw.title.lower():
                return True
            if process_image_names:
                return True
        except Exception:
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

        try:
            x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
            y = int(w.top) + 15
            if x >= 0 and y >= 0:
                pyautogui.click(x, y)
                time.sleep(0.10)
        except Exception:
            pass

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
    try:
        cp = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq EXCEL.EXE", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, check=False,
        )
        out = (cp.stdout or "").strip()
        pids: set[int] = set()
        if not out:
            return pids
        for row in csv.reader(out.splitlines()):
            if not row:
                continue
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
    web_driver: Optional[WebDriver] = None,
    window_title_contains: Optional[str] = None,
    pre_capture_wait: float = 3.0,
    wait_activate: float = 0.35,
    process_image_names: Optional[set[str]] = None,
) -> Optional[str]:
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
                    time.sleep(wait_activate)
                    try:
                        x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
                        y = int(w.top) + 15
                        if x >= 0 and y >= 0:
                            pyautogui.click(x, y)
                            time.sleep(0.12)
                    except Exception:
                        pass

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

        try:
            x = int(w.left) + min(max(60, int(w.width) // 6), max(60, int(w.width) - 60))
            y = int(w.top) + 15
            if x >= 0 and y >= 0:
                pyautogui.click(x, y)
                time.sleep(0.12)
        except Exception:
            pass

        try:
            w.close()
        except Exception:
            pass

        time.sleep(0.8)
        if not _find_excel_wins():
            return True

        if _active_is_excel():
            try:
                aw = gw.getActiveWindow()
                aw_title = (aw.title or "").lower() if aw else ""
                is_dialog = ("microsoft excel" in aw_title) and (key not in aw_title)
            except Exception:
                is_dialog = False

            if is_dialog:
                try:
                    pyautogui.hotkey("alt", "n")
                    time.sleep(0.25)
                except Exception:
                    pass
                try:
                    pyautogui.hotkey("alt", "d")
                    time.sleep(0.25)
                except Exception:
                    pass
                try:
                    pyautogui.press("enter")
                    time.sleep(0.25)
                except Exception:
                    pass

        time.sleep(0.5)

    if spawned:
        _taskkill_pids(spawned)
        time.sleep(1.0)
        if not _find_excel_wins():
            return True

    if force_kill_excel or (kill_only_if_no_excel_was_running and not pids_before):
        try:
            subprocess.run(["taskkill", "/IM", "EXCEL.EXE", "/F"], capture_output=True, text=True, check=False)
            time.sleep(1.0)
            return True
        except Exception as ex:
            logging.warning(f"taskkill EXCEL.EXE falló: {ex}")

    logging.warning("No se logró cerrar Excel de forma segura; considera force_kill_excel=True.")
    return False

# ============================================================
# Helpers GENERALES
# ============================================================

def _screenshot(driver: WebDriver, prefix: str) -> Optional[str]:
    try:
        os.makedirs("screens", exist_ok=True)
        path = os.path.join("screens", f"{prefix}_{uuid.uuid4().hex}.png")
        driver.save_screenshot(path)
        return path
    except Exception:
        return None

def _wait_overlays(driver: WebDriver, timeout_overlays: float = 15.0) -> None:
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
            logging.warning(f"El overlay {sel} tardó más de {timeout_overlays}s en desaparecer.")
            
    time.sleep(0.5)

def _switch_into_iframe_if_needed(driver: WebDriver, wait: WebDriverWait, iframe_xpath: Optional[str]) -> None:
    if iframe_xpath:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframe_xpath)))

def _topmost_ok(driver: WebDriver, el) -> bool:
    return driver.execute_script("""
        const el=arguments[0], r=el.getBoundingClientRect();
        const x=Math.floor(r.left + r.width/2), y=Math.floor(r.top + r.height/2);
        const t=document.elementFromPoint(x,y);
        return el===t || (t && (el.contains(t)||t.contains(el)));
    """, el)

def _restore_outline(driver: WebDriver, el, prev: Optional[str]) -> None:
    if el is None:
        return
    try:
        driver.execute_script("arguments[0].style.outline=arguments[1];", el, prev)
    except Exception:
        pass

def ui_cleanup_state(driver: WebDriver, timeout: int = 3) -> None:
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
# Helpers STALE-SAFE
# ============================================================

def _refind(wait: WebDriverWait, xpath: str, visible: bool):
    cond = EC.visibility_of_element_located if visible else EC.presence_of_element_located
    return wait.until(cond((By.XPATH, xpath)))

def _do_with_refetch(driver: WebDriver, wait: WebDriverWait, xpath: str, visible: bool, func, max_retries: int = 3):
    el = _refind(wait, xpath, visible=visible)
    for _ in range(max_retries):
        try:
            return func(el)
        except StaleElementReferenceException:
            el = _refind(wait, xpath, visible=visible)
    return func(el)

def _center_and_highlight_stalesafe(
    driver: WebDriver,
    wait: WebDriverWait,
    xpath: str,
    outline_css: str = "4px solid #00FF00",
    pause: float = 0.1,
    visible: bool = True
):
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


# ============================================================
# FUNCIONES DE UI PRINCIPALES
# ============================================================

def ui_navigate(
    driver: WebDriver,
    url: str,
    nombre_pagina: str = "Pagina_Web",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
):
    driver.get(url)
    try:
        _wait_overlays(driver)
    except Exception:
        pass
    take_global_evidence(driver, "goto_url", nombre_pagina, usar_create_screenshot, screenshot_step)

def ui_clear_downloads():
    download_dir = os.path.join(os.getcwd(), 'outputs', 'downloads')
    if os.path.exists(download_dir):
        archivos = glob.glob(os.path.join(download_dir, "*"))
        for archivo in archivos:
            try:
                os.remove(archivo)
            except Exception:
                pass
    else:
        os.makedirs(download_dir, exist_ok=True)

def ui_validate_download(
    extension: str = (".csv",),
    timeout: int = 30,
    nombre_elemento: str = "Archivo_Descargado",
    usar_create_screenshot: bool = False,
    screenshot_step: str = None
) -> bool:
    download_dir = os.path.join(os.getcwd(), 'outputs', 'downloads')
    os.makedirs(download_dir, exist_ok=True)
    
    if isinstance(extension, str):
        extensiones = [extension]
    else:
        extensiones = extension
        
    patrones = [f"*{ext}" if ext.startswith(".") else f"*.{ext}" for ext in extensiones]
    
    start_time = time.time()
    archivo_descargado = None
    
    while time.time() - start_time < timeout:
        archivos_encontrados = []
        for patron in patrones:
            archivos_encontrados.extend(glob.glob(os.path.join(download_dir, patron)))
            
        if archivos_encontrados:
            archivo_descargado = max(archivos_encontrados, key=os.path.getctime)
            if os.path.getsize(archivo_descargado) > 0:
                break
        time.sleep(1)
        
    if archivo_descargado:
        tiempo_total = time.time() - start_time
        peso_bytes = os.path.getsize(archivo_descargado)
        
        dir_evidencia = getattr(_evidence_state, 'dir_name', "")
        
        if usar_create_screenshot and dir_evidencia:
            GetEvidence.create_download_receipt(
                step=screenshot_step, 
                label=nombre_elemento, 
                dir_name=dir_evidencia, 
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
    try:
        time.sleep(2.0)
        contenido_texto = ""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as archivo:
            contenido_texto = archivo.read()
            
        if not contenido_texto or contenido_texto.strip() == "":
            raise AssertionError(f"El archivo {os.path.basename(file_path)} se descargó, pero está VACÍO.")
            
        if textos_esperados:
            for texto in textos_esperados:
                if texto not in contenido_texto:
                    raise AssertionError(f"No se encontró el texto esperado '{texto}' en el archivo .txt")
                    
        dir_evidencia = getattr(_evidence_state, 'dir_name', "")
        if usar_create_screenshot and dir_evidencia:
            lineas = contenido_texto.split('\n')
            texto_preview = '\n'.join(lineas[:20])
            
            if len(lineas) > 20:
                texto_preview += "\n... [MÁS DATOS OCULTOS PARA LA VISTA PREVIA] ..."
                
            GetEvidence.create_data_preview_receipt(
                step=screenshot_step,
                label=nombre_elemento,
                dir_name=dir_evidencia,
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
    try:
        time.sleep(2.0)
        df_final = pd.DataFrame()
        hoja_con_datos = ""
        
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
            df = df.dropna(how='all').dropna(axis=1, how='all')
            if not df.empty:
                df_final = df
        else:
            engine_to_use = 'calamine' 
            hojas = pd.read_excel(file_path, engine=engine_to_use, sheet_name=None)
            
            for nombre_hoja, df_hoja in hojas.items():
                df_limpio = df_hoja.dropna(how='all').dropna(axis=1, how='all')
                if not df_limpio.empty and len(df_limpio.columns) > 0:
                    df_final = df_limpio
                    hoja_con_datos = nombre_hoja
                    break
                    
        if df_final is None or len(df_final.columns) == 0:
            raise AssertionError(f"El archivo {os.path.basename(file_path)} está totalmente VACÍO.")
            
        if columnas_esperadas:
            for col in columnas_esperadas:
                if col not in df_final.columns:
                    raise AssertionError(
                        f"Falta la columna '{col}'. \nHoja leída: '{hoja_con_datos}' \nColumnas encontradas: {df_final.columns.tolist()}"
                    )
        
        dir_evidencia = getattr(_evidence_state, 'dir_name', "")
        if usar_create_screenshot and dir_evidencia:
            logging.info(f"\n[RADAR] Columnas detectadas: {df_final.columns.tolist()}\n")
            with pd.option_context('display.max_columns', None, 'display.width', 2000, 'display.max_colwidth', None):
                tabla_texto = df_final.head(15).to_string(index=False)
            
            titulo_recibo = nombre_elemento if not hoja_con_datos else f"{nombre_elemento}_({hoja_con_datos})"
            
            GetEvidence.create_data_preview_receipt(
                step=screenshot_step,
                label=titulo_recibo,
                dir_name=dir_evidencia,
                file_path=file_path,
                data_string=tabla_texto
            )
            
        return True
    except Exception as e:
        raise AssertionError(f"Error crítico al validar el contenido del archivo: {str(e)}")

ActionType = Literal["click", "insertTxt", "getValue", "highlight", "assertNotVisible"]

def ui_interact(
    driver: WebDriver,
    xPath_elemento: str,
    accion: ActionType,
    nombre_elemento: str = "Elemento",
    valor: Optional[str] = None,
    iframe_xpath: Optional[str] = None,
    timeout: int = 15,
    borde_css: str = "4px solid #00FF00",
    usar_click_js_si_falla: bool = True,
    usar_js_para_input: bool = True,
    restaurar_borde: bool = True,
    cleanup_al_final: bool = True,
    usar_create_screenshot: bool = False,
    screenshot_step: Optional[str] = None,
    screenshot_dir_name: str = "",
    create_screenshot_fn=None,
):
    wait = WebDriverWait(driver, timeout)
    el = None
    prev_outline = None

    try:
        _switch_into_iframe_if_needed(driver, wait, iframe_xpath)

        if accion == "assertNotVisible":
            _wait_overlays(driver)
            elementos = driver.find_elements(By.XPATH, xPath_elemento)
            visibles = [e for e in elementos if e.is_displayed()]
            
            if visibles:
                el_error = visibles[0]
                try:
                    driver.execute_script("arguments[0].style.outline='6px solid #FF0000';", el_error)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el_error)
                except Exception:
                    pass
                msg = f"FALLO DEL TEST: Apareció el mensaje/pop-up inesperado '{nombre_elemento}'. XPATH: {xPath_elemento}"
                logging.error(msg)
                raise AssertionError(msg)
            else:
                take_global_evidence(driver, accion, nombre_elemento, usar_create_screenshot, screenshot_step)
                return True

        if accion in ["click", "insertTxt"]:
            wait.until(EC.element_to_be_clickable((By.XPATH, xPath_elemento)))
        else:
            wait.until(EC.visibility_of_element_located((By.XPATH, xPath_elemento)))

        _wait_overlays(driver)

        el, prev_outline = _center_and_highlight_stalesafe(
            driver, wait, xPath_elemento, outline_css=borde_css, pause=0.1, visible=True
        )

        if accion == "click":
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
            take_global_evidence(driver, accion, nombre_elemento, usar_create_screenshot, screenshot_step)
            return el

        else:
            raise AssertionError(f"Acción no soportada: {accion}")

    except TimeoutException as e:
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
        raise AssertionError(f'No fue posible abrir "{nombre_menu}" o encontrar la opción "{nombre_opcion}" en {timeout}s.') from e
    except Exception as e:
        snap = _screenshot(driver, "menu_action_error")
        msg = (f'Fallo al seleccionar "{nombre_opcion}" en "{nombre_menu}". Detalles: {e}\nScreenshot: {snap}')
        logging.error(msg)
        raise AssertionError(msg)
    finally:
        if restaurar_borde:
            try:
                _restore_outline(driver, el_menu, prev_outline_menu)
                _restore_outline(driver, el_item, prev_outline_item)
            except Exception:
                pass

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
    wait = WebDriverWait(driver, timeout)

    if xpath:
        _switch_into_iframe_if_needed(driver, wait, iframe_xpath)
        try:
            _wait_overlays(driver) 
        except Exception:
            pass

        if wait_for_xpath:
            wait.until(EC.presence_of_element_located((By.XPATH, wait_for_xpath)))

        el = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        
        try:
            driver.execute_script(f"arguments[0].scrollIntoView({{behavior: 'instant', block: '{scroll_block}', inline: 'center'}});", el) 
            time.sleep(0.15) 
        except Exception:
            pass

        try:
            driver.execute_script("arguments[0].style.outline='2px solid #00A000';", el)
        except Exception:
            pass

        ActionChains(driver).move_to_element_with_offset(el, offset[0], offset[1]).perform()
        
        take_global_evidence(driver, "hover", nombre_elemento, usar_create_screenshot, screenshot_step)

        try:
            driver.execute_script("arguments[0].style.outline='';", el)
        except Exception:
            pass
        
        return
    
    if x_abs is not None and y_abs is not None:
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
    wait = WebDriverWait(driver, timeout)

    if anchor_to_body:
        body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        vw = driver.execute_script("return Math.max(document.documentElement.clientWidth, window.innerWidth || 0);")
        vh = driver.execute_script("return Math.max(document.documentElement.clientHeight, window.innerHeight || 0);")
        cx = max(2, int(vw // 2))
        cy = max(2, int(vh // 2))
        ActionChains(driver).move_to_element_with_offset(body, cx, cy).perform()

    if dx == 0 and dy == 0:
        return

    vw = driver.execute_script("return Math.max(document.documentElement.clientWidth, window.innerWidth || 0);")
    vh = driver.execute_script("return Math.max(document.documentElement.clientHeight, window.innerHeight || 0);")
    max_dx = int(vw // 2) - 3
    max_dy = int(vh // 2) - 3
    dx = int(max(-max_dx, min(max_dx, dx)))
    dy = int(max(-max_dy, min(max_dy, dy)))

    ActionChains(driver).move_by_offset(dx, dy).perform()

def ui_mouse_move_vertical_pixels(driver: WebDriver, pixels: int, *, direction: str = "down", anchor_to_body: bool = True, timeout: int = 10) -> None:
    direction_norm = (direction or "").strip().lower()
    if direction_norm in ("down", "abajo", "bottom"):
        dy = abs(int(pixels))
    elif direction_norm in ("up", "arriba", "top"):
        dy = -abs(int(pixels))
    else:
        raise AssertionError("direction debe ser 'down/abajo' o 'up/arriba'.")

    ui_mouse_move_pixels(driver, dx=0, dy=dy, anchor_to_body=anchor_to_body, timeout=timeout)

def ui_scroll_vertical_pixels(driver: WebDriver, pixels: int) -> None:
    driver.execute_script("window.scrollBy(0, arguments[0]);", int(pixels))

def ui_click_screen(driver: WebDriver, *, x_abs: Optional[int] = None, y_abs: Optional[int] = None, click_body_fallback: bool = True) -> None:
    if x_abs is not None and y_abs is not None:
        ActionChains(driver).move_by_offset(-10_000, -10_000).perform()
        ActionChains(driver).move_by_offset(x_abs, y_abs).click().perform()
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
    try:
        el = driver.find_element("xpath", xPath_elemento)
        val = el.get_attribute("value")
        if not val:
            val = el.get_attribute("textContent") or el.get_attribute("innerText") or ""
        return val.strip()
    except Exception as e:
        raise AssertionError(f'No se pudo obtener valor de "{nombre_elemento}". Detalle: {e}')

def select_dropdown_option(driver, dropdown_label_text, option_text, timeout=10):
    wait = WebDriverWait(driver, timeout)
    dropdown_label = wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[@data-testid='select-label' and text()='{dropdown_label_text}']")))
    dropdown_label.click()
    option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[@class='select-items--option'][contains(.,'{option_text}')]")))
    option.click()   

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
        raise ValueError(f"No pude interpretar date_str='{s}'. Proporciona date_format.")

    dt = _parse_date(date_str)
    iso_value = dt.strftime("%Y-%m-%d")
    day_num = str(dt.day)

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
            f'Input XPATH: {input_xpath}.'
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
    wait = WebDriverWait(driver, timeout)
    el = wait.until(EC.presence_of_element_located(input_locator))

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

    used_fp = driver.execute_script(
        """
        const el = arguments[0];
        const dateStr = arguments[1];
        const fmt = arguments[2];
        const fp = el._flatpickr;

        if (fp && typeof fp.setDate === 'function') {
            fp.setDate(dateStr, true, fmt);
            return true;
        }
        return false;
        """,
        el, date_str, flatpickr_format
    )

    if used_fp:
        return (el.get_attribute("value") or "").strip()

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

def _mark_element(driver, el):
    driver.execute_script(
        "arguments[0].style.outline='2px solid #00A000';"
        "arguments[0].style.outlineOffset='2px';",
        el
    )

def _mark_by_xpath(driver, xpath: str, timeout: int = 3):
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
    wait = WebDriverWait(driver, timeout)

    try:
        if scroll_to_top:
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
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
                _mark_by_xpath(driver, root_xpath, timeout=2)

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

        subsubmenu = wait.until(EC.element_to_be_clickable((By.XPATH, subsubmenu_click_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", subsubmenu)

        if mark_subsubmenu:
            try:
                _mark_element(driver, subsubmenu)
            except StaleElementReferenceException:
                subsubmenu = _mark_by_xpath(driver, subsubmenu_click_xpath, timeout=2)
                take_global_evidence(driver, "click_menu", nombre_elemento, usar_create_screenshot, screenshot_step)
        
        take_global_evidence(driver, "select_menu", nombre_elemento, usar_create_screenshot, screenshot_step)        

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
    wait = WebDriverWait(driver, timeout)

    try:
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

        sub = wait.until(EC.element_to_be_clickable((By.XPATH, submenu_click_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", sub)
        if mark_submenu:
            try:
                _mark_element(driver, sub)
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
    wait = WebDriverWait(driver, timeout)
    el = None
    prev_outline = None

    try:
        el = wait.until(EC.element_to_be_clickable((By.XPATH, xPath_elemento)))
        _wait_overlays(driver) 
        
        el, prev_outline = _center_and_highlight_stalesafe(
            driver, wait, xPath_elemento, outline_css=borde_css, pause=0.4, visible=True
        )
        
        select_obj = Select(el)
        
        if tipo_seleccion == "value":
            select_obj.select_by_value(str(valor_seleccion))
        elif tipo_seleccion == "text":
            select_obj.select_by_visible_text(str(valor_seleccion))
        elif tipo_seleccion == "index":
            select_obj.select_by_index(int(valor_seleccion))
        else:
            raise ValueError(f"El tipo_seleccion '{tipo_seleccion}' no es válido. Usa 'value', 'text' o 'index'.")
            
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """, el)

        take_global_evidence(driver, "select_dropdown", nombre_elemento, usar_create_screenshot, screenshot_step)
        return el

    except TimeoutException as e:
        raise AssertionError(f'El dropdown "{nombre_elemento}" no estuvo disponible tras {timeout}s. XPATH: {xPath_elemento}') from e
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
    fecha_consulta: str,                           
    nameExcel: str,                                
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
    download_dir = Path(download_dir).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    nameExcel = (nameExcel or "").rstrip()
    target_prefix = f"{nameExcel}{fecha_consulta}".lower()
    pattern = re.compile(rf"^{re.escape(nameExcel)}{re.escape(fecha_consulta)}.*\.xlsx$", re.IGNORECASE)

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
        raise TimeoutError(f"No apareció/terminó el XLSX esperado. Prefijo: '{nameExcel}{fecha_consulta}' en {download_dir}")

    folder_hint = (explorer_window_hint or download_dir.name).strip() if (explorer_window_hint or download_dir.name) else download_dir.name
    hwnds_before = _window_hwnds_by_title_contains(folder_hint, process_image_names={'explorer.exe'})

    try:
        subprocess.run(["explorer", "/select,", str(xlsx_path)], check=False)
    except Exception:
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

    excel_pids_before = _list_excel_pids()
    os.startfile(str(xlsx_path))
    time.sleep(excel_wait)

    excel_pids_after = _list_excel_pids()
    spawned_pids = set(excel_pids_after) - set(excel_pids_before)

    hint = ((excel_window_hint or xlsx_path.stem).strip() or xlsx_path.stem)
    if not activate_window_by_title_contains(hint, timeout=10.0, process_image_names={'excel.exe'}):
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
    wait = WebDriverWait(driver, 20)
    
    try:
        _wait_overlays(driver)
        element = wait.until(EC.visibility_of_element_located((By.XPATH, locator)))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5) 
        
        if highlight:
            driver.execute_script("arguments[0].style.outline = '3px solid #28a745';", element)
        
        script = """
            var container = arguments[0].closest('.table-responsive') || arguments[0].parentNode;
            if (container) {
                container.scrollLeft = container.scrollWidth;
            }
        """
        driver.execute_script(script, element)
        time.sleep(0.8)
        
        take_global_evidence(
            driver=driver, 
            default_step="scroll_horizontal", 
            nombre_elemento=nombre_elemento, 
            usar_create_screenshot=usar_create_screenshot, 
            screenshot_step=screenshot_step
        )
            
    except Exception as e:
        logging.error(f"Error crítico en scroll_horizontal_to_end para {locator}: {e}")
