"""
Cliente Value Edge / ALM Octane (sin Tkinter; apto para UI web / ELIA).

Copyright (c) 2025 Alejandro Ramírez — LAR v1.0
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib3
import requests
from pathlib import Path
from typing import Any, Dict, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ValueEdgeExtractor:
    """
    Sesión Value Edge. Credenciales vía dict ``settings`` o archivo ini (ver ``core.integrations_config_loader``).
    """

    def __init__(
        self,
        *,
        settings: Dict[str, str],
        verify_ssl: bool = False,
    ) -> None:
        missing = [k for k in ("url", "shared_space", "workspace", "tech_preview_flag", "user", "password") if not settings.get(k)]
        if missing:
            raise ValueError(f"Value Edge: faltan claves en settings: {missing}")

        self.url = settings["url"].rstrip("/")
        self.shared_space = settings["shared_space"]
        self.workspace = settings["workspace"]
        self.tech_preview_flag = settings["tech_preview_flag"]
        self.user = settings["user"]
        self.password = settings["password"]
        self.login_url = settings["login"]

        self.session = requests.Session()
        self.session.verify = verify_ssl

        self.headers = {
            "Content-Type": "application/json",
            "ALM_OCTANE_TECH_PREVIEW": self.tech_preview_flag,
        }
        self.cookies: Optional[Dict[str, str]] = None

    def login(self) -> bool:
        try:
            data = f'{{"client_id": "{self.user}", "client_secret": "{self.password}"}}'
            logger.info("Intentando login en Value Edge...")
            response = self.session.post(
                self.url + "/authentication/sign_in",
                headers=self.headers,
                data=data,
            )
            if response.status_code == 200:
                if "OCTANE_USER" in response.cookies and "LWSSO_COOKIE_KEY" in response.cookies:
                    self.cookies = {
                        "OCTANE_USER": response.cookies["OCTANE_USER"],
                        "LWSSO_COOKIE_KEY": response.cookies["LWSSO_COOKIE_KEY"],
                    }
                    self.session.cookies.update(self.cookies)
                    logger.info("Login exitoso")
                    return True
                logger.error("No se recibieron las cookies esperadas")
                return False
            logger.error("Error en login: %s — %s", response.status_code, response.text[:500])
            return False
        except Exception as e:
            logger.error("Error durante login: %s", e)
            return False

    def get_test_case(self, test_id: str) -> Optional[Dict[str, Any]]:
        if not self.cookies:
            logger.error("No hay sesión activa. Ejecute login() primero")
            return None

        try:
            logger.info("Obteniendo caso de prueba %s...", test_id)
            title_url = f"{self.url}/api/shared_spaces/{self.shared_space}/workspaces/{self.workspace}/tests"
            params = {
                "query": f"\"id EQ '{test_id}'\"",
                "fields": "name,application_modules",
            }
            title_response = self.session.get(title_url, params=params, headers=self.headers)
            if title_response.status_code != 200:
                logger.error("Error obteniendo detalles del test: %s", title_response.status_code)
                return None
            title_data = title_response.json()
            if not title_data.get("data"):
                logger.error("No se encontró el caso de prueba")
                return None
            test_info = title_data["data"][0]

            steps_url = f"{self.url}/api/shared_spaces/{self.shared_space}/workspaces/{self.workspace}/tests/{test_id}/script"
            steps_response = self.session.get(steps_url, headers=self.headers)
            if steps_response.status_code != 200:
                logger.error("Error obteniendo pasos: %s", steps_response.status_code)
                return None

            test_case: Dict[str, Any] = {
                "Titulo": test_info["name"],
                "Modulo": test_info["application_modules"]["data"][0]["name"],
                "CasoPrueba": {},
            }
            script = steps_response.json()["script"].split("\n- ")
            current_step = 1
            for line in script:
                line = self._clean_text(line)
                if not line:
                    continue
                if str(current_step) not in test_case["CasoPrueba"]:
                    test_case["CasoPrueba"][str(current_step)] = {"paso": "", "validacion": ""}
                if line.startswith("?"):
                    test_case["CasoPrueba"][str(current_step)]["validacion"] = line
                    current_step += 1
                else:
                    test_case["CasoPrueba"][str(current_step)]["paso"] = line.replace("- ", "")
            return test_case
        except Exception as e:
            logger.error("Error procesando caso de prueba: %s", e)
            return None

    def get_all_test_cases(self) -> Optional[list]:
        if not self.cookies:
            logger.error("No hay sesión activa. Ejecute login() primero")
            return None
        try:
            tests_url = f"{self.url}/api/shared_spaces/{self.shared_space}/workspaces/{self.workspace}/tests"
            params = {"fields": "id", "limit": 1000}
            response = self.session.get(tests_url, params=params, headers=self.headers)
            if response.status_code != 200:
                logger.error("Error obteniendo lista de tests: %s", response.status_code)
                return None
            tests_data = response.json()
            if not tests_data.get("data"):
                return []
            return [test["id"] for test in tests_data["data"]]
        except Exception as e:
            logger.error("Error obteniendo lista de casos: %s", e)
            return None

    def save_test_case(self, test_case: Dict[str, Any], output_dir: str = "test_cases") -> None:
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            output_file = Path(output_dir) / f"{test_case['Titulo']}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(test_case, f, indent=2, ensure_ascii=False)
            logger.info("Caso guardado en %s", output_file)
        except Exception as e:
            logger.error("Error guardando archivo: %s", e)

    @staticmethod
    def _clean_text(text: str) -> str:
        replacements = {
            "ú": "u",
            "ó": "o",
            "í": "i",
            "é": "e",
            "É": "E",
            "⚪": "",
            "⦿": "",
            "⦾": "",
            "●": "",
            "✅": "",
            "❌": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.strip()


def _legacy_cli_with_tk() -> None:
    """CLI opcional (Tkinter); no se importa tk en el arranque del módulo."""
    import tkinter as tk
    from tkinter import messagebox, simpledialog

    from core.integrations_config_loader import load_config_parser, value_edge_settings

    cfg, _ = load_config_parser()
    settings = value_edge_settings(cfg)
    if not settings.get("url"):
        print("Falta configuración Value Edge (secrets.ini o variables ELIA_VALUEEDGE_*).")
        return
    try:
        extractor = ValueEdgeExtractor(settings=settings)
    except ValueError as e:
        print(e)
        return
    if not extractor.login():
        print("Error: no se pudo realizar el login")
        return

    root = tk.Tk()
    root.withdraw()
    opcion = messagebox.askyesno(
        "Extracción de casos de prueba",
        "¿Desea extraer todos los casos de prueba?",
    )
    out = os.path.join(os.getcwd(), "test_cases")
    if opcion:
        test_ids = extractor.get_all_test_cases()
        if not test_ids:
            print("No se encontraron casos de prueba")
            return
        for test_id in test_ids:
            tc = extractor.get_test_case(test_id)
            if tc:
                extractor.save_test_case(tc, out)
    else:
        test_id = simpledialog.askstring("ID del caso de prueba", "Ingrese el ID del caso de prueba:")
        if test_id:
            tc = extractor.get_test_case(test_id)
            if tc:
                extractor.save_test_case(tc, out)


if __name__ == "__main__":
    _legacy_cli_with_tk()
