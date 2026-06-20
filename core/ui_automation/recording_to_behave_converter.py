"""
Conversión de grabaciones JSON (móvil Appium / legacy escritorio) a proyectos Behave.

- Modo simple y agrupado (varias grabaciones → un Feature)
- Localizadores Appium desde page_source XML
- Vinculación opcional a escenario BDD existente (link_scenario)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ui.interfaces import ActionItem, BDDUserCancelled, IUI

from webui.job_manager import PROMPT_ANSWER_BACK

from core.ui_automation.flow_analyzer import ActionTuple, FlowAnalyzer
from core.ui_automation.mobile_dom_parser import MobileElement, parse_android_page_source
from core.ui_automation.web_capture_behave_builder import WebCaptureBehaveBuilder
from core.ui_automation.recording_flow_analyzer import (
    enrich_mobile_events,
    extract_recording_actions,
    extract_recording_background_steps,
)
from core.ui_automation.recording_linkage import (
    apply_grouped_link_to_scenario,
    apply_link_to_existing_scenario,
    decode_scenario_link,
)

logger = logging.getLogger(__name__)


def _trim_recording_for_preview(content: str, max_chars: int = 10000) -> str:
    s = (content or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 20] + "\n... [truncado]"


def parse_recording_json(content: str) -> Dict[str, Any]:
    data = json.loads(content or "{}")
    if not isinstance(data, dict):
        raise ValueError("El archivo de grabación no es un objeto JSON válido.")
    return data


def recording_events_to_action_items(
    events: Sequence[Dict[str, Any]],
    platform: str,
) -> List[ActionItem]:
    items: List[ActionItem] = []
    screen_idx = 0
    for idx, ev in enumerate(events):
        if not isinstance(ev, dict):
            continue
        et = str(ev.get("type") or "")
        line_id = f"event:{idx}"

        if platform == "legacy":
            if et == "click":
                label = ev.get("control_name") or f"({ev.get('x')}, {ev.get('y')})"
                ctype = ev.get("control_type") or ""
                desc = f"Clic en «{label}»"
                if ctype:
                    desc += f" [{ctype}]"
                items.append({"type": "Clic", "description": desc, "original_line": line_id})
            elif et == "key":
                items.append(
                    {
                        "type": "Teclado",
                        "description": f"Tecla: {ev.get('key', '')}",
                        "original_line": line_id,
                    }
                )
        elif platform == "mobile":
            if et == "page_source":
                screen_idx += 1
                sig = ev.get("screen_signature") or f"pantalla_{screen_idx}"
                items.append(
                    {
                        "type": "Pantalla",
                        "description": f"Pantalla: {sig}",
                        "original_line": line_id,
                    }
                )
                for el in ev.get("elements") or []:
                    if not isinstance(el, dict):
                        continue
                    rid = el.get("resource_id") or ""
                    txt = el.get("text") or el.get("content_desc") or rid
                    if rid or txt:
                        items.append(
                            {
                                "type": "Elemento",
                                "description": f"  · {txt} ({rid})" if rid else f"  · {txt}",
                                "original_line": line_id,
                            }
                        )

    return items


def recording_events_to_unique_actions(
    events: Sequence[Dict[str, Any]],
    platform: str,
    meta: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, str]]:
    """Acciones normalizadas para BDD (desde flow analyzer)."""
    actions = extract_recording_actions(list(events), platform, meta)
    # Convertir ActionTuple → (type, description) para el generador BDD
    out: List[Tuple[str, str]] = []
    for kind, val, extra in actions:
        if kind == "launch":
            if platform == "mobile":
                out.append(("given", f'Abrir aplicación móvil "{val}"'))
            else:
                out.append(("given", f'Abrir ventana "{val}"'))
        elif kind == "screen":
            out.append(("screen", f"El usuario llega a la pantalla {val}"))
        elif kind == "click":
            label = extra or val
            out.append(("click", f'Interacción con «{label or val}»'))
        elif kind == "key":
            out.append(("key", f'Pulsar tecla «{extra or val}»'))
    unique: List[Tuple[str, str]] = []
    last = None
    for a in out:
        if a != last:
            unique.append(a)
            last = a
    return unique


def _filter_events_by_selection(
    events: List[Dict[str, Any]],
    selected_lines: Sequence[str],
) -> List[Dict[str, Any]]:
    if not selected_lines:
        return list(events)
    selected_set = set(selected_lines)
    out: List[Dict[str, Any]] = []
    for idx, ev in enumerate(events):
        if f"event:{idx}" in selected_set:
            out.append(ev)
    return out if out else list(events)


class RecordingToBehaveConverter(WebCaptureBehaveBuilder):
    """Convierte grabaciones .json de móvil o legacy a Behave."""

    def __init__(
        self,
        base_dir: str,
        ui: IUI,
        platform: str,
        use_ai: bool = False,
        link_scenario: Optional[str] = None,
    ) -> None:
        super().__init__(base_dir, ui, use_ai=use_ai, link_scenario=link_scenario, platform=platform)
        if platform not in ("mobile", "legacy"):
            raise ValueError(f"Plataforma no soportada: {platform}")
        self.platform = platform
        self._recording_data: Dict[str, Any] = {}
        self._recording_events: List[Dict[str, Any]] = []
        self._link_scenario = decode_scenario_link(link_scenario)

    def _platform_label(self) -> str:
        return "Móvil" if self.platform == "mobile" else "Legacy"

    def _prepare_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.platform == "mobile":
            return enrich_mobile_events(events)
        return events

    def convert_script(self) -> None:
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir, exist_ok=True)

        projects = [
            d
            for d in os.listdir(self.projects_dir)
            if os.path.isdir(os.path.join(self.projects_dir, d))
        ]
        if not projects:
            self.ui.info("No hay proyectos", "No se encontraron proyectos existentes.")
            return

        project_name = self.ui.pick_project(sorted(projects))
        if not project_name:
            return

        project_path = os.path.join(self.projects_dir, project_name)
        scripts_dir = os.path.join(project_path, "scripts")
        if not os.path.isdir(scripts_dir):
            self.ui.error(
                "Error",
                f"No se encontró la carpeta 'scripts' en el proyecto {project_name}.",
            )
            return

        recordings = [f for f in os.listdir(scripts_dir) if f.lower().endswith(".json")]
        if not recordings:
            self.ui.error(
                "Error",
                f"No hay grabaciones {self._platform_label()} (.json) en scripts/.",
            )
            return

        mode = self.ui.pick_conversion_mode()

        if mode == "grouped":
            selected_files = self.ui.pick_scripts_multi(sorted(recordings), project_name)
            if not selected_files:
                return
            suggested = re.sub(r"[^a-zA-Z0-9_]", "_", project_name).strip("_") or "feature_agrupado"
            feature_name = self.ui.pick_feature_name(suggested)
            if not feature_name:
                return
            full_paths = [os.path.join(scripts_dir, f) for f in selected_files]
            try:
                self._process_grouped_recording_conversion(
                    full_paths, project_path, feature_name
                )
            except BDDUserCancelled:
                self.ui.info("Conversión cancelada", "Se canceló la generación del escenario BDD.")
            except Exception as e:
                self.ui.error("Error", f"No se pudo convertir:\n{e}")
            return

        selected_file = self.ui.pick_script(sorted(recordings), project_name)
        if not selected_file:
            return

        json_path = os.path.join(scripts_dir, selected_file)
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                content = "{}"
            data = parse_recording_json(content)
            events = data.get("events") if isinstance(data.get("events"), list) else []
            self._recording_data = data
            self._recording_events = self._prepare_events(
                [e for e in events if isinstance(e, dict)]
            )

            action_items = recording_events_to_action_items(
                self._recording_events, self.platform
            )
            if action_items:
                selected_lines = self.ui.pick_actions(action_items)
                if selected_lines == PROMPT_ANSWER_BACK:
                    return
                if not selected_lines:
                    raise BDDUserCancelled()
                self.selected_actions = list(selected_lines)
                self._recording_events = _filter_events_by_selection(
                    self._recording_events,
                    self.selected_actions,
                )
            else:
                self.selected_actions = []

            self._process_recording_conversion(json_path, content, project_path)

        except json.JSONDecodeError as e:
            self.ui.error("Error", f"JSON inválido:\n{e}")
        except BDDUserCancelled:
            self.ui.info("Conversión cancelada", "Se canceló la generación del escenario BDD.")
        except Exception as e:
            self.ui.error("Error", f"No se pudo convertir:\n{e}")

    def _load_recording_bundle(self, json_path: str) -> Dict[str, Any]:
        with open(json_path, "r", encoding="utf-8") as fh:
            content = fh.read() or "{}"
        data = parse_recording_json(content)
        events = data.get("events") if isinstance(data.get("events"), list) else []
        events = self._prepare_events([e for e in events if isinstance(e, dict)])
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        actions = extract_recording_actions(events, self.platform, data)
        return {
            "json_file": json_path,
            "base_name": base_name,
            "class_name": base_name.capitalize()
            + ("MobilePage" if self.platform == "mobile" else "LegacyPage"),
            "content": content,
            "meta": data,
            "events": events,
            "actions": actions,
        }

    def _process_grouped_recording_conversion(
        self,
        json_files: List[str],
        project_path: str,
        feature_name: str,
    ) -> None:
        from ui.interfaces import BDDUserCancelled as _Cancel

        self._copy_support_files(project_path)
        scripts_data: List[Dict[str, Any]] = []
        for jf in json_files:
            bundle = self._load_recording_bundle(jf)
            scripts_data.append(bundle)

        actions_lists = [d["actions"] for d in scripts_data]
        common_prefix = FlowAnalyzer.detect_common_prefix(actions_lists)
        background_steps = extract_recording_background_steps(
            common_prefix, self.platform, scripts_data[0]["meta"] if scripts_data else {}
        )

        for d in scripts_data:
            d["unique_actions"] = d["actions"][len(common_prefix) :]

        feature_content = self._generate_grouped_feature(
            scripts_data, feature_name, background_steps
        )

        try:
            review = self.ui.grouped_feature_review(
                feature_text=feature_content,
                script_names=[d["base_name"] for d in scripts_data],
                background_count=len(background_steps),
            )
            if review.get("action") != "accept":
                return
            feature_content = review.get("feature_text") or feature_content
        except _Cancel:
            raise BDDUserCancelled()

        linked = False
        if self._link_scenario:
            ff, sn = self._link_scenario
            linked = apply_grouped_link_to_scenario(feature_content, ff, sn, mode="append")

        dirs = {
            "features": os.path.join(project_path, "features"),
            "steps": os.path.join(project_path, "features", "steps"),
            "pages": os.path.join(project_path, "pages"),
            "data": os.path.join(project_path, "resources", "data"),
        }
        for p in dirs.values():
            os.makedirs(p, exist_ok=True)

        if not linked:
            feature_path = os.path.join(dirs["features"], f"{feature_name}.feature")
            with open(feature_path, "w", encoding="utf-8") as fh:
                fh.write(feature_content)

        steps_content = self._generate_grouped_recording_steps(
            feature_name, scripts_data, background_steps, common_prefix
        )
        grouped_steps_path: Optional[str] = None
        if linked and self._link_scenario and self.platform == "mobile":
            from core.ui_automation.linked_steps_regenerator import regenerate_linked_steps

            ff, sn = self._link_scenario
            first = scripts_data[0] if scripts_data else {}
            bn = first.get("base_name", feature_name)
            cn = first.get("class_name", "Page")
            grouped_steps_path = regenerate_linked_steps(
                project_path=project_path,
                feature_file=ff,
                scenario_name=sn,
                steps_module_content=steps_content,
                page_import_line=f"from pages.{bn}_page import {cn}",
            )
        else:
            steps_path = os.path.join(dirs["steps"], f"{feature_name}_steps.py")
            with open(steps_path, "w", encoding="utf-8") as fh:
                fh.write(steps_content)
            grouped_steps_path = steps_path

        created_pages: List[str] = []
        for d in scripts_data:
            self._recording_events = d["events"]
            page_content = self._generate_page_object(
                d["class_name"], d["content"]
            )
            page_path = os.path.join(dirs["pages"], f"{d['base_name']}_page.py")
            with open(page_path, "w", encoding="utf-8") as fh:
                fh.write(page_content)
            created_pages.append(f"{d['base_name']}_page.py")

        json_combined = json.dumps(
            [{"base_name": d["base_name"], "meta": d["meta"], "events": d["events"]} for d in scripts_data],
            indent=2,
            ensure_ascii=False,
        )
        with open(os.path.join(dirs["data"], f"{feature_name}.json"), "w", encoding="utf-8") as fh:
            fh.write(json_combined)

        link_msg = (
            f"\n  • Pasos fusionados en escenario existente: {self._link_scenario[1]}"
            if linked
            else ""
        )
        from webui.conversion_result import conversion_result

        grouped_files: List[Tuple[str, str]] = []
        if not linked:
            grouped_files.append(("feature", os.path.join(dirs["features"], f"{feature_name}.feature")))
        if grouped_steps_path:
            grouped_files.append(("steps", grouped_steps_path))
        for page_name in created_pages:
            grouped_files.append(("page", os.path.join(dirs["pages"], page_name)))
        grouped_files.append(("json", os.path.join(dirs["data"], f"{feature_name}.json")))
        self.ui.info(
            "Éxito",
            f"Feature agrupado {self._platform_label()} en {os.path.basename(project_path)}\n"
            f"  • {feature_name}.feature ({len(scripts_data)} scenarios)\n"
            f"  • {feature_name}_steps.py\n"
            + "\n".join(f"  • {p}" for p in created_pages)
            + link_msg,
            result=conversion_result(project_dir=project_path, files=grouped_files),
        )

    def _generate_grouped_recording_steps(
        self,
        feature_name: str,
        scripts_data: List[Dict[str, Any]],
        background_steps: List[Tuple[str, str]],
        common_prefix: List[ActionTuple],
    ) -> str:
        page_imports = "\n".join(
            f"from pages.{d['base_name']}_page import {d['class_name']}" for d in scripts_data
        )
        header = (
            f"from behave import *\n{page_imports}\nfrom environment import *\n\n"
        )
        parts = [header, self._generate_grouped_recording_background(common_prefix)]

        step_n = 0
        for data in scripts_data:
            when_text = data.get("_when_text") or f"el usuario completa {data['base_name']}"
            then_text = data.get("_then_text") or "el sistema responde correctamente"
            method_names = self._event_method_names(data["events"], self.platform)
            step_n += 1
            esc_when = when_text.replace("\\", "\\\\").replace("'", "\\'")
            esc_then = then_text.replace("\\", "\\\\").replace("'", "\\'")
            body = [f"    context.page = {data['class_name']}(None)" if self.platform == "legacy" else f"    context.page = {data['class_name']}(context.driver)"]
            when_id = f"{step_n:02d}_when"
            then_id = f"{step_n:02d}_then"
            for mn in method_names:
                if self.platform == "legacy" and not mn.startswith("wait_"):
                    body.append(
                        f"    context.page.{mn}(step='{when_id}', tomar_evidencia=context.generate_evidence)"
                    )
                else:
                    body.append(f"    context.page.{mn}()")
            parts.append(
                f"\n@when('{esc_when}')\ndef step_{step_n:02d}_when(context):\n"
                + "\n".join(body)
                + "\n"
            )
            then_body = ""
            if self.platform == "legacy":
                then_body = (
                    f"    context.page.capturar_estado(step='{then_id}', tomar_evidencia=context.generate_evidence)\n"
                )
            parts.append(
                f"\n@then('{esc_then}')\ndef step_{step_n:02d}_then(context):\n"
                + then_body
                + "    assert True\n"
            )
        return "".join(parts)

    def _generate_grouped_recording_background(
        self, common_prefix: List[ActionTuple]
    ) -> str:
        if not common_prefix:
            return ""
        lines = ["# ── Background ─────────────────────────────────────\n\n"]
        if self.platform == "mobile":
            launch = next((v for k, v, _ in common_prefix if k == "launch"), "app")
            lines.append(
                f"@given('el usuario abre la aplicación móvil \"{launch}')\n"
                "def step_background_mobile(context):\n"
                "    pass\n\n"
            )
        else:
            launch = next((v for k, v, _ in common_prefix if k == "launch"), "app")
            lines.append(
                f"@given('el usuario tiene abierta la ventana \"{launch}')\n"
                "def step_background_legacy(context):\n"
                "    pass\n\n"
            )
        return "".join(lines)

    def _process_recording_conversion(
        self, json_path: str, content: str, project_path: str
    ) -> None:
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        class_name = base_name.capitalize() + (
            "MobilePage" if self.platform == "mobile" else "LegacyPage"
        )

        self._copy_support_files(project_path)
        project_dirs = {
            "features": os.path.join(project_path, "features"),
            "steps": os.path.join(project_path, "features", "steps"),
            "pages": os.path.join(project_path, "pages"),
            "resources": os.path.join(project_path, "resources", "data"),
        }
        for dir_path in project_dirs.values():
            os.makedirs(dir_path, exist_ok=True)

        file_paths = {
            "feature": os.path.join(project_dirs["features"], f"{base_name}.feature"),
            "steps": os.path.join(project_dirs["steps"], f"{base_name}_steps.py"),
            "page": os.path.join(project_dirs["pages"], f"{base_name}_page.py"),
            "json": os.path.join(project_dirs["resources"], f"{base_name}.json"),
        }

        linked_steps_path: Optional[str] = None
        feature_content = self._generate_bdd_feature(content, base_name)
        linked = False
        if self._link_scenario:
            ff, sn = self._link_scenario
            linked = apply_link_to_existing_scenario(
                feature_content, ff, sn, mode="append", prefer_named_scenario=True
            )
            if linked:
                file_paths.pop("feature", None)

        if "feature" in file_paths:
            with open(file_paths["feature"], "w", encoding="utf-8") as f:
                f.write(feature_content)

        feature_for_steps = feature_content
        if linked and self._link_scenario:
            try:
                with open(self._link_scenario[0], "r", encoding="utf-8") as f:
                    feature_for_steps = f.read()
            except OSError:
                pass

        if self.platform == "mobile" and self._link_scenario:
            linked_steps_path = self._persist_generated_steps(
                project_path,
                base_name,
                class_name,
                content,
                feature_for_steps,
                file_paths,
            )
        else:
            linked_steps_path = None
            steps_content = self._generate_adaptive_steps(
                base_name, class_name, content, feature_for_steps
            )
            with open(file_paths["steps"], "w", encoding="utf-8") as f:
                f.write(steps_content)

        page_content = self._generate_page_object(class_name, content)
        with open(file_paths["page"], "w", encoding="utf-8") as f:
            f.write(page_content)

        with open(file_paths["json"], "w", encoding="utf-8") as f:
            f.write(content)

        msg = f"Conversión {self._platform_label()} completada."
        if linked:
            msg += f"\n\nPasos vinculados al escenario «{self._link_scenario[1]}»."
            if self.platform == "mobile" and linked_steps_path:
                msg += f"\n  • Steps: {os.path.basename(linked_steps_path)}"
        from webui.conversion_result import conversion_result

        result_files: List[Tuple[str, str]] = [(name, path) for name, path in file_paths.items()]
        if linked_steps_path:
            result_files.append(("steps (vinculados)", linked_steps_path))
        self.ui.info(
            "Éxito",
            msg,
            result=conversion_result(project_dir=project_path, files=result_files),
        )

    def _generate_bdd_feature(self, recording_content: str, base_name: str) -> str:
        data = parse_recording_json(recording_content)
        events = self._recording_events or [
            e for e in (data.get("events") or []) if isinstance(e, dict)
        ]
        unique_actions = recording_events_to_unique_actions(
            events, self.platform, meta=data
        )
        excerpt = _trim_recording_for_preview(recording_content)
        return self._generate_bdd_feature_from_unique_actions(
            unique_actions,
            base_name,
            excerpt,
            platform=self.platform,
        )

    def _appium_locator_code(self, el: MobileElement) -> Tuple[str, str]:
        by = el.appium_by
        val = el.appium_value.replace("\\", "\\\\").replace('"', '\\"')
        if by == "ID":
            return "AppiumBy.ID", f'"{val}"'
        if by == "ACCESSIBILITY_ID":
            return "AppiumBy.ACCESSIBILITY_ID", f'"{val}"'
        if by == "ANDROID_UIAUTOMATOR":
            return "AppiumBy.ANDROID_UIAUTOMATOR", f'"{val}"'
        return "AppiumBy.ID", f'"{val}"'

    def _generate_mobile_page_object(
        self,
        class_name: str,
        events: List[Dict[str, Any]],
        meta: Dict[str, Any],
    ) -> str:
        methods: List[str] = []
        screen_idx = 0
        used_methods: set[str] = set()

        for ev in events:
            if ev.get("type") != "page_source":
                continue
            screen_idx += 1
            elements_raw = ev.get("elements")
            if isinstance(elements_raw, list) and elements_raw:
                elements = [
                    MobileElement(
                        resource_id=str(x.get("resource_id") or ""),
                        text=str(x.get("text") or ""),
                        content_desc=str(x.get("content_desc") or ""),
                        class_name=str(x.get("class_name") or ""),
                        bounds=str(x.get("bounds") or ""),
                        clickable=bool(x.get("clickable")),
                        appium_by=str(x.get("appium_by") or ""),
                        appium_value=str(x.get("appium_value") or ""),
                        method_suffix=str(x.get("method_suffix") or ""),
                    )
                    for x in elements_raw
                    if isinstance(x, dict)
                ]
            else:
                elements = parse_android_page_source(str(ev.get("source") or ""))

            anchor = ev.get("anchor")
            if isinstance(anchor, dict) and anchor.get("appium_by"):
                a_el = MobileElement(
                    resource_id=str(anchor.get("resource_id") or ""),
                    text=str(anchor.get("text") or ""),
                    content_desc=str(anchor.get("content_desc") or ""),
                    appium_by=str(anchor.get("appium_by") or ""),
                    appium_value=str(anchor.get("appium_value") or ""),
                    method_suffix=str(anchor.get("method_suffix") or f"screen_{screen_idx}"),
                )
            else:
                from core.ui_automation.mobile_dom_parser import screen_anchor_element

                a_el = screen_anchor_element(elements)

            if a_el and a_el.appium_by:
                by_const, by_val = self._appium_locator_code(a_el)
                mname = f"wait_screen_{screen_idx}"
                methods.append(
                    f"""
    def {mname}(self):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located(({by_const}, {by_val}))
        )
"""
                )
                used_methods.add(mname)

            for el in elements:
                if not el.appium_by:
                    continue
                suffix = el.method_suffix
                if suffix in used_methods:
                    suffix = f"{suffix}_{screen_idx}"
                used_methods.add(suffix)
                by_const, by_val = self._appium_locator_code(el)
                methods.append(
                    f"""
    def tap_{suffix}(self):
        self.driver.find_element({by_const}, {by_val}).click()
"""
                )

        if not methods:
            methods.append(
                """
    def interact_default(self):
        pass
"""
            )

        apk = meta.get("apk_path") or ""
        caps = f"    # APK: {apk}\n" if apk else ""
        return (
            "from appium.webdriver.common.appiumby import AppiumBy\n"
            f"\n\nclass {class_name}:\n"
            f"    def __init__(self, driver):\n"
            f"        self.driver = driver\n{caps}\n"
            + "".join(methods)
        )

    def _generate_legacy_page_object(
        self,
        class_name: str,
        events: List[Dict[str, Any]],
        meta: Dict[str, Any],
    ) -> str:
        methods: List[str] = []
        click_idx = 0
        for ev in events:
            if ev.get("type") != "click":
                continue
            click_idx += 1
            x, y = ev.get("x", 0), ev.get("y", 0)
            ctrl = ev.get("control_name") or f"control_{click_idx}"
            safe = re.sub(r"[^\w]", "_", str(ctrl))[:40].strip("_") or f"click_{click_idx}"
            methods.append(
                f"""
    def click_{safe}(self, step=None, tomar_evidencia=False):
        legacy_click({x}, {y}, nombre_elemento={ctrl!r}, step=step, usar_create_screenshot=tomar_evidencia)
"""
            )
        if not methods:
            methods.append(
                "\n    def interact_default(self, step=None, tomar_evidencia=False):\n        pass\n"
            )
        methods.append(
            "\n    def capturar_estado(self, step=None, tomar_evidencia=False):\n"
            "        legacy_capture_screen(step=step, nombre_elemento='estado_final', usar_create_screenshot=tomar_evidencia)\n"
        )
        win = meta.get("window_name") or ""
        win_line = f"    # Ventana: {win}\n" if win else ""
        return (
            "from utils.button_functions import legacy_click, legacy_capture_screen\n"
            f"\n\nclass {class_name}:\n"
            f"    def __init__(self, driver):\n"
            f"        self.driver = driver\n{win_line}\n"
            + "".join(methods)
        )

    def _generate_page_object(self, class_name: str, recording_content: str) -> str:
        data = parse_recording_json(recording_content)
        events = self._recording_events or [
            e for e in (data.get("events") or []) if isinstance(e, dict)
        ]
        if self.platform == "mobile":
            return self._generate_mobile_page_object(class_name, events, data)
        return self._generate_legacy_page_object(class_name, events, data)

    def _generate_adaptive_steps(
        self,
        base_name: str,
        class_name: str,
        recording_content: str,
        existing_feature: Optional[str] = None,
    ) -> str:
        if existing_feature and existing_feature.strip():
            feature_steps = self._extract_steps_from_feature(existing_feature)
            if self._feature_is_business_language(feature_steps):
                return self._generate_platform_steps_from_business_feature(
                    base_name, class_name, feature_steps, recording_content
                )
        return self._generate_platform_steps_from_business_feature(
            base_name,
            class_name,
            [("when", "completar el flujo grabado"), ("then", "el sistema responde correctamente")],
            recording_content,
        )

    def _generate_platform_steps_from_business_feature(
        self,
        base_name: str,
        class_name: str,
        feature_steps: List[Tuple[str, str]],
        recording_content: str,
    ) -> str:
        data = parse_recording_json(recording_content)
        events = self._recording_events or [
            e for e in (data.get("events") or []) if isinstance(e, dict)
        ]

        if self.platform == "mobile":
            imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from environment import *
"""
            given_desc = next(
                (d for t, d in feature_steps if t.lower() == "given"),
                "el usuario tiene la aplicación móvil abierta y lista para usar",
            )
            esc_given = given_desc.replace("\\", "\\\\").replace("'", "\\'")
            body = [
                f"""
@given('{esc_given}')
def step_mobile_given(context):
    context.page = {class_name}(context.driver)
"""
            ]
        else:
            imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from utils.button_functions import activate_window_by_title_contains
from environment import *
"""
            win = data.get("window_name") or "aplicación"
            given_desc = next((d for t, d in feature_steps if t.lower() == "given"), None)
            if given_desc:
                m = re.search(r'"([^"]+)"', given_desc)
                if m:
                    win = m.group(1)
                esc_given = given_desc.replace("\\", "\\\\").replace("'", "\\'")
            else:
                esc_given = "el usuario tiene abierta la aplicación de escritorio bajo prueba"
            body = [
                f"""
@given('{esc_given}')
def step_legacy_given(context):
    activate_window_by_title_contains({json.dumps(str(win))}, timeout=10.0)
    context.page = {class_name}(None)
"""
            ]

        method_idx = 0
        event_methods = self._event_method_names(events, self.platform)
        ev_pos = 0
        n_main = max(1, sum(1 for t, _ in feature_steps if t.lower() in ("when", "and")))

        for step_type, description in feature_steps:
            method_idx += 1
            st = step_type.lower()
            if st == "given":
                continue
            esc = description.replace("\\", "\\\\").replace("'", "\\'")
            mname = f"step_{method_idx:02d}_{st}"
            calls: List[str] = []
            step_id = f"{method_idx:02d}_{st}"
            if st in ("when", "and") and event_methods:
                chunk_size = max(1, len(event_methods) // n_main)
                chunk = event_methods[ev_pos : ev_pos + chunk_size]
                ev_pos += len(chunk)
                for em in chunk:
                    if self.platform == "legacy" and not em.startswith("wait_"):
                        calls.append(
                            f"    context.page.{em}(step='{step_id}', tomar_evidencia=context.generate_evidence)"
                        )
                    else:
                        calls.append(f"    context.page.{em}()")
            if st == "then":
                if self.platform == "legacy":
                    calls.append(
                        f"    context.page.capturar_estado(step='{step_id}', tomar_evidencia=context.generate_evidence)"
                    )
                calls.append(
                    '    assert True, "Verificar resultado esperado según el escenario de negocio"'
                )
            if not calls and st in ("when", "and"):
                calls.append("    context.page.interact_default()")

            dec = "And" if st == "and" else st.capitalize()
            page_ctor = "None" if self.platform == "legacy" else "context.driver"
            body.append(
                f"""
@{dec}('{esc}')
def {mname}(context):
    if not hasattr(context, 'page') or context.page is None:
        context.page = {class_name}({page_ctor})
"""
                + "\n".join(calls)
                + "\n"
            )
        return imports + "".join(body)

    def _event_method_names(self, events: List[Dict[str, Any]], platform: str) -> List[str]:
        names: List[str] = []
        if platform == "mobile":
            screen_idx = 0
            for ev in events:
                if ev.get("type") != "page_source":
                    continue
                screen_idx += 1
                names.append(f"wait_screen_{screen_idx}")
                for el in ev.get("elements") or []:
                    if isinstance(el, dict) and el.get("method_suffix"):
                        names.append(f"tap_{el['method_suffix']}")
        else:
            click_idx = 0
            for ev in events:
                if ev.get("type") != "click":
                    continue
                click_idx += 1
                ctrl = ev.get("control_name") or f"control_{click_idx}"
                safe = re.sub(r"[^\w]", "_", str(ctrl))[:40].strip("_") or f"click_{click_idx}"
                names.append(f"click_{safe}")
        return names
