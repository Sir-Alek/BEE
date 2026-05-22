import os
import logging
from datetime import datetime
from utils.env_manager import *

def before_all(context):
    RunLogCoordinator.init_global_logger(context)
    RunStatsTracker.init_stats(context)
    logging.info("Inicio de pruebas")

def before_feature(context, feature):
    context.generate_evidence = os.getenv("GENERATE_EVIDENCE", "false").lower() == "true"
    RunLogCoordinator.setup_feature_logger(context, feature)

def before_scenario(context, scenario):
    context.start_time = datetime.now()
    headless_mode = os.getenv("HEADLESS", "true").lower() == "true"
    
    # 1. Levantar el navegador (incluye configs CDP, geolocalización, evasión)
    context.driver = BrowserSessionFactory.create_driver(headless_mode)
    
    # 2. Configurar contextos de Log y Datos
    context.diagnostic_logger = logging.getLogger('diagnostic')
    context.diagnostic_logger.info("\n✓ Iniciando escenario: %s", scenario.name)
    
    FeatureDatasetLoader.load_dataset(context)
    RunEvidenceCoordinator.setup_evidence(context, scenario)
    RunLogCoordinator.setup_scenario_logger(context, scenario)
    
    logging.info(f"\n✓ --> Iniciando escenario: {scenario.name}")
    logging.info(f"✓ Configuración completa - Evidencias: {context.generate_evidence}, Headless: {headless_mode}")

def after_step(context, step):
    RunLogCoordinator.log_step_diagnostics(context, step)
    
    if not context.generate_evidence:
        return
        
    # Extraemos el string puro del Enum
    step_status = step.status.name
        
    if step_status == "passed":
        logging.info(f"    [Step] PASADO: {step.keyword} {step.name}")
    elif step_status == "skipped":
        logging.warning(f"    [Step] OMITIDO: {step.keyword} {step.name}")
    elif step_status == "failed":
        if hasattr(context, 'driver'):
            bf.ui_inject_tab_indicator(context.driver, is_redirection=True)
        error_msg = RunEvidenceCoordinator.parse_step_error(context, step, str(step.exception) if step.exception else "")
        logging.error(f"    [Step] FALLIDO: {step.keyword} {step.name} - {error_msg}")
        RunEvidenceCoordinator.capture_failure(context, step)

def after_scenario(context, scenario):
    if hasattr(context, 'driver'):
        context.driver.quit()
        
    RunStatsTracker.update_stats(context, scenario)
    
    # Extraemos el string puro del Enum
    status_name = scenario.status.name
    
    if hasattr(context, 'start_time'):
        duration = datetime.now() - context.start_time
        context.diagnostic_logger.info("Escenario completado: %s | Duración: %s | Estado: %s", 
                                       scenario.name, duration, status_name)
    
    if context.generate_evidence:
        status_msg = {"passed": "PASADO", "failed": "FALLIDO", "skipped": "OMITIDO"}
        logging_fn = {"passed": logging.info, "failed": logging.error, "skipped": logging.warning}
        
        # Ahora la validación y el diccionario usan el string correctamente
        if status_name in status_msg:
            logging_fn[status_name](f"<-- Escenario {status_msg[status_name]}: {scenario.name}")
            
        logging.info("==== FIN DE LA EJECUCIÓN ====")     
        logging.info(f"Resultado: {'Ok' if status_name == 'passed' else 'FAILED'}")

        if hasattr(context, 'txt_filename') and hasattr(context, 'start_time'):
            end_time = datetime.now()
            duration_obj = end_time - context.start_time
            
            if hasattr(context, 'scenario_file_handler'):
                context.scenario_file_handler.flush()
                logging.root.removeHandler(context.scenario_file_handler)
                context.scenario_file_handler.close()
                delattr(context, 'scenario_file_handler')

            try:
                with open(context.txt_filename, 'a', encoding='utf-8') as f:
                    f.write(f"\nTook: {duration_obj}\n") 
            except Exception as e:
                logging.error(f"No se pudo escribir el Took en el log: {e}")
            
            screenshots = getattr(context, 'failure_screenshots', None)
            RunReportPublisher.generate_scenario_report(context, scenario, end_time, screenshots)

def after_feature(context, feature):
    RunLogCoordinator.consolidate_feature_logs(context, feature)

def after_all(context):
    RunReportPublisher.generate_consolidated_report(context)
    
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)
