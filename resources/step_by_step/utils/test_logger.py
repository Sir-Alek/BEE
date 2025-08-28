# test_logger.py
import os
import logging
import sys
from datetime import datetime

class TestLogger:
    def __init__(self, test_name, project_dir=None):
        """
        Inicializa el logger para un test específico
        
        Args:
            test_name (str): Nombre del test
            project_dir (str): Directorio base del proyecto (opcional)
        """
        self.test_name = test_name
        self.project_dir = project_dir or os.getcwd()
        self.logs_dir = os.path.join(self.project_dir, "outputs", "logs")
        self.log_file = None
        self.start_time = None
        self.logger = None
        self.file_handler = None
        self.console_handler = None
        
    def setup_logger(self):
        """Configura el logger sin redirigir stdout/stderr"""
        try:
            # Crear directorio de logs si no existe
            os.makedirs(self.logs_dir, exist_ok=True)
            
            # Nombre del archivo de log con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{self.test_name}.txt"
            self.log_file = os.path.join(self.logs_dir, log_filename)
            
            # Configurar logger personalizado
            self.logger = logging.getLogger(f"test_{self.test_name}")
            self.logger.setLevel(logging.INFO)
            
            # Eliminar handlers existentes
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
            
            # Formato del log
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # Handler para archivo - MODIFICADO: modo 'w' para sobrescribir
            self.file_handler = logging.FileHandler(self.log_file, mode='w', encoding='utf-8')
            self.file_handler.setFormatter(formatter)
            self.file_handler.setLevel(logging.INFO)
            
            # Handler para consola
            self.console_handler = logging.StreamHandler(sys.stdout)
            self.console_handler.setFormatter(formatter)
            self.console_handler.setLevel(logging.INFO)
            
            # Agregar handlers al logger
            self.logger.addHandler(self.file_handler)
            self.logger.addHandler(self.console_handler)
            
            # Desactivar propagación al logger root
            self.logger.propagate = False
            
            self.start_time = datetime.now()
            self.logger.info(f"=== INICIO TEST: {self.test_name} ===")
            self.logger.info(f"Hora de inicio: {self.start_time}")
            self.logger.info(f"Archivo de log: {self.log_file}")
            self.logger.info("=" * 50)
            
            return self.log_file
            
        except Exception as e:
            print(f"Error configurando logger: {str(e)}")
            return None
    
    def info(self, message):
        """Registra mensaje de información"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
    
    def error(self, message):
        """Registra mensaje de error"""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"ERROR: {message}")
    
    def warning(self, message):
        """Registra mensaje de advertencia"""
        if self.logger:
            self.logger.warning(message)
        else:
            print(f"WARNING: {message}")
    
    def log_test_result(self, status, error_message=None, execution_time=None):
        """
        Registra el resultado del test en el log
        
        Args:
            status (str): "OK" o "FAILED"
            error_message (str): Mensaje de error si falló
            execution_time (float): Tiempo de ejecución en segundos
        """
        end_time = datetime.now()
        
        if execution_time is None and self.start_time:
            execution_time = (end_time - self.start_time).total_seconds()
        
        self.info("=" * 50)
        self.info(f"=== RESULTADO TEST: {self.test_name} ===")
        self.info(f"Estado: {status}")
        self.info(f"Hora de finalización: {end_time}")
        
        if self.start_time:
            self.info(f"Duración: {execution_time:.2f} segundos")
        
        if status == "FAILED" and error_message:
            self.error(f"Error: {error_message}")
        
        self.info("=" * 50)
    
    def cleanup(self):
        """Limpia los handlers del logger"""
        try:
            if self.file_handler:
                self.file_handler.close()
                self.logger.removeHandler(self.file_handler)
            if self.console_handler:
                self.console_handler.close()
                self.logger.removeHandler(self.console_handler)
        except Exception as e:
            print(f"Error limpiando logger: {str(e)}")
    
    def get_log_path(self):
        """Retorna la ruta del archivo de log"""
        return self.log_file