"""Diálogo nativo para elegir ejecutables (Windows / tkinter)."""
from __future__ import annotations

import sys
import threading
from typing import List, Optional, Tuple


def pick_executable_path(
    *,
    title: str = "Seleccionar ejecutable",
    filetypes: Optional[List[Tuple[str, str]]] = None,
) -> Optional[str]:
    if sys.platform != "win32":
        return None
    if filetypes is None:
        filetypes = [("Ejecutables", "*.exe"), ("Todos", "*.*")]

    result: dict = {"path": None, "error": None}

    def _run_dialog() -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            try:
                root.attributes("-topmost", True)
            except Exception:
                pass
            root.update()
            selected = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes,
            )
            if selected:
                result["path"] = str(selected)
            root.destroy()
        except Exception as exc:
            result["error"] = str(exc)

    thread = threading.Thread(target=_run_dialog, daemon=True)
    thread.start()
    thread.join(timeout=120.0)
    if result.get("error"):
        raise RuntimeError(result["error"])
    path = result.get("path")
    return str(path).strip() if path else None


def pick_directory_path(*, title: str = "Seleccionar carpeta") -> Optional[str]:
    if sys.platform != "win32":
        return None
    result: dict = {"path": None, "error": None}

    def _run_dialog() -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            try:
                root.attributes("-topmost", True)
            except Exception:
                pass
            root.update()
            selected = filedialog.askdirectory(title=title)
            if selected:
                result["path"] = str(selected)
            root.destroy()
        except Exception as exc:
            result["error"] = str(exc)

    thread = threading.Thread(target=_run_dialog, daemon=True)
    thread.start()
    thread.join(timeout=120.0)
    if result.get("error"):
        raise RuntimeError(result["error"])
    path = result.get("path")
    return str(path).strip() if path else None
