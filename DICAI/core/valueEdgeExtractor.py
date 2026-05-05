"""
Copyright (c) 2025 Alejandro Ramírez  
Bajo la Licencia de Autor Restringida (LAR) v1.0  
Más detalles en LICENSE
""" 

import json
import requests
import logging
import urllib3
import configparser
from pathlib import Path
from typing import Dict, Optional
import tkinter as tk
from tkinter import messagebox, simpledialog
import sys
import os
from urllib.parse import quote


# Suprimir advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ValueEdgeExtractor:
    def __init__(self, config_path: str = None):
        # Determinar si el código está empaquetado
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Ruta absoluta del archivo de configuración
        config_path = os.path.join(base_dir, 'secrets', 'secrets.ini')
        
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(config_path, encoding='utf-8')
        
        # Verificar sección crítica
        if not self.config.has_section('ValueEdge'):
            raise ValueError(f"Sección [ValueEdge] no encontrada en {config_path}")
        # Leer secrets
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # Obtener valores de secrets
        self.url = self.config.get('ValueEdge', 'URL').rstrip('/')
        self.shared_space = self.config.get('ValueEdge', 'SHARED_SPACE')
        self.workspace = self.config.get('ValueEdge', 'WORKSPACE')
        self.tech_preview_flag = self.config.get('ValueEdge', 'TECH_PREVIEW_FLAG')
        self.user = self.config.get('ValueEdge', 'USER')
        self.password = self.config.get('ValueEdge', 'PASSWORD', raw=True)
        self.login_url = self.config.get('ValueEdge', 'LOGIN')
        
        # Inicializar sesión
        self.session = requests.Session()
        self.session.verify = False
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.headers = {
            "Content-Type": "application/json",
            "ALM_OCTANE_TECH_PREVIEW": self.tech_preview_flag
        }
        self.cookies = None


    def login(self) -> bool:
        """Realizar login en Value Edge"""
        try:
            # Construir el cuerpo JSON manualmente para evitar problemas de codificación
            data = f'{{"client_id": "{self.user}", "client_secret": "{self.password}"}}'
            
            self.logger.info("Intentando login en Value Edge...")
            self.logger.debug(f"Datos de login crudos: {data}")  # Para diagnóstico
            
            response = self.session.post(
                self.url + '/authentication/sign_in',
                headers=self.headers,
                data=data  # Usar data en lugar de json para evitar codificación automática
            )
            
            # self.logger.info(f"Código de respuesta: {response.status_code}")
            # self.logger.info(f"Cookies recibidas: {response.cookies}")
            
            if response.status_code == 200:
                if "OCTANE_USER" in response.cookies and "LWSSO_COOKIE_KEY" in response.cookies:
                    self.cookies = {
                        "OCTANE_USER": response.cookies["OCTANE_USER"],
                        "LWSSO_COOKIE_KEY": response.cookies["LWSSO_COOKIE_KEY"]
                    }
                    self.session.cookies.update(self.cookies)
                    self.logger.info("Login exitoso")
                    return True
                else:
                    self.logger.error("No se recibieron las cookies esperadas")
                    return False
            else:
                self.logger.error(f"Error en login: {response.status_code}")
                self.logger.error(f"Respuesta: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error durante login: {str(e)}")
            return False        
        
    # def debug_password(self):
    #     """Método para verificar cómo se está leyendo la contraseña"""
    #     print(f"Contraseña leída: {self.password}")
    #     print(f"Longitud: {len(self.password)}")
    #     print(f"Últimos 3 caracteres: {self.password[-3:]}")
    #     print(f"Representación escape: {self.password.encode('unicode-escape')}")        

    def get_test_case(self, test_id: str) -> Optional[Dict]:
        """
        Obtener caso de prueba específico
        
        Args:
            test_id: ID del caso de prueba
        """
        if not self.cookies:
            self.logger.error("No hay sesión activa. Ejecute login() primero")
            return None

        try:
            # Obtener detalles del test
            self.logger.info(f"Obteniendo caso de prueba {test_id}...")
            
            # Obtener título y módulo
            title_url = f"{self.url}/api/shared_spaces/{self.shared_space}/workspaces/{self.workspace}/tests"
            params = {
                'query': f'"id EQ \'{test_id}\'"',
                'fields': 'name,application_modules'
            }
            
            title_response = self.session.get(
                title_url,
                params=params,
                headers=self.headers
            )
            
            # self.logger.info(f"Respuesta de título: {title_response.status_code}")
            
            if title_response.status_code != 200:
                self.logger.error(f"Error obteniendo detalles del test: {title_response.status_code}")
                self.logger.error(f"Respuesta: {title_response.text}")
                return None
                
            title_data = title_response.json()
            if not title_data.get('data'):
                self.logger.error("No se encontró el caso de prueba")
                return None
                
            test_info = title_data['data'][0]
            
            # Obtener pasos del test
            steps_url = f"{self.url}/api/shared_spaces/{self.shared_space}/workspaces/{self.workspace}/tests/{test_id}/script"
            steps_response = self.session.get(steps_url, headers=self.headers)
            
            # self.logger.info(f"Respuesta de pasos: {steps_response.status_code}")
            
            if steps_response.status_code != 200:
                self.logger.error(f"Error obteniendo pasos del test: {steps_response.status_code}")
                self.logger.error(f"Respuesta: {steps_response.text}")
                return None
                
            # Procesar los datos
            test_case = {
                "Titulo": test_info['name'],
                "Modulo": test_info['application_modules']['data'][0]['name'],
                "CasoPrueba": {}
            }
            
            # Procesar pasos
            script = steps_response.json()['script'].split("\n- ")
            current_step = 1
            
            for line in script:
                line = self._clean_text(line)
                if not line:
                    continue
                    
                if str(current_step) not in test_case["CasoPrueba"]:
                    test_case["CasoPrueba"][str(current_step)] = {
                        "paso": "",  # Inicializar con cadena vacía
                        "validacion": ""  # Inicializar con cadena vacía
                    }
                    
                if line.startswith("?"):
                    test_case["CasoPrueba"][str(current_step)]["validacion"] = line
                    current_step += 1
                else:
                    test_case["CasoPrueba"][str(current_step)]["paso"] = line.replace('- ', '')
            
            return test_case
            
        except Exception as e:
            self.logger.error(f"Error procesando caso de prueba: {str(e)}")
            return None
            
    def get_all_test_cases(self) -> Optional[list]:
            """
            Obtener todos los casos de prueba disponibles
            
            Returns:
                Lista de IDs de casos de prueba o None si hay error
            """
            if not self.cookies:
                self.logger.error("No hay sesión activa. Ejecute login() primero")
                return None

            try:
                # Obtener lista de todos los tests
                tests_url = f"{self.url}/api/shared_spaces/{self.shared_space}/workspaces/{self.workspace}/tests"
                params = {
                    'fields': 'id',
                    'limit': 1000  # Ajustar según necesidad
                }
                
                self.logger.info("Obteniendo lista de casos de prueba...")
                response = self.session.get(
                    tests_url,
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Error obteniendo lista de tests: {response.status_code}")
                    return None
                    
                tests_data = response.json()
                if not tests_data.get('data'):
                    self.logger.info("No se encontraron casos de prueba")
                    return []
                    
                test_ids = [test['id'] for test in tests_data['data']]
                # self.logger.info(f"Se encontraron {len(test_ids)} casos de prueba")
                return test_ids
                
            except Exception as e:
                self.logger.error(f"Error obteniendo lista de casos de prueba: {str(e)}")
                return None            

    def save_test_case(self, test_case: Dict, output_dir: str = "test_cases") -> None:
        """Guardar caso de prueba en archivo JSON"""
        try:
            # Crear directorio si no existe
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Guardar archivo
            output_file = Path(output_dir) / f"{test_case['Titulo']}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(test_case, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Caso de prueba guardado en {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error guardando archivo: {str(e)}")

    @staticmethod
    def _clean_text(text: str) -> str:
        """Limpiar texto de caracteres especiales"""
        replacements = {
            'ú': 'u', 'ó': 'o', 'í': 'i', 'é': 'e', 'É': 'E',
            '⚪': '', '⦿': '', '⦾': '', '●': '', '✅': '', '❌': ''
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.strip()

def center_window(window):
    """
    Centrar una ventana en la pantalla.
    
    Args:
        window: La ventana de tkinter que se desea centrar.
    """
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

def main():
    """Función principal para ejecutar el extractor"""
    try:
        # Crear instancia del extractor
        extractor = ValueEdgeExtractor('secrets/secrets.ini')
        
        # Realizar login
        if not extractor.login():
            print("\nError: No se pudo realizar el login")
            return

        # Crear una ventana emergente con tkinter
        root = tk.Tk()
        root.withdraw()  # Ocultar la ventana principal de tkinter

        # Preguntar al usuario si desea extraer todos los casos de prueba
        opcion = messagebox.askyesno("Extracción de casos de prueba", "¿Desea extraer todos los casos de prueba?")
        center_window(root)  # Centrar la ventana de confirmación

        if opcion:
            # Extraer todos los casos
            test_ids = extractor.get_all_test_cases()
            if not test_ids:
                print("\nNo se encontraron casos de prueba para extraer")
                return
                
            print(f"\nSe encontraron {len(test_ids)} casos de prueba")
            print("Iniciando extracción...\n")
            
            total = len(test_ids)
            exitosos = 0
            fallidos = 0
            
            for i, test_id in enumerate(test_ids, 1):
                print(f"\nProcesando caso {i}/{total} (ID: {test_id})")
                test_case = extractor.get_test_case(test_id)
                
                if test_case:
                    extractor.save_test_case(test_case)
                    exitosos += 1
                else:
                    fallidos += 1
            
            print(f"\nExtracción completada:")
            print(f"- Casos exitosos: {exitosos}")
            print(f"- Casos fallidos: {fallidos}")
            print(f"- Total procesados: {total}")
            
        else:
            # Pedir al usuario el ID del caso de prueba a extraer
            test_id = simpledialog.askstring("ID del caso de prueba", "Ingrese el ID del caso de prueba a extraer:")
            
            if test_id:
                test_case = extractor.get_test_case(test_id)
                if test_case:
                    extractor.save_test_case(test_case)
                    print("\nCaso de prueba extraído y guardado exitosamente!")
                else:
                    print("\nNo se pudo extraer el caso de prueba")
            else:
                print("\nOperación cancelada o no se ingresó un ID válido")
            
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()