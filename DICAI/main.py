"""
Copyright (c) 2025 Alejandro Ramírez  
Bajo la Licencia de Autor Restringida (LAR) v1.0  
Más detalles en LICENSE
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import configparser
import os
import sys
import logging
from PIL import Image, ImageTk 

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s @ %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Detectar si estamos en modo empaquetado
IS_FROZEN = getattr(sys, 'frozen', False)

# Manejo robusto de importaciones
try:
    if IS_FROZEN:
        # En modo empaquetado, usar importación desde archivos ofuscados
        from core.__dynamic_importer import gherkin_converter, jira_extractor, value_edge_extractor
        UltimateGherkinConverter = gherkin_converter.UltimateGherkinConverter
        JiraExtractor = jira_extractor.JiraExtractor
        ValueEdgeExtractor = value_edge_extractor.ValueEdgeExtractor

    else:
        # En modo desarrollo, usar importaciones normales
        from core.gherkinConverter import UltimateGherkinConverter
        from core.jiraExtractor import JiraExtractor
        from core.valueEdgeExtractor import ValueEdgeExtractor   
except ImportError as e:
    # Fallback para casos especiales
    try:
        from core.__dynamic_importer import gherkin_converter, jira_extractor, value_edge_extractor
        UltimateGherkinConverter = gherkin_converter.UltimateGherkinConverter
        JiraExtractor = jira_extractor.JiraExtractor
        ValueEdgeExtractor = value_edge_extractor.ValueEdgeExtractor
    except ImportError:
        # Fallback extremo - definir clases vacías
        class UltimateGherkinConverter:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Módulo UltimateGherkinConverter no disponible")
        
        class JiraExtractor:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Módulo JiraExtractor no disponible")
        
        class ValueEdgeExtractor:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Módulo ValueEdgeExtractor no disponible")
        
        # Mostrar advertencia
        print("Advertencia: Módulos críticos no disponibles")

def check_config():
    """Verificación avanzada del archivo de configuración"""
    try:
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        config_path = os.path.join(base_dir, 'secrets', 'secrets.ini')
        config = configparser.ConfigParser(interpolation=None)
        config.read(config_path, encoding='utf-8')
        
        required_sections = {
            'ValueEdge': ['URL', 'USER', 'PASSWORD', 'SHARED_SPACE'],
            'JIRA': ['URL', 'EMAIL', 'API_TOKEN']
        }
        
        errors = []
        for section, keys in required_sections.items():
            if not config.has_section(section):
                errors.append(f"❌ Falta sección: [{section}]")
                continue
                
            for key in keys:
                if not config.has_option(section, key):
                    errors.append(f"❌ Falta clave: [{section}] {key}")
        
        if errors:
            error_msg = "\n".join(errors)
            error_msg += f"\n\n🔍 Ruta del archivo: {config_path}"
            raise RuntimeError(error_msg)
            
        return True
            
    except Exception as e:
        messagebox.showerror("Error de Configuración", 
            f"Error en el archivo secrets.ini:\n\n{str(e)}\n\n"
            "Verifica que:\n"
            "1. El archivo existe en secrets/secrets.ini\n"
            "2. Tiene las secciones [ValueEdge] y [JIRA]\n"
            "3. Todas las claves requeridas están presentes")
        sys.exit(1)

class AutomationApp:
    def __init__(self):
        check_config()
        self.root = tk.Tk()
        self.root.title("DICAI v1.1.0")
        self.root.geometry("600x450")
        self.current_project = None
        self.current_workspace = None
        self.jira_extractor = None
        self.ve_extractor = None
        self.use_ai = tk.BooleanVar(value=False)
        self.load_config()
        self.create_main_menu()

    def load_config(self):
        """Cargar configuración con manejo de rutas empaquetadas"""
        try:
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            config_path = os.path.join(base_dir, 'secrets', 'secrets.ini')
            self.config = configparser.ConfigParser(interpolation=None)
            self.config.read(config_path, encoding='utf-8')
            
            if not self.config.has_section('JIRA'):
                raise ValueError("Sección [JIRA] no encontrada en configuración")
            if not self.config.has_section('ValueEdge'):
                raise ValueError("Sección [ValueEdge] no encontrada")   
                
        except Exception as e:
            logger.error(f"Error cargando configuración: {str(e)}")
            messagebox.showerror("Error Fatal", "Configuración inválida")
            sys.exit(1)

    def create_main_menu(self):
        """Crear menú principal con nuevos estilos"""
        self.root.configure(bg="#f0f0f0")
        
        title_frame = tk.Frame(self.root, bg="#f0f0f0")
        title_frame.pack(pady=10)
        
        self.load_logo()         
        
        button_frame = tk.Frame(self.root, bg="#f0f0f0")
        button_frame.pack(pady=20)
        
        button_style = {
            "width": 25,
            "height": 2,
            "bg": "#2196F3",
            "fg": "white",
            "font": ("Arial", 10),
            "borderwidth": 0
        }
        
        tk.Button(
            button_frame,
            text="Extraer de ValueEdge",
            command=self.handle_valueedge,
            **button_style
        ).pack(pady=10)
        
        tk.Button(
            button_frame,
            text="Extraer de JIRA",
            command=self.handle_jira,
            **button_style
        ).pack(pady=10)
        
        # Checkbox para IA
        # tk.Checkbutton(
        #     button_frame,
        #     text=" Usar IA avanzada",
        #     variable=self.use_ai,
        #     bg="#f0f0f0",
        #     font=("Arial", 9),
        #     activebackground="#f0f0f0"
        # ).pack(pady=5)
        
        tk.Button(
            button_frame,
            text="Salir",
            command=self.root.quit,
            bg="#f44336",
            **{k:v for k,v in button_style.items() if k != 'bg'}
        ).pack(pady=15)

    def load_logo(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(self.base_dir, "resources", "dicai_logo.png")

        try:
            # Cargar la imagen y redimensionar si es necesario
            logo_image = Image.open(self.logo_path)
            logo_image = logo_image.resize((300, 150), Image.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            
            # Mostrar el logo en title_frame que ya existe
            logo_label = tk.Label(self.root, image=self.logo_photo)  # Cambiado a self.root
            logo_label.pack(pady=(0, 5))
            
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
            # Si falla la carga, mostrar un texto alternativo
            logo_label = tk.Label(
                self.root,  # Cambiado a self.root
                text="© DICAI",
                font=("Arial", 16, "bold"),
                fg="blue"
            )
            logo_label.pack(pady=(0, 10)) 

    def handle_jira(self):
        """Manejador para JIRA con selección de proyecto primero"""
        self.current_project = simpledialog.askstring(
            "Proyecto JIRA", 
            "Ingrese clave del proyecto (ej: BT115):",
            parent=self.root
        )
        
        if self.current_project and self.current_project.strip():
            self.current_project = self.current_project.strip().upper()
            self.initialize_jira_extractor()
            self.show_jira_options()
        else:
            messagebox.showwarning("Entrada inválida", "Proyecto requerido")

    def handle_valueedge(self):
        """Manejador corregido para ValueEdge"""
        self.current_workspace = simpledialog.askstring(
            "Workspace ValueEdge", 
            "Ingrese Workspace ID de ValueEdge:",
            parent=self.root
        )
        
        if self.current_workspace and self.current_workspace.strip():
            self.current_workspace = self.current_workspace.strip()
            self.show_valueedge_options()
        else:
            messagebox.showwarning("Entrada inválida", "Workspace requerido")

    def show_valueedge_options(self):
        """Nuevo menú para ValueEdge"""
        option_window = tk.Toplevel(self.root)
        option_window.title(f"ValueEdge - Workspace {self.current_workspace}")
        option_window.geometry("300x200")
        option_window.configure(bg="#f0f0f0")
        
        tk.Label(
            option_window,
            text=f"Workspace: {self.current_workspace}",
            font=("Arial", 11),
            bg="#f0f0f0"
        ).pack(pady=10)
        
        button_style = {
            "width": 20,
            "height": 1,
            "bg": "#4CAF50",
            "fg": "white",
            "font": ("Arial", 10)
        }
        
        tk.Button(
            option_window,
            text="Extraer TODOS los casos",
            command=lambda: self.run_valueedge_extraction("all"),
            **button_style
        ).pack(pady=10)
        
        tk.Button(
            option_window,
            text="Extraer caso específico",
            command=lambda: self.run_valueedge_extraction("single"),
            **button_style
        ).pack(pady=10)

    def initialize_jira_extractor(self):
        """Inicializar extractor JIRA con validación"""
        try:
            self.jira_extractor = JiraExtractor(
                self.config.get('JIRA', 'URL'),
                self.config.get('JIRA', 'EMAIL'),
                self.config.get('JIRA', 'API_TOKEN')
            )
            
            if not self.jira_extractor.check_connection():
                messagebox.showerror(
                    "Error de conexión",
                    "Falló la conexión con JIRA\nVerifique credenciales",
                    parent=self.root
                )
                self.jira_extractor = None

        except Exception as e:
            messagebox.showerror("Error", f"Error inicializando JIRA: {str(e)}")
            self.jira_extractor = None

    def show_jira_options(self):
        """Ventana de opciones para JIRA"""
        if not self.jira_extractor:
            return
            
        option_window = tk.Toplevel(self.root)
        option_window.title(f"JIRA - {self.current_project}")
        option_window.geometry("300x200")
        option_window.configure(bg="#f0f0f0")
        
        tk.Label(
            option_window,
            text=f"Proyecto: {self.current_project}",
            font=("Arial", 11),
            bg="#f0f0f0"
        ).pack(pady=10)
        
        button_style = {
            "width": 20,
            "height": 1,
            "bg": "#2196F3",
            "fg": "white",
            "font": ("Arial", 10)
        }
        
        tk.Button(
            option_window,
            text="Extraer UN issue",
            command=lambda: self.run_jira_extraction("single"),
            **button_style
        ).pack(pady=10)
        
        tk.Button(
            option_window,
            text="Extraer TODOS los issues",
            command=lambda: self.run_jira_extraction("all"),
            **button_style
        ).pack(pady=10)

    def run_jira_extraction(self, mode):
        """Ejecutar extracción JIRA con conversión automática"""
        if not self.jira_extractor or not self.current_project:
            return
            
        try:
            output_dir = os.path.join("output", "jira_issues", self.current_project)
            os.makedirs(output_dir, exist_ok=True)
            
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Progreso")
            progress_window.geometry("300x100")
            
            progress_label = tk.Label(
                progress_window,
                text="Iniciando extracción...",
                font=("Arial", 10)
            )
            progress_label.pack(pady=20)
            self.root.update()
            
            if mode == "all":
                issues = self.jira_extractor.get_all_issues(self.current_project)
                if not issues:
                    messagebox.showinfo("Info", "No se encontraron issues")
                    return
                    
                total = len(issues)
                for idx, issue_id in enumerate(issues, 1):
                    issue = self.jira_extractor.get_issue(issue_id)
                    if issue:
                        self.jira_extractor.save_issue(issue, output_dir)
                    progress_label.config(
                        text=f"Procesando {idx}/{total}\n{issue_id}"
                    )
                    progress_window.update()
                    
                messagebox.showinfo("Éxito", f"{total} issues extraídos")
                
            elif mode == "single":
                issue_number = simpledialog.askstring(
                    "Número de Issue", 
                    "Ingrese solo el número (ej: 123):",
                    parent=self.root
                )
                
                if issue_number and issue_number.strip().isdigit():
                    issue_id = f"{self.current_project}-{issue_number.strip()}"
                    issue = self.jira_extractor.get_issue(issue_id)
                    if issue:
                        self.jira_extractor.save_issue(issue, output_dir)
                        messagebox.showinfo("Éxito", f"Issue {issue_id} guardado")
                    else:
                        messagebox.showerror("Error", "Issue no encontrado")
                else:
                    messagebox.showwarning("Error", "Número inválido")
            
            # Conversión a Gherkin
            self.convert_files(
                input_dir=output_dir,
                output_dir=os.path.join("output", "features", "jira"),
                prefix=f"JIRA_{self.current_project}_"
            )

        except Exception as e:
            logger.error(f"Error en extracción JIRA: {str(e)}")
            messagebox.showerror("Error", f"Error crítico: {str(e)}")
        finally:
            if 'progress_window' in locals():
                progress_window.destroy()

    def run_valueedge_extraction(self, mode):
        """Ejecutar extracción ValueEdge con conversión"""
        try:
            output_dir = os.path.join("output", "test_cases", self.current_workspace)
            os.makedirs(output_dir, exist_ok=True)
            
            self.ve_extractor = ValueEdgeExtractor('secrets/secrets.ini')
            self.ve_extractor.workspace = self.current_workspace
            
            if not self.ve_extractor.login():
                messagebox.showerror("Error", "Falló login en ValueEdge")
                return
                
            if mode == "all":
                test_ids = self.ve_extractor.get_all_test_cases()
                if not test_ids:
                    messagebox.showinfo("Info", "No hay casos de prueba")
                    return
                    
                total = len(test_ids)
                progress_window = tk.Toplevel(self.root)
                progress_window.title("Progreso")
                progress_window.geometry("300x100")
                progress_label = tk.Label(progress_window, text="Iniciando...")
                progress_label.pack(pady=20)
                
                for idx, test_id in enumerate(test_ids, 1):
                    test_case = self.ve_extractor.get_test_case(test_id)
                    self.ve_extractor.save_test_case(test_case, output_dir)
                    progress_label.config(
                        text=f"Procesando {idx}/{total}\n{test_id}"
                    )
                    progress_window.update()
                    
                progress_window.destroy()
                messagebox.showinfo("Éxito", f"{total} casos extraídos")
                
            elif mode == "single":
                test_id = simpledialog.askstring(
                    "ID Caso", 
                    "Ingrese ID del caso (ej: 456):",
                    parent=self.root
                )
                
                if test_id and test_id.strip():
                    test_case = self.ve_extractor.get_test_case(test_id.strip())
                    if test_case:
                        self.ve_extractor.save_test_case(test_case, output_dir)
                        messagebox.showinfo("Éxito", "Caso guardado")
                    else:
                        messagebox.showerror("Error", "Caso no encontrado")
            
            # Conversión a Gherkin
            self.convert_files(
                input_dir=output_dir,
                output_dir=os.path.join("output", "features", "ve"),
                prefix=f"VE_{self.current_workspace}_"
            )

        except Exception as e:
            logger.error(f"Error en ValueEdge: {str(e)}")
            messagebox.showerror("Error", f"Error crítico: {str(e)}")

    def convert_files(self, input_dir: str, output_dir: str, prefix: str):
        """Conversión a Gherkin con control de IA"""
        try:
            # logger.info(f"Iniciando conversión con IA: {self.use_ai.get()}")
            
            converter = UltimateGherkinConverter(
                input_dir=input_dir,
                output_dir=output_dir,
                use_ai=self.use_ai.get()
            )
            
            # Monkey patch para nombres únicos
            original_normalize = converter._normalize_filename
            converter._normalize_filename = lambda x: prefix + original_normalize(x)
            
            converter.convert()
            logger.info(f"Conversión exitosa: {input_dir} -> {output_dir}")
            
            messagebox.showinfo(
                "Éxito", 
                f"Conversión completada!\nArchivos generados en:\n{output_dir}"
            )
            
        except Exception as e:
            logger.error(f"Error en conversión: {str(e)}", exc_info=True)
            messagebox.showerror(
                "Error de Conversión", 
                f"No se pudieron generar features:\n{str(e)}"
            )

if __name__ == "__main__":
    print("""
            ███████╗ ████████╗████████╗ ██████╗ ████████╗
            ██╔═══██╗   ██║   ██╔════╝ ██╔══██╗    ██║   
            ██║   ██║   ██║   ██║      ███████║    ██║   
            ██║   ██║   ██║   ██║      ██╔══██║    ██║   
            ██║   ██║   ██║   ██║      ██║  ██║    ██║   
            ███████║ ████████║████████║╚═╝  ╚═╝ ████████║ v1.1.0
            </Alek>          
              """)  
    check_config()
    app = AutomationApp()
    app.root.mainloop()