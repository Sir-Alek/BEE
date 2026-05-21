from __future__ import annotations

import re
from typing import Any, Optional, Sequence

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
    Entry,
    Frame,
    Label,
    Listbox,
    Scrollbar,
    StringVar,
    Text,
    Toplevel,
    messagebox,
    ttk,
)

from ui.interfaces import ActionItem, BDDUserCancelled, IUI


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

    def pick_conversion_mode(self) -> str:
        result: dict = {"mode": "single"}

        win = Toplevel(self.master)
        win.title("Modo de conversión")
        win.geometry("480x220")
        win.resizable(False, False)
        win.transient(self.master)
        win.grab_set()
        self._center_window(win)

        Label(
            win,
            text="¿Cómo deseas convertir las grabaciones?",
            font=("Arial", 12, "bold"),
        ).pack(pady=(22, 8))

        btn_frame = Frame(win)
        btn_frame.pack(pady=10)

        def on_single() -> None:
            result["mode"] = "single"
            win.destroy()

        def on_grouped() -> None:
            result["mode"] = "grouped"
            win.destroy()

        Button(btn_frame, text="Una grabación", command=on_single, width=20, height=2).pack(
            side=LEFT, padx=14
        )
        Button(btn_frame, text="Agrupar grabaciones", command=on_grouped, width=22, height=2).pack(
            side=LEFT, padx=14
        )

        Label(
            win,
            text="Agrupando puedes combinar varios flujos en un mismo Feature\ncon múltiples Scenarios y Background compartido.",
            font=("Arial", 9),
            foreground="gray",
            justify="center",
        ).pack(pady=(8, 0))

        self.master.wait_window(win)
        return result["mode"]

    def pick_scripts_multi(self, scripts: Sequence[str], project_name: str) -> Sequence[str]:
        selected_scripts: list[str] = []

        win = Toplevel(self.master)
        win.title(f"Seleccionar grabaciones para agrupar — {project_name}")
        win.geometry("620x520")
        win.transient(self.master)
        win.grab_set()
        self._center_window(win)

        top = Frame(win, padx=12, pady=8)
        top.pack(fill="x")
        Label(top, text="Selecciona las grabaciones a incluir en el Feature:", font=("Arial", 11)).pack(
            anchor="w"
        )
        Label(top, text="(selecciona al menos 2)", font=("Arial", 9), foreground="gray").pack(
            anchor="w"
        )

        main_frame = Frame(win, padx=12)
        main_frame.pack(expand=True, fill="both")

        canvas = Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, pady=5)
        scrollbar.pack(side="right", fill="y")

        check_vars: list[tuple[BooleanVar, str]] = []
        for script in sorted(scripts):
            row = Frame(scrollable_frame)
            row.pack(fill="x", pady=3, padx=8)
            var = BooleanVar(value=False)
            check_vars.append((var, script))
            Checkbutton(row, variable=var).pack(side=LEFT, padx=4)
            Label(row, text=script, font=("Consolas", 10), anchor="w").pack(side=LEFT)

        def on_select_all() -> None:
            for v, _ in check_vars:
                v.set(True)

        def on_continue() -> None:
            nonlocal selected_scripts
            chosen = [s for v, s in check_vars if v.get()]
            if len(chosen) < 2:
                messagebox.showwarning(
                    "Selección insuficiente",
                    "Selecciona al menos 2 grabaciones para agrupar.",
                    parent=win,
                )
                return
            selected_scripts = chosen
            win.destroy()

        btn_frame = Frame(win, pady=10)
        btn_frame.pack()
        Button(btn_frame, text="Seleccionar todas", command=on_select_all, width=16).pack(
            side=LEFT, padx=8
        )
        Button(btn_frame, text="Continuar", command=on_continue, width=12).pack(side=LEFT, padx=8)
        Button(btn_frame, text="Cancelar", command=win.destroy, width=12).pack(side=LEFT, padx=8)

        self.master.wait_window(win)
        return selected_scripts

    def pick_feature_name(self, suggested: str) -> Optional[str]:
        result: dict = {"name": None}

        win = Toplevel(self.master)
        win.title("Nombre del Feature agrupado")
        win.geometry("460x195")
        win.resizable(False, False)
        win.transient(self.master)
        win.grab_set()
        self._center_window(win)

        frame = Frame(win, padx=22, pady=18)
        frame.pack(fill=BOTH, expand=True)

        Label(frame, text="Nombre del Feature agrupado:", font=("Arial", 11)).pack(anchor="w")
        Label(
            frame,
            text="Será el nombre del archivo .feature y del steps generado.",
            font=("Arial", 9),
            foreground="gray",
        ).pack(anchor="w", pady=(2, 10))

        name_var = StringVar(value=suggested)
        entry = Entry(frame, textvariable=name_var, font=("Arial", 12), width=42)
        entry.pack(fill="x", pady=(0, 16))
        entry.select_range(0, "end")
        entry.focus_set()

        def on_confirm() -> None:
            val = name_var.get().strip()
            if not val:
                messagebox.showwarning("Nombre requerido", "El nombre no puede estar vacío.", parent=win)
                return
            result["name"] = re.sub(r"[^a-zA-Z0-9_\-]", "_", val).strip("_") or "feature_agrupado"
            win.destroy()

        btn_frame = Frame(frame)
        btn_frame.pack()
        Button(btn_frame, text="Confirmar", command=on_confirm, width=12).pack(side=LEFT, padx=10)
        Button(btn_frame, text="Cancelar", command=win.destroy, width=12).pack(side=LEFT, padx=10)
        entry.bind("<Return>", lambda _: on_confirm())

        self.master.wait_window(win)
        return result["name"]

    def grouped_feature_review(
        self,
        *,
        feature_text: str,
        script_names: Sequence[str],
        background_count: int,
    ) -> dict:
        result: dict = {}

        win = Toplevel(self.master)
        win.title("Vista previa — Feature agrupado")
        win.geometry("920x680")
        win.transient(self.master)
        win.grab_set()
        self._center_window(win)

        info_parts = [f"Grabaciones: {', '.join(script_names)}"]
        if background_count > 0:
            info_parts.append(f"Background: {background_count} paso(s) compartido(s)")
        Label(win, text="  |  ".join(info_parts), font=("Arial", 10), foreground="gray").pack(
            anchor="w", padx=12, pady=(12, 2)
        )
        Label(win, text="Revisa y edita el Feature agrupado antes de generarlo:", font=("Arial", 11)).pack(
            anchor="w", padx=12, pady=(0, 4)
        )

        body = Text(win, height=24, wrap="word", font=("Consolas", 10))
        body.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        body.insert("1.0", feature_text)

        def on_accept() -> None:
            result["action"] = "accept"
            result["feature_text"] = body.get("1.0", "end").strip()
            win.destroy()

        def on_cancel() -> None:
            win.destroy()

        bf = Frame(win)
        bf.pack(pady=(0, 14))
        Button(bf, text="Aceptar y generar", command=on_accept, width=18).pack(side=LEFT, padx=10)
        Button(bf, text="Cancelar", command=on_cancel, width=14).pack(side=LEFT, padx=10)

        self.master.wait_window(win)
        if not result:
            raise BDDUserCancelled()
        return result

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
    def info(self, title: str, message: str, **kwargs: Any) -> None:
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

    def bdd_preview_review(
        self,
        *,
        feature_text: str,
        attempt: int,
        max_attempts: int,
        script_excerpt: str,
        can_manual: bool,
    ) -> dict:
        win = Toplevel(self.master)
        win.title("Vista previa del escenario BDD (IA)")
        win.geometry("900x620")
        win.transient(self.master)
        win.grab_set()
        self._center_window(win)

        header = (
            f"Intento {attempt} de {max_attempts}. "
            + ("Edita el escenario y confirma." if can_manual else "Revisa el texto generado.")
        )
        Label(win, text=header, font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=(12, 6))

        if script_excerpt.strip():
            lf = Frame(win)
            lf.pack(fill="x", padx=12, pady=(0, 6))
            Label(lf, text="Extracto del script (referencia):", font=("Arial", 9)).pack(anchor="w")
            st_ref = Text(lf, height=6, wrap="word", font=("Consolas", 9))
            st_ref.pack(fill="x")
            st_ref.insert("1.0", script_excerpt)
            st_ref.configure(state="disabled")

        Label(win, text="Feature (.feature):", font=("Arial", 9)).pack(anchor="w", padx=12)
        body = Text(win, height=18, wrap="word", font=("Consolas", 10))
        body.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        body.insert("1.0", feature_text)
        if not can_manual:
            body.configure(state="disabled")

        result: dict = {}

        def on_accept() -> None:
            txt = body.get("1.0", "end").strip()
            result.clear()
            result["action"] = "accept"
            result["feature_text"] = txt
            result["edited"] = bool(can_manual or (txt != feature_text.strip()))
            win.destroy()

        def on_reject() -> None:
            result.clear()
            result["action"] = "reject"
            win.destroy()

        def on_cancel() -> None:
            win.destroy()

        bf = Frame(win)
        bf.pack(pady=(0, 12))
        if can_manual:

            def on_heuristic() -> None:
                result.clear()
                result["action"] = "use_heuristic"
                win.destroy()

            Button(bf, text="Aceptar escenario", command=on_accept, width=16).pack(side="left", padx=8)
            Button(bf, text="Usar generación heurística", command=on_heuristic, width=22).pack(side="left", padx=8)
            Button(bf, text="Cancelar conversión", command=on_cancel, width=18).pack(side="left", padx=8)
        else:
            Button(bf, text="Aceptar", command=on_accept, width=14).pack(side="left", padx=8)
            Button(bf, text="Rechazar (regenerar)", command=on_reject, width=18).pack(side="left", padx=8)
            Button(bf, text="Cancelar", command=on_cancel, width=12).pack(side="left", padx=8)

        self.master.wait_window(win)

        if not result:
            raise BDDUserCancelled()

        return result

