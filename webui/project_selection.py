"""Flujo reutilizable: elegir proyecto nuevo o existente con opción de regresar."""
from __future__ import annotations

import os
import re
import uuid
from typing import Optional

from webui.job_manager import PROMPT_ANSWER_BACK, JobManager, Prompt


def _mk_prompt(
    prompt_type: str,
    *,
    title: str,
    message: str,
    options=None,
    allow_back: bool = False,
) -> Prompt:
    return Prompt(
        prompt_id=str(uuid.uuid4()),
        type=prompt_type,
        title=title,
        message=message,
        options=options,
        payload={"allow_back": True} if allow_back else None,
    )


def _normalize_project_name(raw: str, *, sanitize: bool) -> str:
    name = str(raw).strip()
    if not name:
        return ""
    if sanitize:
        return re.sub(r"[^\w\-_.]", "_", name)
    return name


def prompt_project_path(
    jm: JobManager,
    job_id: str,
    *,
    projects_dir: str,
    new_project_title: str = "Nuevo Proyecto",
    new_project_message: str = "Nombre del proyecto",
    yes_no_title: str = "Selección de Proyecto",
    existing_title: str = "Proyecto existente",
    existing_message: str = "Selecciona el proyecto",
    sanitize_project_name: bool = True,
) -> Optional[str]:
    """
    Pregunta si el proyecto es nuevo o existente y devuelve la ruta absoluta.
    None si el usuario cancela. PROMPT_ANSWER_BACK vuelve de pick/input al yes_no.
    """
    projects = [
        d for d in os.listdir(projects_dir)
        if os.path.isdir(os.path.join(projects_dir, d))
    ]

    if not projects:
        ans = jm.create_prompt_and_wait(
            job_id,
            prompt=_mk_prompt(
                "input_text",
                title=new_project_title,
                message=new_project_message,
            ),
        )
        if not ans or ans == PROMPT_ANSWER_BACK:
            return None
        project_name = _normalize_project_name(str(ans), sanitize=sanitize_project_name)
        if not project_name:
            return None
        return os.path.join(projects_dir, project_name)

    project_path: Optional[str] = None
    while project_path is None:
        is_new = jm.create_prompt_and_wait(
            job_id,
            prompt=_mk_prompt(
                "yes_no",
                title=yes_no_title,
                message="¿Es un proyecto nuevo?",
            ),
        )
        if is_new:
            while True:
                ans = jm.create_prompt_and_wait(
                    job_id,
                    prompt=_mk_prompt(
                        "input_text",
                        title=new_project_title,
                        message=new_project_message,
                        allow_back=True,
                    ),
                )
                if ans == PROMPT_ANSWER_BACK:
                    break
                if not ans:
                    return None
                project_name = _normalize_project_name(str(ans), sanitize=sanitize_project_name)
                if not project_name:
                    continue
                project_path = os.path.join(projects_dir, project_name)
                break
        else:
            while True:
                pick = jm.create_prompt_and_wait(
                    job_id,
                    prompt=_mk_prompt(
                        "pick_project",
                        title=existing_title,
                        message=existing_message,
                        options=[{"value": p, "label": p} for p in projects],
                        allow_back=True,
                    ),
                )
                if pick == PROMPT_ANSWER_BACK:
                    break
                if not pick:
                    return None
                project_path = os.path.join(projects_dir, str(pick))
                break

    return project_path
