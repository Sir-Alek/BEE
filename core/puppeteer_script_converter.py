import os
import shutil
import re
import time
import json
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple

from ui.interfaces import BDDUserCancelled, IUI


def _trim_script_for_preview(script_content: str, max_chars: int = 10000) -> str:
    s = (script_content or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 20] + "\n... [truncado]"


class PuppeteerToBehaveConverter:
    
    def __init__(self, base_dir, ui: IUI, use_ai: bool = False):
        self.base_dir = base_dir
        from core.bee_paths import behave_projects_dir

        self.projects_dir = str(behave_projects_dir())
        self.selected_actions = []
        self.ui = ui
        self.use_ai = use_ai
        self._recording_meta: Optional[Dict[str, Any]] = None

    def _create_project_structure(self):
        """Crea la estructura de directorios necesaria para Behave"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "features"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "features", "steps"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "pages"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "resources", "data"), exist_ok=True)
        
    def parse_fill(self, line):
        """Parsea una línea de acción de relleno (fill)"""
        patterns = [
            r'page\.(?:type|fill)\((["\'])(.*?)\1,\s*(["\'])(.*?)\3\)',
            r'page\.locator\((["\'])(.*?)\1\)\.(?:type|fill)\((["\'])(.*?)\3\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return {
                    'selector': match.group(2),
                    'value': match.group(4)
                }
        return None   

    def convert_script(self):
        """Convierte el script grabado (JS) a estructura Behave"""
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir, exist_ok=True)
        
        projects = [d for d in os.listdir(self.projects_dir) 
                   if os.path.isdir(os.path.join(self.projects_dir, d))]
        
        if not projects:
            self.ui.info("No hay proyectos", "No se encontraron proyectos existentes.")
            return
        project_name = self.ui.pick_project(sorted(projects))
        if not project_name:
            return

        project_path = os.path.join(self.projects_dir, project_name)
        scripts_dir = os.path.join(project_path, "scripts")

        if not os.path.exists(scripts_dir):
            self.ui.error("Error", "No se encontró la carpeta 'scripts' en el proyecto seleccionado.")
            return

        js_files = [f for f in os.listdir(scripts_dir) if f.endswith(".js")]
        if not js_files:
            self.ui.error("Error", "No se encontraron archivos JavaScript (.js) en la carpeta 'scripts' del proyecto.")
            return

        selected_file = self.ui.pick_script(sorted(js_files), project_name)
        if not selected_file:
            return

        js_file = os.path.join(project_path, "scripts", selected_file)

        try:
            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()

            if content is None or content == "":
                content = "// Archivo vacío"

            actions = self._extract_all_actions(content)
            selected_lines = self.ui.pick_actions(actions)
            if actions and not selected_lines:
                return
            self.selected_actions = list(selected_lines)

            filtered_content = self._filter_content_by_actions(content, self.selected_actions)
            self._process_conversion(js_file, filtered_content, project_path)

        except Exception as e:
            self.ui.error("Error", f"No se pudo convertir:\n{str(e)}")
         
    def _find_project_path(self, js_file_path):
        """Busca la carpeta del proyecto basada en la ubicación del script"""
        # Normalizar la ruta para manejar correctamente las barras
        js_file_path = os.path.normpath(js_file_path)
        
        # Buscar la carpeta 'proyectos' en la ruta
        parts = js_file_path.split(os.sep)
        try:
            proyectos_index = parts.index('proyectos')
            if proyectos_index + 1 < len(parts):
                project_path = os.path.join(*parts[:proyectos_index + 2])
                return project_path
        except ValueError:
            pass
        
        return None            

    def _extract_all_actions(self, script_content):
        """Extrae todas las acciones del script para mostrarlas en la selección"""
        actions = []
        lines = script_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            action = None
            try:
                if "page.goto(" in line:
                    url_match = re.search(r'page\.goto\((["\'])(.*?)\1', line)
                    if url_match:
                        action = ("Navegación", f'Ir a URL: {url_match.group(2)}')

                elif "page.click(" in line:
                    selector_match = re.search(r'page\.click\((["\'])(.*?)\1', line)
                    if selector_match:
                        selector = selector_match.group(2)
                        action = ("Click", f'Click en: {selector}')

                elif "page.type(" in line or "page.fill(" in line:
                    type_match = re.search(r'page\.(?:type|fill)\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if type_match:
                        selector = type_match.group(2)
                        value = type_match.group(4)
                        action = ("Rellenar", f'Rellenar campo {selector} con: {value}')

                elif "page.select(" in line:
                    select_match = re.search(r'page\.select\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if select_match:
                        selector = select_match.group(2)
                        option = select_match.group(4)
                        action = ("Seleccionar", f'Seleccionar {option} en: {selector}')

            except Exception as e:
                print(f"Error procesando línea para selección: {line}\n{str(e)}")
                continue
            
            if action:
                actions.append({
                    "type": action[0],
                    "description": action[1],
                    "original_line": line
                })
        
        return actions

    def _show_action_selection(self, actions):
        """Muestra ventana para seleccionar acciones a convertir"""
        if not actions:
            return True

        selected_lines = self.ui.pick_actions(actions)
        self.selected_actions = list(selected_lines)
        return bool(self.selected_actions)

    def _confirm_selection(self, actions, check_vars, window):
        self.selected_actions = [
            action["original_line"]
            for action, var in zip(actions, check_vars)
            if var.get()]
        window.destroy()

    def _toggle_all(self, check_vars, state):
        """Marca/desmarca todos los checkboxes"""
        for var in check_vars:
            var.set(state)

    def _get_selected_actions(self, actions, check_vars, window):
        """Obtiene las acciones seleccionadas"""
        self.selected_actions = []
        for i, (action, var) in enumerate(zip(actions, check_vars)):
            if var.get():
                self.selected_actions.append(action["original_line"])
        window.destroy()

    def _filter_content_by_actions(self, original_content, selected_lines):
        """Filtra el contenido manteniendo solo las líneas seleccionadas"""
        lines = original_content.split('\n')
        filtered_lines = []
        
        # Mantener las primeras líneas (imports y setup)
        for line in lines[:4]:
            filtered_lines.append(line)
            
        # Añadir solo las líneas seleccionadas
        for line in lines[4:]:
            if line.strip() in selected_lines:
                filtered_lines.append(line)
                
        # Mantener las últimas líneas (cierre)
        for line in lines[-2:]:
            filtered_lines.append(line)
            
        return '\n'.join(filtered_lines)
            
    def _process_conversion(self, js_file, content, project_path):
        """Procesa la conversión con el contenido filtrado dentro del proyecto seleccionado"""
        try:
            self._recording_meta = self._load_recording_meta(js_file)
            # 1. Copiar archivos de soporte primero
            self._copy_support_files(project_path)
            
            # 2. Generar archivos de conversión
            base_name = os.path.splitext(os.path.basename(js_file))[0]
            class_name = base_name.capitalize() + "Page"
            
            # Estructura de directorios dentro del proyecto
            project_dirs = {
                'features': os.path.join(project_path, "features"),
                'steps': os.path.join(project_path, "features", "steps"),
                'pages': os.path.join(project_path, "pages"),
                'resources': os.path.join(project_path, "resources", "data"),
                'outputs': os.path.join(project_path, "outputs"),
                'utils': os.path.join(project_path, "utils")
            }
            
            # Crear directorios si no existen
            for dir_path in project_dirs.values():
                os.makedirs(dir_path, exist_ok=True)

            # Definir rutas de archivos dentro del proyecto
            file_paths = {
                'feature': os.path.join(project_dirs['features'], f"{base_name}.feature"),
                'steps': os.path.join(project_dirs['steps'], f"{base_name}_steps.py"),
                'page': os.path.join(project_dirs['pages'], f"{base_name}_page.py"),
                'json': os.path.join(project_dirs['resources'], f"{base_name}.json")
            }

            # Verificar archivos existentes
            existing_files = {name: path for name, path in file_paths.items() if os.path.exists(path)}
            response = True  # True=sobrescribir/crear, False=no sobrescribir, None=cancelar
            created_files = []
            
            if existing_files:
                file_list = "\n".join([f"- {name}: {os.path.basename(path)}" for name, path in existing_files.items()])
                response = self.ui.yes_no_cancel(
                    "Archivos existentes",
                    f"Los siguientes archivos ya existen en el proyecto:\n\n{file_list}\n\n"
                    "¿Qué deseas hacer?\n"
                    "• 'Sí': Sobrescribir todos\n"
                    "• 'No': Continuar sin sobrescribir\n"
                    "• 'Cancelar': Abortar conversión"
                )
                
                if response is None:  # Cancelar
                    return
                elif not response:    # No sobrescribir
                    file_paths = {name: path for name, path in file_paths.items() if not os.path.exists(path)}
                    if not file_paths:
                        self.ui.info("Información", "Todos los archivos ya existen en el proyecto y no se sobrescribirán.")
                        return

            # Contenido del feature usado para steps: debe ser el mismo que se escribe (nuevo o existente).
            feature_content_for_steps = ""

            # Procesar feature file
            if 'feature' in file_paths:
                feature_exists = 'feature' in existing_files and not response
                existing_content = ""
                
                if feature_exists:
                    try:
                        with open(file_paths['feature'], "r", encoding="utf-8") as f:
                            existing_content = f.read()
                    except Exception as e:
                        self.ui.warning("Advertencia", f"No se pudo leer el feature existente:\n{str(e)}")
                        feature_exists = False

                if not feature_exists:
                    try:
                        feature_content = self._generate_bdd_feature(content, base_name)
                    except BDDUserCancelled:
                        self.ui.info("Conversión cancelada", "Se canceló la generación del escenario BDD.")
                        return
                    with open(file_paths['feature'], "w", encoding="utf-8") as f:
                        f.write(feature_content)
                    feature_content_for_steps = feature_content
                else:
                    feature_content_for_steps = existing_content

            # Generar steps file
            if 'steps' in file_paths:
                steps_content = self._generate_adaptive_steps(
                    base_name, 
                    class_name, 
                    content, 
                    feature_content_for_steps,
                )
                with open(file_paths['steps'], "w", encoding="utf-8") as f:
                    f.write(steps_content)

            # Generar page object
            if 'page' in file_paths:
                page_content = self._generate_page_object(class_name, content)
                with open(file_paths['page'], "w", encoding="utf-8") as f:
                    f.write(page_content)

            # Generar JSON data
            if 'json' in file_paths:
                json_content = self._generate_json_data(content)
                with open(file_paths['json'], "w", encoding="utf-8") as f:
                    f.write(json_content)

            # Mensaje final
            created_files = list(file_paths.keys())
            success_msg = f"Proyecto configurado correctamente en:\n{os.path.basename(project_path)}\n\n"
            success_msg += "Se incluyeron:\n"
            success_msg += "- Archivos de soporte completos (environment, utils, resources)\n"
            success_msg += "- Archivos generados:\n"
            success_msg += "\n".join([f"  • {os.path.basename(file_paths[name])}" for name in created_files])
            
            self.ui.info("Éxito", success_msg)

        except Exception as e:
            error_msg = f"Error al configurar el proyecto {os.path.basename(project_path)}:\n{str(e)}"
            self.ui.error("Error", error_msg)
            
            # Limpiar archivos creados parcialmente
            if 'file_paths' in locals():
                for file_type, path in file_paths.items():
                    if file_type in created_files and os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
        
    def _copy_support_files(self, project_path):
        """Copia toda la estructura de soporte al proyecto destino"""
        try:
            # 1. Copiar environment.py a features/
            # Modelo final: environment y utils provienen de resources/behave
            src_env = os.path.join(self.base_dir, "resources", "behave", "features", "environment.py")
            dst_env = os.path.join(project_path, "features", "environment.py")
            shutil.copy2(src_env, dst_env)
            
            # 2. Crear carpeta outputs vacía
            os.makedirs(os.path.join(project_path, "outputs"), exist_ok=True)
            
            # 3. Copiar recursos PDF
            src_resources = os.path.join(self.base_dir, "resources", "behave", "resources", "resourcesPDF")
            dst_resources = os.path.join(project_path, "resources", "resourcesPDF")
            if os.path.exists(src_resources):
                shutil.copytree(src_resources, dst_resources, dirs_exist_ok=True)
            
            # 4. Copiar utils completa
            src_utils = os.path.join(self.base_dir, "resources", "behave", "utils")
            dst_utils = os.path.join(project_path, "utils")
            if os.path.exists(src_utils):
                shutil.copytree(src_utils, dst_utils, dirs_exist_ok=True)
                
        except Exception as e:
            self.ui.warning("Advertencia", 
                f"No se pudieron copiar algunos archivos de soporte:\n{str(e)}\n"
                "El proyecto puede necesitar configuración manual adicional.")            
            
    def _generate_bdd_feature(self, script_content, base_name):
        """Genera feature con el formato exacto solicitado usando nombres de elementos"""
        if script_content is None:
            script_content = ""
        
        lines = script_content.split('\n')
        actions = []
        
        for line in lines:
            line = line.strip()
            try:
                if "page.goto(" in line:
                    url_match = re.search(r'page\.goto\((["\'])(.*?)\1', line)
                    if url_match:
                        url = url_match.group(2)
                        actions.append(("given", f'Acceder a la pagina "{url}"'))
                        continue  

                elif "page.click(" in line:
                    selector_match = re.search(r'page\.click\((["\'])(.*?)\1', line)
                    if selector_match:
                        selector = selector_match.group(2)
                        element_name = f"click_{self._generate_element_name(selector)}"
                        actions.append(("click", f'clic en elemento "{element_name}"'))

                elif "page.type(" in line or "page.fill(" in line:
                    type_match = re.search(r'page\.(?:type|fill)\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if type_match:
                        selector = type_match.group(2)
                        value = type_match.group(4)
                        field_name = f"enter_{self._generate_element_name(selector)}"
                        actions.append(("fill", f'Ingresar "{field_name}" con "{value}"'))

                elif "page.select(" in line:
                    select_match = re.search(r'page\.select\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if select_match:
                        selector = select_match.group(2)
                        option = select_match.group(4)
                        field_name = f"select_{self._generate_element_name(selector)}"
                        actions.append(("select", f'Seleccionar "{option}" en "{field_name}"'))

            except Exception as e:
                print(f"Error procesando línea: {line}\n{str(e)}")
                continue

        # Eliminar duplicados consecutivos
        unique_actions = []
        last_action = None
        for action in actions:
            if action != last_action:
                unique_actions.append(action)
                last_action = action
        
        if self.use_ai:
            try:
                from core import gemma_inference
                from core.bee_memory import append_correction, recent_examples_for_prompt

                if gemma_inference.is_ai_runtime_configured():
                    script_excerpt = _trim_script_for_preview(script_content)
                    temps = [0.1, 0.4]
                    examples = recent_examples_for_prompt(limit=3)
                    last_rendered: Optional[str] = None

                    for attempt in range(1, 4):
                        can_manual = attempt >= 3
                        if attempt <= 2:
                            temp = temps[attempt - 1]
                            ai_steps = gemma_inference.suggest_bdd_steps_from_actions(
                                unique_actions,
                                base_name=base_name,
                                temperature=temp,
                                few_shot_examples=examples,
                            )
                            rendered: Optional[str] = None
                            if ai_steps:
                                rendered = self._feature_text_from_ai_steps(base_name, ai_steps)
                            if not rendered:
                                rendered = self._generate_bdd_feature_heuristic_business(
                                    unique_actions, base_name
                                )
                        else:
                            rendered = last_rendered or self._generate_bdd_feature_heuristic_business(
                                unique_actions, base_name
                            )

                        last_rendered = rendered
                        review = self.ui.bdd_preview_review(
                            feature_text=rendered,
                            attempt=attempt,
                            max_attempts=3,
                            script_excerpt=script_excerpt,
                            can_manual=can_manual,
                        )
                        action = str(review.get("action") or "")
                        if action == "accept":
                            ft = str(review.get("feature_text") or rendered).strip()
                            if not ft:
                                ft = rendered
                            edited = bool(review.get("edited"))
                            if edited or ft != rendered.strip():
                                append_correction(script_snippet=script_content, feature_text=ft)
                            return ft
                        if action == "reject":
                            if attempt >= 3:
                                break
                            continue
                        if action == "use_heuristic":
                            return self._generate_bdd_feature_heuristic_business(unique_actions, base_name)

            except BDDUserCancelled:
                raise
            except Exception as e:
                print(f"BEE IA BDD: fallback heurístico: {e}")

        return self._generate_bdd_feature_heuristic_business(unique_actions, base_name)

    def _bdd_parse_actions(self, unique_actions: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Extrae URL, tokens de clic, textos de relleno y selecciones desde descripciones heurísticas."""
        start_url: Optional[str] = None
        click_tokens: List[str] = []
        fills: List[str] = []
        selects: List[str] = []

        for action_type, description in unique_actions:
            if action_type == "given":
                m = re.search(r'"([^"]+)"', description)
                if m:
                    start_url = m.group(1)
            elif action_type == "click":
                m = re.search(r'"([^"]+)"', description)
                if m:
                    click_tokens.append(m.group(1))
            elif action_type == "fill":
                m = re.search(
                    r'Ingresar\s+"[^"]+"\s+con\s+"((?:[^"\\]|\\.)*)"',
                    description,
                )
                if m:
                    fills.append(m.group(1).replace('\\"', '"'))
            elif action_type == "select":
                m = re.search(r'Seleccionar\s+"((?:[^"\\]|\\.)*)"\s+en', description)
                if m:
                    selects.append(m.group(1).replace('\\"', '"'))

        blob = " ".join(click_tokens).lower()
        return {
            "start_url": start_url,
            "click_tokens": click_tokens,
            "fills": fills,
            "selects": selects,
            "blob": blob,
            "n_clicks": len(click_tokens),
        }

    def _bdd_business_when_and_text(self, ctx: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
        """
        Un solo When, opcional And, un Then — textos en lenguaje de negocio (sin nombres técnicos).
        """
        blob = ctx["blob"]
        fills = ctx["fills"]
        selects = ctx["selects"]
        n_clicks = ctx["n_clicks"]

        nav_bits: List[str] = []
        if "prestamo" in blob or "préstamo" in blob:
            nav_bits.append("el flujo de préstamos")
        if "personal" in blob and "prestamo" in blob:
            nav_bits.append("el producto de crédito personal")
        if "modal" in blob or "aviso" in blob or "banner" in blob or "cookie" in blob:
            nav_bits.append("gestionar avisos o modales iniciales")
        if "nav_" in blob or "menu" in blob or "accordion" in blob:
            nav_bits.append("el menú y las secciones del sitio")

        if nav_bits:
            nav_phrase = " y ".join(dict.fromkeys(nav_bits))  # dedupe preserve order
            when_nav = (
                f"el usuario navega por el sitio para acceder a {nav_phrase}"
                if len(nav_bits) <= 2
                else "el usuario navega por el sitio hasta el flujo de producto deseado"
            )
        else:
            when_nav = (
                "el usuario interactúa con la interfaz para avanzar en el proceso"
                if n_clicks > 0
                else "el usuario utiliza la aplicación"
            )

        has_data = bool(fills or selects)
        if has_data:
            parts_data = []
            if fills:
                parts_data.append("el importe o cantidad indicados")
            if selects:
                parts_data.append("el plazo u opción seleccionada")
            data_phrase = " y ".join(parts_data)
            when_body = (
                f"{when_nav.capitalize()}, completa {data_phrase} y confirma para continuar en el flujo."
            )
        else:
            when_body = f"{when_nav.capitalize()} hasta completar el paso previsto."

        and_body: Optional[str] = None
        if n_clicks >= 5 and has_data:
            and_body = (
                "completa los datos del formulario y confirma la solicitud cuando el sistema lo solicite"
            )
        elif n_clicks >= 8 and not has_data:
            and_body = (
                "confirma la acción en las pantallas intermedias hasta finalizar el recorrido"
            )

        then_body = (
            "el sistema debe mostrar la confirmación o el siguiente paso del proceso "
            "sin errores de validación"
        )

        return when_body, and_body, then_body

    def _generate_bdd_feature_heuristic_business(
        self, unique_actions: List[Tuple[str, str]], base_name: str
    ) -> str:
        """Given / When / (And) / Then — máximo un And; texto orientado a negocio."""
        ctx = self._bdd_parse_actions(unique_actions)
        given_line = ""
        if ctx["start_url"]:
            try:
                netloc = urlparse(ctx["start_url"]).netloc or ctx["start_url"]
                given_line = f'    Given el usuario ingresa al sitio "{netloc}"\n'
            except Exception:
                given_line = '    Given el usuario accede al sitio web bajo prueba\n'

        when_body, and_body, then_body = self._bdd_business_when_and_text(ctx)

        lines = [
            f"Feature: {base_name}\n",
            "\n",
            "  Scenario: Flujo de negocio grabado\n",
            given_line,
            f"    When {when_body}\n",
        ]
        if and_body:
            lines.append(f"    And {and_body}\n")
        lines.append(f"    Then {then_body}\n")
        return "".join(lines)

    def _feature_text_from_ai_steps(self, base_name: str, ai_steps: List[Tuple[str, str]]) -> Optional[str]:
        """Convierte pasos IA a .feature; exige exactamente 1 When y 1 Then, ≤1 Given, ≤1 And, orden Gherkin."""
        if not ai_steps:
            return None
        given_c = sum(1 for k, _ in ai_steps if k.lower() == "given")
        when_c = sum(1 for k, _ in ai_steps if k.lower() == "when")
        and_c = sum(1 for k, _ in ai_steps if k.lower() == "and")
        then_c = sum(1 for k, _ in ai_steps if k.lower() == "then")
        if when_c != 1 or then_c != 1 or given_c > 1 or and_c > 1:
            return None
        seen = [k.lower() for k, _ in ai_steps]
        expected: List[str] = []
        if "given" in seen:
            expected.append("given")
        expected.extend(["when"])
        if "and" in seen:
            expected.append("and")
        expected.append("then")
        if seen != expected:
            return None
        lines = [f"Feature: {base_name}\n", "\n", "  Scenario: Flujo de negocio\n"]
        kw_map = {"given": "Given", "when": "When", "then": "Then", "and": "And"}
        for kw, txt in ai_steps:
            lines.append(f"    {kw_map.get(kw.lower(), 'When')} {txt}\n")
        return "".join(lines)

    def _load_recording_meta(self, js_file: str) -> Optional[Dict[str, Any]]:
        meta_path = re.sub(r"\.js$", "", js_file, flags=re.I) + "_bee_meta.json"
        if not os.path.isfile(meta_path):
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _preferred_selector_for_locator(self, selector: str) -> str:
        """Si hay metadatos de grabación y IA activa, puede preferir CSS o xpath."""
        if not self.use_ai or not self._recording_meta:
            return selector
        actions = self._recording_meta.get("actions") if isinstance(self._recording_meta, dict) else None
        if not isinstance(actions, list):
            return selector
        for rec in actions:
            if not isinstance(rec, dict):
                continue
            if rec.get("selector") != selector:
                continue
            xp = (rec.get("xpath") or "").strip()
            if not xp:
                return selector
            try:
                from core import gemma_inference

                if not gemma_inference.is_ai_runtime_configured():
                    return selector
                pref = gemma_inference.suggest_preferred_locator(
                    selector=selector,
                    xpath=xp,
                    tag=str(rec.get("tag") or ""),
                    element_id=str(rec.get("id") or ""),
                )
                if pref:
                    return pref
            except Exception:
                pass
            return selector
        return selector

    def _group_similar_actions(self, actions):
        """Agrupa acciones similares para crear steps más lógicos"""
        if not actions:
            return []
            
        grouped = []
        i = 0
        
        while i < len(actions):
            current_action = actions[i]
            
            # Detectar patrones repetitivos (como múltiples select_option)
            if "select_option" in str(current_action):
                # Contar cuántas veces se repite la misma acción
                count = 1
                while (i + count < len(actions) and 
                       actions[i + count][1] == current_action[1]):
                    count += 1
                
                if count > 1:
                    # Simplificar acciones repetitivas
                    field = re.search(r'en "(.*?)"', current_action[1])
                    if field:
                        field_name = field.group(1)
                        grouped.append(("and", f'Configurar el campo "{field_name}"'))
                    i += count
                else:
                    grouped.append(current_action)
                    i += 1
            else:
                grouped.append(current_action)
                i += 1
                
        return grouped

    def _generate_adaptive_steps(self, base_name, class_name, script_content, existing_feature=None):
        """Genera steps adaptados al feature existente o crea nuevos steps funcionales"""
        
        if existing_feature and existing_feature.strip():
            feature_steps = self._extract_steps_from_feature(existing_feature)
            if self._feature_is_business_language(feature_steps):
                return self._generate_steps_from_business_feature(
                    base_name, class_name, feature_steps, script_content
                )
            return self._generate_steps_from_feature(base_name, class_name, feature_steps, script_content)

        # Sin texto de feature: generar desde el script (reconstruye feature técnico internamente).
        return self._generate_steps_from_script(base_name, class_name, script_content)

    def _feature_is_business_language(self, feature_steps: List[Tuple[str, str]]) -> bool:
        """True si el .feature usa redacción de negocio (no pasos 'clic en elemento ...')."""
        if not feature_steps:
            return False
        for _t, desc in feature_steps:
            if "clic en elemento" in desc:
                return False
        return True

    def _extract_ordered_page_actions(self, script_content: str) -> List[Tuple[str, str, Optional[str]]]:
        """
        Orden de acciones del JS grabado alineado con nombres de método del Page Object.
        Tuplas: ("goto", url, None), ("click", method_base, None), ("fill", method_base, value), ("select", method_base, option).
        method_base sin prefijo btn_/txt_/ddl_ — se resuelve con _bdd_locator_kind_for_selector.
        """
        ordered: List[Tuple[str, str, Optional[str]]] = []
        if not script_content:
            return ordered
        for line in script_content.split("\n"):
            line = line.strip()
            try:
                if "page.goto(" in line:
                    m = re.search(r'page\.goto\((["\'])(.*?)\1', line)
                    if m:
                        ordered.append(("goto", m.group(2), None))
                    continue
                if "page.click(" in line:
                    m = re.search(r'page\.click\((["\'])(.*?)\1', line)
                    if m:
                        sel = m.group(2)
                        name = self._generate_element_name(sel)
                        ordered.append(("click", name, None))
                    continue
                if "page.type(" in line or "page.fill(" in line:
                    m = re.search(r'page\.(?:type|fill)\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if m:
                        sel, val = m.group(2), m.group(4)
                        name = self._generate_element_name(sel)
                        ordered.append(("fill", name, val))
                    continue
                if "page.select(" in line:
                    m = re.search(r'page\.select\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if m:
                        sel, opt = m.group(2), m.group(4)
                        name = self._generate_element_name(sel)
                        ordered.append(("select", name, opt))
                    continue
            except Exception:
                continue
        return ordered

    def _page_method_name(self, kind: str, base_name: str) -> str:
        """Nombres de método como en _generate_methods: click_, enter_, select_."""
        if kind == "click":
            return f"click_{base_name}"
        if kind == "fill":
            return f"enter_{base_name}"
        if kind == "select":
            return f"select_{base_name}"
        return base_name

    def _generate_steps_from_business_feature(
        self,
        base_name: str,
        class_name: str,
        feature_steps: List[Tuple[str, str]],
        script_content: str,
    ) -> str:
        """
        Feature en lenguaje de negocio: los decoradores coinciden con el .feature;
        el cuerpo ejecuta las acciones del script en orden usando el Page Object.
        """
        imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from utils.button_functions import ui_navigate
from environment import *
"""

        ordered = self._extract_ordered_page_actions(script_content)
        if not ordered:
            return imports + "\n# No se pudieron extraer acciones del script grabado.\n"

        goto_url = ""
        for kind, a, _b in ordered:
            if kind == "goto":
                goto_url = a
                break

        actions_after_goto = [x for x in ordered if x[0] != "goto"]
        n_main = sum(1 for t, _ in feature_steps if t.lower() in ("when", "and"))
        if n_main < 1:
            n_main = 1
        chunks: List[List[Tuple[str, str, Optional[str]]]] = []
        n_act = len(actions_after_goto)
        if n_act == 0:
            chunks = [[] for _ in range(n_main)]
        else:
            base = n_act // n_main
            rem = n_act % n_main
            pos = 0
            for i in range(n_main):
                sz = base + (1 if i < rem else 0)
                chunks.append(actions_after_goto[pos : pos + sz])
                pos += sz

        step_methods: List[str] = []
        last_non_and: Optional[str] = None
        step_counter = 0
        chunk_i = 0

        for step_type, description in feature_steps:
            step_counter += 1
            st = step_type.lower()
            if st in ("given", "when", "then", "and"):
                suffix = st
            else:
                suffix = "and"
            step_id = f"{step_counter:02d}_{suffix}"

            if st == "and":
                eff = last_non_and or "when"
            else:
                eff = st
                if st != "and":
                    last_non_and = st

            method_name = self._create_step_method_name(eff, description)
            esc = description.replace("\\", "\\\\").replace("'", "\\'")

            if st == "given":
                if "Acceder a la pagina" in description:
                    step_methods.append(f"""
@{eff}('Acceder a la pagina "{{url}}"')
def {method_name}(context, url):
    context.page = {class_name}(context.driver)
    ui_navigate(
        driver=context.driver,
        url=url,
        nombre_pagina="Acceder_a_la_pagina",
        usar_create_screenshot=context.generate_evidence,
        screenshot_step='{step_id}'
    )
""")
                else:
                    url_lit = goto_url or ""
                    if not url_lit:
                        m = re.search(r'"([^"]+)"', description)
                        if m:
                            host = m.group(1).strip()
                            if host and not host.startswith("http"):
                                url_lit = "https://" + host
                            else:
                                url_lit = host
                    step_methods.append(f"""
@{eff}('{esc}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    ui_navigate(
        driver=context.driver,
        url={json.dumps(url_lit)},
        nombre_pagina="inicio",
        usar_create_screenshot=context.generate_evidence,
        screenshot_step='{step_id}'
    )
""")

            elif st in ("when", "and"):
                body_lines: List[str] = [
                    f"    context.page = {class_name}(context.driver)",
                ]
                use_chunk = chunks[chunk_i] if chunk_i < len(chunks) else []
                chunk_i += 1
                for act in use_chunk:
                    ak, base, extra = act
                    if ak == "goto":
                        continue
                    meth = self._page_method_name(ak, base)
                    if ak == "click":
                        body_lines.append(
                            f"    context.page.{meth}(tomar_evidencia=context.generate_evidence, step='{step_id}')"
                        )
                    elif ak == "fill" and extra is not None:
                        ev = json.dumps(extra)
                        body_lines.append(
                            f"    context.page.{meth}({ev}, tomar_evidencia=context.generate_evidence, step='{step_id}')"
                        )
                    elif ak == "select" and extra is not None:
                        ev = json.dumps(extra)
                        body_lines.append(
                            f"    context.page.{meth}({ev}, tomar_evidencia=context.generate_evidence, step='{step_id}')"
                        )
                step_methods.append(f"""
@{eff}('{esc}')
def {method_name}(context):
{chr(10).join(body_lines)}
""")

            elif st == "then":
                step_methods.append(f"""
@{eff}('{esc}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    assert True
""")

        return imports + "\n".join(step_methods)

    def _extract_steps_from_feature(self, feature_content):
        """Extrae los steps de un feature existente"""
        steps = []
        type_consolidation = {}
        
        # Validación para evitar el error NoneType
        if feature_content is None:
            feature_content = ""
        
        lines = feature_content.split('\n')        
        
        for line in lines:
            if 'page.type' in line:
                parsed = self.parse_fill(line)
                if parsed:
                    type_consolidation[parsed['selector']] = parsed['value']
                continue
            line = line.strip()
            if line.startswith(('Given ', 'When ', 'Then ', 'And ', 'But ')):
                # Extraer el tipo de step y la descripción
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    step_type = parts[0].lower()
                    description = parts[1]
                    steps.append((step_type, description))
        
        return steps

    def _generate_steps_from_feature(self, base_name, class_name, feature_steps, script_content):
        """Genera steps usando nombres de elementos del Page Object"""
        imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from environment import *
            """

        step_methods = []
        last_non_and_step = None
        step_counter = 0

        for step_type, description in feature_steps:
            step_counter += 1

            # Sufijo para evidence/PDF (solo tipos esperados por genReport)
            if step_type in ("given", "when", "then", "and"):
                suffix = step_type
            else:
                suffix = "and"

            step_id = f"{step_counter:02d}_{suffix}"

            if step_type == "and":
                effective_step_type = last_non_and_step or "given"
            else:
                effective_step_type = step_type
                last_non_and_step = step_type

            method_name = self._create_step_method_name(effective_step_type, description)

            if "Acceder a la pagina" in description:
                step_methods.append(f"""
@{effective_step_type}('Acceder a la pagina "{{url}}"')
def {method_name}(context, url):
    context.page = {class_name}(context.driver)
    ui_navigate(
        driver=context.driver,
        url=url,
        nombre_pagina="Acceder_a_la_pagina",
        usar_create_screenshot=context.generate_evidence,
        screenshot_step='{step_id}'
    )
        """)

            elif "clic en elemento" in description and "," in description:
                click_names = re.findall(r'"(.*?)"', description)
                step_content = f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)"""
                for name in click_names:
                    step_content += (
                        f"\n    context.page.{name}(tomar_evidencia=context.generate_evidence, step='{step_id}')"
                    )
                step_methods.append(step_content)

            elif "clic en elemento" in description:
                name = re.search(r'"(.*?)"', description).group(1)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.page.{name}(tomar_evidencia=context.generate_evidence, step='{step_id}')
            """)

            elif "Ingresar" in description:
                match = re.search(r'Ingresar "(.*?)" con "(.*?)"', description)
                name, value = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.page.{name}("{value}", tomar_evidencia=context.generate_evidence, step='{step_id}')
            """)

            elif "Seleccionar" in description:
                match = re.search(r'Seleccionar "(.*?)" en "(.*?)"', description)
                option, name = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.page.{name}("{option}", tomar_evidencia=context.generate_evidence, step='{step_id}')
            """)

            elif "Verificar que se completó el flujo" in description:
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    # Verificación de completado
    assert True
        """)

        return imports + "\n".join(step_methods)

    def _generate_steps_from_script(self, base_name, class_name, script_content):
        """Genera steps directamente desde el script usando nombres de elementos"""
        feature_content = self._generate_bdd_feature(script_content, base_name)
        feature_steps = self._extract_steps_from_feature(feature_content)
            
        imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from utils.button_functions import ui_navigate
            """

        step_methods = []
        last_non_and_step = None
        step_counter = 0

        for step_type, description in feature_steps:
            step_counter += 1

            if step_type in ("given", "when", "then", "and"):
                suffix = step_type
            else:
                suffix = "and"

            step_id = f"{step_counter:02d}_{suffix}"

            if step_type == "and":
                effective_step_type = last_non_and_step or "given"
            else:
                effective_step_type = step_type
                last_non_and_step = step_type

            method_name = self._create_step_method_name(effective_step_type, description)

            if "clic en elemento" in description and "," in description:
                click_names = re.findall(r'"(.*?)"', description)
                step_content = f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)"""
                for name in click_names:
                    step_content += (
                        f"\n    context.page.{name}(tomar_evidencia=context.generate_evidence, step='{step_id}')"
                    )
                step_methods.append(step_content)

            elif "clic en elemento" in description:
                name = re.search(r'"(.*?)"', description).group(1)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.page.{name}(tomar_evidencia=context.generate_evidence, step='{step_id}')
            """)

            elif "Ingresar" in description:
                match = re.search(r'Ingresar "(.*?)" con "(.*?)"', description)
                name, value = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.page.{name}("{value}", tomar_evidencia=context.generate_evidence, step='{step_id}')
            """)

            elif "Seleccionar" in description:
                match = re.search(r'Seleccionar "(.*?)" en "(.*?)"', description)
                option, name = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.page.{name}("{option}", tomar_evidencia=context.generate_evidence, step='{step_id}')
            """)

            elif "Acceder a la pagina" in description:
                step_methods.append(f"""
@{effective_step_type}('Acceder a la pagina "{{url}}"')
def {method_name}(context, url):
    context.page = {class_name}(context.driver)
    ui_navigate(
        driver=context.driver,
        url=url,
        nombre_pagina="Acceder_a_la_pagina",
        usar_create_screenshot=context.generate_evidence,
        screenshot_step='{step_id}'
    )
        """)

            elif "Verificar que se completó el flujo" in description:
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    # Verificación de completado
    assert True
        """)

        return imports + "\n".join(step_methods)

    def _extract_script_actions(self, script_content):
        """Extrae todas las acciones del script en orden"""
        actions = []
        lines = script_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(action in line for action in ['.click()', '.fill(', '.select_option(']):
                actions.append(line)
        
        return actions

    def _find_corresponding_click_action(self, description, script_actions, step_index):
        """Encuentra la acción de click correspondiente en el script"""
        click_actions = [action for action in script_actions if '.click()' in action]
        if step_index < len(click_actions):
            return click_actions[step_index]
        return None

    def _find_corresponding_fill_action(self, description, script_actions, step_index):
        """Encuentra la acción de fill correspondiente en el script"""
        fill_actions = [action for action in script_actions if '.fill(' in action]
        if step_index < len(fill_actions):
            return fill_actions[step_index]
        return None

    def _find_corresponding_select_action(self, description, script_actions, step_index):
        """Encuentra la acción de select correspondiente en el script"""
        select_actions = [action for action in script_actions if '.select_option(' in action]
        if step_index < len(select_actions):
            return select_actions[step_index]
        return None

    def _generate_method_call_from_action(self, action):
        """Genera la llamada al método del page object basada en la acción del script"""
        if '.click()' in action:
            if 'get_by_role(' in action:
                name_match = re.search(r'name="(.*?)"', action)
                if name_match:
                    method_name = name_match.group(1).lower().replace(' ', '_')
                    return f"context.page.click_{method_name}()"
            elif 'locator(' in action:
                selector_match = re.search(r'locator\("(.*?)"\)', action)
                if selector_match:
                    selector = selector_match.group(1).replace('#', '')
                    return f"context.page.click_{selector}()"
        elif '.fill(' in action:
            selector_match = re.search(r'locator\("(.*?)"\)', action)
            value_match = re.search(r'fill\("(.*?)"\)', action)
            if selector_match and value_match:
                selector = selector_match.group(1).replace('#', '')
                value = value_match.group(1)
                return f"context.page.enter_{selector}('{value}')"
        elif '.select_option(' in action:
            selector_match = re.search(r'locator\("(.*?)"\)', action)
            option_match = re.search(r'select_option\("(.*?)"\)', action)
            if selector_match and option_match:
                selector = selector_match.group(1).replace('#', '')
                option = option_match.group(1)
                return f"context.utils.select_from_dropdown(context.page.select_{selector}, '{option}')"
        
        return "# TODO: Implementar método correspondiente"

    def _create_step_method_name(self, step_type, description):
        """Crea un nombre de método único para el step"""
        clean_desc = re.sub(r'[^a-zA-Z0-9\s]', '', description)
        words = clean_desc.split()[:4]  # Tomar solo las primeras 4 palabras
        method_name = f"step_{'_'.join(words).lower()}"
        return re.sub(r'[^a-zA-Z0-9_]', '', method_name)

    def _generate_json_data(self, script_content):
        """Genera un JSON básico con datos extraídos del script"""
        data = {  
            "url": [],
            "elements": [],
            "inputs": []
        }

        # Extraer URL - compatible con comillas simples y dobles
        url = re.findall(r'page\.goto\([\'"](.*?)[\'"]\)', script_content)
        if url:
            data["url"] = url

        # Extraer elementos clickeables - múltiples patrones
        clicks = []
        # Patrón para page.click('selector')
        clicks += re.findall(r'page\.click\([\'"](.*?)[\'"]\)', script_content)
        # Patrón para page.locator('selector').click()
        clicks += re.findall(r'page\.locator\([\'"](.*?)[\'"]\)\.click\(\)', script_content)
        # Patrón para selectores con atributos como [aria-label="Close"]
        clicks += re.findall(r'page\.click\(([^\'"][^)]*)\)', script_content)  # Para selectores sin comillas
        
        if clicks:
            data["elements"] = list(set(clicks))  # Eliminar duplicados

        # Extraer inputs - múltiples patrones
        fills = []
        # Patrón para page.fill('selector', 'value')
        fills += re.findall(r'page\.(?:type|fill)\([\'"](.*?)[\'"],\s*[\'"](.*?)[\'"]\)', script_content)
        # Patrón para page.locator('selector').fill('value')
        fills += re.findall(r'page\.locator\([\'"](.*?)[\'"]\)\.(?:type|fill)\([\'"](.*?)[\'"]\)', script_content)
        # Patrón para selectores sin comillas
        fills += re.findall(r'page\.(?:type|fill)\(([^\'"][^,]*),\s*[\'"](.*?)[\'"]\)', script_content)
        
        if fills:
            data["inputs"] = [{"selector": selector, "value": value} for selector, value in fills]

        return json.dumps(data, indent=4, ensure_ascii=False)

    def _generate_feature(self, script_content, base_name):
        lines = script_content.split('\n')
        feature_lines = [
            f"Feature: {base_name.replace('_', ' ').title()}\n",
            "\n",
            "  Scenario: Flujo grabado\n"
        ]

        for line in lines:
            line = line.strip()
            if "page.goto(" in line:
                url = re.search(r'"(.*?)"', line)
                if url:
                    feature_lines.append(f'    Given I navigate to "{url.group(1)}"\n')
            elif "page.click(" in line:
                target = re.search(r'"(.*?)"', line)
                if target:
                    feature_lines.append(f'    When I click on "{target.group(1)}"\n')
            elif "page.fill(" in line:
                parts = re.findall(r'"(.*?)"', line)
                if len(parts) == 2:
                    feature_lines.append(f'    And I fill "{parts[0]}" with "{parts[1]}"\n')
            elif "page.locator(" in line:
                # Manejar selectores más complejos
                pass

        return ''.join(feature_lines)        

    def _generate_page_object(self, class_name, script_content):
        """Genera un page object"""
        # Modelo nuevo: usar button_functions (no ElementUtils)
        imports = """from utils.button_functions import *
        """

        class_template = f"""
class {class_name}:
    def __init__(self, driver):
        self.driver = driver

        # Locators
{self._generate_locators(script_content)}

    # Methods
{self._generate_methods(script_content)}

    # para dar click en botones de permisos, por texto
    # def click_tab(self):

    #     # ===== utilidades =====
    #     SP_BUTTON_PATTERNS = [
    #         r".*Permitir mientras visitas el sitio.*",
    #         r".*Permitir.*",
    #     ]
    #     EN_BUTTON_PATTERNS = [
    #         r".*Allow while visiting this site.*",
    #         r".*Allow.*",
    #     ]
       
    #     print("si entro")
    #     # 1. Buscar ventanas abiertas con título que contenga "Chrome"
    #     wins = Desktop(backend="uia").windows()
    #     chrome_windows = [w for w in wins if "Chrome" in (w.window_text() or "")]

    #     if not chrome_windows:
    #         raise RuntimeError("No encontré una ventana de Chrome abierta")

    #     # 2. Conectar a la primera ventana encontrada
    #     app = Application(backend="uia").connect(handle=chrome_windows[0].handle)
    #     win = app.window(handle=chrome_windows[0].handle)

    #     # 3. Traer al frente y enviar teclas
    #     win.set_focus()
    #     time.sleep(1)

    #     t0 = time.time()
    #     patterns = [re.compile(p, re.IGNORECASE) for p in (SP_BUTTON_PATTERNS + EN_BUTTON_PATTERNS)]
    #     while time.time() - t0 < 5:
    #         try:
    #             # Busca botones expuestos por UIA
    #             for btn in win.descendants(control_type="Button"):
    #                 name = (btn.window_text() or "").strip()
    #                 if not name and isinstance(btn.element_info, UIAElementInfo):
    #                     name = (btn.element_info.name or "").strip()
    #                 if not name:
    #                     continue
    #                 if any(rx.match(name) for rx in patterns):
                       
    #                     ButtonWrapper(btn.element_info).click_input()
    #                     return True
    #         except Exception:
    #             pass
    #         time.sleep(0.2)

    """
        return imports + class_template
    
    def _generate_element_name(self, selector):
        """Genera un nombre consistente para elementos a partir del selector"""
        # Primero eliminamos acentos si los hubiera
        clean_selector = self._remove_accents(selector)
        
        # Si es un selector XPath (comienza con /)
        if clean_selector.startswith('/'):
            # Tomamos el último segmento del XPath
            segments = [s for s in clean_selector.split('/') if s]
            if segments:
                last_segment = segments[-1]
                # Si el último segmento es un nombre de etiqueta (como "span")
                if not last_segment.startswith(('@', '[')):
                    name = last_segment
                else:
                    # Si es un atributo o algo más complejo, usamos "xpath_element"
                    name = 'xpath_element'
            else:
                name = 'xpath_root'
        # Si es un selector CSS por id (#)
        elif clean_selector.startswith('#'):
            name = clean_selector[1:]  # Eliminamos el #
        # Si es un selector por clase (.)
        elif clean_selector.startswith('.'):
            name = clean_selector[1:]  # Eliminamos el .
        # Si es un selector de atributo ([...])
        elif clean_selector.startswith('['):
            name = clean_selector.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
        # Si es una etiqueta HTML (a, img, etc.)
        else:
            name = clean_selector
        
        # Reemplazamos caracteres especiales conservando guiones bajos
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Reemplazamos múltiples guiones bajos por uno solo
        name = re.sub(r'_{2,}', '_', name)
        
        # Eliminamos guiones bajos al inicio y final
        name = name.strip('_')
        
        # Convertimos a minúsculas
        name = name.lower()
        
        # Aseguramos que no empiece con número
        if name and name[0].isdigit():
            name = f"el_{name}"
        
        return name

    def _remove_accents(self, text):
        """Elimina acentos de un texto"""
        replacements = (
            ("á", "a"),
            ("é", "e"),
            ("í", "i"),
            ("ó", "o"),
            ("ú", "u"),
            ("Á", "A"),
            ("É", "E"),
            ("Í", "I"),
            ("Ó", "O"),
            ("Ú", "U"),
        )
        for a, b in replacements:
            text = text.replace(a, b)
        return text    
        
    def _escape_xpath_for_python_string(self, xpath: str) -> str:
        """
        Escapa comillas dobles para embedear XPath dentro de una string Python con ".
        """
        return (xpath or "").replace("\\", "\\\\").replace('"', '\\"')

    def _css_token_to_xpath(self, token: str) -> str:
        """
        Convierte un token CSS simple (ej: '#id', '.cls', 'div.cls', 'li:nth-child(3)', 'input[data-x=\"y\"]')
        a un fragmento XPath sin prefijo //.
        Best-effort: no soporta todo CSS, solo lo más común generado por grabaciones.
        """
        token = (token or "").strip()
        if not token:
            return "*"

        # Tag (si existe)
        tag_match = re.match(r"^([a-zA-Z][a-zA-Z0-9_-]*)", token)
        tag = tag_match.group(1) if tag_match else "*"

        # id / class / nth-child / attrs
        id_match = re.search(r"#([a-zA-Z0-9_-]+)", token)
        classes = re.findall(r"\.([a-zA-Z0-9_-]+)", token)
        nth_match = re.search(r":nth-child\((\d+)\)", token)

        # Attr selectors: [attr='value'] or [attr="value"]
        attr_matches = re.findall(r"\[\s*([a-zA-Z0-9_-]+)\s*=\s*([\"'])(.*?)\2\s*\]", token)

        predicates = []
        if id_match:
            predicates.append(f"@id='{id_match.group(1)}'")

        for cls in classes:
            # evitar match parcial: clase exacta como palabra
            predicates.append(
                "contains(concat(' ', normalize-space(@class), ' '), ' " + cls + " ')"
            )

        if nth_match:
            predicates.append(f"position()={int(nth_match.group(1))}")

        for attr_name, _q, attr_val in attr_matches:
            predicates.append(f"@{attr_name}='{attr_val}'")

        # Si el token era solo '#id' o '.cls', el tag inicial puede ser '*', que está bien.
        if predicates:
            return f"{tag}[{' and '.join(predicates)}]"
        return tag

    def _selector_to_xpath(self, selector: str) -> str:
        """
        Convierte selectores CSS (best-effort) o XPath ya existentes a XPath string usable por button_functions.
        """
        sel = (selector or "").strip()
        if not sel:
            return "//*"

        if sel.startswith("xpath="):
            sel = sel[len("xpath="):].strip()

        # Si ya es XPath
        if sel.startswith("//") or sel.startswith("(") or sel.startswith(".//"):
            return sel

        # Combinadores: primero childs con '>'
        if ">" in sel:
            parts = [p.strip() for p in re.split(r"\s*>\s*", sel) if p.strip()]
            xps = [self._css_token_to_xpath(p) for p in parts]
            xpath = '//' + '/'.join(xps)
            return xpath

        # Descendientes por whitespace
        tokens = [t.strip() for t in re.split(r"\s+", sel) if t.strip()]
        if len(tokens) > 1:
            xps = [self._css_token_to_xpath(t) for t in tokens]
            xpath = '//'.join([''] + xps)  # => //a//b//c
            return xpath

        # Token único
        xpath = self._css_token_to_xpath(sel)
        if not xpath.startswith("/"):
            xpath = "//" + xpath
        return xpath

    def _generate_locators(self, script_content):
        """Extrae y nombra los locators de forma descriptiva manteniendo coherencia"""
        locators = set()
        
        # Extraer todos los selectores únicos de diferentes acciones
        all_selectors = set()
        
        # Clicks con diferentes patrones
        all_selectors.update(re.findall(r'page\.click\(["\'](.*?)["\']\)', script_content) or [])
        all_selectors.update(re.findall(r'page\.locator\(["\'](.*?)["\']\)\.click\(\)', script_content) or [])
        
        # Fills/types
        all_selectors.update(re.findall(r'page\.(?:type|fill)\(["\'](.*?)["\']', script_content) or [])
        all_selectors.update(re.findall(r'page\.locator\(["\'](.*?)["\']\)\.(?:type|fill)\(', script_content) or [])
        
        # Selects
        all_selectors.update(re.findall(r'page\.select\(["\'](.*?)["\']', script_content) or [])
        all_selectors.update(re.findall(r'page\.locator\(["\'](.*?)["\']\)\.select_option\(', script_content) or [])
        
        locator_lines = []
        
        # Procesar todos los selectores
        for selector in all_selectors:
            if not selector:
                continue

            use_sel = self._preferred_selector_for_locator(selector)
            name = self._generate_element_name(selector)
            xpath = self._selector_to_xpath(use_sel)
            
            # Determinar tipo de elemento
            if any(f"page.type('{selector}'" in line or 
                f"page.fill('{selector}'" in line or
                f'page.type("{selector}"' in line or
                f'page.fill("{selector}"' in line 
                for line in script_content.split('\n')):
                locator_type = "txt"
            elif any(f"page.select('{selector}'" in line or 
                    f'page.select("{selector}"' in line or
                    f"select_option('{selector}'" in line or
                    f'select_option("{selector}"' in line
                    for line in script_content.split('\n')):
                locator_type = "ddl"
            else:
                locator_type = "btn"
            
            xpath_escaped = self._escape_xpath_for_python_string(xpath)
            locator_lines.append(f'        self.{locator_type}_{name} = "{xpath_escaped}"')
        
        return "\n".join(locator_lines)    

    def _generate_methods(self, script_content):
        """Genera métodos manteniendo coherencia con los locators y asegurando todas las acciones"""
        method_lines = []
        generated_methods = set()
        
        # Extraer todos los clicks
        click_selectors = set(re.findall(r'page\.click\(["\'](.*?)["\']\)', script_content) or [])
        
        # Extraer todos los fills/types
        fill_selectors = set()
        fill_matches = re.finditer(r'page\.(?:type|fill)\(["\'](.*?)["\']', script_content)
        for match in fill_matches:
            fill_selectors.add(match.group(1))
        
        # Extraer todos los selects
        select_selectors = set(re.findall(r'page\.select\(["\'](.*?)["\']', script_content) or [])
        
        # Generar métodos para clicks
        for selector in click_selectors:
            name = self._generate_element_name(selector)
            method_key = f"click_{name}"
            
            if method_key not in generated_methods:
                if selector in fill_selectors:
                    locator_type = "txt"
                elif selector in select_selectors:
                    locator_type = "ddl"
                else:
                    locator_type = "btn"
                
                method_lines.append(f"""
    def {method_key}(self, tomar_evidencia=False, step=None):
        \"\"\"Hace click en el elemento {selector}\"\"\"
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.{locator_type}_{name},
            accion="click",
            nombre_elemento="{method_key}",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
                """)
                generated_methods.add(method_key)
        
        # Generar métodos para fills/types
        for selector in fill_selectors:
            name = self._generate_element_name(selector)
            method_key = f"enter_{name}"
            
            if method_key not in generated_methods:
                method_lines.append(f"""
    def {method_key}(self, text, tomar_evidencia=False, step=None):
        \"\"\"Escribe texto en el campo {selector}\"\"\"
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.txt_{name},
            accion="insertTxt",
            nombre_elemento="{method_key}",
            valor=text,
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
                """)
                generated_methods.add(method_key)
        
        # Generar métodos para selects (nativos <select>)
        for selector in select_selectors:
            name = self._generate_element_name(selector)
            select_method = f"select_{name}"

            if select_method not in generated_methods:
                method_lines.append(f"""
    def {select_method}(self, option_text, tomar_evidencia=False, step=None):
        \"\"\"Selecciona opción en dropdown {selector}\"\"\"
        ui_select_native_dropdown(
            driver=self.driver,
            xPath_elemento=self.ddl_{name},
            valor_seleccion=str(option_text),
            tipo_seleccion="value",
            nombre_elemento="{select_method}",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
                """)
                generated_methods.add(select_method)
        
        return "\n".join(method_lines) if method_lines else "    # No se generaron métodos"

    def _generate_steps(self, base_name, class_name):
        """Genera los steps de behave con el nuevo formato para selects"""
        # Método legacy (no usado por el flujo principal). Eliminado ElementUtils.
        return f"""from behave import *
from pages.{base_name}_page import {class_name}

@given('I navigate to "{{url}}"')
def step_navigate(context, url):
    context.page = {class_name}(context.driver)
    context.driver.get(url)

@when('I click on "{{selector}}"')
def step_click(context, selector):
    context.page = {class_name}(context.driver)
    # TODO: Resolver selector -> nombre de método de Page Object
    assert True

@when('I fill "{{field}}" with "{{text}}"')
def step_fill(context, field, text):
    context.page = {class_name}(context.driver)
    # TODO: Resolver field -> nombre de método de Page Object
    assert True

@when('I select "{{option}}" from "{{dropdown}}"')
def step_select(context, option, dropdown):
    context.page = {class_name}(context.driver)
    # TODO: Resolver dropdown -> nombre de método de Page Object
    assert True
    """
