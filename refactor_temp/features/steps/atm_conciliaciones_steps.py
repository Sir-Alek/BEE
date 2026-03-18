from behave import *
from pages.atm_conciliaciones_page import ATMConciliacionesPage
from environment import *

# ---> Steps globales 

# Acceso conciliaciones
@given('Ingresar al portal de Conciliaciones')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        # context.driver.get(context.dataset["url_atm_conciliacion"])
        # context.conciliaciones.send_username(context.dataset["user_qa"])
        # context.conciliaciones.send_password(context.dataset["pass_qa"])
        context.driver.get(context.dataset["url_conciliacion_qa"])
        context.conciliaciones.send_username(context.dataset["usuario"])
        context.conciliaciones.send_password(context.dataset["contrasena"])
        context.conciliaciones.click_login()
        context.conciliaciones.validar_acceso_conciliaciones(tomar_evidencia=context.generate_evidence, step='01_given')

# Seleccionar fecha a consultar, genera reporte diario                
@when('Selecionar Fecha a Consultar')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.seleccionar_fecha(tomar_evidencia=context.generate_evidence, step='02_when')              

# Visualizar detalle de cajero
@then('El sistema muestra El detalle del cajero')                    
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_detalle_cajero(tomar_evidencia=context.generate_evidence, step='05_then') 

# Visualizar reporte cajeros tabla deposito  
@then('El sistema muestra correctamente el reporte de cajeros coincidiendo con lo que indica la tabla deposito superior')                
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='04_then')

# Visualizar reporte cajeros tabla retiro 
@then('El sistema muestra correctamente el reporte de cajeros coincidiendo con lo que indica la tabla retiro superior')                
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='04_then')
                
# Visualziar registro cajeros en ceros
@then('El sistema muestra en Ceros el registro de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='04_then')
        
@then('El sistema permite la descarga del archivo Excel')                     
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)  
        context.conciliaciones.validar_descarga_reporte_excel(tomar_evidencia=context.generate_evidence, step='05_then')        

# Visualizar datos de fecha distinta
@then('Vizualizamos datos de la fecha distinta consultada en el dashboard')
def step_impl(context):                         
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_fecha_seleccionada(tomar_evidencia=context.generate_evidence, step='04_then')
        
# Descarga el excel en outputs y valida su contenido        
@then('El sistema permite la descarga del archivo Excel y valida su contenido')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        # columnas_req = ["DepositoStat"] 
        columnas_req = None
        context.conciliaciones.descargar_y_validar_excel(columnas=columnas_req,
            tomar_evidencia=context.generate_evidence,
            step='04_then'
        )      
        
# Abre el excel FORMULA, en resources/utils        
@then('Abrimos el archivo FORMULA, el calculo indica que los porcentajes son correctos')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)           
        context.conciliaciones.validar_archivo_formula(
        tomar_evidencia=context.generate_evidence,
        step='04_then'
    )
                

# ---> Tests
                
# test_ATM_AT_CON_CP001_Validar_Selector_de_Fechas                      
@then('Vizualizamos datos de la fecha consultada en el dashboard')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_fecha_seleccionada(tomar_evidencia=context.generate_evidence, step='03_then')  
                
                
# test_ATM_AT_CON_CP002_Validar_Grafica_Comportamiento_ATMs      
@then('Vizualizamos la Grafica de comportamiento de ATMs')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_grafica_pastel_reporte_diario(tomar_evidencia=context.generate_evidence, step='03_then')       


# test_ATM_AT_CON_CP003_Validar_Grafica_de_Reporte_Diario               
@then('El sistema muestra numero de cajeros conciliados')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.posicionar_cursor_barras(tomar_evidencia=context.generate_evidence, step='03_then')     


# test_ATM_AT_CON_CP004_Descarga_de_Reporte_Diario
@when('Dar click en la opción de descarga del reporte y elegir la opción de descarga')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.download_incidencias_csv(tomar_evidencia=context.generate_evidence, step='03_and')

@then('El sistema permite la descarga del archivo')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_descarga_reporte_csv(tomar_evidencia=context.generate_evidence, step='04_then')

                
# test_ATM_AT_CON_CP006_Descarga_de_Reporte_General
@when('Se selecciona opcion de descarga de excel en Cifras Generales')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.click_download_excel_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP007_Validar_Vinculos_de_Navegacion
@when('Desplegamos el menu de opciones, seleccionamos Cifras Generales Depositos y Cajeros Conciliados')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_cifras_grales_depositos(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='04_and')
        
@then('El sistema manda a Cajeros Conciliados')   
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='05_then')


# test_ATM_AT_CON_CP008_Revisar_Datos_Tabla_Cifras_Generales
# test_ATM_AT_CON_CP043_Total_TX_STAT
# test_ATM_AT_CON_CP044_Importe_total_STAT
# test_ATM_AT_CON_CP053_Total_STAT
@when('Se selecciona opcion de descarga de excel en cajeros sin STAT')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.click_download_excel_cajeros_sin_stat(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP009_Descargar_TXT_Tabla_Cifras_Generales
@when('Se selecciona opcion de descarga de TXT')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.click_btn_download_txt_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='03_and')

@then('El sistema permite la descarga del archivo txt y valida su contenido')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        textos_req = None 
        # Invocamos la orquestación maestra
        context.conciliaciones.descargar_y_validar_txt(
            textos=textos_req,
            tomar_evidencia=context.generate_evidence,
            step='04_then'
        )


# test_ATM_AT_CON_CP010_Descargar_Excel_Tabla_Cifras_Generales
@when('Se selecciona opcion de descarga de excel en cajeros conciliados')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.click_download_excel_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP011_Filtrar_Tabla_Cifras_Generales 
@when('Selecciona del combo Cifras generales retiros y depositos')
def step_imp(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_cifras_grales_retiros(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.validar_tabla_cifras_generales(tomar_evidencia=context.generate_evidence, step='04_then')
        context.conciliaciones.select_cifras_grales_depositos(tomar_evidencia=context.generate_evidence, step='05_and')
        
@then('El sistema muestra la tabla de Cifras generales')
def step_imp(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_cifras_generales(tomar_evidencia=context.generate_evidence, step='06_then')
        

# test_ATM_AT_CON_CP012_Revisar_Datos_Tabla_vs_Grafica_Reporte_Diario
@when('Se mueve el mouse a la barra de las distintas opciones y muestra el importe')
def step_imp(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.posicionar_barras_conciliado(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_conciliado_rd()
        context.conciliaciones.posicionar_barras_no_conciliado(tomar_evidencia=context.generate_evidence, step='04_and')
        context.conciliaciones.click_no_conciliado_rd()        
        context.conciliaciones.posicionar_barras_sin_journal(tomar_evidencia=context.generate_evidence, step='05_and')
        
@then('La tabla coincide con los importes')     
def step_imp(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)   
        context.conciliaciones.validar_tabla_cifras_generales(tomar_evidencia=context.generate_evidence, step='06_then')


# test_ATM_AT_CON_CP014_Revisar_Semaforo_Importe_Txs_Conciliado
@when('Nos dirigimos a la seccion de semaforos')
def step_imp(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver) 
        context.conciliaciones.validar_semaforos(tomar_evidencia=context.generate_evidence, step='03_and')  
        

# test_ATM_AT_CON_CP015_Revisar_Datos_Reporte_Cajeros_Conciliados
@when('Nos dirigimos a la seccion de Cifras e importes Generales')
def step_imp(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver) 
        context.conciliaciones.click_download_excel_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='03_and')
        

#test_ATM_AT_CON_CP016_Revisar_Semáforo_Txs_Conciliadas  
@when('Nos dirigimos a la secciones de Cifras generales y semaforos')            
def step_imp(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver) 
        context.conciliaciones.validar_tabla_cifras_generales(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.validar_semaforos(tomar_evidencia=context.generate_evidence, step='04_and')
        

# test_ATM_AT_CON_CP018_Revisar_Reporte_Cajeros_Sin_Journal_Solo_Stat
@when('Ingresa a la seccion Deposito, cajeros sin journal y selecciona opcion de descarga de Excel')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_sin_journal(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_download_excel_cajeros_sin_journal(tomar_evidencia=context.generate_evidence, step='04_and')      
                
                
# test_ATM_AT_CON_CP024_Revisar_Tabla_de_Deposito_Cajero_conciliados
@when('Ingresa a la seccion Deposito, cajeros conciliados y selecciona opcion de descarga de Excel')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_download_excel_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='04_and')      
                
@then('El sistema muestra unicamente transacciones Deposito - Cajero conciliados')   
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='05_then')


# test_ATM_AT_CON_CP025_Revisar_Tabla_de_Retiro_Cajero_conciliados
@when('Ingresa a la seccion Retiros, cajeros conciliados y selecciona opcion de descarga de Excel')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_retiros_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_download_excel_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='04_and')     
                
@then('El sistema muestra unicamente transacciones Retiro - Cajeros conciliados')                
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='05_then')


# test_ATM_AT_CON_CP026_Revisar_Detalle_de_ID_de_Deposito_Cajero_conciliados
# test_ATM_AT_CON_CP054_deposito_cajero_conciliado
# test_ATM_AT_CON_CP060_Detalle_deposito_conciliado
@when('ingresa a la seccion Deposito - Cajero conciliados y selecciona el cajero PH0008')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_conciliados(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_ph0008(tomar_evidencia=context.generate_evidence, step='04_and')           


# test_ATM_AT_CON_CP028_Revisar_Tabla_de_Deposito_Cajeros_Con_Diferencia_TRX_Conciliadas
# test_ATM_AT_CON_CP030_Revisar_Detalle_de_ID_de_Deposito_Cajeros_Con_Diferencia_TRX_Conciliadas  
# test_ATM_AT_CON_CP055_deposito_cajero_con_diferencia_TRX_conciliadas
@when('Ingresa a la seccion Deposito - Cajeros Con Diferencia y ver la tabla de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_con_diferencia(tomar_evidencia=context.generate_evidence, step='03_and')
                

# test_ATM_AT_CON_CP029_Revisar_Tabla_de_Retiro_Cajeros_Con_Diferencia_TRX_Conciliadas
# test_ATM_AT_CON_CP031_Revisar_Detalle_de_ID_de_Retiro_Cajeros_Con_Diferencia_TRX_Conciliadas
@when('Ingresa a la seccion Retiro - Cajeros Con Diferencia y ver la tabla de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_retiros_cajeros_con_diferencia(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP032_Revisar_Tabla_de_Deposito_Cajeros_con_diferencia_TRX_no_Conciliadas  
# test_ATM_AT_CON_CP049_Cajero_con_diferencia_TRX_no_conciliadas            
# test_ATM_AT_CON_CP056_deposito_cajero_con_diferencia_TRX_no_conciliadas
@when('Ingresa a la seccion Deposito - Cajeros Con Diferencia no conciliada y ver la tabla de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_con_diferencia_no_conciliada(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP033_Revisar_Tabla_de_Retiro_Cajeros_Con_Diferencia_TRX_no_Conciliadas
@when('Ingresa a la seccion Retiro - Cajeros Con Diferencia no conciliada y ver la tabla de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_retiros_cajeros_con_diferencia_no_conciliada(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP034_Revisar_Detalle_de_ID_de_Deposito_Cajeros_Con_Diferencia_TRX_no_Conciliadas
# test_ATM_AT_CON_CP047_Cajero_conciliado
@when('Ingresa a la seccion Deposito - Cajero no conciliados y selecciona el cajero PH0008')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_con_diferencia_no_conciliada(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_ph0008(tomar_evidencia=context.generate_evidence, step='04_and')


# test_ATM_AT_CON_CP036_Revisar_Tabla_de_Deposito_Cajeros_sin_Journal_TRX_solo_Stat
# test_ATM_AT_CON_CP050_Cajero_sin_Journal
@when('Ingresa a la seccion Deposito - Cajeros sin Journal y ver la tabla de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_sin_journal(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP037_Revisar_Tabla_de_Retiro_Cajeros_sin_Journal_TRX_solo_Stat
@when('Ingresa a la seccion Retiro - Cajeros sin Journal y ver la tabla de cajeros')
def step_impl(context): 
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_retiros_cajeros_sin_journal(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP040_Validar_Grafica_Reporte_Diario_seleccion_filtros
@when('Se quita No conciliado y Sin Journal en reporte diario')
def step_impl(context): 
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.click_no_conciliado_rd(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_sin_journal_rd(tomar_evidencia=context.generate_evidence, step='04_and')   
        context.conciliaciones.click_conciliado_rd(tomar_evidencia=context.generate_evidence, step='05_and')
        context.conciliaciones.click_no_conciliado_rd(tomar_evidencia=context.generate_evidence, step='06_and')
        context.conciliaciones.click_no_conciliado_rd(tomar_evidencia=context.generate_evidence, step='07_and')                                 
        context.conciliaciones.click_sin_journal_rd(tomar_evidencia=context.generate_evidence, step='08_and')
        
@then('El sistema muestra unicamente Sin Journal')
def step_impl(context): 
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.posicionar_cursor_barras(tomar_evidencia=context.generate_evidence, step='09_then')


# test_ATM_AT_CON_CP041_Cambio_de_mes
@when('Selecciona mes diferente a Consultar')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.seleccionar_fecha_diferente_mes(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP042_Cambio_de_año
@when('Selecciona año diferente a Consultar')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.seleccionar_fecha_diferente_year(tomar_evidencia=context.generate_evidence, step='03_and')


# test_ATM_AT_CON_CP047_Cajero_conciliado
# test_ATM_AT_CON_CP054_deposito_cajero_conciliado
# test_ATM_AT_CON_CP056_deposito_cajero_con_diferencia_TRX_no_conciliadas
@then('El sistema muestra El detalle del cajero completo')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.desplazar_tabla_al_final(tomar_evidencia=context.generate_evidence, step='04_then')


# test_ATM_AT_CON_CP048_Cajero_con_diferencia_TRX_conciliadas
# test_ATM_AT_CON_CP049_Cajero_con_diferencia_TRX_no_conciliadas
# test_ATM_AT_CON_CP050_Cajero_sin_Journal}
# test_ATM_AT_CON_CP055_deposito_cajero_con_diferencia_TRX_conciliadas
@then('Se visualiza la tabla de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='04_then')


# test_ATM_AT_CON_CP052_Subtotal_conciliados
@then('El sistema valida que coincidan los importes')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_cifras_generales


# test_ATM_AT_CON_CP057_deposito_cajero_sin_Journal
@when('Ingresa a la seccion Deposito - Cajeros sin Journal y selecciona el cajero PH0191')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_sin_journal(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_ph0191(tomar_evidencia=context.generate_evidence, step='04_and') 
        
        
# test_ATM_AT_CON_CP059_Detalle_deposito_cajero
@when('Ingresa a la seccion Deposito - Reporte general y selecciona el cajero PH0008')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_reporte_general(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_ph0008(tomar_evidencia=context.generate_evidence, step='04_and')
        
        
# test_ATM_AT_CON_CP061_Detalle_deposito_no_conciliado
@when('Ingresa a la seccion Deposito - Cajeros Con Diferencia y selecciona el cajero PH0008')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_cajeros_con_diferencia(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_ph0008(tomar_evidencia=context.generate_evidence, step='04_and')


# test_ATM_AT_CON_CP062_Descarga_Excel_depositos
@when('Ingresa a la seccion Deposito - Reporte general y selecciona boton descargar Excel')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_reporte_general(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='04_and')
        context.conciliaciones.click_btn_exportar_excel(tomar_evidencia=context.generate_evidence, step='05_and')
        

# test_ATM_AT_CON_CP063_Descarga_CSV_depositos
@when('Ingresa a la seccion Deposito - Reporte general y selecciona boton descargar CSV')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_reporte_general(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='04_and')
        context.conciliaciones.click_btn_exportar_csv(tomar_evidencia=context.generate_evidence, step='05_and')


# test_ATM_AT_CON_CP064_Buscador_deposito_por_cajero
@when('Ingresa a la seccion Deposito - Reporte general y ver la tabla de cajeros')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_reporte_general(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='04_and')
        
@then('Se da click en el buscador y muestra unicamente el cajero PH0008')        
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.click_filtro_id(tomar_evidencia=context.generate_evidence, step='05_then')
        context.conciliaciones.validar_cajero_ph0008(tomar_evidencia=context.generate_evidence, step='06_then')
        

# test_ATM_AT_CON_CP065_Paginacion_depositos
@when('Ingresa a la seccion Deposito - Reporte general y dar click en el boton siguiente')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.select_operativa_depositos_reporte_general(tomar_evidencia=context.generate_evidence, step='03_and')
        context.conciliaciones.click_boton_siguiente(tomar_evidencia=context.generate_evidence, step='04_and')

@then('El sistema muestra la siguiente pagina')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.validar_tabla_registros(tomar_evidencia=context.generate_evidence, step='05_then')


# test_ATM_AT_CON_CP066_Sin_datos_depositos
@when('Seleccionar una fecha sin datos')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)
        context.conciliaciones.seleccionar_fecha_sin_datos(tomar_evidencia=context.generate_evidence, step='03_and')

@then('El sistema no muestra informacion en esta fecha')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)    
        context.conciliaciones.validar_sin_datos_en_fecha(tomar_evidencia=context.generate_evidence, step='04_then')


# test_ATM_AT_CON_CP068_Acceso_reporte_general_retiros
@when('Desplazarse a cifras generales e ingresar a reporte general')
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)   
        context.conciliaciones.posicionar_cifras_generales(tomar_evidencia=context.generate_evidence, step='03_and')      
        context.conciliaciones.select_operativa_retiros_reporte_general(tomar_evidencia=context.generate_evidence, step='04_and')                                      
        
@then('El sistema muestra el reporte general de Retiros')  
def step_impl(context):
        context.conciliaciones = ATMConciliacionesPage(context.driver)     
        context.conciliaciones.validar_reporte_general_retiros(tomar_evidencia=context.generate_evidence, step='05_then')           