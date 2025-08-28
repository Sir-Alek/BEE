from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


class Browsers():
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
            
            service = ChromeService(ChromeDriverManager().install())
            chrome_driver = webdriver.Chrome(service=service, options=chrome_options)
            return chrome_driver
                   