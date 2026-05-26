"""Generación de locustfile.py desde escenarios API."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import List

from core.api_automation.models import ApiRequest


def generate_locustfile(requests: List[ApiRequest], *, host: str = "") -> str:
    base_host = host.rstrip("/") if host else ""
    tasks: List[str] = []
    for req in requests:
        url = req.url
        if base_host and url.startswith("/"):
            url = base_host + url
        method = req.method.upper()
        headers_repr = json.dumps(req.headers, ensure_ascii=False)
        body = req.body
        body_block = ""
        if body and method not in ("GET", "HEAD"):
            body_block = f"\n        payload = {json.dumps(body, ensure_ascii=False)!r}"
            send = f'self.client.request("{method}", {url!r}, headers=headers, data=payload)'
        else:
            send = f'self.client.request("{method}", {url!r}, headers=headers)'
        tasks.append(
            textwrap.dedent(
                f"""
                @task
                def task_{req.id.replace("-", "_")}(self):
                    headers = {headers_repr}{body_block}
                    with {send} as response:
                        if response.status_code >= 400:
                            response.failure(f"HTTP {{response.status_code}}")
                """
            ).strip()
        )

    tasks_src = "\n\n    ".join(tasks) if tasks else "    pass"
    host_line = f'    host = {base_host!r}\n' if base_host else ""
    return textwrap.dedent(
        f'''
        from locust import HttpUser, task, between


        class EliaApiUser(HttpUser):
            wait_time = between(0.5, 2.0)
        {host_line}
            {tasks_src}
        '''
    ).strip() + "\n"


def write_locustfile(project_dir: str, requests: List[ApiRequest], *, host: str = "") -> str:
    path = Path(project_dir) / "locustfile.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_locustfile(requests, host=host), encoding="utf-8")
    return str(path)
