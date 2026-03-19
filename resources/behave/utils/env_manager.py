import os
import json
import logging
import shutil
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

from utils.evidence import GetEvidence
import utils.button_functions as bf
from utils.gen_reporTest import PDF
from utils.PDFFeatureReport import PDFFeatureReport

class BaseUtils:
    """Utilidades generales compartidas"""
    @staticmethod
    def sanitize_filename(name):
        return str(name).replace(" ", "").replace("/", "").replace("\\", "").replace(":", "").replace("*", "").replace("?", "")

    @staticmethod
    def get_element_status(element):
        try:
            return {
                "text": element.text[:200] + "..." if element.text else "",
                "visible": element.is_displayed(),
                "enabled": element.is_enabled(),
                "location": element.location,
                "size": element.size,
                "tag": element.tag_name,
                "id": element.get_attribute("id") or "",
                "classes": element.get_attribute("class") or ""
            }
        except StaleElementReferenceException:
            return {"error": "Elemento obsoleto (stale)"}
        except Exception as e:
            return {"error": str(e)}

class DirectoryManager:
    """Gestión de carpetas (Outputs y Descargas)"""
    @staticmethod
    def get_base_dir():
        return os.getcwd()

    @staticmethod
    def setup_downloads():
        download_dir = os.path.join(DirectoryManager.get_base_dir(), "outputs", "downloads")
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
        os.makedirs(download_dir, exist_ok=True)
        return download_dir

class DriverManager:
    """Configuración extrema del ChromeDriver y CDP"""
    @staticmethod
    def create_driver(headless_mode):
        options = Options()
        download_dir = DirectoryManager.setup_downloads()
        
        # Opciones base de seguridad y UI
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-insecure-localhost')
        options.set_capability('acceptInsecureCerts', True)
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-webgl")
        options.add_argument("--disable-webgl2")
        options.add_argument("--disable-features=WebGPU")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Medios y Angle
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-real-device-for-media-stream")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--use-angle=swiftshader")
        options.add_argument("--enable-unsafe-webgpu")
        
        # Preferencias Críticas
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.managed_default_content_settings.popups": 1,
            "profile.default_content_settings.popups": 1,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        
        if headless_mode:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
            
        local_driver_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "drivers", "chromedriver.exe")

        try:
            logging.info("Iniciando con Selenium Manager Nativo...")
            driver = webdriver.Chrome(options=options)
            logging.info("✓ Driver iniciado con Selenium Manager Nativo")
        except Exception as e:
            logging.error(f"Error con Selenium Manager: {str(e)}")
            logging.info("Intentando iniciar con ChromeDriver local...")
            service = Service(local_driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            logging.info("✓ Driver iniciado con ChromeDriver local")

        DriverManager._apply_cdp_overrides(driver, headless_mode)
        return driver

    @staticmethod
    def _apply_cdp_overrides(driver, headless_mode):
        # Anti-detección crítica
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['es-MX', 'es', 'en-US', 'en']});
                window.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({query: () => Promise.resolve({ state: 'granted' })})
                });
            """
        })
        
        # Mock de Geolocalización CDP (CDMX)
        latitude, longitude, accuracy = 19.432608, -99.133209, 50
        try:
            driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
                "latitude": latitude, "longitude": longitude, "accuracy": accuracy
            })
            logging.info("✓ Geolocalización configurada via CDP")
        except Exception as e:
            logging.warning(f"Error configurando geolocalización CDP: {e}")
            
        if headless_mode:
            try:
                driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                    "platform": "Win32",
                    "acceptLanguage": "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7"
                })
                logging.info("✓ User-Agent configurado para headless")
            except Exception as e:
                pass
                
        DriverManager._inject_geolocation_mock(driver, latitude, longitude, accuracy)

    @staticmethod
    def _inject_geolocation_mock(driver, lat, lng, acc):
        script = f"""
        const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);
        navigator.geolocation.getCurrentPosition = function(success, error, options) {{
            if (success) {{
                success({{coords: {{latitude: {lat}, longitude: {lng}, accuracy: {acc}, altitude: null, altitudeAccuracy: null, heading: null, speed: null}}, timestamp: Date.now()}});
            }}
        }};
        navigator.geolocation.watchPosition = function(success, error, options) {{
            return navigator.geolocation.getCurrentPosition(success, error, options);
        }};
        """
        driver.execute_script(script)
        logging.info("✓ Mock inyectado correctamente")

class LogManager:
    """Manejo centralizado de Logs, Diagnósticos y Consolidación"""
    
    @staticmethod
    def init_global_logger(context):
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            handler.close()
            
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        logging.root.addHandler(console_handler)
        
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.root.setLevel(getattr(logging, log_level, logging.INFO))
        
        diagnostic_logger = logging.getLogger('diagnostic')
        diagnostic_logger.setLevel(logging.INFO)
        for handler in diagnostic_logger.handlers[:]:
            diagnostic_logger.removeHandler(handler)
            handler.close()
            
        if not diagnostic_logger.handlers:
            diag_handler = logging.StreamHandler()
            diag_formatter = logging.Formatter('%(asctime)s | DIAGNOSTIC | %(message)s')
            diag_handler.setFormatter(diag_formatter)
            diagnostic_logger.addHandler(diag_handler)
            
        context.all_feature_logs = []

    @staticmethod
    def setup_feature_logger(context, feature):
        if not context.generate_evidence:
            return None
            
        logs_dir = os.path.join(DirectoryManager.get_base_dir(), "outputs", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        feature_name = BaseUtils.sanitize_filename(feature.name)
        feature_log_path = os.path.join(logs_dir, f"{feature_name}_feature.txt")
        
        feature_log_handler = logging.FileHandler(feature_log_path, mode='w', encoding='utf-8')
        feature_log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logging.root.addHandler(feature_log_handler)
        
        context.feature_log_path = feature_log_path
        context.feature_start_time = datetime.now()
        context.all_feature_logs.append(feature_log_path)
        context.feature_log_handler = feature_log_handler
        
        logging.info(f"==== INICIO DE FEATURE: {feature.name} ====")

    @staticmethod
    def setup_scenario_logger(context, scenario):
        logs_dir = os.path.join(DirectoryManager.get_base_dir(), "outputs", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        scenario_name = BaseUtils.sanitize_filename(scenario.name)
        context.txt_filename = os.path.join(logs_dir, f"{scenario_name}.txt")
        
        file_handler = logging.FileHandler(context.txt_filename, mode='w', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logging.root.addHandler(file_handler)
        context.scenario_file_handler = file_handler
        
        if not hasattr(context.config, 'log_files'):
            context.config.log_files = []
        context.config.log_files.append(context.txt_filename)

    @staticmethod
    def log_step_diagnostics(context, step):
        if hasattr(context, 'driver') and context.driver:
            try:
                context.diagnostic_logger.info("Current URL: %s", context.driver.current_url)
                context.diagnostic_logger.info("Page Title: %s", context.driver.title)
                
                try:
                    body = context.driver.find_element(By.TAG_NAME, "body")
                    visible_text = body.text.replace('\n', ' ').replace('\r', ' ')[:1000] + "..."
                    context.diagnostic_logger.info("Texto visible: %s", visible_text)
                except:
                    context.diagnostic_logger.warning("Problema obteniendo texto visible")
                
                try:
                    buttons = context.driver.find_elements(By.XPATH, "//button")
                    context.diagnostic_logger.info("=== Botones visibles ===")
                    for i, button in enumerate(buttons[:3]):
                        if button.is_displayed():
                            status = BaseUtils.get_element_status(button)
                            context.diagnostic_logger.info(f" - Botón {i+1}: '{status.get('text', '')}' Habilitado: {status.get('enabled', 'N/A')}")
                except StaleElementReferenceException:
                    context.diagnostic_logger.warning("Elementos cambiaron durante diagnóstico")
                    
            except Exception as e:
                context.diagnostic_logger.warning("Problema en diagnóstico general: %s", str(e))

            if step.status.name == "failed":
                try:
                    context.diagnostic_logger.warning("=== DOM en fallo ===")
                    inputs = context.driver.find_elements(By.TAG_NAME, "input")
                    buttons = context.driver.find_elements(By.TAG_NAME, "button")
                    context.diagnostic_logger.warning("Campos de entrada (%d):", len(inputs))
                    for i, input_elem in enumerate(inputs[:3]):
                        context.diagnostic_logger.warning(" - Input %d: %s", i+1, BaseUtils.get_element_status(input_elem))
                except Exception as dom_error:
                    context.diagnostic_logger.warning("Problema analizando DOM: %s", str(dom_error))

    @staticmethod
    def consolidate_feature_logs(context, feature):
        if not context.generate_evidence:
            return
            
        logs_dir = os.path.join(DirectoryManager.get_base_dir(), "outputs", "logs")
        feature_start_time_str = context.feature_start_time.strftime('%Y%m%d_%H%M%S')
        scenario_logs = glob.glob(os.path.join(logs_dir, f"{BaseUtils.sanitize_filename(feature.name)}_*{feature_start_time_str}*.txt"))
        
        with open(context.feature_log_path, 'a', encoding='utf-8') as feature_log:
            feature_log.write("\n=== LOGS DE ESCENARIOS CONSOLIDADOS ===\n")
            for scenario_log in sorted(scenario_logs):
                try:
                    with open(scenario_log, 'r', encoding='utf-8') as f:
                        feature_log.write(f"\n---- Contenido de {os.path.basename(scenario_log)} ----\n")
                        feature_log.write(f.read())
                        feature_log.write("\n")
                except Exception as e:
                    logging.error(f"Error consolidando log {scenario_log}: {str(e)}")
                    
            summary = StatsManager.get_execution_summary(context, datetime.now() - context.feature_start_time)
            feature_log.write("\n=== RESUMEN DE EJECUCIÓN ===\n")
            feature_log.write(summary)
            
        if hasattr(context, 'feature_log_handler') and context.feature_log_handler:
            logging.root.removeHandler(context.feature_log_handler)
            context.feature_log_handler.close()

class DatasetManager:
    """Carga y manejo de datos de prueba"""
    @staticmethod
    def load_dataset(context):
        json_path = os.path.join(DirectoryManager.get_base_dir(), 'resources', 'data', f"{context.feature.name}.json")
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                context.dataset = json.load(file)
                context.personas = context.dataset.get('personas', [])
                print(f"Datos de personas cargados correctamente para la característica {context.feature.name}:", context.personas)
        except FileNotFoundError:
            raise Exception(f"Archivo JSON no encontrado: {json_path}")
        except json.JSONDecodeError:
            raise Exception(f"Error leyendo JSON: {json_path}")

class EvidenceManager:
    """Manejo de capturas y enlaces al helper global"""
    @staticmethod
    def setup_evidence(context, scenario):
        if context.generate_evidence:
            context.evidence = GetEvidence()  
            context.evidence_dir = context.evidence.create_evidence_dir(scenario.name)
            
            # Usar la nueva función de configuración thread-safe de button_functions
            bf.set_global_evidence_config(
                take=False, 
                dir_name=context.evidence_dir, 
                func=context.evidence.create_screenshot
            )
        else:
            # Desactivar configuración para este hilo
            bf.set_global_evidence_config(
                take=False, 
                dir_name="", 
                func=None
            )

    @staticmethod
    def parse_step_error(context, step, full_error):
        error_msg = "Error desconocido"
        if hasattr(context, 'last_error_message') and context.last_error_message:
            return context.last_error_message
            
        lines = full_error.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Error al hacer clic') or line.startswith('Campo no encontrado'):
                return line
                
        if "TimeoutException" in full_error:
            if "element_to_be_clickable" in full_error: return "TimeoutException: Elemento no es clickeable"
            if "presence_of_element_located" in full_error: return "TimeoutException: Elemento no encontrado"
            if "visibility_of_element_located" in full_error: return "TimeoutException: Elemento no visible"
            return "TimeoutException: Timeout esperando condición"
        if "NoSuchElementException" in full_error: return "NoSuchElementException: Elemento no encontrado en el DOM"
        if "ElementNotInteractableException" in full_error: return "ElementNotInteractableException: Elemento no interactuable"
        
        error_lines = full_error.split("Stacktrace:")[0].strip().split('\n')
        if error_lines and error_lines[0].replace("Message:", "").strip():
            return error_lines[0].replace("Message:", "").strip()
            
        return "Error de Selenium - revisar stacktrace completo"

    @staticmethod
    def capture_failure(context, step):
        if not (step.status == "failed" and hasattr(context, 'driver') and context.driver and context.generate_evidence):
            return
            
        try:
            if not hasattr(context, 'evidence_dir'):
                context.evidence_dir = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.makedirs(os.path.join(DirectoryManager.get_base_dir(), 'outputs', 'evidences', context.evidence_dir), exist_ok=True)
            
            evidence_dir = os.path.join(DirectoryManager.get_base_dir(), 'outputs', 'evidences', context.evidence_dir)
            step_name = BaseUtils.sanitize_filename(step.name)[:30]
            timestamp = datetime.now().strftime('%H%M%S')
            
            screenshot_name = f"FAIL_{timestamp}_{step_name}.png"
            screenshot_path = os.path.join(evidence_dir, screenshot_name)
            
            try:
                context.driver.save_screenshot(screenshot_path)
                if not os.path.exists(screenshot_path) or os.path.getsize(screenshot_path) == 0:
                    raise Exception("Captura inválida")
            except Exception:
                screenshot_name = f"FAIL_{timestamp}.png"
                screenshot_path = os.path.join(evidence_dir, screenshot_name)
                context.driver.save_screenshot(screenshot_path)
                logging.error(f"Captura guardada con nombre corto: {screenshot_path}")
            
            logging.info(f"Captura de fallo guardada correctamente en: {screenshot_path}")
            
            if not hasattr(context, 'failure_screenshots'):
                context.failure_screenshots = {}
            context.failure_screenshots[step.name] = screenshot_name
            
        except Exception as e:
            logging.error(f"Error crítico al guardar captura: {str(e)}")

class StatsManager:
    """Gestión de métricas de ejecución"""
    @staticmethod
    def init_stats(context):
        context._runner.summary = {
            'scenarios_passed': 0, 'scenarios_failed': 0, 'scenarios_skipped': 0,
            'steps_passed': 0, 'steps_failed': 0, 'steps_skipped': 0, 'steps_undefined': 0
        }

    @staticmethod
    def update_stats(context, scenario):
        status_name = scenario.status.name
        
        if status_name == "passed": context._runner.summary['scenarios_passed'] += 1
        elif status_name == "failed": context._runner.summary['scenarios_failed'] += 1
        elif status_name == "skipped": context._runner.summary['scenarios_skipped'] += 1
        
        for step in scenario.steps:
            step_status = step.status.name
            if step_status == "passed": context._runner.summary['steps_passed'] += 1
            elif step_status == "failed": context._runner.summary['steps_failed'] += 1
            elif step_status == "skipped": context._runner.summary['steps_skipped'] += 1
            elif step_status == "undefined": context._runner.summary['steps_undefined'] += 1

    @staticmethod
    def get_execution_summary(context, duration):
        stats = context._runner.summary
        executed = stats['scenarios_passed'] + stats['scenarios_failed'] + stats['scenarios_skipped']
        mins, secs = divmod(duration.total_seconds(), 60)
        
        return "\n".join([
            f"\n{executed} scenarios ({stats['scenarios_passed']} passed, {stats['scenarios_failed']} failed, {stats['scenarios_skipped']} skipped)",
            f"{stats['steps_passed']} steps passed, {stats['steps_failed']} failed, {stats['steps_skipped']} skipped, {stats['steps_undefined']} undefined",
            f"Took {int(mins)}m{secs:.3f}s"
        ])

class ReportManager:
    """Generación de Reportes PDF"""
    @staticmethod
    def generate_scenario_report(context, scenario, end_time, failure_screenshots=None):
        if not context.generate_evidence:
            return
        try:
            # Aseguramos pasar los screenshots al método genReport
            PDF.genReport(
                context.feature.name, 
                scenario.name,
                context.start_time.strftime('%Y-%m-%d_%H-%M-%S'),
                end_time.strftime('%Y-%m-%d_%H-%M-%S'),
                screenshots=failure_screenshots
            )
            logging.info(f"✓ Reporte PDF de escenario generado: {scenario.name}")
        except Exception as e:
            # exc_info=True nos dirá exactamente la línea que falló en genReport
            logging.error(f"Error crítico al generar PDF del escenario: {str(e)}", exc_info=True)

    @staticmethod
    def generate_consolidated_report(context):
        evidence_env = os.getenv("GENERATE_EVIDENCE", "false").lower()
        if evidence_env == "true" and hasattr(context, 'all_feature_logs') and context.all_feature_logs:
            logging.info("Generando reporte PDF consolidado...")
            try:
                reporte_final = PDFFeatureReport.generate_consolidated_report(context.all_feature_logs)
                logging.info(f"Reporte consolidado listo: {reporte_final}")
            except Exception as e:
                logging.error(f"Fallo al generar reporte consolidado: {str(e)}")
