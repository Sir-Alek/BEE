import os
import logging
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab

BASE_DIR = os.getcwd()

class GetEvidence():
    
    @staticmethod
    def create_screenshot(step, label, dir_name, web_driver, step_type=None):
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