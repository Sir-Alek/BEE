import os
import logging
import time 
from datetime import datetime
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from PIL import Image, ImageDraw, ImageFont
import pandas as pd


BASE_DIR = os.getcwd()

class GetEvidence():
    
    @staticmethod
    def create_screenshot(step, label, dir_name, web_driver, step_type=None):
        # 1. ESPERA DINÁMICA
        try:
            from utils.button_functions import _wait_overlays
            _wait_overlays(web_driver, timeout_overlays=20.0)
        except Exception:
            pass 
            
        # 2. MICRO-PAUSA VISUAL (Le damos 1 segundo extra al navegador para renderizar las gráficas)
        time.sleep(1)

        dt = datetime.now()
        dt_format = dt.strftime('%Y-%m-%d_%H-%M-%S')
        
        # Nombre de la imagen: paso + tipo (given/when/then/and) + etiqueta
        img_name = f"{step}_{step_type}_{label}.png" if step_type else f"{step}_{label}.png"
        
        evidence_dir = os.path.join(BASE_DIR, 'outputs', 'evidences', dir_name)
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        
        full_img_path = os.path.join(evidence_dir, img_name)
        web_driver.get_screenshot_as_file(full_img_path)
        
        logging.info(f'Screenshot {step}: {label}')

    @staticmethod    
    def create_evidence_dir(test_name):
        date_time = datetime.now()
        dt_format = date_time.strftime('%Y-%m-%d_%H-%M-%S')
        
        # Sanitizar nombre del escenario
        sanitized_name = test_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        sanitized_name = sanitized_name.replace(":", "_").replace("*", "_").replace("?", "_")
        
        evidence_dir_name = f"{sanitized_name}_{dt_format}"
        
        test_dir_path = os.path.join(BASE_DIR, 'outputs', 'evidences', evidence_dir_name)
        Path(test_dir_path).mkdir(parents=True, exist_ok=True)
        
        return evidence_dir_name
    
    @staticmethod
    def create_download_receipt(step, label, dir_name, file_path, file_size_bytes, download_time_sec):
        """
        Genera una imagen PNG (Recibo) con los datos del archivo descargado.
        Ideal para integraciones Headless (Jenkins) donde no hay interfaz gráfica.
        """
        try:
            # 1. Crear un "lienzo" en blanco (Fondo gris claro) de 600x300 pixeles
            img = Image.new('RGB', (600, 300), color=(240, 245, 249))
            d = ImageDraw.Draw(img)
            
            # Intentar cargar una fuente por defecto, si no, usa la básica
            try:
                font_title = ImageFont.truetype("arial.ttf", 24)
                font_text = ImageFont.truetype("arial.ttf", 18)
            except IOError:
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()

            # 2. Escribir los metadatos del archivo en la imagen
            size_kb = file_size_bytes / 1024
            file_name = os.path.basename(file_path)
            
            d.text((20, 20), " VALIDACIÓN DE DESCARGA EXITOSA (HEADLESS)", fill=(0, 100, 0), font=font_title)
            d.text((20, 80), f" Archivo: {file_name}", fill=(0, 0, 0), font=font_text)
            d.text((20, 120), f" Peso del archivo: {size_kb:.2f} KB", fill=(0, 0, 0), font=font_text)
            d.text((20, 160), f"⏱ Tiempo de descarga: {download_time_sec:.2f} segundos", fill=(0, 0, 0), font=font_text)
            d.text((20, 200), f" Ruta Servidor: .../{os.path.basename(os.path.dirname(file_path))}", fill=(80, 80, 80), font=font_text)
            d.text((20, 250), f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(100, 100, 100), font=font_text)

            # 3. Guardar la imagen en la carpeta de evidencias
            evidence_dir = os.path.join(os.getcwd(), 'outputs', 'evidences', dir_name)
            os.makedirs(evidence_dir, exist_ok=True)
            
            # 4. Generamos y guardamos la imagen
            img_name = f"{step}_{label}.png"
            full_img_path = os.path.join(evidence_dir, img_name)
            img.save(full_img_path)
            logging.info(f"Recibo de descarga generado en: {full_img_path}")
            return full_img_path
            
        except Exception as e:
            logging.error(f"Fallo al generar recibo de descarga: {e}")
            return None
        

    @staticmethod
    def create_data_preview_receipt(step, label, dir_name, file_path, data_string):
        """
        Genera una imagen PNG que muestra una previsualización de los datos (texto)
        de un archivo Excel/CSV. 100% compatible con modo Headless.
        """
        try:
            # 1. Crear un lienzo más grande para que quepan los datos (ej: 1000x400)
            img = Image.new('RGB', (1000, 400), color=(30, 30, 30)) # Fondo oscuro, estilo terminal
            d = ImageDraw.Draw(img)
            
            # 2. Intentar cargar una fuente monoespaciada (vital para que las columnas se alineen)
            try:
                # En Windows suele estar cour.ttf o consolas.ttf
                font = ImageFont.truetype("cour.ttf", 14)
            except IOError:
                font = ImageFont.load_default()

            # 3. Dibujar el texto en la imagen
            file_name = os.path.basename(file_path)
            d.text((20, 20), f" VISTA PREVIA DE DATOS - {file_name}", fill=(0, 255, 0), font=font)
            d.text((20, 60), data_string, fill=(200, 200, 200), font=font)
            
            # 4. Guardar en la subcarpeta del test
            # evidence_dir = os.path.join(os.getcwd(), 'outputs', 'evidences', dir_name)
            # os.makedirs(evidence_dir, exist_ok=True)
            
            # img_name = f"{step}_{label}_Datos.png"
            # full_img_path = os.path.join(evidence_dir, img_name)
            
            # img.save(full_img_path)
            # logging.info(f"Recibo de datos generado: {full_img_path}")
            # return full_img_path
            
            # 4. Enrutamiento inteligente y a prueba de fallos
            ruta_base_evidencias = os.path.join(os.getcwd(), 'outputs', 'evidences')
            
            # Si el framework ya mandó la ruta completa, la usamos. Si no, la armamos.
            if ruta_base_evidencias in dir_name:
                evidence_dir = dir_name
            else:
                evidence_dir = os.path.join(ruta_base_evidencias, dir_name)
                
            os.makedirs(evidence_dir, exist_ok=True)
            img_name = f"{step}_{label}_Datos.png"
            full_img_path = os.path.join(evidence_dir, img_name)
            img.save(full_img_path)
            
        except Exception as e:
            logging.error(f"Fallo al generar recibo de datos: {e}")
            return None        
