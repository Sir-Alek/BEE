"""
flow_analyzer.py
================
Analiza y agrupa grabaciones JS de ELIA con el objetivo de:

  1. Detectar el prefijo de acciones compartidas entre varias grabaciones
     (candidato a Background en Gherkin).
  2. Calcular similitud entre dos flujos de acciones.
  3. Sugerir grupos de grabaciones similares dentro de un proyecto.
  4. Convertir el prefijo común en pasos Gherkin para el bloque Background.

Usa exclusivamente la stdlib — no tiene dependencias externas.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# (kind, selector_or_url, extra_value)
# kind: 'goto' | 'click' | 'fill' | 'select'
ActionTuple = Tuple[str, str, Optional[str]]

# Selector keywords que indican un formulario de login / credenciales
_LOGIN_KEYWORDS = frozenset(
    {"user", "username", "email", "login", "password", "passwd", "pass", "pwd", "credential"}
)


def _is_login_selector(selector: str) -> bool:
    low = selector.lower()
    return any(kw in low for kw in _LOGIN_KEYWORDS)


class FlowAnalyzer:
    """Utilidades estáticas de análisis de flujos de grabación."""

    # ------------------------------------------------------------------ #
    # Extracción de acciones desde contenido JS                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def extract_actions(script_content: str) -> List[ActionTuple]:
        """
        Parsea el contenido de un script JS grabado y devuelve una lista
        ordenada de ActionTuple: (kind, value, extra).

        Soporta los patrones generados por web_capture_engine.js de ELIA:
          page.goto(url)
          page.click(selector)
          page.fill(selector, value) / page.type(selector, value)
          page.select(selector, option)
        """
        actions: List[ActionTuple] = []
        for line in script_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            m = re.search(r'page\.goto\(["\']([^"\']+)["\']\)', line)
            if m:
                actions.append(("goto", m.group(1), None))
                continue

            m = re.search(r'page\.click\(["\']([^"\']+)["\']\)', line)
            if m:
                actions.append(("click", m.group(1), None))
                continue

            m = re.search(
                r'page\.(?:type|fill)\(["\']([^"\']+)["\'],\s*["\']([^"\']*)["\']',
                line,
            )
            if m:
                actions.append(("fill", m.group(1), m.group(2)))
                continue

            m = re.search(
                r'page\.select\(["\']([^"\']+)["\'],\s*["\']([^"\']*)["\']',
                line,
            )
            if m:
                actions.append(("select", m.group(1), m.group(2)))

        return actions

    # ------------------------------------------------------------------ #
    # Análisis de prefijos comunes                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def detect_common_prefix(
        actions_lists: List[List[ActionTuple]],
    ) -> List[ActionTuple]:
        """
        Encuentra el prefijo de acciones idénticas (kind + selector) que
        comparten TODAS las listas de acciones proporcionadas.

        Para 'fill', el valor extra (contraseña, etc.) no se compara —
        solo el selector debe coincidir para que la acción sea "común".
        """
        if not actions_lists or any(not lst for lst in actions_lists):
            return []

        min_len = min(len(lst) for lst in actions_lists)
        common: List[ActionTuple] = []

        for i in range(min_len):
            first_kind, first_val, first_extra = actions_lists[0][i]
            match = all(
                lst[i][0] == first_kind and lst[i][1] == first_val
                for lst in actions_lists[1:]
            )
            if match:
                common.append((first_kind, first_val, first_extra))
            else:
                break

        return common

    # ------------------------------------------------------------------ #
    # Similitud entre dos flujos                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_similarity(
        actions_a: List[ActionTuple],
        actions_b: List[ActionTuple],
    ) -> float:
        """
        Ratio de longitud del prefijo común respecto al máximo de ambas
        listas. Devuelve un valor en [0.0, 1.0].
        """
        if not actions_a and not actions_b:
            return 1.0
        if not actions_a or not actions_b:
            return 0.0
        common = FlowAnalyzer.detect_common_prefix([actions_a, actions_b])
        return len(common) / max(len(actions_a), len(actions_b))

    # ------------------------------------------------------------------ #
    # Agrupación automática de grabaciones similares                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def suggest_groups(
        scripts_actions: Dict[str, List[ActionTuple]],
        threshold: float = 0.25,
    ) -> List[List[str]]:
        """
        Agrupa scripts cuya similitud supera `threshold` Y que comparten
        la misma URL base (goto). Usa un algoritmo greedy de una pasada.

        Devuelve una lista de grupos; cada grupo es una lista de nombres
        de script. Scripts sin pareja forman grupos de tamaño 1.
        """
        names = list(scripts_actions.keys())
        if not names:
            return []

        def _base_url(n: str) -> Optional[str]:
            goto = next(
                (v for k, v, _ in scripts_actions[n] if k == "goto"), None
            )
            if not goto:
                return None
            try:
                p = urlparse(goto)
                return f"{p.scheme}://{p.netloc}"
            except Exception:
                return goto

        visited: set = set()
        groups: List[List[str]] = []

        for name_a in names:
            if name_a in visited:
                continue
            group = [name_a]
            visited.add(name_a)
            url_a = _base_url(name_a)

            for name_b in names:
                if name_b in visited or name_b == name_a:
                    continue
                url_b = _base_url(name_b)
                shared_url = url_a and url_b and url_a == url_b
                sim = FlowAnalyzer.compute_similarity(
                    scripts_actions[name_a], scripts_actions[name_b]
                )
                if sim >= threshold and shared_url:
                    group.append(name_b)
                    visited.add(name_b)

            groups.append(group)

        return groups

    # ------------------------------------------------------------------ #
    # Generación de pasos Gherkin para Background                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def extract_background_steps(
        common_prefix: List[ActionTuple],
    ) -> List[Tuple[str, str]]:
        """
        Convierte el prefijo común en una lista de tuplas (keyword, texto)
        listas para escribirse en un bloque Background de Gherkin.

        Reglas:
          - El primer goto → 'Given el usuario ingresa al sitio "{netloc}"'
          - Si hay fills/clicks con selectores de login → paso de sesión.
          - Si hay fills/clicks no-login → paso genérico de acceso inicial.
          - Todos los pasos adicionales usan keyword 'and'.
        """
        if not common_prefix:
            return []

        steps: List[Tuple[str, str]] = []

        non_goto = [(k, v, e) for k, v, e in common_prefix if k != "goto"]
        has_login = any(_is_login_selector(v) for k, v, _ in non_goto if k in ("fill", "click"))
        has_other = bool(non_goto) and not has_login

        # Siempre: paso de navegación desde el goto
        goto_action = next((v for k, v, _ in common_prefix if k == "goto"), None)
        if goto_action:
            try:
                netloc = urlparse(goto_action).netloc or goto_action
            except Exception:
                netloc = goto_action
            steps.append(("given", f'el usuario ingresa al sitio "{netloc}"'))

        if has_login:
            steps.append(("and", "el usuario inicia sesion en el sistema"))
        elif has_other:
            steps.append(("and", "el usuario completa el flujo de acceso inicial"))

        return steps
