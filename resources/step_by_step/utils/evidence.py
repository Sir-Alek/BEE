import os
import logging
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab


# BASE_DIR = os.getcwd()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # carpeta del test
PROJECT_DIR = os.path.dirname(BASE_DIR) 

class RunEvidenceStore():
    
    @staticmethod
    def create_screenshot(step, label, dir_name, web_driver):
        # #Logging format configuration
        # logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')
        
        # BASE_DIR = os.getcwd()
        dt = datetime.now()
        dt_format = dt.strftime('%Y-%m-%d_%H-%M-%S')
        
        evidence_name = dir_name.split('_')
        
        # #Evidence path
        evidence_dir = os.path.join(PROJECT_DIR, 'outputs', 'evidences', dir_name)
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        
        img_name = '{}_{}_{}.png'.format(step, evidence_name[0], label)
        full_img_path = os.path.join(evidence_dir, img_name)
        
        # # Complete desktop window:
        # ss = ImageGrab.grab()
        # ss.save(full_img_path, 'png')
        
        # #With selenium
        web_driver.get_screenshot_as_file(full_img_path)
        
        logging.info('Screenshot {}: {} {}'.format(step, dir_name, label))
        
        
    @staticmethod
    def alert_screenshot(step, label, dir_name):
        dt = datetime.now()
        dt_format = dt.strftime('%Y-%m-%d_%H-%M-%S')
        
        evidence_name = dir_name.split('_')
        
        # #Evidence path
        evidence_dir = os.path.join(PROJECT_DIR, 'outputs', 'evidences', dir_name)
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        
        img_name = '{}_{}_{}.png'.format(step, evidence_name[0], label)
        full_img_path = os.path.join(evidence_dir, img_name)
        
        # Complete desktop window:
        ss = ImageGrab.grab()
        ss.save(full_img_path, 'png')
        
        
        # #With selenium
        # web_driver.get_screenshot_as_file(full_img_path)
        
        logging.info('Screenshot {}: {} {}'.format(step, dir_name, label))        
        
    @staticmethod    
    def create_evidence_dir(test_name):
        date_time = datetime.now()
        dt_format = date_time.strftime('%Y-%m-%d_%H-%M-%S')
        
        tn = test_name.split('_')
        t_n = '_'.join(tn[0:])
        
        evidence_dir_name = t_n + '_' + dt_format
        
        test_dir_path = os.path.join(PROJECT_DIR, 'outputs', 'evidences', evidence_dir_name)
        
        Path(test_dir_path).mkdir(parents=True, exist_ok=True)
        # logging.info('Se crea la carpeta para evidencias con nombre: {}'.format(evidence_dir_name))
        
        return evidence_dir_name