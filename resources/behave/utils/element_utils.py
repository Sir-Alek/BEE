# utils/element_utils.py
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import ActionChains
import time
import logging
import requests
import re
from selenium.webdriver.common.by import By
import os
from selenium import webdriver


class ElementUtils:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 62)
        self.long_wait = WebDriverWait (driver, 300)

    # ------------------------- Esperas y Elementos Básicos -------------------------
    def wait_for_element(self, locator: tuple) -> WebElement:
        return self.wait.until(EC.visibility_of_element_located(locator))

    def wait_for_element_to_be_clickable(self, locator: tuple) -> WebElement:
        return self.wait.until(EC.element_to_be_clickable(locator))
    
    def wait_for_message(self, locator: tuple) -> WebElement:
        return self.long_wait.until(EC.visibility_of_element_located(locator))
    
    def wait_for_next_action(self, locator: tuple) -> WebElement:
        return self.long_wait.until(EC.element_to_be_clickable(locator))

    # ------------------------- Efectos Visuales -------------------------
    def highlight_element(self, element: WebElement):
        try:
            self.driver.execute_script("arguments[0].style.border='3px solid red'", element)
        except WebDriverException:
            print("No se pudo resaltar el elemento")

    def unhighlight_element(self, element: WebElement):
        try:
            self.driver.execute_script("arguments[0].style.border=''", element)
        except WebDriverException:
            print("No se pudo quitar el resaltado")

    # ------------------------- Interacciones Básicas -------------------------
    def click_element(self, locator: tuple):
        element = None
        try:
            element = self.wait_for_element_to_be_clickable(locator)
            self.scroll_to_element(element)
            time.sleep(0.3)
            self.highlight_element(element)
            ActionChains(self.driver).move_to_element(element).click().perform()
        except Exception as e:
            error_msg = f"Error al hacer clic en {locator}: {str(e)}"
            logging.error(error_msg)
            # Guardar en contexto para capturarlo en after_step
            if hasattr(self, 'driver') and hasattr(self.driver, 'context'):
                self.driver.context.last_error_message = error_msg
            
            raise
        finally:
            if element:
                self.unhighlight_element(element)

    def send_text(self, locator: tuple, text: str):
        try:
            element = self.wait_for_element(locator)
            self.scroll_to_element(element)
            self.highlight_element(element)
            element.clear()
            element.send_keys(text)
            self.unhighlight_element(element)
        except TimeoutException:
            print(f"Campo no encontrado: {locator}")

    # ------------------------- Manejo de Dropdowns -------------------------
    def select_from_dropdown1(self, locator: tuple, visible_text: str):
        try:
            self.wait_for_element(locator)
            self.highlight_element(locator)
            locator.send_keys(visible_text)
            self.unhighlight_element(locator)
        except TimeoutException:
            print(f"Dropdown no encontrado: {locator}")
            
    def select_from_dropdown(self, click_function, option_text, wait_time=30):
        """
        Selecciona una opción de un dropdown list
        Args:
            click_function: función que abre el dropdown (ej: context.b2page.click_dlist_ingresos)
            option_text: texto de la opción a seleccionar
            wait_time: tiempo máximo de espera (default 30 segundos)
        """
        # Ejecuta la función que abre el dropdown
        click_function()
        time.sleep(1)  # Pequeña pausa para que se abra el dropdown
        # Espera y haz clic en la opción
        WebDriverWait(self.driver, wait_time).until(
            EC.visibility_of_element_located((By.XPATH, f"//*[contains(text(), '{option_text}')]"))
        ).click()            

    # ------------------------- Scrolls -------------------------
    def scroll_to_element(self, element: WebElement):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        except WebDriverException:
            print("Error al hacer scroll")

    def scroll_to_element_top(self, element: WebElement):
        try:
            self.driver.execute_script(
                "window.scrollTo(0, arguments[0].getBoundingClientRect().top);", 
                element
            )
        except WebDriverException:
            print("Error al desplazar a la parte superior")

    # ------------------------- Validación de Texto -------------------------
    def validate_text(
        self, 
        locator: tuple, 
        expected_text: str, 
        exact_match: bool = True
    ):
        """
        Valida que un elemento contenga un texto específico.
        - Si el texto no coincide, lanza AssertionError y falla el paso.
        - Si el elemento no existe, también falla.

        Parámetros:
            locator (tuple): Localizador del elemento (By, selector).
            expected_text (str): Texto esperado.
            exact_match (bool): True para validar texto exacto, False para substring.
        """
        element = None
        try:
            # Esperar a que el elemento sea visible
            element = self.wait_for_element(locator)
            self.highlight_element(element)
            actual_text = element.text.strip()

            # Validar según el tipo de coincidencia
            if exact_match:
                assert actual_text == expected_text, \
                    f"Texto esperado: '{expected_text}'. Texto real: '{actual_text}'"
            else:
                assert expected_text in actual_text, \
                    f"Texto '{expected_text}' no encontrado en: '{actual_text}'"

        except TimeoutException:
            raise AssertionError(f"Elemento {locator} no encontrado")
        except AssertionError as e:
            raise AssertionError(f"Validación fallida: {str(e)}")
        finally:
            if element:
                self.unhighlight_element(element)   
                
                
    # ------------------------- Excepción, subir comprobante de domicilio -------------------------                     
    def subir_comprobante_domicilio(self, b1page, nombre_archivo='comprobante_domicilio.pdf'):
        """
        Sube el comprobante de domicilio si detecta el mensaje correspondiente.
        Luego da clic en 'Continuar'.

        :param b1page: página donde está el método click_continuar()
        :param nombre_archivo: nombre del archivo que se encuentra en resources
        """
        try:
            # Verifica si está el texto "Sube un comprobante de tu domicilio"
            if b1page.verify_sube_comprobante_message():
                # Construye ruta del archivo
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                file_path = os.path.join(project_root, 'resources', nombre_archivo)
                # Verifica si el archivo realmente existe
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
                # Encuentra el input y sube el archivo
                file_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[data-testid='input'][type='file']"
                )
                file_input.send_keys(file_path)
                time.sleep(2)  # espera para asegurar carga
                # Da clic en continuar
                b1page.click_continuar()    
            else:
                print("No se encontró el mensaje de subir comprobante, se continúa el flujo.")
        except (NoSuchElementException, TimeoutException, FileNotFoundError, Exception) as e:
            raise AssertionError(f"Error al subir comprobante de domicilio: {e}")
        
    def switch_to_new_window(driver, timeout=10):
        original_window = driver.current_window_handle
        WebDriverWait(driver, timeout).until(lambda d: len(d.window_handles) > 1)
        for window in driver.window_handles:
            if window != original_window:
                driver.switch_to.window(window)        
