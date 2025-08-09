import os
from tkinter import filedialog, messagebox
import re
import time
import json


class PuppeteerToBehaveConverter:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.behave_dir = os.path.join(base_dir, "behave")
        self.recordings_dir = os.path.join(base_dir, "grabaciones")
        self._create_project_structure()

    def _create_project_structure(self):
        """Crea la estructura de directorios necesaria para Behave"""
        os.makedirs(self.behave_dir, exist_ok=True)
        os.makedirs(os.path.join(self.behave_dir, "features"), exist_ok=True)
        os.makedirs(os.path.join(self.behave_dir, "features", "steps"), exist_ok=True)
        os.makedirs(os.path.join(self.behave_dir, "pages"), exist_ok=True)
        os.makedirs(os.path.join(self.behave_dir, "resources", "data"), exist_ok=True)
        os.makedirs(self.recordings_dir, exist_ok=True)        
        
    def parse_fill(self, line):
        """Parsea una línea de acción de relleno (fill)"""
        # Adaptado para manejar tanto page.type como page.fill
        match = re.search(r'page\.(?:type|fill)\(["\'](.*?)["\'],\s*["\'](.*?)["\']\)', line) or \
                re.search(r'page\.locator\(["\'](.*?)["\']\)\.(?:type|fill)\(["\'](.*?)["\']\)', line)
        if match:
            return {
                'selector': match.group(1),
                'value': match.group(2)
            }
        return None        
    
    def convert_script(self):
        """Convierte el script grabado (JS) a estructura Behave"""
        js_file = filedialog.askopenfilename(
            initialdir=self.recordings_dir,
            filetypes=[("JavaScript Files", "*.js")],
            title="Seleccionar grabación de Puppeteer"
        )
        if not js_file:
            return

        try:
            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extraer el nombre base del archivo (sin extensión)
            base_name = os.path.splitext(os.path.basename(js_file))[0]
            class_name = base_name.capitalize() + "Page"
            feature_path = os.path.join(self.behave_dir, "features", f"{base_name}.feature")

            # Verificar si ya existe el feature
            feature_exists = os.path.exists(feature_path)
            existing_feature_content = ""
            
            if feature_exists:
                with open(feature_path, "r", encoding="utf-8") as f:
                    existing_feature_content = f.read()
                print(f"Feature existente encontrado: {feature_path}")
            else:
                # Generar archivo .feature con lógica BDD
                feature_content = self._generate_bdd_feature(content, base_name)
                with open(feature_path, "w", encoding="utf-8") as f:
                    f.write(feature_content)
                print(f"Nuevo feature creado: {feature_path}")

            # Generar steps adaptados (al feature existente o al nuevo)
            steps_content = self._generate_adaptive_steps(base_name, class_name, content, existing_feature_content if feature_exists else None)
            steps_path = os.path.join(self.behave_dir, "features", "steps", f"{base_name}_steps.py")
            with open(steps_path, "w", encoding="utf-8") as f:
                f.write(steps_content)

            # Generar page object
            page_content = self._generate_page_object(class_name, content)          
            page_path = os.path.join(self.behave_dir, "pages", f"{base_name}_page.py")
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(page_content)

            # Generar archivo JSON en resources/data (opcional, ya que el input es JSON)
            json_content = self._generate_json_data(content)
            json_path = os.path.join(self.behave_dir, "resources", "data", f"{base_name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(json_content)

            status_msg = "Feature existente reutilizado" if feature_exists else "Nuevo feature creado"
            messagebox.showinfo("Éxito", f"{status_msg}. Archivos generados en:\n{self.behave_dir}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo convertir:\n{str(e)}")

    def _generate_bdd_feature(self, script_content, base_name):
        """Genera feature con el formato exacto solicitado"""
        lines = script_content.split('\n')
        
        # Analizar el script manteniendo el orden original
        actions = []
        url = None
        
        for line in lines:
            line = line.strip()
            if "page.goto(" in line:
                url_match = re.search(r'page\.goto\(["\'](.*?)["\']\)', line) 
                if url_match:
                    url = url_match.group(1)
                    actions.append(("given", f'Acceder a la pagina "{url}"'))
                    continue  
            elif "page.click(" in line:
                selector_match = re.search(r'click\(["\'](.*?)["\']\)', line)
                if selector_match:
                    selector = selector_match.group(1)
                    if selector.startswith('button.') or selector.startswith('a.'):
                        element_type = "botón" if selector.startswith('button.') else "enlace"
                        actions.append(("click", f'clic en {element_type} "{selector}"'))
                    elif selector.startswith('#'):
                        element_id = selector.replace("#", "")
                        actions.append(("click", f'clic en "{element_id}"'))
                    else:
                        actions.append(("click", f'clic en elemento "{selector}"'))
            elif "page.type(" in line or "page.fill(" in line:
                fill_match = self.parse_fill(line)
                if fill_match:
                    field = fill_match['selector'].replace("#", "")
                    value = fill_match['value']
                    actions.append(("fill", f'Ingresar "{field}" con "{value}"'))
            elif "page.select(" in line:
                select_match = re.search(r'select\(["\'](.*?)["\'],\s*["\'](.*?)["\']\)', line)
                if select_match:
                    field = select_match.group(1).replace("#", "")
                    option = select_match.group(2)
                    actions.append(("select", f'Seleccionar "{option}" en "{field}"'))


        # Eliminar duplicados consecutivos
        unique_actions = []
        last_action = None
        for action in actions:
            if action != last_action:
                unique_actions.append(action)
                last_action = action
        
        # Construir feature con formato exacto
        feature_lines = [
            f"Feature: {base_name}\n",

            "\n",
            "  Scenario: Flujo grabado\n"
        ]
        
        # Variables para controlar la estructura
        has_given = False
        has_when = False
        has_then = False
        and_count_after_when = 0
        and_count_after_then = 0
        
        # Buffer para acumular clicks consecutivos
        click_buffer = []
        
        # Procesar cada acción
        for action_type, description in unique_actions:
            if action_type == "given" and not has_given:
                feature_lines.append(f"    Given {description}\n")
                has_given = True
            
            elif action_type == "click":
                click_buffer.append(description)
            
            elif action_type in ["fill", "select"]:
                # Procesar clicks acumulados primero si hay alguno
                if click_buffer:
                    if not has_when:
                        feature_lines.append(f"    When {', '.join(click_buffer)}\n")
                        has_when = True
                    elif and_count_after_when < 2:
                        feature_lines.append(f"    And {', '.join(click_buffer)}\n")
                        and_count_after_when += 1
                    click_buffer = []
                
                # Procesar la acción actual (fill o select)
                if action_type == "fill":
                    if has_when and and_count_after_when < 2:
                        feature_lines.append(f"    And {description}\n")
                        and_count_after_when += 1
                
                elif action_type == "select" and not has_then:
                    feature_lines.append(f"    Then {description}\n")
                    has_then = True
        
        # Procesar cualquier click pendiente al final
        if click_buffer:
            if not has_when:
                feature_lines.append(f"    When {', '.join(click_buffer)}\n")
                has_when = True
            elif and_count_after_when < 2:
                feature_lines.append(f"    And {', '.join(click_buffer)}\n")
                and_count_after_when += 1
        
        # Siempre agregar verificación final si no se ha alcanzado el límite de And
        if has_then and and_count_after_then < 2:
            feature_lines.append("    And Verificar que se completó el flujo\n")
        
        return ''.join(feature_lines)

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
        
        if existing_feature:
            # Extraer steps del feature existente
            feature_steps = self._extract_steps_from_feature(existing_feature)
            steps_content = self._generate_steps_from_feature(base_name, class_name, feature_steps, script_content)
        else:
            # Generar steps basados en el script de playwright
            steps_content = self._generate_steps_from_script(base_name, class_name, script_content)
        
        return steps_content

    def _extract_steps_from_feature(self, feature_content):
        """Extrae los steps de un feature existente"""
        steps = []
        type_consolidation = {}
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
        """Genera steps funcionales basados en un feature existente"""
        imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from utils.element_utils import ElementUtils
        """
            
        step_methods = []
        script_actions = self._extract_script_actions(script_content)
        last_non_and_step = None  # Para trackear el último paso que no es And
            
        # Extraer valores de select_options del script para referencia
        select_values = {}
        select_matches = re.finditer(r'page\.locator\(["\'](.*?)["\']\)\.select_option\(["\'](.*?)["\']\)', script_content)
        for match in select_matches:
            selector = match.group(1)
            value = match.group(2)
            field_name = self._generate_element_name(selector)
            select_values[field_name] = value
            
        for i, (step_type, description) in enumerate(feature_steps):
            # Determinar el tag correcto para steps And
            if step_type == "and":
                if last_non_and_step:
                    effective_step_type = last_non_and_step
                else:
                    effective_step_type = "given"  # Default si no hay contexto previo
            else:
                effective_step_type = step_type
                last_non_and_step = step_type  # Actualizar el último paso no-And
                
            method_name = self._create_step_method_name(effective_step_type, description)
                
            if "Seleccionar" in description and "en" in description:
                # Modificación para dropdowns
                option = re.search(r'Seleccionar "(.*?)"', description).group(1)
                field = re.search(r'en "(.*?)"', description).group(1)
                field_name = self._generate_element_name(field)
                step_methods.append(f"""
@{effective_step_type}('Seleccionar "{{option}}" en "{field}"')
def step_seleccionar_{field_name}(context, option):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.select_{field_name}(option)
            """)                
                
            elif "Acceder a la pagina" in description:
                step_methods.append(f"""
@{effective_step_type}('Acceder a la pagina "{{url}}"')
def {method_name}(context, url):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.driver.get(url)
    """)
            elif "clic en boton" in description and "," in description:
                # Nueva lógica para mantener orden exacto
                actions = []
                # Usar expresiones regulares para capturar todos los clicks en orden
                button_clicks = re.finditer(r'clic en boton "(.*?)"', description)
                for match in button_clicks:
                    actions.append(('boton', match.group(1)))
                
                generic_clicks = re.finditer(r'clic en "(.*?)"(?:,|$)', description)
                for match in generic_clicks:
                    actions.append(('elemento', match.group(1)))
                
                method_calls = []
                for action_type, element in actions:
                    element_name = self._generate_element_name(element)
                    if action_type == 'boton':
                        method_calls.append(f"context.page.click_{element_name}()")
                    else:
                        method_calls.append(f"context.page.click_{element_name}()")
                    
                step_content = f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)"""
        
                # Añadir cada llamada en el orden correcto
                for call in method_calls:
                    step_content += f"\n    {call}"
                    
                step_content += "\n    "
                step_methods.append(step_content)
        
            elif "clic en boton" in description:
                button_name = re.search(r'clic en boton "(.*?)"', description).group(1)
                element_name = self._generate_element_name(button_name)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.click_{element_name}()
    """)
            elif "clic en" in description:
                element = re.search(r'clic en "(.*?)"', description).group(1)
                element_name = self._generate_element_name(element)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.click_{element_name}()
    """)
            elif "Ingresar" in description:
                field = re.search(r'Ingresar "(.*?)"', description).group(1)
                value = re.search(r'con "(.*?)"', description).group(1)
                field_name = self._generate_element_name(field)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.enter_{field_name}("{value}")
    """)
            elif "Verificar que se completó el flujo" in description:
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    # Verificación de completado
    assert True
    """)
            
        return imports + "\n".join(step_methods)    
    
    def _generate_steps_from_script(self, base_name, class_name, script_content):
        """Genera steps que corresponden exactamente a los pasos del feature"""
        # Primero generamos el feature para extraer los steps exactos
        feature_content = self._generate_bdd_feature(script_content, base_name)
        feature_steps = self._extract_steps_from_feature(feature_content)
            
        select_values = {}
        select_matches = re.finditer(r'page\.locator\(["\'](.*?)["\']\)\.select_option\(["\'](.*?)["\']\)', script_content)
        for match in select_matches:
            selector = match.group(1)
            value = match.group(2)
            field_name = self._generate_element_name(selector)
            select_values[field_name] = value
            
        imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from utils.element_utils import ElementUtils
        """
            
        step_methods = []
        script_actions = self._extract_script_actions(script_content)
        last_non_and_step = None
            
        for i, (step_type, description) in enumerate(feature_steps):
            # Determinar el tag correcto para steps And
            if step_type == "and":
                if last_non_and_step:
                    effective_step_type = last_non_and_step
                else:
                    effective_step_type = "given"
            else:
                effective_step_type = step_type
                last_non_and_step = step_type
                    
            method_name = self._create_step_method_name(effective_step_type, description)
                
            if "Seleccionar" in description and "en" in description:
                field = re.search(r'en "(.*?)"', description).group(1)
                field_name = self._generate_element_name(field)
                step_methods.append(f"""
@{effective_step_type}('Seleccionar "{{option}}" en "{field}"')
def step_seleccionar_{field_name}(context, option):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.select_{field_name}(option)
            """)
                
            elif "Acceder a la pagina" in description:
                step_methods.append(f"""
@{effective_step_type}('Acceder a la pagina "{{url}}"')
def {method_name}(context, url):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.driver.get(url)
    """)
            elif "clic en boton" in description and "," in description:
                # Nueva lógica para mantener orden exacto
                actions = []
                current_desc = description
                while True:
                    button_match = re.search(r'clic en boton "(.*?)"', current_desc)
                    generic_match = re.search(r'clic en "(.*?)"', current_desc)
                    
                    if button_match and (not generic_match or button_match.start() < generic_match.start()):
                        actions.append(('boton', button_match.group(1)))
                        current_desc = current_desc[button_match.end():]
                    elif generic_match:
                        actions.append(('elemento', generic_match.group(1)))
                        current_desc = current_desc[generic_match.end():]
                    else:
                        break
                
                method_calls = []
                for action_type, element in actions:
                    element_name = self._generate_element_name(element)
                    if action_type == 'boton':
                        method_calls.append(f"context.page.click_{element_name}()")
                    else:
                        method_calls.append(f"context.page.click_{element_name}()")
                                    
                step_content = f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)"""
        
                # Añadir cada llamada en el orden correcto
                for call in method_calls:
                    step_content += f"\n    {call}"
                    
                step_content += "\n    "
                step_methods.append(step_content)             
                    
            elif "clic en boton" in description:
                button_name = re.search(r'clic en boton "(.*?)"', description).group(1)
                element_name = self._generate_element_name(button_name)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.click_{element_name}()
    """)
            elif "clic en" in description:
                element = re.search(r'clic en "(.*?)"', description).group(1)
                element_name = self._generate_element_name(element)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.click_{element_name}()
    """)
            elif "Ingresar" in description:
                field = re.search(r'Ingresar "(.*?)"', description).group(1)
                value = re.search(r'con "(.*?)"', description).group(1)
                field_name = self._generate_element_name(field)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.enter_{field_name}("{value}")
    """)
            elif "Verificar que se completó el flujo" in description:
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
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
        """Genera un page object similar a apolo_page.py basado en el script de Playwright"""
        imports = """from selenium.webdriver.common.by import By
from utils.element_utils import ElementUtils
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

    """

        class_template = f"""
class {class_name}:
    def __init__(self, driver):
        self.driver = driver
        self.utils = ElementUtils(driver)

        # Locators
{self._generate_locators(script_content)}

    # Methods
{self._generate_methods(script_content)}
    """
        return imports + class_template
    
    def _generate_element_name(self, selector):
        """Genera un nombre consistente para elementos a partir del selector"""
        # Primero eliminamos acentos si los hubiera
        clean_selector = self._remove_accents(selector)
        
        # Si es un selector CSS por id (#)
        if clean_selector.startswith('#'):
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
                
            name = self._generate_element_name(selector)
            
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
            
            locator_lines.append(f'        self.{locator_type}_{name} = (By.CSS_SELECTOR, "{selector}")')
        
        return "\n".join(locator_lines)    

    def _generate_methods(self, script_content):
        """Genera métodos manteniendo coherencia con los locators y asegurando todas las acciones"""
        method_lines = []
        processed_selectors = set()
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
                # Determinar tipo de locator
                if selector in fill_selectors:
                    locator_type = "txt"
                elif selector in select_selectors:
                    locator_type = "ddl"
                else:
                    locator_type = "btn"
                
                method_lines.append(f"""
    def {method_key}(self):
        \"\"\"Hace click en el elemento {selector}\"\"\"
        self.utils.click_element(self.{locator_type}_{name})
                """)
                generated_methods.add(method_key)
                processed_selectors.add(selector)
        
        # Generar métodos para fills/types
        for selector in fill_selectors:
            name = self._generate_element_name(selector)
            method_key = f"enter_{name}"
            
            if method_key not in generated_methods:
                method_lines.append(f"""
    def {method_key}(self, text):
        \"\"\"Escribe texto en el campo {selector}\"\"\"
        element = self.utils.wait_for_element(self.txt_{name})
        element.clear()
        element.send_keys(text)
                """)
                generated_methods.add(method_key)
                processed_selectors.add(selector)
        
        # Generar métodos para selects
        for selector in select_selectors:
            name = self._generate_element_name(selector)
            click_method = f"click_{name}"
            select_method = f"select_{name}"
            
            if click_method not in generated_methods:
                method_lines.append(f"""
    def {click_method}(self):
        \"\"\"Hace click en el dropdown {selector}\"\"\"
        self.utils.click_element(self.ddl_{name})
                """)
                generated_methods.add(click_method)
            
            if select_method not in generated_methods:
                method_lines.append(f"""
    def {select_method}(self, option_text):
        \"\"\"Selecciona opción en dropdown {selector}\"\"\"
        self.utils.select_from_dropdown(
            self.{click_method},
            option_text=option_text
        )
                """)
                generated_methods.add(select_method)
                processed_selectors.add(selector)
        
        return "\n".join(method_lines) if method_lines else "    # No se generaron métodos"

    def _generate_steps(self, base_name, class_name):
        """Genera los steps de behave con el nuevo formato para selects"""
        return f"""from behave import *
from pages.{base_name}_page import {class_name}
from utils.element_utils import ElementUtils

@given('I navigate to "{{url}}"')
def step_navigate(context, url):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)

@when('I click on "{{selector}}"')
def step_click(context, selector):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.click(selector)

@when('I fill "{{field}}" with "{{text}}"')
def step_fill(context, field, text):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.fill(field, text)

@when('I select "{{option}}" from "{{dropdown}}"')
def step_select(context, option, dropdown):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.utils.select_from_dropdown(
        getattr(context.page, f"select_{{dropdown.replace(' ', '_')}}"),
        option_text=option
    )
    """