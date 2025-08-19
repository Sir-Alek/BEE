import os
import shutil
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, Y, Canvas, Label, Listbox, Scrollbar, filedialog, messagebox, ttk, Toplevel, Frame, Checkbutton, BooleanVar, Button
import re
import time
import json


class PuppeteerToBehaveConverter:
    
    def __init__(self, base_dir, master):
        self.base_dir = base_dir
        self.master = master
        self.projects_dir = os.path.join(base_dir, "behave", "proyectos")
        self.selected_actions = []

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
        # Primero seleccionar el proyecto
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir, exist_ok=True)
        
        projects = [d for d in os.listdir(self.projects_dir) 
                   if os.path.isdir(os.path.join(self.projects_dir, d))]
        
        if not projects:
            messagebox.showinfo("No hay proyectos", "No se encontraron proyectos existentes.")
            return
        
        # Crear ventana de selección de proyectos
        selection_window = Toplevel()
        selection_window.title("Seleccionar Proyecto")
        selection_window.geometry("500x400")
        selection_window.transient(self.master)
        selection_window.grab_set()
        
        # Centrar ventana
        selection_window.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - selection_window.winfo_width()) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - selection_window.winfo_height()) // 2
        selection_window.geometry(f"+{x}+{y}")
        
        frame = Frame(selection_window, padx=20, pady=20)
        frame.pack(fill=BOTH, expand=True)
        
        Label(frame, text="Selecciona un proyecto:", font=("Arial", 12)).pack(pady=(0, 10))
        
        # Listbox para proyectos
        listbox = Listbox(frame, font=("Arial", 11), height=15)
        scrollbar = Scrollbar(frame, orient=VERTICAL)
        
        for project in sorted(projects):
            listbox.insert(END, project)
        
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        
        listbox.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
        scrollbar.pack(side=RIGHT, fill=Y)
        
        project_path = None
        
        def on_select_project():
            nonlocal project_path
            selection = listbox.curselection()
            if selection:
                project_name = projects[selection[0]]
                project_path = os.path.join(self.projects_dir, project_name)
                selection_window.destroy()
                select_script(project_path)
            else:
                messagebox.showwarning("Selección requerida", "Por favor selecciona un proyecto.", parent=selection_window)
                
        def on_cancel_project():
            selection_window.destroy()
        
        # Frame para botones
        btn_frame = Frame(frame)
        btn_frame.pack(pady=(20, 0))
        
        Button(btn_frame, text="Seleccionar", command=on_select_project, width=12).pack(side=LEFT, padx=10)
        Button(btn_frame, text="Cancelar", command=on_cancel_project, width=12).pack(side=LEFT, padx=10)
        
        # Doble clic para seleccionar
        listbox.bind('<Double-Button-1>', lambda e: on_select_project())
        
        def select_script(project_path):
            # Luego seleccionar el script dentro de ese proyecto
            scripts_dir = os.path.join(project_path, "scripts")
            
            # Verificar si existe la carpeta de scripts
            if not os.path.exists(scripts_dir):
                messagebox.showerror("Error", f"No se encontró la carpeta 'scripts' en el proyecto seleccionado.")
                return
                
            # Obtener lista de archivos JS en la carpeta scripts
            js_files = [f for f in os.listdir(scripts_dir) if f.endswith('.js')]
            
            if not js_files:
                messagebox.showerror("Error", "No se encontraron archivos JavaScript (.js) en la carpeta 'scripts' del proyecto.")
                return
                
            # Crear ventana de selección de scripts
            script_window = Toplevel()
            script_window.title("Seleccionar script de Interacciones")
            script_window.geometry("500x400")
            script_window.transient(self.master)
            script_window.grab_set()
            
            # Centrar ventana
            script_window.update_idletasks()
            x = self.master.winfo_x() + (self.master.winfo_width() - script_window.winfo_width()) // 2
            y = self.master.winfo_y() + (self.master.winfo_height() - script_window.winfo_height()) // 2
            script_window.geometry(f"+{x}+{y}")            
            
            script_frame = Frame(script_window, padx=20, pady=20)
            script_frame.pack(fill=BOTH, expand=True)
            
            Label(script_frame, text="Selecciona un script:", font=("Arial", 12)).pack(pady=(0, 10))
            
            # Listbox para mostrar los archivos
            script_listbox = Listbox(script_frame, height=15, font=("Arial", 11))
            script_scrollbar = Scrollbar(script_frame, orient=VERTICAL)
            
            for file in sorted(js_files):
                script_listbox.insert(END, file)
                
            script_listbox.config(yscrollcommand=script_scrollbar.set)
            script_scrollbar.config(command=script_listbox.yview)
            
            script_listbox.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
            script_scrollbar.pack(side=RIGHT, fill=Y)
            
            selected_file = None
            
            def on_select_script():
                nonlocal selected_file
                selection = script_listbox.curselection()
                if selection:
                    selected_file = js_files[selection[0]]
                    script_window.destroy()
                    process_script(project_path, selected_file)
                else:
                    messagebox.showwarning("Selección requerida", "Por favor selecciona un script.", parent=script_window)
                    
            def on_cancel_script():
                script_window.destroy()
            
            # Frame para botones
            script_btn_frame = Frame(script_frame)
            script_btn_frame.pack(pady=(20, 0))
            
            Button(script_btn_frame, text="Seleccionar", command=on_select_script, width=12).pack(side=LEFT, padx=10)
            Button(script_btn_frame, text="Cancelar", command=on_cancel_script, width=12).pack(side=LEFT, padx=10)
            
            # Doble clic para seleccionar
            script_listbox.bind('<Double-Button-1>', lambda e: on_select_script())
            
        def process_script(project_path, selected_file):
            js_file = os.path.join(project_path, "scripts", selected_file)

            try:
                with open(js_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if content is None or content == "":
                    content = "// Archivo vacío"

                actions = self._extract_all_actions(content)
                if not self._show_action_selection(actions):
                    return

                filtered_content = self._filter_content_by_actions(content, self.selected_actions)
                self._process_conversion(js_file, filtered_content, project_path)

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo convertir:\n{str(e)}")
        
        # Esperar a que se cierre la ventana de selección de proyecto
        self.master.wait_window(selection_window)
         
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
            
        self.selected_actions = []
        selection_window = Toplevel()
        selection_window.title("Seleccionar acciones para conversión")
        selection_window.geometry("900x550")
        
        # Frame principal con menos espacio vertical
        main_frame = Frame(selection_window, padx=10, pady=5)
        main_frame.pack(expand=True, fill="both")
        
        # Canvas y scrollbar
        canvas = Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetado con menos espacio
        canvas.pack(side="left", fill="both", expand=True, pady=(0,5))
        scrollbar.pack(side="right", fill="y")
        
        # Contenido de la tabla
        check_vars = []
        for i, action in enumerate(actions):
            frame = Frame(scrollable_frame)
            frame.pack(fill="x", pady=1)
            
            var = BooleanVar(value=True)
            check_vars.append(var)
            
            Checkbutton(frame, variable=var).pack(side="left", padx=5)
            Label(frame, text=action["type"], width=15, anchor="w").pack(side="left", padx=5)
            Label(frame, text=action["description"], width=80, anchor="w").pack(side="left", padx=5)
        
        # Frame de botones
        button_frame = Frame(main_frame)
        button_frame.pack(pady=(3,5)) 
        
        # Botones
        Button(button_frame, text="Incluir todas",
               command=lambda: [var.set(True) for var in check_vars]).pack(side="left", padx=10)
        Button(button_frame, text="Excluir todas",
               command=lambda: [var.set(False) for var in check_vars]).pack(side="left", padx=10)
        Button(button_frame, text="Continuar",
               command=lambda: [self._confirm_selection(actions, check_vars, selection_window)]).pack(side="right", padx=10)
        Button(button_frame, text="Cancelar", 
               command=selection_window.destroy).pack(side="right", padx=10)
        
        selection_window.wait_window()
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
            
            if existing_files:
                file_list = "\n".join([f"- {name}: {os.path.basename(path)}" for name, path in existing_files.items()])
                response = messagebox.askyesnocancel(
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
                        messagebox.showinfo("Información", "Todos los archivos ya existen en el proyecto y no se sobrescribirán.")
                        return

            # Procesar feature file
            if 'feature' in file_paths:
                feature_exists = 'feature' in existing_files and not response
                existing_content = ""
                
                if feature_exists:
                    try:
                        with open(file_paths['feature'], "r", encoding="utf-8") as f:
                            existing_content = f.read()
                    except Exception as e:
                        messagebox.showwarning("Advertencia", f"No se pudo leer el feature existente:\n{str(e)}")
                        feature_exists = False

                if not feature_exists:
                    feature_content = self._generate_bdd_feature(content, base_name)
                    with open(file_paths['feature'], "w", encoding="utf-8") as f:
                        f.write(feature_content)

            # Generar steps file
            if 'steps' in file_paths:
                steps_content = self._generate_adaptive_steps(
                    base_name, 
                    class_name, 
                    content, 
                    existing_content if feature_exists else ""
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
            created_files = [name for name in file_paths.keys() if name not in existing_files or response]
            success_msg = f"Proyecto configurado correctamente en:\n{os.path.basename(project_path)}\n\n"
            success_msg += "Se incluyeron:\n"
            success_msg += "- Archivos de soporte completos (environment, utils, resources)\n"
            success_msg += "- Archivos generados:\n"
            success_msg += "\n".join([f"  • {os.path.basename(file_paths[name])}" for name in created_files])
            
            messagebox.showinfo("Éxito", success_msg)

        except Exception as e:
            error_msg = f"Error al configurar el proyecto {os.path.basename(project_path)}:\n{str(e)}"
            messagebox.showerror("Error", error_msg)
            
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
            src_env = os.path.join(self.base_dir, "resources","features", "environment.py")
            dst_env = os.path.join(project_path, "features", "environment.py")
            shutil.copy2(src_env, dst_env)
            
            # 2. Crear carpeta outputs vacía
            os.makedirs(os.path.join(project_path, "outputs"), exist_ok=True)
            
            # 3. Copiar recursos PDF
            src_resources = os.path.join(self.base_dir, "resources", "resources", "resourcesPDF")
            dst_resources = os.path.join(project_path, "resources", "resourcesPDF")
            if os.path.exists(src_resources):
                shutil.copytree(src_resources, dst_resources, dirs_exist_ok=True)
            
            # 4. Copiar utils completa
            src_utils = os.path.join(self.base_dir, "resources", "utils")
            dst_utils = os.path.join(project_path, "utils")
            if os.path.exists(src_utils):
                shutil.copytree(src_utils, dst_utils, dirs_exist_ok=True)
                
        except Exception as e:
            messagebox.showwarning("Advertencia", 
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
        
        # Construir feature
        feature_lines = [
            f"Feature: {base_name}\n",
            "\n",
            "  Scenario: Flujo grabado\n"
        ]
        
        has_given = False
        has_when = False
        has_then = False
        click_buffer = []
        and_count_after_when = 0
        and_count_after_then = 0
        
        for action_type, description in unique_actions:
            if action_type == "given" and not has_given:
                feature_lines.append(f"    Given {description}\n")
                has_given = True
            
            elif action_type == "click":
                click_buffer.append(description)
            
            elif action_type in ["fill", "select"]:
                if click_buffer:
                    if not has_when:
                        feature_lines.append(f"    When {', '.join(click_buffer)}\n")
                        has_when = True
                    elif and_count_after_when < 2:
                        feature_lines.append(f"    And {', '.join(click_buffer)}\n")
                        and_count_after_when += 1
                    click_buffer = []
                
                if action_type == "fill":
                    if has_when and and_count_after_when < 2:
                        feature_lines.append(f"    And {description}\n")
                        and_count_after_when += 1
                
                elif action_type == "select":
                    if not has_then:
                        feature_lines.append(f"    Then {description}\n")
                        has_then = True
        
        if click_buffer:
            if not has_when:
                feature_lines.append(f"    When {', '.join(click_buffer)}\n")
                has_when = True
            elif and_count_after_when < 2:
                feature_lines.append(f"    And {', '.join(click_buffer)}\n")
                and_count_after_when += 1
        
        # Agregar verificación final según reglas
        if has_then:
            if and_count_after_then < 2:
                feature_lines.append("    And Verificar que se completó el flujo\n")
        else:
            feature_lines.append("    Then Verificar que se completó el flujo\n")
        
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
from utils.element_utils import ElementUtils
            """
            
        step_methods = []
        last_non_and_step = None

        for step_type, description in feature_steps:
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
    context.utils = ElementUtils(context.driver)
    context.driver.get(url)
        """)

            elif "clic en elemento" in description and "," in description:
                click_names = re.findall(r'"(.*?)"', description)
                step_content = f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)"""
                for name in click_names:
                    step_content += f"\n    context.page.{name}()"
                step_methods.append(step_content)

            elif "clic en elemento" in description:
                name = re.search(r'"(.*?)"', description).group(1)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.{name}()
            """)

            elif "Ingresar" in description:
                match = re.search(r'Ingresar "(.*?)" con "(.*?)"', description)
                name, value = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.{name}("{value}")
            """)

            elif "Seleccionar" in description:
                match = re.search(r'Seleccionar "(.*?)" en "(.*?)"', description)
                option, name = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.{name}("{option}")
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
        """Genera steps directamente desde el script usando nombres de elementos"""
        feature_content = self._generate_bdd_feature(script_content, base_name)
        feature_steps = self._extract_steps_from_feature(feature_content)
            
        imports = f"""from behave import *
from pages.{base_name}_page import {class_name}
from utils.element_utils import ElementUtils
            """
            
        step_methods = []
        last_non_and_step = None
            
        for step_type, description in feature_steps:
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
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)"""
                for name in click_names:
                    step_content += f"\n    context.page.{name}()"
                step_methods.append(step_content)

            elif "clic en elemento" in description:
                name = re.search(r'"(.*?)"', description).group(1)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.{name}()
            """)

            elif "Ingresar" in description:
                match = re.search(r'Ingresar "(.*?)" con "(.*?)"', description)
                name, value = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.{name}("{value}")
            """)

            elif "Seleccionar" in description:
                match = re.search(r'Seleccionar "(.*?)" en "(.*?)"', description)
                option, name = match.group(1), match.group(2)
                step_methods.append(f"""
@{effective_step_type}('{description}')
def {method_name}(context):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.page.{name}("{option}")
            """)
                
            elif "Acceder a la pagina" in description:
                step_methods.append(f"""
@{effective_step_type}('Acceder a la pagina "{{url}}"')
def {method_name}(context, url):
    context.page = {class_name}(context.driver)
    context.utils = ElementUtils(context.driver)
    context.driver.get(url)
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
            
            locator_lines.append(f"        self.{locator_type}_{name} = (By.CSS_SELECTOR, '{selector}')")
        
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