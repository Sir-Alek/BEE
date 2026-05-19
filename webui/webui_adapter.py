from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from ui.interfaces import ActionItem, BDDUserCancelled, IUI

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

    def pick_conversion_mode(self) -> str:
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="pick_conversion_mode",
            title="Modo de conversión",
            message="¿Cómo deseas convertir las grabaciones?",
            options=[
                {"value": "single", "label": "Una grabación"},
                {"value": "grouped", "label": "Agrupar grabaciones"},
            ],
        )
        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return "single"
        if answer is None:
            return "single"
        mode = str(answer).strip().lower()
        return mode if mode in ("single", "grouped") else "single"

    def pick_scripts_multi(self, scripts: Sequence[str], project_name: str) -> Sequence[str]:
        if not scripts:
            return []

        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="pick_scripts_multi",
            title="Seleccionar grabaciones para agrupar",
            message=f"Selecciona al menos 2 grabaciones ({project_name}):",
            actions=[
                {"type": "Grabación", "description": s, "original_line": s}
                for s in scripts
            ],
        )
        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return []

        if not answer:
            return []
        chosen = list(answer)
        return chosen if len(chosen) >= 2 else []

    def pick_feature_name(self, suggested: str) -> Optional[str]:
        import re

        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="input_text",
            title="Nombre del Feature agrupado",
            message="Nombre del archivo .feature y del steps generado:",
            payload={"suggested": suggested, "purpose": "feature_name"},
        )
        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            return None

        if answer is None:
            return None
        val = str(answer).strip()
        if not val:
            return None
        return re.sub(r"[^a-zA-Z0-9_\-]", "_", val).strip("_") or "feature_agrupado"

    def grouped_feature_review(
        self,
        *,
        feature_text: str,
        script_names: Sequence[str],
        background_count: int,
    ) -> Dict[str, Any]:
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="grouped_feature_review",
            title="Vista previa — Feature agrupado",
            message="Revisa y edita el Feature agrupado antes de generarlo:",
            payload={
                "feature_text": feature_text,
                "script_names": list(script_names),
                "background_count": background_count,
            },
        )
        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            raise BDDUserCancelled()

        if answer is None or not isinstance(answer, dict):
            raise BDDUserCancelled()
        return answer

    def info(self, title: str, message: str) -> None:
        # Paridad con Tk: messagebox bloqueante hasta Aceptar.
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="message_ack",
            title=title,
            message=message,
            severity="info",
        )
        try:
            self._safe_wait(prompt)
        except JobCancelledError:
            return

    def warning(self, title: str, message: str) -> None:
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="message_ack",
            title=title,
            message=message,
            severity="warning",
        )
        try:
            self._safe_wait(prompt)
        except JobCancelledError:
            return

    def error(self, title: str, message: str) -> None:
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="message_ack",
            title=title,
            message=message,
            severity="error",
        )
        try:
            self._safe_wait(prompt)
        except JobCancelledError:
            return

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

    def bdd_preview_review(
        self,
        *,
        feature_text: str,
        attempt: int,
        max_attempts: int,
        script_excerpt: str,
        can_manual: bool,
    ) -> Dict[str, Any]:
        prompt_id = self._new_prompt_id()
        prompt = Prompt(
            prompt_id=prompt_id,
            type="bdd_preview",
            title="Vista previa del escenario BDD (IA)",
            message="Revisa el escenario generado. Puedes aceptarlo, pedir otra versión o editarlo manualmente.",
            payload={
                "feature_text": feature_text,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "script_excerpt": script_excerpt,
                "can_manual": can_manual,
            },
        )
        try:
            answer = self._safe_wait(prompt)
        except JobCancelledError:
            raise BDDUserCancelled()

        if answer is None or not isinstance(answer, dict):
            raise BDDUserCancelled()
        return answer

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

