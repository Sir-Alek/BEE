from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, TypedDict


class ActionItem(TypedDict):
    type: str
    description: str
    original_line: str


@dataclass(frozen=True)
class ExistingFilesPrompt:
    title: str
    message: str


class BDDUserCancelled(Exception):
    """Usuario canceló la revisión del escenario BDD (vista previa con IA)."""


class IUI(Protocol):
    """
    Abstracción de UI para desacoplar tkinter del core.
    Implementaciones típicas:
      - TkUI (GUI actual)
      - CliUI / HeadlessUI (futuro)
      - WebUI (FastAPI + frontend)
    """

    # ----- Selecciones -----
    def pick_project(self, projects: Sequence[str]) -> Optional[str]:
        """Devuelve el nombre del proyecto seleccionado o None si cancela."""

    def pick_script(self, scripts: Sequence[str], project_name: str) -> Optional[str]:
        """Devuelve el nombre del script seleccionado o None si cancela."""

    def pick_actions(self, actions: Sequence[ActionItem]) -> Sequence[str]:
        """Devuelve una lista de `original_line` seleccionadas (puede ser vacía)."""

    def pick_conversion_mode(self) -> str:
        """
        Pregunta al usuario si desea convertir una sola grabación o agrupar varias.
        Devuelve 'single' o 'grouped'. Nunca devuelve None.
        """

    def pick_scripts_multi(self, scripts: Sequence[str], project_name: str) -> Sequence[str]:
        """
        Selección múltiple de scripts para agrupación.
        Devuelve lista de nombres seleccionados (mínimo 2). Lista vacía = cancelación.
        """

    def pick_feature_name(self, suggested: str) -> Optional[str]:
        """
        Pide al usuario un nombre para el Feature agrupado.
        Devuelve el nombre sanitizado o None si cancela.
        """

    def grouped_feature_review(
        self,
        *,
        feature_text: str,
        script_names: Sequence[str],
        background_count: int,
    ) -> Dict[str, Any]:
        """
        Revisión del .feature agrupado antes de escribirlo.
        Devuelve {"action": "accept", "feature_text": str}.
        Lanza BDDUserCancelled si el usuario cierra la ventana.
        """

    # ----- Mensajes -----
    def info(self, title: str, message: str, **kwargs: Any) -> None:
        ...

    def warning(self, title: str, message: str, **kwargs: Any) -> None:
        ...

    def error(self, title: str, message: str, **kwargs: Any) -> None:
        ...

    # ----- Confirmaciones -----
    def yes_no(self, title: str, message: str) -> bool:
        ...

    def yes_no_cancel(self, title: str, message: str) -> Optional[bool]:
        """True=Sí, False=No, None=Cancelar."""

    def bdd_preview_review(
        self,
        *,
        feature_text: str,
        attempt: int,
        max_attempts: int,
        script_excerpt: str,
        can_manual: bool,
    ) -> Dict[str, Any]:
        """
        Revisión del .feature generado (IA). Debe devolver un dict:
          {"action": "accept", "feature_text": str, "edited": bool}
          {"action": "reject"}
        Si el usuario cancela el flujo, implementaciones pueden lanzar BDDUserCancelled.
        """

