from __future__ import annotations

from typing import Optional, Sequence

import tkinter as tk
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    VERTICAL,
    Y,
    BooleanVar,
    Button,
    Canvas,
    Checkbutton,
    Frame,
    Label,
    Listbox,
    Scrollbar,
    Toplevel,
    messagebox,
    ttk,
)

from ui.interfaces import ActionItem, IUI


class TkUI(IUI):
    """
    Implementación de IUI usando tkinter.
    Toda la lógica de ventanas (Toplevel/Listbox/Canvas/Checkbutton/messagebox) vive aquí.
    """

    def __init__(self, master: tk.Tk):
        self.master = master

    # ---------------------------
    # Helpers
    # ---------------------------
    def _center_window(self, window: tk.Toplevel) -> None:
        window.update_idletasks()
        try:
            x = self.master.winfo_x() + (self.master.winfo_width() - window.winfo_width()) // 2
            y = self.master.winfo_y() + (self.master.winfo_height() - window.winfo_height()) // 2
            window.geometry(f"+{x}+{y}")
        except Exception:
            # Best-effort: si no podemos centrar, no fallamos.
            pass

    def _pick_from_list(self, *, title: str, prompt: str, items: Sequence[str]) -> Optional[str]:
        if not items:
            return None

        selection_window = Toplevel(self.master)
        selection_window.title(title)
        selection_window.geometry("500x400")
        selection_window.transient(self.master)
        selection_window.grab_set()
        self._center_window(selection_window)

        frame = Frame(selection_window, padx=20, pady=20)
        frame.pack(fill=BOTH, expand=True)

        Label(frame, text=prompt, font=("Arial", 12)).pack(pady=(0, 10))

        listbox = Listbox(frame, font=("Arial", 11), height=15)
        scrollbar = Scrollbar(frame, orient=VERTICAL)

        for item in sorted(items):
            listbox.insert(END, item)

        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        listbox.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
        scrollbar.pack(side=RIGHT, fill=Y)

        selected: Optional[str] = None

        def on_select() -> None:
            nonlocal selected
            selection = listbox.curselection()
            if selection:
                selected = listbox.get(selection[0])
                selection_window.destroy()
            else:
                messagebox.showwarning("Selección requerida", "Por favor selecciona un elemento.", parent=selection_window)

        def on_cancel() -> None:
            selection_window.destroy()

        btn_frame = Frame(frame)
        btn_frame.pack(pady=(20, 0))

        Button(btn_frame, text="Seleccionar", command=on_select, width=12).pack(side=LEFT, padx=10)
        Button(btn_frame, text="Cancelar", command=on_cancel, width=12).pack(side=LEFT, padx=10)

        listbox.bind("<Double-Button-1>", lambda e: on_select())

        self.master.wait_window(selection_window)
        return selected

    # ---------------------------
    # IUI: Selecciones
    # ---------------------------
    def pick_project(self, projects: Sequence[str]) -> Optional[str]:
        return self._pick_from_list(
            title="Seleccionar Proyecto",
            prompt="Selecciona un proyecto:",
            items=projects,
        )

    def pick_script(self, scripts: Sequence[str], project_name: str) -> Optional[str]:
        return self._pick_from_list(
            title="Seleccionar script de Interacciones",
            prompt=f"Selecciona un script ({project_name}):",
            items=scripts,
        )

    def pick_actions(self, actions: Sequence[ActionItem]) -> Sequence[str]:
        if not actions:
            return []

        selected_actions: list[str] = []

        selection_window = Toplevel(self.master)
        selection_window.title("Seleccionar acciones para conversión")
        selection_window.geometry("900x550")
        selection_window.transient(self.master)
        selection_window.grab_set()
        self._center_window(selection_window)

        main_frame = Frame(selection_window, padx=10, pady=5)
        main_frame.pack(expand=True, fill="both")

        canvas = Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, pady=(0, 5))
        scrollbar.pack(side="right", fill="y")

        check_vars: list[BooleanVar] = []
        for action in actions:
            row = Frame(scrollable_frame)
            row.pack(fill="x", pady=1)

            var = BooleanVar(value=True)
            check_vars.append(var)

            Checkbutton(row, variable=var).pack(side="left", padx=5)
            Label(row, text=action["type"], width=15, anchor="w").pack(side="left", padx=5)
            Label(row, text=action["description"], width=80, anchor="w").pack(side="left", padx=5)

        button_frame = Frame(main_frame)
        button_frame.pack(pady=(3, 5))

        def include_all() -> None:
            for v in check_vars:
                v.set(True)

        def exclude_all() -> None:
            for v in check_vars:
                v.set(False)

        def on_continue() -> None:
            nonlocal selected_actions
            selected_actions = [
                action["original_line"]
                for action, var in zip(actions, check_vars)
                if var.get()
            ]
            selection_window.destroy()

        Button(button_frame, text="Incluir todas", command=include_all).pack(side="left", padx=10)
        Button(button_frame, text="Excluir todas", command=exclude_all).pack(side="left", padx=10)
        Button(button_frame, text="Continuar", command=on_continue).pack(side="right", padx=10)
        Button(button_frame, text="Cancelar", command=selection_window.destroy).pack(side="right", padx=10)

        self.master.wait_window(selection_window)
        return selected_actions

    # ---------------------------
    # IUI: Mensajes
    # ---------------------------
    def info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self.master)

    def warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=self.master)

    def error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self.master)

    # ---------------------------
    # IUI: Confirmaciones
    # ---------------------------
    def yes_no(self, title: str, message: str) -> bool:
        return bool(messagebox.askyesno(title, message, parent=self.master))

    def yes_no_cancel(self, title: str, message: str) -> Optional[bool]:
        return messagebox.askyesnocancel(title, message, parent=self.master)

