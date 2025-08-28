import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


class Browsers():
    @staticmethod
    def choose_browser(selection):
        if selection == 'chrome':
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-webgl')

            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument('--start-maximized')

            # Ruta local de respaldo
            local_driver_path = os.path.join(
                os.path.dirname(__file__), "drivers", "chromedriver.exe"
            )

            try:
                service = ChromeService(ChromeDriverManager().install())
                chrome_driver = webdriver.Chrome(service=service, options=chrome_options)
                logging.info("✅ Chrome iniciado con WebDriverManager")
                return chrome_driver
            except Exception as e:
                logging.error(f"❌ Error con WebDriverManager: {str(e)}")
                logging.info("🔄 Intentando con ChromeDriver local...")

                try:
                    service = ChromeService(local_driver_path)
                    chrome_driver = webdriver.Chrome(service=service, options=chrome_options)
                    logging.info("✅ Chrome iniciado con driver local")
                    return chrome_driver
                except Exception as e2:
                    logging.critical(f"🚨 Error también con driver local: {str(e2)}")
                    raise
                   