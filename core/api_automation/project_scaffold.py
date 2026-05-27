"""Scaffold de proyecto Behave API bajo behave/api/."""
from __future__ import annotations

from pathlib import Path


def scaffold_api_project(project_path: Path) -> None:
    project_path.mkdir(parents=True, exist_ok=True)
    for sub in ("scripts", "scenarios", "features/steps", "resources/data", "outputs/evidences", "outputs/reports"):
        (project_path / sub).mkdir(parents=True, exist_ok=True)

    env_path = project_path / "features" / "environment.py"
    if not env_path.is_file():
        env_path.write_text(_ENVIRONMENT_PY, encoding="utf-8")

    steps_path = project_path / "features" / "steps" / "api_steps.py"
    if not steps_path.is_file():
        steps_path.write_text(_API_STEPS_PY, encoding="utf-8")

    behave_ini = project_path / "behave.ini"
    if not behave_ini.is_file():
        behave_ini.write_text(
            "[behave]\npaths = features\nstdout_capture = false\nstderr_capture = false\n",
            encoding="utf-8",
        )


_ENVIRONMENT_PY = '''"""Entorno Behave API — sesión HTTP compartida (sin Selenium)."""
import os
import logging

import httpx


def before_all(context):
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def before_scenario(context, scenario):
    context.http = httpx.Client(timeout=float(os.getenv("ELIA_API_TIMEOUT", "30")), follow_redirects=True)
    context.last_response = None


def after_scenario(context, scenario):
    client = getattr(context, "http", None)
    if client is not None:
        client.close()


def after_all(context):
    pass
'''

_API_STEPS_PY = '''"""Steps genéricos HTTP para escenarios API generados por ELIA."""
from __future__ import annotations

import json

from behave import given, then, when


@given('la petición usa el header "{name}" con valor "{value}"')
def step_set_header(context, name, value):
    context._api_headers = getattr(context, "_api_headers", {})
    context._api_headers[name] = value


@when('envío una petición "{method}" a "{url}"')
def step_send_request(context, method, url):
    headers = getattr(context, "_api_headers", {})
    body = getattr(context, "_api_body", None)
    kwargs = {"headers": headers}
    if body is not None and method.upper() not in ("GET", "HEAD"):
        kwargs["content"] = body if isinstance(body, (bytes, str)) else json.dumps(body)
    context.last_response = context.http.request(method.upper(), url, **kwargs)


@when('envío el cuerpo JSON de la petición')
def step_send_json_body(context):
    context._api_body = getattr(context, "_scenario_body", None)


@then("el código HTTP de respuesta es {code:d}")
def step_status_code(context, code):
    assert context.last_response is not None, "Sin respuesta HTTP"
    assert context.last_response.status_code == code, (
        f"Esperado {code}, recibido {context.last_response.status_code}: "
        f"{context.last_response.text[:500]}"
    )


@then('el JSON de respuesta contiene la clave "{key}"')
def step_json_has_key(context, key):
    assert context.last_response is not None
    data = context.last_response.json()
    assert key in data, f"Clave {key!r} no encontrada en {data!r}"
'''
