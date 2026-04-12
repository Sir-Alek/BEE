# step_by_step_converter.py
import os
import re
import json
import shutil
import time

from ui.interfaces import IUI


class PuppeteerToStepByStepConverter:
    def __init__(self, base_dir, ui: IUI):
        self.base_dir = base_dir
        from core.bee_paths import behave_projects_dir, step_by_step_dir

        self.projects_dir = str(behave_projects_dir())
        self.step_by_step_dir = str(step_by_step_dir())
        self.selected_actions = []
        self.ui = ui
        os.makedirs(self.step_by_step_dir, exist_ok=True)

    def convert_script(self):
        """Convierte el script grabado (JS) a test step by step"""
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
        self._select_script(project_path, project_name)

    def _select_script(self, project_path, project_name: str):
        """Selecciona el script dentro del proyecto"""
        scripts_dir = os.path.join(project_path, "scripts")
        
        # Verificar si existe la carpeta de scripts
        if not os.path.exists(scripts_dir):
            self.ui.error("Error", "No se encontró la carpeta 'scripts' en el proyecto seleccionado.")
            return
            
        # Obtener lista de archivos JS en la carpeta scripts
        js_files = [f for f in os.listdir(scripts_dir) if f.endswith('.js')]
        
        if not js_files:
            self.ui.error("Error", "No se encontraron archivos JavaScript (.js) en la carpeta 'scripts' del proyecto.")
            return

        selected_file = self.ui.pick_script(sorted(js_files), project_name)
        if not selected_file:
            return
        self._process_script(project_path, selected_file)

    def _process_script(self, project_path, selected_file):
        """Procesa el script seleccionado"""
        js_file = os.path.join(project_path, "scripts", selected_file)

        try:
            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content or content.strip() == "":
                content = "// Archivo vacío"

            actions = self._extract_all_actions(content)
            if not self._show_action_selection(actions):
                return

            filtered_content = self._filter_content_by_actions(content, self.selected_actions)
            self._generate_step_by_step_test(js_file, filtered_content, project_path)

        except Exception as e:
            self.ui.error("Error", f"No se pudo convertir:\n{str(e)}")

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

                elif "page.waitForSelector(" in line or "page.waitFor(" in line:
                    wait_match = re.search(r'page\.waitFor(?:Selector)?\((["\'])(.*?)\1', line)
                    if wait_match:
                        selector = wait_match.group(2)
                        action = ("Espera", f'Esperar elemento: {selector}')

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
    
    def _generate_steps_json(self, test_name, actions, project_name=None):
        """Genera un archivo JSON con los pasos del test en la estructura del proyecto step by step"""
        try:
            # Determinar la ruta base para info_steps
            if project_name:
                # Dentro de la estructura del proyecto step by step
                info_steps_dir = os.path.join(self.step_by_step_dir, "proyectos", project_name, "resources", "info_steps")
            else:
                # En la raíz de step_by_step (para cuando no se reorganiza)
                info_steps_dir = os.path.join(self.step_by_step_dir, "resources", "info_steps")
            
            # Crear directorio info_steps si no existe
            os.makedirs(info_steps_dir, exist_ok=True)
            
            # Construir la estructura de pasos
            steps = []
            step_number = 1
            
            for action in actions:
                step_info = self._extract_step_info(action, step_number)
                if step_info:
                    steps.append(step_info)
                    step_number += 1
            
            # Crear el objeto JSON completo
            test_info = {
                "test_name": test_name,
                "total_steps": len(steps),
                "steps": steps,
                "generated_date": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Guardar el archivo JSON
            json_filename = f"{test_name}.json"
            json_path = os.path.join(info_steps_dir, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(test_info, f, indent=4, ensure_ascii=False)
            
            return json_path
            
        except Exception as e:
            print(f"Error generando JSON de pasos: {str(e)}")
            return None

    def _extract_step_info(self, action, step_number):
        """Extrae información del paso para el JSON basado en el tipo de acción"""
        action_type = action[0]
        
        step_info = {
            "step_number": step_number,
            "action_type": action_type,
            "description": "",
            "element": "",
            "value": ""
        }
        
        if action_type == 'goto':
            url = action[1]
            step_info["description"] = f"Navegar a URL: {url}"
            step_info["value"] = url
            
        elif action_type == 'click':
            selector = action[1]
            step_info["description"] = f"Click en elemento: {selector}"
            step_info["element"] = selector
            
        elif action_type == 'fill':
            selector, value = action[1], action[2]
            step_info["description"] = f"Rellenar campo {selector} con: {value}"
            step_info["element"] = selector
            step_info["value"] = value
            
        elif action_type == 'select':
            selector, option = action[1], action[2]
            step_info["description"] = f"Seleccionar opción {option} en: {selector}"
            step_info["element"] = selector
            step_info["value"] = option
            
        elif action_type == 'wait':
            selector = action[1]
            step_info["description"] = f"Esperar elemento: {selector}"
            step_info["element"] = selector
        
        return step_info
    
    def _generate_step_by_step_test(self, js_file, script_content, project_path):
        """Genera el test step by step y ofrece reorganizar el proyecto"""
        try:
            base_name = os.path.splitext(os.path.basename(js_file))[0]
            test_name = f"test_{base_name}"
            
            # Extraer acciones para el JSON
            actions_for_json = self._extract_actions_for_test(script_content)
            
            # Preguntar primero si desea reorganizar el proyecto
            reorganize = self.ui.yes_no(
                "Reorganizar proyecto",
                f"¿Deseas reorganizar el proyecto '{os.path.basename(project_path)}' para step by step?\n\n"
                "Esto moverá los scripts y grabaciones a la estructura de step by step."
            )
            
            if reorganize:
                # Crear estructura de carpetas en el nuevo proyecto
                project_name = os.path.basename(project_path)
                new_project_path = os.path.join(self.step_by_step_dir, "proyectos", project_name)
                new_tests_dir = os.path.join(new_project_path, "tests")
                os.makedirs(new_tests_dir, exist_ok=True)
                
                # Generar el test directamente en la carpeta de tests
                output_file = os.path.join(new_tests_dir, f"{test_name}.py")
                
                # Generar el JSON dentro de la estructura del proyecto
                json_path = self._generate_steps_json(test_name, actions_for_json, project_name)
            else:
                # Generar el test en la carpeta step_by_step
                output_file = os.path.join(self.step_by_step_dir, f"{test_name}.py")
                
                # Generar el JSON en la raíz de step_by_step
                json_path = self._generate_steps_json(test_name, actions_for_json)
            
            # Verificar si el archivo ya existe
            if os.path.exists(output_file):
                response = self.ui.yes_no(
                    "Archivo existente",
                    f"El archivo {os.path.basename(output_file)} ya existe.\n\n¿Deseas sobrescribirlo?"
                )
                if not response:
                    return
            
            # Generar contenido del test
            test_content = self._generate_test_case_content(script_content, base_name)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(test_content)
            
            if reorganize:
                self._reorganize_project(project_path, base_name, output_file)
                success_message = (f"Proyecto reorganizado exitosamente:\n"
                                f"• Test: {output_file}\n"
                                f"• JSON de pasos: {json_path}" if json_path else "")
            else:
                success_message = (f"Test step by step generado en:\n{output_file}\n\n"
                                f"JSON de pasos generado en:\n{json_path}" if json_path else "")
            
            self.ui.info("Éxito", success_message)
                    
        except Exception as e:
            self.ui.error("Error", f"Error al generar test step by step:\n{str(e)}")
            
    def _copy_support_files_to_step_by_step(self, project_path):
        """Copia toda la estructura de soporte al proyecto step by step"""
        try:
            # 1. Crear carpeta outputs vacía
            os.makedirs(os.path.join(project_path, "outputs", "evidences"), exist_ok=True)
            
            # 2. Copiar recursos
            src_resources = os.path.join(self.base_dir, "resources", "step_by_step", "resources", "resourcesPDF")
            dst_resources = os.path.join(project_path, "resources", "resourcesPDF")
            if os.path.exists(src_resources):
                shutil.copytree(src_resources, dst_resources, dirs_exist_ok=True)
            
            # 3. Copiar utils completa
            src_utils = os.path.join(self.base_dir, "resources", "step_by_step", "utils")
            dst_utils = os.path.join(project_path, "utils")
            if os.path.exists(src_utils):
                shutil.copytree(src_utils, dst_utils, dirs_exist_ok=True)
                
        except Exception as e:
            self.ui.warning("Advertencia", 
                f"No se pudieron copiar algunos archivos de soporte:\n{str(e)}\n"
                "El proyecto puede necesitar configuración manual adicional.")

    def _reorganize_project(self, project_path, base_name, test_file_path):
        """Reorganiza el proyecto para step by step moviendo solo archivos relacionados"""
        try:
            # Obtener el nombre del proyecto desde la ruta
            project_name = os.path.basename(project_path)
            
            # Ruta del nuevo proyecto en step_by_step/proyectos
            new_project_path = os.path.join(self.step_by_step_dir, "proyectos", project_name)
            
            # Crear estructura de carpetas en el nuevo proyecto
            new_scripts_dir = os.path.join(new_project_path, "scripts")
            new_recordings_dir = os.path.join(new_project_path, "grabaciones")
            new_tests_dir = os.path.join(new_project_path, "tests")
            
            os.makedirs(new_scripts_dir, exist_ok=True)
            os.makedirs(new_recordings_dir, exist_ok=True)
            os.makedirs(new_tests_dir, exist_ok=True)
            
            # Mover el script específico que se está convirtiendo
            old_script_path = os.path.join(project_path, "scripts", f"{base_name}.js")
            script_timestamp = None
            
            if os.path.exists(old_script_path):
                # Obtener timestamp antes de mover
                script_timestamp = os.path.getctime(old_script_path)
                new_script_path = os.path.join(new_scripts_dir, f"{base_name}.js")
                shutil.copy(old_script_path, new_script_path)
            
            # Buscar y mover grabaciones de video relacionadas
            self._move_related_recordings(project_path, new_recordings_dir, base_name, script_timestamp)
            
            # Mover el test a la carpeta tests (si no está ya ahí)
            if not test_file_path.startswith(new_tests_dir):
                test_file_name = os.path.basename(test_file_path)
                new_test_file = os.path.join(new_tests_dir, test_file_name)
                shutil.move(test_file_path, new_test_file)
            
            # COPIAR ARCHIVOS DE SOPORTE
            self._copy_support_files_to_step_by_step(new_project_path)
            
            # Verificar si el proyecto original está vacío y eliminarlo si es así
            self._cleanup_original_project(project_path)
            
            self.ui.info("Éxito", 
                f"Proyecto reorganizado exitosamente:\n"
                f"• Proyecto: {new_project_path}\n"
                f"• Script: {base_name}.js\n"
                f"• Test: test_{base_name}.py\n\n"
                f"Los archivos se han organizado en las carpetas:\n"
                f"• scripts/: Contiene el script de grabación\n"
                f"• grabaciones/: Contiene las grabaciones relacionadas\n"
                f"• tests/: Contiene el test step by step\n"
                f"• outputs/: Carpeta para outputs\n"
                f"• resources/: Recursos del proyecto\n"
                f"• utils/: Utilidades compartidas")
            
        except Exception as e:
            self.ui.error("Error", f"Error al reorganizar el proyecto:\n{str(e)}")
    
    def _move_related_recordings(self, project_path, new_recordings_dir, base_name, script_timestamp):
        """Mueve las grabaciones de video relacionadas con el script"""
        old_recordings_dir = os.path.join(project_path, "grabaciones")
        
        if not os.path.exists(old_recordings_dir):
            return
        
        # Estrategia 1: Buscar todos los videos y usar el más reciente si no hay coincidencia por nombre
        videos = [item for item in os.listdir(old_recordings_dir) if item.endswith(('.avi', '.mp4', '.mov', '.wmv'))]
        
        if not videos:
            return
        
        # Si hay solo un video, moverlo
        if len(videos) == 1:
            video_to_move = videos[0]
            old_item_path = os.path.join(old_recordings_dir, video_to_move)
            new_item_path = os.path.join(new_recordings_dir, video_to_move)
            shutil.move(old_item_path, new_item_path)
            return
        
        # Si hay múltiples videos, usar el más reciente
        most_recent_video = None
        most_recent_time = 0
        
        for video in videos:
            video_path = os.path.join(old_recordings_dir, video)
            video_time = os.path.getctime(video_path)
            
            if video_time > most_recent_time:
                most_recent_time = video_time
                most_recent_video = video
        
        if most_recent_video:
            old_item_path = os.path.join(old_recordings_dir, most_recent_video)
            new_item_path = os.path.join(new_recordings_dir, most_recent_video)
            shutil.move(old_item_path, new_item_path)
    
    def _cleanup_original_project(self, project_path):
        """Limpia el proyecto original si está vacío"""
        try:
            original_dirs = [
                os.path.join(project_path, "scripts"),
                os.path.join(project_path, "grabaciones"),
                os.path.join(project_path, "features"),
                os.path.join(project_path, "pages"),
                os.path.join(project_path, "resources"),
                os.path.join(project_path, "outputs"),
                os.path.join(project_path, "utils")
            ]
            
            is_empty = True
            for dir_path in original_dirs:
                if os.path.exists(dir_path) and os.listdir(dir_path):
                    is_empty = False
                    break
            
            if is_empty:
                shutil.rmtree(project_path)
                # También eliminar la carpeta del proyecto si está vacía
                project_parent = os.path.dirname(project_path)
                if not os.listdir(project_parent):
                    os.rmdir(project_parent)
        except:
            pass  # No importa si no se puede eliminar
    
    def _generate_test_case_content(self, script_content, base_name):
        """Genera el contenido del test case step by step"""
        test_name = base_name.upper().replace('_', ' ')
        
        imports = '''import unittest
import logging
import time
import os
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # carpeta del test
PROJECT_DIR = os.path.dirname(BASE_DIR) 
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
from utils.evidence import GetEvidence
from utils.browser import Browsers
from utils.test_logger import TestLogger
from utils.gen_reporTest import PDF

'''
        class_def = f'''class Test{base_name.capitalize()}(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Configuración inicial de la prueba"""
        cls.test_name = "{base_name}"
        
        # Configurar logger personalizado
        cls.test_logger = TestLogger(cls.test_name, PROJECT_DIR)
        cls.log_file = cls.test_logger.setup_logger()
        
        # Configurar logging estándar para compatibilidad
        logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
        
        cls.wd = Browsers.choose_browser('chrome')
        cls.wd.implicitly_wait(10)
        cls.test_dir = GetEvidence.create_evidence_dir(cls.test_name)
        
    def test_{base_name.lower()}_flow(self):
        """Test: {test_name}"""
        wait = WebDriverWait(self.wd, 15)
        action = ActionChains(self.wd)
        
        self.test_logger.info(f'Iniciando test: {{self.test_name}}')
        
        try:
'''
        
        # Extraer acciones del script
        actions = self._extract_actions_for_test(script_content)
        test_steps = []
        step_number = 1
        
        for action in actions:
            step_code = self._generate_step_code(action, step_number)
            if step_code:
                test_steps.append(step_code)
                step_number += 1
        
        test_body = '\n'.join(test_steps)
        
        tear_down = '''
            # REGISTRAR RESULTADO EXITOSO 
            self.test_logger.log_test_result("OK")
            
        except Exception as e:
            error_msg = f"Error durante la ejecución: {str(e)}"
            self.test_logger.error(error_msg)
            # Registrar resultado fallido
            self.test_logger.log_test_result("FAILED", error_msg)
            self.fail(f"Test falló: {str(e)}")

    @classmethod
    def tearDownClass(cls):
        """Limpieza y generación de reporte"""
        cls.wd.quit()
        try: 
            PDF.genReportFromLog(cls.test_name, os.path.basename(PROJECT_DIR))
        except Exception as e: 
            cls.test_logger.error(f"PDF error: {str(e)}")
        cls.test_logger.cleanup()

if __name__ == "__main__":
    unittest.main()
'''
        
        return imports + class_def + test_body + tear_down

    def _extract_actions_for_test(self, script_content):
        """Extrae acciones del script para generar el test"""
        actions = []
        lines = script_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                if "page.goto(" in line:
                    url_match = re.search(r'page\.goto\((["\'])(.*?)\1', line)
                    if url_match:
                        actions.append(('goto', url_match.group(2)))
                        
                elif "page.click(" in line:
                    selector_match = re.search(r'page\.click\((["\'])(.*?)\1', line)
                    if selector_match:
                        actions.append(('click', selector_match.group(2)))
                        
                elif "page.type(" in line or "page.fill(" in line:
                    type_match = re.search(r'page\.(?:type|fill)\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if type_match:
                        actions.append(('fill', type_match.group(2), type_match.group(4)))
                        
                elif "page.select(" in line:
                    select_match = re.search(r'page\.select\((["\'])(.*?)\1,\s*(["\'])(.*?)\3', line)
                    if select_match:
                        actions.append(('select', select_match.group(2), select_match.group(4)))
                        
                elif "page.waitForSelector(" in line:
                    wait_match = re.search(r'page\.waitForSelector\((["\'])(.*?)\1', line)
                    if wait_match:
                        actions.append(('wait', wait_match.group(2)))
                        
            except Exception as e:
                print(f"Error procesando línea: {line}\n{str(e)}")
                continue
        
        return actions

    def _generate_step_code(self, action, step_number):
        """Genera el código para cada paso del test"""
        action_type = action[0]
        
        # Extraer la descripción del paso para la evidencia
        step_descriptions = {
            'goto': 'Navegar a URL',
            'click': 'Click en elemento',
            'fill': 'Rellenar campo',
            'select': 'Seleccionar opción',
            'wait': 'Esperar elemento'
        }
        step_description = step_descriptions.get(action_type, 'Ejecutar paso')
        
        if action_type == 'goto':
            url = action[1]
            return f'''            # Paso {step_number}: Navegar a URL
            self.test_logger.info('Paso {step_number}: Navegando a {url}')
            self.wd.get("{url}")
            time.sleep(2)
            GetEvidence.create_screenshot('{step_number:02d}', 'ingreso_a_la_url', self.test_dir, self.wd)
'''
            
        elif action_type == 'click':
            selector = action[1]
            return f'''            # Paso {step_number}: Click en elemento
            self.test_logger.info('Paso {step_number}: Click en {selector}')
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "{selector}")))
            without_outline = self.wd.execute_script('return arguments[0].style.outline', element)
            self.wd.execute_script('arguments[0].style.outline= "#00FF00 solid 4px";', element)
            GetEvidence.create_screenshot('{step_number:02d}', 'click_en_elemento', self.test_dir, self.wd)
            element.click()
            time.sleep(1)
'''
            
        elif action_type == 'fill':
            selector, value = action[1], action[2]
            return f'''            # Paso {step_number}: Rellenar campo
            self.test_logger.info('Paso {step_number}: Rellenando campo {selector} con {value}')
            element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "{selector}")))
            without_outline = self.wd.execute_script('return arguments[0].style.outline', element)
            self.wd.execute_script('arguments[0].style.outline= "#00FF00 solid 4px";', element)
            GetEvidence.create_screenshot('{step_number:02d}', 'rellenar_campo', self.test_dir, self.wd)
            element.clear()
            element.send_keys("{value}")
            time.sleep(1)
'''
            
        elif action_type == 'select':
            selector, option = action[1], action[2]
            return f'''            # Paso {step_number}: Seleccionar opción
            self.test_logger.info('Paso {step_number}: Seleccionando {option} en {selector}')
            dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "{selector}")))
            without_outline = self.wd.execute_script('return arguments[0].style.outline', dropdown)
            self.wd.execute_script('arguments[0].style.outline= "#00FF00 solid 4px";', dropdown)
            dropdown.click()
            time.sleep(1)
            option_element = wait.until(EC.element_to_be_clickable((By.XPATH, f"//option[contains(text(), '{option}')]")))
            without_outline = self.wd.execute_script('return arguments[0].style.outline', option_element)
            self.wd.execute_script('arguments[0].style.outline= "#00FF00 solid 4px";', option_element)
            GetEvidence.create_screenshot('{step_number:02d}', 'seleccionar_opcion_{option[:5]}
            time.sleep(1)
'''
            
        elif action_type == 'wait':
            selector = action[1]
            return f'''            # Paso {step_number}: Esperar elemento
            self.test_logger.info('Paso {step_number}: Esperando elemento {selector}')
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "{selector}")))
            GetEvidence.create_screenshot('{step_number:02d}', 'esperar_elemento', self.test_dir, self.wd)
            time.sleep(1)
'''
        
        return None
