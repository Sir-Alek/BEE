from utils.button_functions import *
import os

class ATMConciliacionesPage:
    def __init__(self, driver):
        self.driver = driver
        
        # Locators
        self.lbl_username = "//input[@id='username']" 
        self.lbl_password = "//input[@id='password']"
        self.btn_login = "//button[@id='btn-signin']"
        self.tittle_conciliaciones = "//h3[normalize-space(.)='DSC Conciliación']"
        self.input_fecha = "//input[@id='fecha']"
        self.img_grafica_pastel_reporte_diario = "//div[@id='pastel']//div[contains(@class,'apexcharts-canvas')]"
        self.txt_sin_datos_en_fecha = "//*[name()='text' and contains(text(),'Sin datos disponibles')]"
        self.img_barras_reporte_diario = "//div[@id='Dias']"
        self.option_rd_conciliado = "//span[contains(@class,'apexcharts-legend-text') and normalize-space(.)='Conciliado']"
        self.option_rd_no_conciliado = "//span[contains(@class,'apexcharts-legend-text') and normalize-space(.)='No Conciliado']"
        self.option_rd_sin_journal = "//span[contains(@class,'apexcharts-legend-text') and normalize-space(.)='Sin Journal']"
        self.img_barras_conciliado = "(//*[name()='g' and @seriesName='Conciliado']//*[name()='path' and contains(@class,'apexcharts-bar-area')])[1]"
        self.img_barras_no_conciliado = "(//*[name()='g' and @seriesName='NoxConciliado']//*[name()='path' and contains(@class,'apexcharts-bar-area')])[1]"
        self.img_barras_sin_journal = "(//*[name()='g' and @seriesName='SinxJournal']//*[name()='path' and contains(@class,'apexcharts-bar-area')])[4]"
        self.menu_reporte_diario = "//div[@class='apexcharts-menu-icon']"
        self.drop_cifras= "//select[@id='inputcifras']"
        self.tabla_cifras_generales = "//table[@class='table table-striped text-center']"
        self.txt_cajeros_conciliados = "//a[@href='/Deposito/CConciliados/']"
        self.txt_deposito_cajero_conciliados = "//h5[normalize-space(.)='Depósito - Cajero conciliados']"
        self.option_download_csv = "//div[contains(@class, 'apexcharts-menu-item exportCSV') and contains(text(), 'Download CSV')]"
        self.btn_dwnl_excel_conciliacion_cajeros = "//button[@onclick=\"descargarExcel('1) Cajeros Conciliados');\"]"
        self.button_operativa = "//button[@id='dropdownMenuLink']"
        self.option_depositos = "//a[contains(@class, 'dropdown-item') and contains(normalize-space(), 'Depósitos')]"
        self.option_retiros = "//a[contains(@class, 'dropdown-item') and contains(normalize-space(), 'Retiros')]"   
        self.option_depositos_reporte_general = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Deposito/ReporteGeneral')]"     
        self.option_depositos_cajeros_sin_journal = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Deposito/CSinJournal')]"
        self.option_depositos_cajeros_con_diferencia = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Deposito/CDiferenciaConciliada')]"
        self.option_depositos_cajeros_conciliados = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Deposito/CConciliados')]"  
        self.option_depositos_cajeros_con_diferencia_no_conciliada = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Deposito/CDiferenciaNoConciliada')]"
        self.option_retiros_cajeros_conciliados = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Retiro/CConciliados')]" 
        self.option_retiros_cajeros_con_diferencia = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Retiro/CDiferenciaConciliada')]" 
        self.option_retiros_cajeros_con_diferencia_no_conciliada = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Retiro/CDiferenciaNoConciliada')]"
        self.option_retiros_cajeros_sin_journal = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Retiro/CSinJournal')]"
        self.option_retiros_reporte_general = "//a[contains(@class, 'dropdown-item') and contains(@href, '/Retiro/RGRetiro')]"
        self.btn_siguiente = "//li[@id='Deposito_next']"
        self.img_semaforos = "//div[@class='row'][.//div[@id='TCajeros']]"
        self.txt_retiro_reporte_general = "//h5[normalize-space(.)='Retiro - Reporte general']"
        self.btn_dwnld_excel_cajeros_sin_journal = "//button[@onclick=\"descargarExcel('5) Cajeros sin Journal (TRX solo stat)');\"]"
        self.btn_dwnld_excel_cajeros_conciliados = "//button[@onclick=\"descargarExcel('1) Cajeros Conciliados');\"]"
        self.btn_dwnl_excel_cajeros_sin_stat = "//button[@onclick=\"descargarExcel('Cajeros sin STAT (solo Journal)');\"]"
        self.btn_dwnl_txt_cajeros_conciliados = "//button[@onclick=\"descargarTXT('1) Cajeros Conciliados');\"]"
        self.tabla_registros = "//table[@id='Deposito' or @id='Retiro']"
        self.btn_id = "//th[normalize-space()='ID']"
        self.tabla_deposito = "//table[@id='Deposito']"
        self.id_ph0008 = "//a[contains(@href, '/Deposito/DetalleDeposito/') and contains(@href, '/2025-05-05/PH0008')]"
        self.tabla_detalle_cajero = "//table[@id='Detalle']"
        self.btn_conciliado_rd = "//div[contains(@class,'apexcharts-legend-series')][.//span[normalize-space(.)='Conciliado']]"
        self.btn_no_conciliado_rd = "//div[contains(@class,'apexcharts-legend-series')][.//span[normalize-space(.)='No Conciliado']]"
        self.btn_sin_journal_rd = "//div[contains(@class,'apexcharts-legend-series')][.//span[normalize-space(.)='Sin Journal']]"
        self.txt_cifras_generales = "//h3[.//strong[normalize-space(.)='Cifras Generales']]"
        self.btn_exportar_excel = "//button[@title='Excel']"
        self.btn_exportar_csv = "//button[@title='CSV']"


    # Actions
    def send_username(self, username):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.lbl_username,
            accion="insertTxt",              
            nombre_elemento="Input_Username",
            valor=username  
        )
    
    def send_password(self, password):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.lbl_password,
            accion="insertTxt",              
            nombre_elemento="Input_Password",
            valor=password  
        )    
            
    def click_login(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_login,
            accion="click",              
            nombre_elemento="Button_Login",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def validar_acceso_conciliaciones(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.tittle_conciliaciones,
            accion="highlight", 
            nombre_elemento="Title_Conciliaciones",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def seleccionar_fecha(self, tomar_evidencia=False, step=None):    
        set_flatpickr_date(
            self.driver, "2025-05-05", 
            input_locator=(By.ID, "fecha"), 
            flatpickr_format="Y-m-d",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )   
        
    def seleccionar_fecha_diferente_mes(self,tomar_evidencia=False, step=None):    
        set_flatpickr_date(
            self.driver, "2025-12-05", 
            input_locator=(By.ID, "fecha"), 
            flatpickr_format="Y-m-d",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )   
        
    def seleccionar_fecha_diferente_year(self, tomar_evidencia=False, step=None):    
        set_flatpickr_date(
            self.driver, "2026-01-05", 
            input_locator=(By.ID, "fecha"), 
            flatpickr_format="Y-m-d",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )    

    def seleccionar_fecha_sin_datos(self, tomar_evidencia=False, step=None):    
        set_flatpickr_date(
            self.driver, "2026-03-09", 
            input_locator=(By.ID, "fecha"), 
            flatpickr_format="Y-m-d",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )        
        
    def validar_fecha_seleccionada(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.input_fecha,
            accion="highlight", 
            nombre_elemento="Input_Fecha_Seleccionada",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )                   
        
    def validar_grafica_pastel_reporte_diario(self, tomar_evidencia=False, step=None):    
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.img_grafica_pastel_reporte_diario,
            accion="highlight", 
            nombre_elemento="Imagen_Grafica_Pastel_Reporte_Diario",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )   
        
    def validar_sin_datos_en_fecha(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.txt_sin_datos_en_fecha,
            accion="highlight", 
            nombre_elemento="Texto_Sin_Datos_en_Fecha",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )    
        
    def posicionar_cursor_barras(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.img_barras_reporte_diario,
            accion="highlight",
            nombre_elemento="Imagen_Barras_Reporte_Diario",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def click_conciliado_rd(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.option_rd_conciliado,
            accion="click",
            nombre_elemento="Option_Conciliado_RD",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def click_no_conciliado_rd(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.option_rd_no_conciliado,
            accion="click",
            nombre_elemento="Option_No_Conciliado_RD",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def click_sin_journal_rd(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.option_rd_sin_journal,
            accion="click",
            nombre_elemento="Option_Sin_Journal_RD",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )

    def posicionar_barras_conciliado(self, tomar_evidencia=False, step=None):
        ui_mouse_move(
            self.driver,
            xpath=self.img_barras_conciliado,
            nombre_elemento="Imagen_Barras_Conciliado",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step,
            timeout=15
        )
        
    def posicionar_barras_no_conciliado(self, tomar_evidencia=False, step=None):
        ui_mouse_move(
            self.driver,
            xpath=self.img_barras_no_conciliado,
            nombre_elemento="Imagen_Barras_No_Conciliado",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step,
            timeout=15
        )            
        
    def posicionar_barras_sin_journal(self, tomar_evidencia=False, step=None):
        ui_mouse_move(
            self.driver,
            xpath=self.img_barras_sin_journal,
            nombre_elemento="Imagen_Barras_sin_Journal",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step,
            timeout=15
        )
        
    def download_incidencias_csv(self, tomar_evidencia=False, step=None):
        click_root_and_click_submenu(
            driver=self.driver,
            root_xpath=self.menu_reporte_diario,
            submenu_click_xpath=self.option_download_csv,
            timeout=15,
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
            )     

    def validar_descarga_reporte_csv(self, extension=".csv", tomar_evidencia=False, step=None):
        ui_validate_download(
            extension=extension,
            timeout=30,
            nombre_elemento="Recibo_Descarga_Reporte",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def select_cifras_grales_depositos(self, tomar_evidencia=False, step=None):
        ui_select_native_dropdown(
            driver=self.driver,
            xPath_elemento=self.drop_cifras,
            valor_seleccion="2",               
            tipo_seleccion="value",
            nombre_elemento="Dropdown_Depositos",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )    
        
    def select_cifras_grales_retiros(self, tomar_evidencia=False, step=None):
        ui_select_native_dropdown(
            driver=self.driver,
            xPath_elemento=self.drop_cifras,
            valor_seleccion="1",               
            tipo_seleccion="value",
            nombre_elemento="Dropdown_Retiros",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )      
        
    def validar_tabla_cifras_generales(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.tabla_cifras_generales,
            accion="highlight", 
            nombre_elemento="Tabla_Cifras_Generales",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        ) 

    def click_cajeros_conciliados(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.txt_cajeros_conciliados,
            accion="click",              
            nombre_elemento="Link_Cajeros_Conciliados",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )    
        
    def validar_cajeros_conciliados(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.txt_deposito_cajero_conciliados,
            accion="highlight", 
            nombre_elemento="Texto_Cajeros_Conciliados",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def select_operativa_depositos_reporte_general(self, tomar_evidencia=False, step=None): 
        select_menu_option(
            driver=self.driver,
            root_xpath=self.button_operativa,
            submenu_hover_xpath=self.option_depositos,
            subsubmenu_click_xpath=self.option_depositos_reporte_general,
            timeout=15,
            pause=0.35,
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def select_operativa_depositos_cajeros_sin_journal(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_depositos,
        subsubmenu_click_xpath=self.option_depositos_cajeros_sin_journal,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step
        )  
        
    def select_operativa_depositos_cajeros_con_diferencia(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_depositos,
        subsubmenu_click_xpath=self.option_depositos_cajeros_con_diferencia,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step
        )  
        
    def select_operativa_depositos_cajeros_conciliados(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_depositos,
        subsubmenu_click_xpath=self.option_depositos_cajeros_conciliados,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step    
        )  
        
    def select_operativa_depositos_cajeros_con_diferencia_no_conciliada(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_depositos,
        subsubmenu_click_xpath=self.option_depositos_cajeros_con_diferencia_no_conciliada,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step
        )    
        
    def select_operativa_retiros_cajeros_conciliados(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_retiros,
        subsubmenu_click_xpath=self.option_retiros_cajeros_conciliados,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step
        )    
        
    def select_operativa_retiros_cajeros_con_diferencia(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_retiros,
        subsubmenu_click_xpath=self.option_retiros_cajeros_con_diferencia,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia, 
        screenshot_step=step
        )    
        
    def select_operativa_retiros_cajeros_con_diferencia_no_conciliada(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_retiros,
        subsubmenu_click_xpath=self.option_retiros_cajeros_con_diferencia_no_conciliada,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step
        )    
        
    def select_operativa_retiros_cajeros_sin_journal(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_retiros,
        subsubmenu_click_xpath=self.option_retiros_cajeros_sin_journal,
        timeout=15,
        pause=0.35,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step
        )    
        
    def select_operativa_retiros_reporte_general(self, tomar_evidencia=False, step=None):
        select_menu_option(
        driver=self.driver,
        root_xpath=self.button_operativa,
        submenu_hover_xpath=self.option_retiros,
        subsubmenu_click_xpath=self.option_retiros_reporte_general,
        timeout=15,
        pause=0.35,
        scroll_to_top=True,
        usar_create_screenshot=tomar_evidencia,
        screenshot_step=step
        ) 
        
    def click_boton_siguiente(self, tomar_evidencia=False, step=None):           
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_siguiente,
            accion="click",              
            nombre_elemento="Button_Siguiente",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )   

    def validar_semaforos(self, tomar_evidencia=False, step=None):  
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.img_semaforos,
            accion="highlight", 
            nombre_elemento="Imagen_Semaforos",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )   

    def validar_reporte_general_retiros(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.txt_retiro_reporte_general,
            accion="highlight", 
            nombre_elemento="Texto_Retiro_Reporte_General",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  

    def click_download_excel_cajeros_sin_journal(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_dwnld_excel_cajeros_sin_journal,
            accion="click",              
            nombre_elemento="Button_Download_Excel_Cajeros_Sin_Journal",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )    
        
    def click_download_excel_cajeros_conciliados(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_dwnld_excel_cajeros_conciliados,
            accion="click",              
            nombre_elemento="Button_Download_Excel_Cajeros_Conciliados",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def click_download_excel_cajeros_sin_stat(self, tomar_evidencia=False, step=None) :
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_dwnl_excel_cajeros_sin_stat,
            accion="click",              
            nombre_elemento="Button_Download_Excel_Cajeros_sin_STAT",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )     
        
    def click_btn_download_txt_cajeros_conciliados(self, tomar_evidencia=False, step=None): 
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_dwnl_txt_cajeros_conciliados,
            accion="click",              
            nombre_elemento="Button_Download_TXT_Cajeros_Conciliados",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )         
        
    def validar_descarga_reporte_excel(self, extension=(".xlsx", ".xlsb"), tomar_evidencia=False, step=None):
        ui_validate_download(
            extension=extension,
            timeout=30,
            nombre_elemento="Recibo_Descarga_Reporte",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )     
        
    def validar_datos_reporte_txt(self, ruta_archivo, textos_req=None, tomar_evidencia=False, step=None):
        ui_validate_txt_content(
            file_path=ruta_archivo,
            textos_esperados=textos_req,
            nombre_elemento="Datos_Reporte_TXT",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )     
        
    def validar_datos_reporte_excel(self, ruta_archivo, columnas=None, tomar_evidencia=False, step=None):
        ui_validate_excel_content(
            file_path=ruta_archivo,
            columnas_esperadas=columnas,
            nombre_elemento="Datos_Reporte_Excel",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )   
        
    def descargar_y_validar_excel(self, columnas=None, tomar_evidencia=False, step=None):
        """
        Espera la descarga del archivo y luego valida su contenido en memoria,
        generando una sola evidencia visual (los datos).
        """
        ruta_archivo = ui_validate_download(
            extension=(".xlsx", ".xlsb", ".csv"),
            timeout=30,
            usar_create_screenshot=False  
        )
        ui_validate_excel_content(
            file_path=ruta_archivo,
            columnas_esperadas=columnas,
            nombre_elemento="Datos_Reporte_Conciliaciones",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )         
        
    def descargar_y_validar_txt(self, textos=None, tomar_evidencia=False, step=None):
        """
        Espera la descarga del archivo TXT y luego valida su contenido en memoria,
        generando una sola evidencia visual de las líneas del archivo.
        """
        ruta_archivo = ui_validate_download(
            extension=".txt", 
            timeout=30,
            usar_create_screenshot=False  
        )
        ui_validate_txt_content(
            file_path=ruta_archivo,
            textos_esperados=textos,
            nombre_elemento="Datos_Reporte_TXT",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def validar_tabla_registros(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.tabla_registros,
            accion="highlight", 
            nombre_elemento="Tabla_Registros_Cajero",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def click_filtro_id(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_id,
            accion="click",              
            nombre_elemento="Button_Filtro_ID",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def desplazar_tabla_al_final(self, tomar_evidencia=False, step=None):
        scroll_horizontal_to_end(
        driver=self.driver,
        locator=self.tabla_deposito,
        highlight=True,
        usar_create_screenshot=tomar_evidencia, 
        screenshot_step=step,                   
        nombre_elemento="Tabla_Deposito_Fin_Scroll"
    )
    
    def click_ph0008(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.id_ph0008,
            accion="click",              
            nombre_elemento="Link_Detalle_Cajero_PH0008",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def validar_cajero_ph0008(self, tomar_evidencia=False, step=None):   
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.id_ph0008,
            accion="highlight", 
            nombre_elemento="Link_Detalle_Cajero_PH0008",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def validar_tabla_detalle_cajero(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.tabla_detalle_cajero,
            accion="highlight", 
            nombre_elemento="Tabla_Detalle_Cajero",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def click_conciliado_rd(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_conciliado_rd,
            accion="click",              
            nombre_elemento="Button_Conciliado_RD",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
    
    def click_no_conciliado_rd(self, tomar_evidencia=False, step=None):           
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_no_conciliado_rd,
            accion="click",              
            nombre_elemento="Button_No_Conciliado_RD",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )   
        
    def click_sin_journal_rd(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_sin_journal_rd,
            accion="click",              
            nombre_elemento="Button_Sin_Journal_RD",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )  
        
    def posicionar_cifras_generales(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.txt_cifras_generales,
            accion="highlight", 
            nombre_elemento="Texto_Cifras_Generales",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )       

    def validar_archivo_formula(self, tomar_evidencia=False, step=None):
        """
        Abre, valida y toma evidencia del archivo FORMULA.xlsx almacenado localmente.
        """
        ruta_archivo = os.path.join(os.getcwd(), 'resources', 'data', 'FORMULA.xlsx')
        if not os.path.exists(ruta_archivo):
            raise AssertionError(f"El archivo estático no se encontró en la ruta: {ruta_archivo}")
        
        columnas_req = None 
        ui_validate_excel_content(
            file_path=ruta_archivo,
            columnas_esperadas=columnas_req,
            nombre_elemento="Archivo_Base_FORMULA",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )          
        
    def click_btn_exportar_excel(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_exportar_excel,
            accion="click",              
            nombre_elemento="Button_Exportar_Excel",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )
        
    def click_btn_exportar_csv(self, tomar_evidencia=False, step=None):
        ui_interact(
            driver=self.driver,
            xPath_elemento=self.btn_exportar_csv,
            accion="click",              
            nombre_elemento="Button_Exportar_CSV",
            usar_create_screenshot=tomar_evidencia,
            screenshot_step=step
        )