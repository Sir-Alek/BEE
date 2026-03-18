from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from utils.evidence import BASE_DIR, GetEvidence
from datetime import datetime
from utils.gen_reporTest import PDF
import logging
import os
import json
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
import glob
import utils.button_functions as bf
import shutil

def sanitize_filename(name):
    """Reemplaza caracteres problemáticos en nombres de archivo"""
    return name.replace(" ", "").replace("/", "").replace("\\", "").replace(":", "").replace("*", "").replace("?", "")

def get_element_status(element):
    """Obtiene el estado detallado de un elemento"""
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
    
def before_feature(context, feature):
    """Configura el log para toda la feature"""
    global feature_log_handler
    
    # Configuración de evidencias (igual que en before_scenario)
    evidence_default = "false"
    evidence_env = os.getenv("GENERATE_EVIDENCE", evidence_default).lower()
    context.generate_evidence = evidence_env == "true"
    
    if not context.generate_evidence:
        return  # No configurar logs si no se generan evidencias
    
    # Configurar el log de la feature
    logs_dir = os.path.join(os.getcwd(), "outputs", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    feature_name = sanitize_filename(feature.name)
    feature_log_path = os.path.join(logs_dir, f"{feature_name}_feature.txt")
    
    # Configurar handler para el log de feature
    feature_log_handler = logging.FileHandler(feature_log_path, mode='w', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    feature_log_handler.setFormatter(formatter)
    
    # Agregar handler al logger raíz
    logging.root.addHandler(feature_log_handler)
    
    # Guardar referencia en el contexto
    context.feature_log_path = feature_log_path
    context.feature_start_time = datetime.now()
    
    # Agregamos este log a nuestra lista global
    if hasattr(context, 'all_feature_logs'):
        context.all_feature_logs.append(feature_log_path)    
    
    logging.info(f"==== INICIO DE FEATURE: {feature.name} ====")    

def before_scenario(context, scenario):
    options = Options()
    
    # Definir y crear la ruta de descargas
    download_dir = os.path.join(os.getcwd(), "outputs", "downloads")
    # Si la carpeta ya existe por pruebas anteriores, la eliminamos
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir, ignore_errors=True)
    # La volvemos a crear completamente en blanco
    os.makedirs(download_dir, exist_ok=True)
    
    # Ignorar la pantalla roja de certificado SSL
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')
    options.set_capability('acceptInsecureCerts', True)
    
    # Configuración básica del navegador
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-webgl2")
    options.add_argument("--disable-features=WebGPU")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Configuración para permisos y medios
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--use-real-device-for-media-stream")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Configuración específica para ANGLE/WebGPU
    options.add_argument("--use-angle=swiftshader")
    options.add_argument("--enable-unsafe-webgpu")
    
    # **CLAVE**: Preferencias de permisos
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.geolocation": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.managed_default_content_settings.popups": 1,
        "profile.default_content_settings.popups": 1,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        
        # Preferencias silenciosas de descarga
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    
    # Headless mode
    headless_default = "true"
    evidence_default = "false"
    
    evidence_env = os.getenv("GENERATE_EVIDENCE", evidence_default).lower()
    headless_env = os.getenv("HEADLESS", headless_default).lower()
    
    context.generate_evidence = evidence_env == "true"
    headless_mode = headless_env == "true"
    
    if headless_mode:
        options.add_argument("--headless=new")
        # ARGUMENTOS ADICIONALES PARA EVITAR DETECCIÓN EN HEADLESS
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
        
    # Coordenadas por defecto (CDMX)
    latitude = 19.432608
    longitude = -99.133209
    accuracy = 50        
    
    # Ruta de respaldo al ChromeDriver local
    local_driver_path = os.path.join(os.path.dirname(__file__), "drivers", "chromedriver.exe")

    try:
        # INTENTO 1: NATIVO (SELENIUM MANAGER)
        # Al no pasar 'service', Selenium 4.33 busca el driver. 
        # Si no lo tiene, lo descarga silenciosamente y lo cachea.
        logging.info("Iniciando con Selenium Manager Nativo...")
        context.driver = webdriver.Chrome(options=options)
        logging.info("✓ Driver iniciado con Selenium Manager Nativo")
        
    except Exception as e:
        logging.error(f"Error con Selenium Manager: {str(e)}")
        logging.info("Intentando iniciar con ChromeDriver local...")

        try:
            # INTENTO 2: FALLBACK LOCAL
            service = Service(local_driver_path)
            context.driver = webdriver.Chrome(service=service, options=options)
            logging.info("✓ Driver iniciado con ChromeDriver local")
        except Exception as e2:
            logging.critical(f"Error también con ChromeDriver local: {str(e2)}")
            raise e2

    # **CRÍTICO: Modificar navigator.webdriver ANTES de cualquier navegación**
    context.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Sobrescribir plugins para parecer navegador real
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Sobrescribir languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-MX', 'es', 'en-US', 'en']
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Permisos
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });
        """
    })
    
    # Configurar geolocalización via CDP
    try:
        context.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy
        })
        logging.info("✓ Geolocalización configurada via CDP")
    except Exception as e:
        logging.warning(f"Error configurando geolocalización CDP: {e}")
    
    # Configurar User-Agent via CDP (sobrescribe el del argumento)
    if headless_mode:
        try:
            context.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                "platform": "Win32",
                "acceptLanguage": "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7"
            })
            logging.info("✓ User-Agent configurado para headless")
        except Exception as e:
            logging.warning(f"Error configurando User-Agent: {e}")
    
    # Inyectar mock de geolocalización
    configure_geolocation_mock(context.driver)
    
    # Configurar logger de diagnóstico
    context.diagnostic_logger = logging.getLogger('diagnostic')
    context.diagnostic_logger.info("\n✓ Iniciando escenario: %s", scenario.name)
    context.start_time = datetime.now()  
    
    # Cargar dataset
    BASE_DIR = os.getcwd()
    json_path = os.path.join(BASE_DIR, 'resources', 'data', f"{context.feature.name}.json")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            context.dataset = json.load(file)
    except FileNotFoundError:
        raise Exception(f"Archivo JSON no encontrado: {json_path}")
    except json.JSONDecodeError:
        raise Exception(f"Error leyendo JSON: {json_path}")
    
    # Obtiene el directorio base del proyecto
    BASE_DIR = os.getcwd()

    # Construye la ruta del archivo JSON usando el nombre de la feature
    json_path = os.path.join(BASE_DIR, 'resources', 'data', f"{context.feature.name}.json")

    try:
        # Abre y carga el archivo JSON
        with open(json_path, 'r', encoding='utf-8') as file:
            context.dataset = json.load(file)  # Carga todo el JSON en 'context.dataset'
            
            # Extrae la lista de personas sin sobrescribir 'context.dataset'
            context.personas = context.dataset.get('personas', [])
            
            # Verifica que los datos se hayan cargado correctamente
            print(f"Datos de personas cargados correctamente para la característica {context.feature.name}:", context.personas)
            
    except FileNotFoundError:
        raise Exception(f"Archivo JSON no encontrado: {json_path}")
    except json.JSONDecodeError:
        raise Exception(f"Error leyendo JSON: {json_path}")
    

    # Configuración de evidencias
    def sanitize_filename(name):
        return str(name).replace(" ", "").replace("/", "").replace("\\", "")\
                       .replace(":", "").replace("*", "").replace("?", "")

    if context.generate_evidence:
        context.evidence = GetEvidence()  
        dir_name_generado = context.evidence.create_evidence_dir(scenario.name)
        context.start_time = datetime.now()
        context.evidence_dir = dir_name_generado
        
        # ---> CONECTAMOS EL PUENTE, PERO APAGAMOS EL PAPARAZZI
        bf.GLOBAL_EVIDENCE_DIR = dir_name_generado
        bf.GLOBAL_EVIDENCE_FUNC = context.evidence.create_screenshot
        bf.GLOBAL_TAKE_EVIDENCE = False # <-- Clave: Apagado globalmente
    else:
        bf.GLOBAL_EVIDENCE_FUNC = None
        bf.GLOBAL_TAKE_EVIDENCE = False

    # ---> ESTO DEBE IR AFUERA DEL IF/ELSE PARA QUE EL PDF FUNCIONE
    logs_dir = os.path.join(os.getcwd(), "outputs", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    scenario_name = sanitize_filename(scenario.name)
    context.txt_filename = os.path.join(logs_dir, f"{scenario_name}.txt")
    
    file_handler = logging.FileHandler(context.txt_filename, mode='w', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    file_handler.setFormatter(formatter)
    logging.root.addHandler(file_handler)
    context.scenario_file_handler = file_handler
    
    logging.info(f"\n✓ --> Iniciando escenario: {scenario.name}")
    
    if not hasattr(context.config, 'log_files'):
        context.config.log_files = []
    context.config.log_files.append(context.txt_filename)
    
    logging.info(f"✓ Configuración completa - Evidencias: {context.generate_evidence}, Headless: {headless_mode}")

def configure_headless_permissions(driver):
    """Configura permisos específicamente para modo headless"""
    try:
        # Configuración adicional para headless
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        # Forzar permisos en headless
        driver.execute_cdp_cmd("Browser.setPermission", {
            "origin": driver.current_url,
            "permission": {"name": "geolocation"},
            "setting": "granted"
        })
        
        logging.info(" Permisos headless configurados via CDP")
        return True
    except Exception as e:
        logging.warning(f"Error configurando permisos headless: {e}")
        return False

def configure_geolocation_mock(driver):
    """Mock de geolocalización con protección anti-detección"""
    try:
        script = """
        console.log('=== Configurando mock de geolocalización ===');
        
        // Guardar el original
        const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);
        
        // Sobrescribir
        navigator.geolocation.getCurrentPosition = function(success, error, options) {
            console.log('>>> Mock: Interceptando getCurrentPosition');
            if (success) {
                const position = {
                    coords: {
                        latitude: 19.432608,
                        longitude: -99.133209,
                        accuracy: 50,
                        altitude: null,
                        altitudeAccuracy: null,
                        heading: null,
                        speed: null
                    },
                    timestamp: Date.now()
                };
                console.log('>>> Mock: Enviando posición CDMX');
                setTimeout(() => success(position), 0);
            }
        };
        
        // También sobrescribir watchPosition
        navigator.geolocation.watchPosition = function(success, error, options) {
            return navigator.geolocation.getCurrentPosition(success, error, options);
        };
        
        console.log('=== Mock configurado ===');
        """
        
        driver.execute_script(script)
        logging.info("✓ Mock inyectado correctamente")
        return True
    except Exception as e:
        logging.error(f"Error con mock: {e}")
        return False 
   

def configure_geolocation(driver, latitude=19.432608, longitude=-99.133209, accuracy=50):
    """
    Configura la geolocalización via CDP y asegura que el Mock persista a la navegación.
    """
    try:        
        # 1. Establecer ubicación nativa via CDP (Emulation)
        driver.execute_cdp_cmd(
            "Emulation.setGeolocationOverride",
            {
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy
            }
        )
        
        # 2. Inyectar Mock persistente usando Page.addScriptToEvaluateOnNewDocument
        # Esto asegura que el script se ejecute INMEDIATAMENTE después de driver.get()
        mock_script = f"""
            console.log('=== Reconfigurando mock de geolocalización persistente ===');
            const coords = {{
                latitude: {latitude},
                longitude: {longitude},
                accuracy: {accuracy}
            }};
            
            // Sobrescribir getCurrentPosition
            navigator.geolocation.getCurrentPosition = function(success, error, options) {{
                console.log('>>> Mock Persistente: Entregando posición ' + coords.latitude);
                if (success) {{
                    success({{
                        coords: {{
                            latitude: coords.latitude,
                            longitude: coords.longitude,
                            accuracy: coords.accuracy,
                            altitude: null,
                            altitudeAccuracy: null,
                            heading: null,
                            speed: null
                        }},
                        timestamp: Date.now()
                    }});
                }}
            }};
            
            // Sobrescribir watchPosition
            navigator.geolocation.watchPosition = function(success, error, options) {{
                return navigator.geolocation.getCurrentPosition(success, error, options);
            }};
        """

        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": mock_script
        })
        
        logging.info(f"✓ Geolocalización reconfigurada y persistente: lat={latitude}")
        return True
    except Exception as e:
        logging.error(f"Error reconfigurando geolocalización: {str(e)}")
        return False  
    
def check_geolocation_permission(driver):
    """Verifica el estado del permiso de geolocalización EN EL DOMINIO ACTUAL"""
    try:
        permission_status = driver.execute_script("""
            return new Promise((resolve) => {
                navigator.permissions.query({name:'geolocation'})
                    .then(permissionStatus => {
                        resolve({
                            state: permissionStatus.state,
                            url: window.location.href
                        });
                    })
                    .catch(error => {
                        resolve({
                            state: 'error',
                            error: error.message,
                            url: window.location.href
                        });
                    });
            });
        """)
        
        state = permission_status.get('state', 'unknown')
        url = permission_status.get('url', 'unknown')
        
        if state == "granted":
            logging.info(f"✓ Permiso de geolocalización: {state} en {url}")
        elif state == "prompt":
            logging.info(f"? Permiso de geolocalización: {state} en {url} (solicitando)")
        else:
            logging.warning(f"✗ Permiso de geolocalización: {state} en {url}")
            
        return state == "granted"
        
    except Exception as perm_error:
        logging.error(f"Error obteniendo estado de permiso: {str(perm_error)}")
        return False

def after_scenario(context, scenario):
    if hasattr(context, 'driver'):
        context.driver.quit()
        # pass    
        
    # Actualizar estadísticas
    if scenario.status == "passed":
        context._runner.summary['scenarios_passed'] += 1
    elif scenario.status == "failed":
        context._runner.summary['scenarios_failed'] += 1
    elif scenario.status == "skipped":
        context._runner.summary['scenarios_skipped'] += 1
    
    # Actualizar contadores de steps
    for step in scenario.steps:
        if step.status == "passed":
            context._runner.summary['steps_passed'] += 1
        elif step.status == "failed":
            context._runner.summary['steps_failed'] += 1
        elif step.status == "skipped":
            context._runner.summary['steps_skipped'] += 1
        elif step.status == "undefined":
            context._runner.summary['steps_undefined'] += 1        
    
    if hasattr(context, 'start_time'):
        duration = datetime.now() - context.start_time
        context.diagnostic_logger.info(
            "Escenario completado: %s | Duración: %s | Estado: %s",
            scenario.name,
            duration,
            scenario.status.name
        )
    
    if context.generate_evidence:
        if scenario.status == "passed":
            logging.info(f"<-- Escenario PASADO: {scenario.name}")
        elif scenario.status == "failed":
            logging.error(f"<-- Escenario FALLIDO: {scenario.name}")
        elif scenario.status == "skipped":
            logging.warning(f"<-- Escenario OMITIDO: {scenario.name}")
            
        logging.info("==== FIN DE LA EJECUCIÓN ====")     
        
        result_status = "Ok" if scenario.status == "passed" else "FAILED"
        logging.info(f"Resultado: {result_status}") 

        if hasattr(context, 'txt_filename') and hasattr(context, 'start_time'):
            try:
                end_time = datetime.now()
                duration = end_time - context.start_time
                
                with open(context.txt_filename, 'a') as f:
                    f.write(f"\nTook: {duration}\n") 

                PDF.genReport(
                    context.feature.name,
                    scenario.name,
                    context.start_time.strftime('%Y-%m-%d_%H-%M-%S'),
                    end_time.strftime('%Y-%m-%d_%H-%M-%S')
                )
            except Exception as e:
                logging.error(f"Error registrando duración: {str(e)}")
        
        if hasattr(context, 'scenario_file_handler'):
            logging.root.removeHandler(context.scenario_file_handler)
            context.scenario_file_handler.close()

def after_step(context, step):
    # ===== DIAGNÓSTICO DE ELEMENTOS VISIBLES =====
    if hasattr(context, 'driver') and context.driver:
        try:
            # 1. Información básica
            current_url = context.driver.current_url
            context.diagnostic_logger.info("Current URL: %s", current_url)
            title = context.driver.title
            context.diagnostic_logger.info("Page Title: %s", title)
            
            # 2. Elementos clave específicos
            # key_elements = {
            #     "BOTON_SOLICITAR": "//button[contains(., 'Solicitar')]",
            #     "TITULO_PRINCIPAL": "//h1[contains(., 'TARJETA')]"
            # }
            
            # context.diagnostic_logger.info("=== Estado de elementos clave ===")
            # for name, xpath in key_elements.items():
            #     try:
            #         element = context.driver.find_element(By.XPATH, xpath)
            #         status = get_element_status(element)
            #         context.diagnostic_logger.info(f" - {name}:")
            #         context.diagnostic_logger.info(f"   Visible: {status.get('visible', 'N/A')}")
            #         context.diagnostic_logger.info(f"   Habilitado: {status.get('enabled', 'N/A')}")
            #         context.diagnostic_logger.info(f"   Texto: '{status.get('text', '')}'")
            #     except Exception:
            #         context.diagnostic_logger.info(f" - {name}: NO ENCONTRADO")
            
            # 3. Texto visible en pantalla
            try:
                body = context.driver.find_element(By.TAG_NAME, "body")
                visible_text = body.text.replace('\n', ' ').replace('\r', ' ')[:1000] + "..."
                context.diagnostic_logger.info("Texto visible: %s", visible_text)
            except Exception:
                context.diagnostic_logger.warning("Problema obteniendo texto visible")
            
            # 4. Estado de elementos interactivos
            try:
                buttons = context.driver.find_elements(By.XPATH, "//button")
                context.diagnostic_logger.info("=== Botones visibles ===")
                for i, button in enumerate(buttons[:3]):  # Limitar botones
                    if button.is_displayed():
                        status = get_element_status(button)
                        context.diagnostic_logger.info(f" - Botón {i+1}: '{status.get('text', '')}'")
                        context.diagnostic_logger.info(f"   Habilitado: {status.get('enabled', 'N/A')}")
            except StaleElementReferenceException:
                context.diagnostic_logger.warning("Elementos cambiaron durante diagnóstico")
            
        except Exception as e:
            context.diagnostic_logger.warning("Problema en diagnóstico: %s", str(e))
    
    # ===== DIAGNÓSTICO DETALLADO EN FALLOS =====
    if step.status == "failed" and hasattr(context, 'driver') and context.driver:
        try:
            # # 1. Capturar HTML de la página
            # html = context.driver.page_source
            # html_path = f"fail_{step.name.replace(' ', '_')}.html"
            # with open(html_path, "w", encoding="utf-8") as f:
            #     f.write(html)
            # context.diagnostic_logger.error("HTML guardado: %s", html_path)
            
            # # 2. Capturar screenshot
            # screenshot_path = f"fail_{step.name.replace(' ', '_')}.png"
            # context.driver.save_screenshot(screenshot_path)
            # context.diagnostic_logger.error("Screenshot guardado: %s", screenshot_path)
            
            # 3. Información detallada del DOM
            try:
                context.diagnostic_logger.warning("=== DOM en fallo ===")
                inputs = context.driver.find_elements(By.TAG_NAME, "input")
                buttons = context.driver.find_elements(By.TAG_NAME, "button")
                
                context.diagnostic_logger.warning("Campos de entrada (%d):", len(inputs))
                for i, input_elem in enumerate(inputs[:3]):
                    status = get_element_status(input_elem)
                    context.diagnostic_logger.warning(" - Input %d: %s", i+1, status)
                
                context.diagnostic_logger.warning("Botones (%d):", len(buttons))
                for i, button in enumerate(buttons[:3]):
                    status = get_element_status(button)
                    context.diagnostic_logger.warning(" - Botón %d: %s", i+1, status)
                    
            except Exception as dom_error:
                context.diagnostic_logger.warning("Problema analizando DOM: %s", str(dom_error))
            
        except Exception as e:
            context.diagnostic_logger.warning("Error guardando diagnóstico: %s", str(e))
    
    # ===== PARTE DE EVIDENCIAS =====
    if not context.generate_evidence:
        return
        
    if step.status == "passed":
        logging.info(f"    [Step] PASADO: {step.keyword} {step.name}")
    elif step.status == "skipped":
        logging.warning(f"    [Step] OMITIDO: {step.keyword} {step.name}")
        
    if step.status == "failed":
        error_msg = "Error desconocido"
        full_error = str(step.exception) if step.exception else ""
        
        if hasattr(context, 'last_error_message') and context.last_error_message:
            error_msg = context.last_error_message
        else:
            lines = full_error.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Error al hacer clic'):
                    error_msg = line
                    break
                elif line.startswith('Campo no encontrado'):
                    error_msg = line
                    break
            
            if error_msg == "Error desconocido":
                if "TimeoutException" in full_error:
                    if "element_to_be_clickable" in full_error:
                        error_msg = "TimeoutException: Elemento no es clickeable (timeout)"
                    elif "presence_of_element_located" in full_error:
                        error_msg = "TimeoutException: Elemento no encontrado (timeout)"
                    elif "visibility_of_element_located" in full_error:
                        error_msg = "TimeoutException: Elemento no visible (timeout)"
                    else:
                        error_msg = "TimeoutException: Timeout esperando condición"
                elif "NoSuchElementException" in full_error:
                    error_msg = "NoSuchElementException: Elemento no encontrado en el DOM"
                elif "ElementNotInteractableException" in full_error:
                    error_msg = "ElementNotInteractableException: Elemento no interactuable"
                else:
                    error_lines = full_error.split("Stacktrace:")[0].strip().split('\n')
                    if error_lines:
                        error_msg = error_lines[0].replace("Message:", "").strip()
                        if not error_msg:
                            error_msg = "Error de Selenium - revisar stacktrace completo"
        
        logging.error(f"    [Step] FALLIDO: {step.keyword} {step.name} - {error_msg}")
        
        # ===== CAPTURA DE PANTALLA EN FALLOS =====
        if step.status == "failed" and hasattr(context, 'driver') and context.driver and context.generate_evidence:
            try:
                # Asegurar que tenemos el directorio de evidencias
                if not hasattr(context, 'evidence_dir'):
                    context.evidence_dir = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.makedirs(os.path.join(BASE_DIR, 'outputs', 'evidences', context.evidence_dir), exist_ok=True)
                
                evidence_dir = os.path.join(BASE_DIR, 'outputs', 'evidences', context.evidence_dir)
                
                # Nombre del archivo
                step_name = step.name.replace(" ", "_").replace("/", "_")[:30]
                timestamp = datetime.now().strftime('%H%M%S')
                screenshot_name = f"FAIL_{timestamp}_{step_name}.png"
                screenshot_path = os.path.join(evidence_dir, screenshot_name)
                
                # Tomar captura
                try:
                    context.driver.save_screenshot(screenshot_path)
                    # Verificar que el archivo existe y tiene tamaño > 0
                    if not os.path.exists(screenshot_path) or os.path.getsize(screenshot_path) == 0:
                        raise Exception(f"La captura no se guardó correctamente en {screenshot_path}")
                except Exception as e:
                    # Intentar con un nombre más corto como último recurso
                    short_path = os.path.join(evidence_dir, f"FAIL_{timestamp}.png")
                    context.driver.save_screenshot(short_path)
                    logging.error(f"Captura guardada con nombre corto: {short_path}")
                    context.failure_screenshots[step.name] = f"FAIL_{timestamp}.png"
                
                # Verificación estricta
                if not os.path.exists(screenshot_path):
                    raise Exception(f"La captura no se guardó en {screenshot_path}")
                
                logging.info(f"Captura de fallo guardada correctamente en: {screenshot_path}")
                
                # Registrar para el reporte
                if not hasattr(context, 'failure_screenshots'):
                    context.failure_screenshots = {}
                context.failure_screenshots[step.name] = screenshot_name
                
            except Exception as e:
                logging.error(f"Error crítico al guardar captura: {str(e)}")
                # Forzar el guardado aunque falle el logging
                print(f"ERROR CRÍTICO - CAPTURA NO GUARDADA: {str(e)}")    
        
    # # ===== DIAGNÓSTICO ADICIONAL =====
    # try:
    #     current_url = context.driver.current_url
    #     page_title = context.driver.title
    #     logging.error(f"    [Diagnóstico] URL actual: {current_url}")
    #     logging.error(f"    [Diagnóstico] Título de página: {page_title}")
        
    #     try:
    #         permission_status = context.driver.execute_script("""
    #             return new Promise((resolve) => {
    #                 navigator.permissions.query({name:'geolocation'})
    #                     .then(permissionStatus => resolve(permissionStatus.state))
    #                     .catch(error => resolve('error: ' + error.message)); 
    #         })
    #         """)
    #         logging.info(f"Estado de permiso geolocalización: {permission_status}")
    #     except Exception as perm_error:
    #         logging.error(f"Error obteniendo estado de permiso: {str(perm_error)}")

    #     try:
    #         location = context.driver.execute_script("""
    #             return new Promise((resolve) => {
    #                 navigator.geolocation.getCurrentPosition(
    #                     pos => resolve({
    #                         lat: pos.coords.latitude,
    #                         lng: pos.coords.longitude,
    #                         acc: pos.coords.accuracy
    #                     }),
    #                     err => resolve({error: err.message})
    #                 );
    #             });
    #         """)
    #         if 'error' in location:
    #             logging.error(f"    [Diagnóstico] Error geolocalización: {location['error']}")
    #         else:
    #             logging.error(f"    [Diagnóstico] Ubicación reportada: {location.get('lat')}, {location.get('lng')}")
    #     except Exception as loc_error:
    #         logging.error(f"    [Diagnóstico] Error verificando ubicación: {str(loc_error)}")
            
    # except Exception as diag_error:
    #     logging.error(f"    [Diagnóstico] Error en diagnóstico: {str(diag_error)}")
    
    
def after_feature(context, feature):
    """Finaliza el log de la feature y consolida información"""
    if not context.generate_evidence:
        return
    global feature_log_handler
    
    # Calcular duración de la feature
    duration = datetime.now() - context.feature_start_time
    
    # Consolidar logs de todos los escenarios
    logs_dir = os.path.join(os.getcwd(), "outputs", "logs")
        # scenario_logs = glob.glob(os.path.join(logs_dir, f"{sanitize_filename(feature.name)}_*.txt"))
    feature_start_time_str = context.feature_start_time.strftime('%Y%m%d_%H%M%S')
    scenario_logs = glob.glob(os.path.join(logs_dir, f"{sanitize_filename(feature.name)}_*{feature_start_time_str}*.txt"))
    # scenario_logs = [log for log in scenario_logs if not log.endswith("_feature.txt")]
    
    # Escribir el contenido de todos los logs de escenarios en el log de feature
    feature_log_path = context.feature_log_path
    with open(feature_log_path, 'a', encoding='utf-8') as feature_log:
        feature_log.write("\n=== LOGS DE ESCENARIOS CONSOLIDADOS ===\n")
        
        for scenario_log in sorted(scenario_logs):
            try:
                with open(scenario_log, 'r', encoding='utf-8') as f:
                    feature_log.write(f"\n---- Contenido de {os.path.basename(scenario_log)} ----\n")
                    feature_log.write(f.read())
                    feature_log.write("\n")
            except Exception as e:
                logging.error(f"Error consolidando log {scenario_log}: {str(e)}")
    
    # Agregar resumen de la ejecución (lo que aparece en terminal)
    summary = get_execution_summary(context, feature, duration)
    
    with open(feature_log_path, 'a', encoding='utf-8') as feature_log:
        feature_log.write("\n=== RESUMEN DE EJECUCIÓN ===\n")
        feature_log.write(summary)
        
    # Limpiar el handler del log de feature
    if feature_log_handler:
        logging.root.removeHandler(feature_log_handler)
        feature_log_handler.close()
        feature_log_handler = None
    
def get_execution_summary(context, feature, duration):
    """Genera el resumen de ejecución similar al de terminal"""
    # Obtener estadísticas de la ejecución
    stats = context._runner.summary
    
    # Contar solo los escenarios ejecutados realmente
    executed_scenarios = sum([
        stats['scenarios_passed'],
        stats['scenarios_failed'],
        stats['scenarios_skipped']
    ])
    
    # Formatear la duración
    minutes, seconds = divmod(duration.total_seconds(), 60)
    duration_str = f"Took {int(minutes)}m{seconds:.3f}s"
    
    # Construir resumen
    summary_lines = [
        f"\n{executed_scenarios} scenarios ({stats['scenarios_passed']} passed, {stats['scenarios_failed']} failed, {stats['scenarios_skipped']} skipped)",
        f"{stats['steps_passed']} steps passed, {stats['steps_failed']} failed, {stats['steps_skipped']} skipped, {stats['steps_undefined']} undefined",
        duration_str
    ]
    return "\n".join(summary_lines)


def before_all(context):
    # Limpiar handlers existentes
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()
    
    # Configurar logger principal
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    logging.root.addHandler(console_handler)
    
    # Configurar nivel de logging desde variable de entorno
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.root.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Configurar logger de diagnóstico una sola vez
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
    
    logging.info("Inicio de pruebas")
    
    # Inicializar estadísticas
    context._runner.summary = {
        'scenarios_passed': 0,
        'scenarios_failed': 0,
        'scenarios_skipped': 0,
        'steps_passed': 0,
        'steps_failed': 0,
        'steps_skipped': 0,
        'steps_undefined': 0
    }
    
    # Lista para guardar los logs de todas las features ejecutadas
    context.all_feature_logs = []    

def after_all(context):
    # 1. Leemos la variable de entorno directamente porque la variable del context 
    # (context.generate_evidence) ya fue destruida por Behave a este nivel.
    evidence_env = os.getenv("GENERATE_EVIDENCE", "false").lower()
    
    # Generar el reporte consolidado si las evidencias están activas
    if evidence_env == "true":
        from utils.PDFFeatureReport import PDFFeatureReport
        if hasattr(context, 'all_feature_logs') and context.all_feature_logs:
            logging.info("Generando reporte PDF consolidado...")
            try:
                reporte_final = PDFFeatureReport.generate_consolidated_report(context.all_feature_logs)
                logging.info(f"Reporte consolidado listo: {reporte_final}")
            except Exception as e:
                logging.error(f"Fallo al generar reporte consolidado: {str(e)}")    
    
    # Limpiar handlers para soltar los archivos .txt
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)
               