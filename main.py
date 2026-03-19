import sys
import os

# Detectar si estamos en modo empaquetado
IS_FROZEN = getattr(sys, 'frozen', False)

# Manejo robusto de importaciones
try:
    if IS_FROZEN:
        # En modo empaquetado, usar importación desde archivos ofuscados
        from core.__dynamic_importer import puppeteer_script_converter, video_recorder, step_by_step_converter
        PuppeteerToBehaveConverter = puppeteer_script_converter.PuppeteerToBehaveConverter
        ScreenRecorder = video_recorder.ScreenRecorder
        PuppeteerToStepByStepConverter = step_by_step_converter.PuppeteerToStepByStepConverter

    else:
        # En modo desarrollo, usar importaciones normales
        from core.puppeteer_script_converter import PuppeteerToBehaveConverter
        from core.video_recorder import ScreenRecorder
        from core.step_by_step_converter import PuppeteerToStepByStepConverter   
except ImportError as e:
    # Fallback para casos especiales
    try:
        from core.__dynamic_importer import puppeteer_script_converter, video_recorder, step_by_step_converter
        PuppeteerToBehaveConverter = puppeteer_script_converter.PuppeteerToBehaveConverter
        ScreenRecorder = video_recorder.ScreenRecorder
        PuppeteerToStepByStepConverter = step_by_step_converter.PuppeteerToStepByStepConverter
    except ImportError:
        # Fallback extremo - definir clases vacías
        class PuppeteerToBehaveConverter:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Módulo PuppeteerToBehaveConverter no disponible")
        
        class PuppeteerToStepByStepConverter:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Módulo PuppeteerToStepByStepConverter no disponible")
        
        class ScreenRecorder:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Módulo ScreenRecorder no disponible")
        
        # Mostrar advertencia
        print("Advertencia: Módulos críticos no disponibles")
        
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import time
from tkinter import simpledialog
from PIL import Image, ImageTk 

from ui.tk_ui import TkUI



def resource_path(relative_path):
    """Obtiene la ruta absoluta, considerando si está empaquetado con PyInstaller"""
    try:
        base_path = sys._MEIPASS  # Carpeta temporal creada por PyInstaller
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class main:  
     
    def __init__(self, master):
        self.master = master
        self.master.title("© BEE - Behave Extractor Engine")
        self.master.geometry("800x400")
        self.ui = TkUI(master)
        
        # Configuración de paths base
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.projects_dir = os.path.join(self.base_dir, "behave", "proyectos")
        os.makedirs(self.projects_dir, exist_ok=True)
        # self.behave_dir = os.path.join(self.base_dir, "behave")
        self.recordings_dir = os.path.join(self.base_dir, "grabaciones")
        self.logo_path = os.path.join(self.base_dir, "resources", "logo_bee_png_transparente.png")
        
        # Frame principal para mejor organización
        self.main_frame = tk.Frame(master, padx=20, pady=20)
        self.main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Cargar y mostrar el logo
        self.load_logo()        
        
        # Título principal
        # self.title_label = tk.Label(
        #     self.main_frame, 
        #     text="© BEE - Behave Extractor Engine",
        #     font=("Arial", 16, "bold")
        # )
        # self.title_label.pack(pady=(0, 30))
        
        # Instrucciones
        self.label = tk.Label(
            self.main_frame, 
            text="Ingresa la URL para grabar:",
            font=("Arial", 12)
        )
        self.label.pack(pady=(0, 10))

        # Campo de entrada de URL más grande
        self.url_entry = tk.Entry(
            self.main_frame, 
            width=60,
            font=("Arial", 12)
        )
        self.url_entry.pack(ipady=5)  # Aumenta el padding interno vertical

        # Frame para los botones
        self.button_frame = tk.Frame(self.main_frame, pady=30)
        self.button_frame.pack()
        
        # Botón de Grabar - más grande
        self.run_button = tk.Button(
            self.button_frame, 
            text="Grabar Interacciones", 
            command=self.run_puppeteer_recorder,
            font=("Arial", 12),
            height=2,
            width=20
        )
        self.run_button.pack(side=tk.LEFT, padx=20)
        
        # Botón de Convertir - más grande
        self.convert_button = tk.Button(
            self.button_frame, 
            text="Convertir a Behave", 
            command=self.convert_script,
            font=("Arial", 12),
            height=2,
            width=20
        )
        self.convert_button.pack(side=tk.LEFT, padx=20)
       
        # Botón de Convertir a step by step
        self.convert_button = tk.Button(
            self.button_frame, 
            text="Convertir a step by step", 
            command=self.convert_to_step_by_step,
            font=("Arial", 12),
            height=2,
            width=20
        )
        self.convert_button.pack(side=tk.LEFT, padx=20)        
        
    def load_logo(self):
        try:
            # Cargar la imagen y redimensionar si es necesario
            logo_image = Image.open(self.logo_path)
            logo_image = logo_image.resize((250, 100), Image.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            
            # Mostrar el logo
            logo_label = tk.Label(self.main_frame, image=self.logo_photo)
            logo_label.pack(pady=(0, 10))
            
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
            # Si falla la carga, mostrar un texto alternativo
            logo_label = tk.Label(
                self.main_frame, 
                text="© BEE\nBEHAVE EXTRACTOR ENGINE",
                font=("Arial", 16, "bold"),
                fg="blue"
            )
            logo_label.pack(pady=(0, 10))  
                       
    def select_or_create_project(self):
        """Selecciona proyecto existente o crea uno nuevo"""
        # Crear ventana personalizada para el diálogo
        dialog = tk.Toplevel(self.master)
        dialog.title("Selección de Proyecto")
        dialog.geometry("300x150")
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Centrar la ventana
        dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - dialog.winfo_width()) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Frame principal
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Pregunta
        label = tk.Label(frame, text="¿Es un proyecto nuevo?", font=("Arial", 12))
        label.pack(pady=(0, 20))
        
        # Frame para botones
        btn_frame = tk.Frame(frame)
        btn_frame.pack()
        
        project_path = None
        
        def create_new():
            nonlocal project_path
            dialog.destroy()
            
            # Diálogo personalizado para nombre de proyecto
            name_dialog = tk.Toplevel(self.master)
            name_dialog.title("Nuevo Proyecto")
            name_dialog.geometry("400x150")
            name_dialog.transient(self.master)
            name_dialog.grab_set()
            
            # Centrar ventana
            name_dialog.update_idletasks()
            x = self.master.winfo_x() + (self.master.winfo_width() - name_dialog.winfo_width()) // 2
            y = self.master.winfo_y() + (self.master.winfo_height() - name_dialog.winfo_height()) // 2
            name_dialog.geometry(f"+{x}+{y}")
            
            name_frame = tk.Frame(name_dialog, padx=20, pady=20)
            name_frame.pack(fill=tk.BOTH, expand=True)
            
            tk.Label(name_frame, text="Ingresa el nombre del proyecto:", font=("Arial", 11)).pack(pady=(0, 10))
            
            name_var = tk.StringVar()
            name_entry = tk.Entry(name_frame, textvariable=name_var, width=40, font=("Arial", 11))
            name_entry.pack(pady=(0, 20))
            name_entry.focus_set()
            
            def confirm_name():
                nonlocal project_path
                project_name = name_var.get().strip()
                if project_name:
                    project_path = os.path.join(self.projects_dir, project_name)
                    os.makedirs(project_path, exist_ok=True)
                    # Crear estructura de carpetas dentro del proyecto
                    os.makedirs(os.path.join(project_path, "scripts"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "features"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "features", "steps"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "pages"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "resources", "data"), exist_ok=True)
                    name_dialog.destroy()
                else:
                    tk.messagebox.showwarning("Nombre requerido", "Por favor ingresa un nombre para el proyecto.", parent=name_dialog)
            
            def cancel_name():
                name_dialog.destroy()
            
            btn_frame_name = tk.Frame(name_frame)
            btn_frame_name.pack()
            
            tk.Button(btn_frame_name, text="Crear", command=confirm_name, width=12).pack(side=tk.LEFT, padx=10)
            tk.Button(btn_frame_name, text="Cancelar", command=cancel_name, width=12).pack(side=tk.LEFT, padx=10)
            
            # Enter para confirmar
            name_dialog.bind('<Return>', lambda e: confirm_name())
            
            self.master.wait_window(name_dialog)
        
        def select_existing():
            nonlocal project_path
            dialog.destroy()
            
            # Listar proyectos existentes
            if not os.path.exists(self.projects_dir):
                os.makedirs(self.projects_dir, exist_ok=True)
            
            projects = [d for d in os.listdir(self.projects_dir) 
                       if os.path.isdir(os.path.join(self.projects_dir, d))]
            
            if not projects:
                tk.messagebox.showinfo("No hay proyectos", "No se encontraron proyectos existentes. Crea uno nuevo.")
                return
            
            # Crear ventana de selección de proyectos
            select_dialog = tk.Toplevel(self.master)
            select_dialog.title("Seleccionar Proyecto Existente")
            select_dialog.geometry("500x400")
            select_dialog.transient(self.master)
            select_dialog.grab_set()
            
            # Centrar ventana
            select_dialog.update_idletasks()
            x = self.master.winfo_x() + (self.master.winfo_width() - select_dialog.winfo_width()) // 2
            y = self.master.winfo_y() + (self.master.winfo_height() - select_dialog.winfo_height()) // 2
            select_dialog.geometry(f"+{x}+{y}")
            
            select_frame = tk.Frame(select_dialog, padx=20, pady=20)
            select_frame.pack(fill=tk.BOTH, expand=True)
            
            tk.Label(select_frame, text="Selecciona un proyecto:", font=("Arial", 12)).pack(pady=(0, 10))
            
            # Listbox para proyectos
            listbox = tk.Listbox(select_frame, font=("Arial", 11), height=15)
            scrollbar = tk.Scrollbar(select_frame, orient=tk.VERTICAL)
            
            for project in sorted(projects):
                listbox.insert(tk.END, project)
            
            listbox.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=listbox.yview)
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            def on_select():
                nonlocal project_path
                selection = listbox.curselection()
                if selection:
                    project_name = projects[selection[0]]
                    project_path = os.path.join(self.projects_dir, project_name)
                    select_dialog.destroy()
            
            def on_cancel():
                select_dialog.destroy()
            
            btn_frame_select = tk.Frame(select_frame)
            btn_frame_select.pack(pady=(20, 0))
            
            tk.Button(btn_frame_select, text="Seleccionar", command=on_select, width=12).pack(side=tk.LEFT, padx=10)
            tk.Button(btn_frame_select, text="Cancelar", command=on_cancel, width=12).pack(side=tk.LEFT, padx=10)
            
            # Doble clic para seleccionar
            listbox.bind('<Double-Button-1>', lambda e: on_select())
            
            self.master.wait_window(select_dialog)
        
        # Botones
        tk.Button(btn_frame, text="Nuevo Proyecto", command=create_new, width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Proyecto Existente", command=select_existing, width=15).pack(side=tk.LEFT, padx=10)
        
        # Esperar a que se cierre el diálogo
        self.master.wait_window(dialog)
        return project_path
                
    def convert_script(self):
        """Maneja la conversión a behave"""
        try:
            converter = PuppeteerToBehaveConverter(self.base_dir, self.ui)
            converter.convert_script()
        except Exception as e:
            messagebox.showerror("Error", f"Error en conversión:\n{str(e)}")     
                   
    def convert_to_step_by_step(self):
        """Maneja la conversión a step by step"""
        try:
            converter = PuppeteerToStepByStepConverter(self.base_dir, self.ui)
            converter.convert_script()
        except Exception as e:
            messagebox.showerror("Error", f"Error en conversión a step by step:\n{str(e)}")         
                    
    def run_puppeteer_recorder(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("URL requerida", "Por favor ingresa una URL válida.")
            return
        
        # Paso 1: Seleccionar o crear proyecto
        project_path = self.select_or_create_project()
        if not project_path:
            return
        
        # Paso 2: Pedir al usuario el nombre del archivo con ventana personalizada
        name_dialog = tk.Toplevel(self.master)
        name_dialog.title("Nombre del Archivo de Grabación")
        name_dialog.geometry("350x150")
        name_dialog.transient(self.master)
        name_dialog.grab_set()
        
        # Centrar ventana
        name_dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - name_dialog.winfo_width()) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - name_dialog.winfo_height()) // 2
        name_dialog.geometry(f"+{x}+{y}")
        
        name_frame = tk.Frame(name_dialog, padx=20, pady=20)
        name_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(name_frame, text="Ingresa el nombre para el archivo de grabación:", font=("Arial", 11)).pack(pady=(0, 10))
        
        # Nombre por defecto
        default_name = "grabacion_" + time.strftime("%Y%m%d_%H%M%S")
        name_var = tk.StringVar(value=default_name)
        name_entry = tk.Entry(name_frame, textvariable=name_var, width=40, font=("Arial", 11))
        name_entry.pack(pady=(0, 20))
        name_entry.select_range(0, tk.END)
        name_entry.focus_set()
        
        output_file = None
        
        def confirm_name():
            nonlocal output_file
            file_name = name_var.get().strip()
            if file_name:
                # Sanitizar nombre de archivo
                file_name = re.sub(r'[^\w\-_.]', '_', file_name)
                file_name = re.sub(r'_{2,}', '_', file_name)
                
                if not file_name.endswith('.js'):
                    file_name += '.js'
                
                scripts_dir = os.path.join(project_path, "scripts")
                os.makedirs(scripts_dir, exist_ok=True)
                output_file = os.path.join(scripts_dir, file_name)
                name_dialog.destroy()
            else:
                tk.messagebox.showwarning("Nombre requerido", "Por favor ingresa un nombre para el archivo.", parent=name_dialog)
        
        def cancel_name():
            name_dialog.destroy()
        
        btn_frame_name = tk.Frame(name_frame)
        btn_frame_name.pack()
        
        tk.Button(btn_frame_name, text="Guardar", command=confirm_name, width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame_name, text="Cancelar", command=cancel_name, width=12).pack(side=tk.LEFT, padx=10)
        
        # Enter para confirmar
        name_dialog.bind('<Return>', lambda e: confirm_name())
        
        self.master.wait_window(name_dialog)
        
        if not output_file:
            return
        
        try:
            # Paso 3: Confirmación con botón Cancelar
            proceed = messagebox.askokcancel(
                "Grabando", 
                "Se abrirá el navegador.\nPara finalizar la grabación, cierra el navegador.\n\n¿Deseas continuar?",
                icon='question'
            )
            if not proceed:
                return # Cancela si el usuario presiona "Cancelar"  
            
            # --- Paso extra: Preguntar si desea grabar video ---
            grabar_video = messagebox.askyesno("Grabación de Video", "¿Deseas grabar video de la pantalla?")
            recorder = None
            video_path = None
    
            if grabar_video:
                # Usar nombre predefinido sin diálogo para evitar conflictos con Tkinter
                file_name = "video_" + time.strftime("%Y%m%d_%H%M%S") + ".avi"
                videos_dir = os.path.join(project_path, "grabaciones")
                os.makedirs(videos_dir, exist_ok=True)
                video_path = os.path.join(videos_dir, file_name)
                
                # Iniciar grabación sin diálogo
                try:
                    recorder = ScreenRecorder(video_path)
                    if recorder.start():
                        print(f"Grabación de video iniciada: {video_path}")
                    else:
                        print("No se pudo iniciar la grabación de video")
                        recorder = None
                except Exception as e:
                    print(f"Error iniciando grabación: {e}")
                    recorder = None                
            
            # Ejecutar diferente según el modo
            if IS_FROZEN:
                # En modo empaquetado, usar el wrapper ofuscado
                from core.node_wrapper import node_wrapper
                result = node_wrapper.run_obfuscated_js('recorder.js', [output_file, url])
            else:
                # En modo desarrollo, ejecutar directamente el script
                import subprocess
                recorder_js_path = os.path.join(self.base_dir, 'core', 'recorder.js')
                result = subprocess.run([
                    'node', recorder_js_path, output_file, url
                ], capture_output=True, text=True, cwd=self.base_dir)

            if result.returncode != 0:
                error = result.stderr if result.stderr else "Error desconocido en Node.js"
                raise Exception(f"Error en Puppeteer:\n{error}")            

            if not os.path.exists(output_file):
                raise Exception("No se generó el archivo de grabación")

            messagebox.showinfo("Éxito", f"Grabación guardada en:\n{output_file}")

            if recorder:
                recorder.stop()
                # Pequeña pausa para permitir que el thread termine
                time.sleep(0.5)
                
                # Verificar que el video realmente se creó
                if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                    messagebox.showinfo("Video Guardado", f"Grabación de video guardada en:\n{video_path}")
                else:
                    messagebox.showwarning("Video no guardado", "No se pudo guardar el video.")

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            # Limpiar recursos
            if IS_FROZEN:
                # Importar y limpiar solo si está en modo empaquetado
                from core.node_wrapper import node_wrapper
                node_wrapper.cleanup()
            else:
                # En modo desarrollo, no hay recursos ofuscados que limpiar
                pass



             
if __name__ == "__main__":
    print(""""
██████╗ ███████╗███████╗
██╔══██╗██╔════╝██╔════╝
██████╔╝█████╗  █████╗  
██╔══██═██╔══╝  ██╔══╝  
██████║ ███████╗███████╗
╚═════╝ ╚══════╝╚══════╝

🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝  
   BEE - Behave Extractor Engine v1.0.2
   </Alek>
🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝     
          """)    
    root = tk.Tk()
    app = main(root)
    root.mainloop()             