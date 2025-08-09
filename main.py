import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import time
import json
import shutil
from PIL import Image, ImageTk 
import psutil
from core.puppeteer_script_converter import PuppeteerToBehaveConverter

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
        
        # Configuración de paths base
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.behave_dir = os.path.join(self.base_dir, "behave")
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
            text="Grabar con Puppeteer", 
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
            
    def convert_script(self):
        """Maneja la conversión del script grabado a estructura Behave"""
        converter = PuppeteerToBehaveConverter(self.base_dir)
        converter.convert_script()            
            
    def run_puppeteer_recorder(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("URL requerida", "Por favor ingresa una URL válida.")
            return
        
        # Paso 1: Pedir al usuario el nombre del archivo
        output_file = filedialog.asksaveasfilename(
            defaultextension=".js",
            filetypes=[("JavaScript Files", "*.js")],
            title="Guardar script de Puppeteer",
            initialdir=self.recordings_dir
        )
        if not output_file:
            return
        
        try:
            messagebox.showinfo("Grabando", "Se abrirá el navegador.\nGraba tus acciones y cierra el navegador cuando termines.")
            
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            
            # USAR NODE PORTABLE DESDE core/node/node.exe
            node_exe = resource_path(os.path.join("core", "node", "node.exe"))
            script_path = resource_path(os.path.join("core", "recorder.js"))
            
            process = subprocess.Popen(
                [node_exe, script_path, output_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            process.wait()

            if process.returncode != 0:
                error = process.stderr.read()
                raise Exception(f"Error en Puppeteer:\n{error}")

            if not os.path.exists(output_file):
                raise Exception("No se generó el archivo de grabación")

            messagebox.showinfo("Éxito", f"Grabación guardada en:\n{output_file}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

             
if __name__ == "__main__":
    print(""""
██████╗ ███████╗███████╗
██╔══██╗██╔════╝██╔════╝
██████╔╝█████╗  █████╗  
██╔══██═██╔══╝  ██╔══╝  
██████║ ███████╗███████╗
╚═════╝ ╚══════╝╚══════╝

🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝  
   BEE - Behave Extractor Engine v1.0
   </Alek>
🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝🐝     
          """)    
    root = tk.Tk()
    app = main(root)
    root.mainloop()             