from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from ui.interfaces import ActionItem, IUI

from webui.job_manager import JobCancelledError, JobManager, Prompt


class WebUIAdapter(IUI):
    """
    Adapter para que el core (sin Tkinter) pueda funcionar contra una UI web.

    Suposición: el core corre en un worker thread y esta clase bloquea
    hasta que el frontend responda (vía JobManager.answer_prompt()).
    """

    def __init__(self, *, job_manager: JobManager, job_id: str) -> None:
        self.job_manager = job_manager
        self.job_id = job_id
        self._prompt_seq = 0

    def _safe_wait(self, prompt: Prompt) -> Any:
        try:
            return self.job_manager.create_prompt_and_wait(self.job_id, prompt=prompt)
        except JobCancelledError:
            # Cancel: el core debe interpretar esto (None/False) según contrato del IUI.
            raise

    def pick_project(self, projects: Sequence[str]) -> Optional[str]:
        if not projects:
            return None

        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="pick_project",
            title="Seleccionar Proyecto",
            message="Selecciona un proyecto:",
            options=[{"value": p, "label": p} for p in projects],
        )

        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return None

        if answer is None:
            return None
        return str(answer)

    def pick_script(self, scripts: Sequence[str], project_name: str) -> Optional[str]:
        if not scripts:
            return None

        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="pick_script",
            title="Seleccionar script de Interacciones",
            message=f"Selecciona un script ({project_name}):",
            options=[{"value": s, "label": s} for s in scripts],
        )

        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return None

        if answer is None:
            return None
        return str(answer)

    def pick_actions(self, actions: Sequence[ActionItem]) -> Sequence[str]:
        if not actions:
            return []

        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="pick_actions",
            title="Seleccionar acciones para conversión",
            message="Selecciona las acciones a convertir:",
            actions=[{"type": a["type"], "description": a["description"], "original_line": a["original_line"]} for a in actions],
        )

        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return []

        if not answer:
            return []
        # Contrato: lista de original_line (strings)
        return list(answer)

    def info(self, title: str, message: str) -> None:
        self.job_manager.add_event(self.job_id, "ui_info", {"title": title, "message": message})

    def warning(self, title: str, message: str) -> None:
        self.job_manager.add_event(self.job_id, "ui_warning", {"title": title, "message": message})

    def error(self, title: str, message: str) -> None:
        self.job_manager.add_event(self.job_id, "ui_error", {"title": title, "message": message})

    def yes_no(self, title: str, message: str) -> bool:
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="yes_no",
            title=title,
            message=message,
        )

        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return False

        return bool(answer)

    def yes_no_cancel(self, title: str, message: str) -> Optional[bool]:
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="yes_no_cancel",
            title=title,
            message=message,
        )

        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return None

        # Contrato: true|false|null
        if answer is None:
            return None
        return bool(answer)

    def _new_prompt_id(self) -> str:
        self._prompt_seq += 1
        return f"p_{self.job_id[:8]}_{self._prompt_seq}"

