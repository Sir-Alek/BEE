from fpdf import FPDF
import os
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np
import re

class PDFFeatureReport(FPDF):
    def __init__(self):
        super().__init__()
        self.feature_name = ""
        self.execution_date = ""
        self.duration = ""
        self.scenarios = []
    
    def header(self):
        # Logo de BEE con validación de existencia
        logo_path = os.path.join('resources', 'logo_bee_png_transparente.png')
        
        # Título con espacio ajustado
        self.set_y(35)
        self.set_font('helvetica', 'B', 13)
        self.cell(0, 10, 'Reporte de Pruebas Automatizadas', 0, 1, 'C')
        
        # Fecha y duración
        self.set_font('helvetica', '', 11)
        self.cell(0, 8, f'Fecha de ejecución: {self.execution_date}', 0, 1, 'C')
        self.cell(0, 8, f'Duración total: {self.duration}', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')
    
    def create_pie_chart(self, passed, failed):
        plt.figure(figsize=(6, 6))  # Figura cuadrada
        sizes = [passed, failed]
        labels = ['Exitosos', 'Fallidos']
        colors = ['#4CAF50', '#F44336']
        
        if passed + failed == 0:
            sizes = [1]
            labels = ['Sin datos']
            colors = ['#CCCCCC']
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
        
        # Asegurar aspecto circular
        plt.axis('equal')
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        return buffer
    
    def add_summary_section(self, passed=None, failed=None):
        # Permitir pasar estadísticas externas (para el resumen consolidado)
        if passed is None or failed is None:
            total = len(self.scenarios)
            passed = sum(1 for s in self.scenarios if s.get('status', '').upper() in ['EXITOSO', 'PASSED'])
            failed = total - passed
        
        success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0.0
        
        # Gráfica
        chart_buffer = self.create_pie_chart(passed, failed)
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'Resumen de Resultados', 0, 1, 'C')
        self.image(chart_buffer, x=60, y=self.get_y(), w=80, h=80)
        self.ln(85)
        
        # Estadísticas
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(0, 128, 0)
        self.cell(0, 10, f'Exitosos: {passed} ({success_rate:.1f}%)', 0, 1, 'C')
        self.set_text_color(255, 0, 0)
        self.cell(0, 10, f'Fallidos: {failed} ({100 - success_rate:.1f}%)', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(10)        
    
    def add_feature_section(self):
        self.set_font('helvetica', 'B', 14)
        self.cell(0, 10, f'Feature: {self.feature_name}', 0, 1)
        self.ln(8)
        
        col_widths = [140, 50] 
        
        # Encabezados
        self.set_font('helvetica', 'B', 11)
        self.set_fill_color(23, 124, 214)
        self.set_text_color(255, 255, 255)
        
        self.cell(col_widths[0], 10, 'Escenario', 1, 0, 'L', fill=True)
        self.cell(col_widths[1], 10, 'Estado', 1, 1, 'C', fill=True)
        
        # Contenido
        self.set_font('helvetica', '', 8)
        self.set_text_color(0, 0, 0)
        
        for scenario in self.scenarios:
            self.cell(col_widths[0], 10, scenario.get('name', 'N/A'), 1, 0, 'L')
            
            status = scenario.get('status', 'N/A').upper()
            if status in ['EXITOSO', 'PASSED']:
                self.set_text_color(0, 128, 0)
            else:
                self.set_text_color(255, 0, 0)
                
            self.cell(col_widths[1], 10, status, 1, 1, 'C')
            self.set_text_color(0, 0, 0)
    
    def _count_text_lines(self, text, max_width):
        """Calcula cuántas líneas ocupará el texto dado el ancho máximo"""
        if not text:
            return 1
            
        words = text.split(' ')
        lines = 1
        current_width = 0
        
        for word in words:
            word_width = self.get_string_width(word + ' ')
            if current_width + word_width > max_width:
                lines += 1
                current_width = word_width
            else:
                current_width += word_width
        
        return lines
    

    @staticmethod
    def parse_log_file(log_path):
        """Analiza el archivo de log y extrae información estructurada"""        
        data = {
            'feature': '',
            'scenarios': [],
            'duration': '0m0.000s',
            'start_time': None,
            'end_time': None
        }
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
                
                # Extraer feature name
                feature_match = re.search(r'==== INICIO DE FEATURE:\s*(.+?)\s*====', log_content)
                if feature_match:
                    data['feature'] = feature_match.group(1).strip()
                    
                # Extraer duración                
                duration_match = re.search(r'Took\s(.+?)$', log_content, re.MULTILINE)
                if duration_match:
                    data['duration'] = duration_match.group(1).strip()
                
                # Extraer escenarios únicos
                scenario_status = {}
                matches = re.finditer(
                    r'Iniciando escenario:\s*(.+?)\s*$.*?Escenario completado:.*?\|\s*Estado:\s*(passed|failed)',
                    log_content,
                    re.DOTALL | re.MULTILINE
                )
                
                for match in matches:
                    scenario_name = match.group(1).strip()
                    status = 'EXITOSO' if match.group(2).lower() == 'passed' else 'FALLIDO'
                    scenario_status[scenario_name] = status  # Usamos diccionario para evitar duplicados
                
                # Convertir a lista de escenarios
                data['scenarios'] = [{'name': name, 'status': status} 
                                    for name, status in scenario_status.items()]
                
                # Si no encontramos escenarios, intentar con formato alternativo
                if not data['scenarios']:
                    starts = [(m.start(), m.group(1)) for m in re.finditer(r'Iniciando escenario:\s*(.+?)\s*$', log_content)]
                    ends = [(m.start(), m.group(1), m.group(2)) for m in re.finditer(
                        r'Escenario completado:\s*(.+?)\s*\|\s*Duración:.+?\|\s*Estado:\s*(passed|failed)', 
                        log_content)]
                    
                    if len(starts) == len(ends):
                        for start, end in zip(starts, ends):
                            data['scenarios'].append({
                                'name': start[1],
                                'status': 'EXITOSO' if end[2].lower() == 'passed' else 'FALLIDO'
                            })
        
        except Exception as e:
            logging.error(f"Error al analizar archivo de log: {str(e)}")
        
        return data

    
    @staticmethod
    def generate_feature_report(feature_name, feature_log_path):
        try:
            log_data = PDFFeatureReport.parse_log_file(feature_log_path)
            feature_name = log_data.get('feature', feature_name)
            
            # Crear PDF            
            pdf = PDFFeatureReport()
            pdf.feature_name = feature_name
            pdf.execution_date = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            pdf.duration = log_data.get('duration', '0m0.000s')
            pdf.scenarios = log_data.get('scenarios', [])
            
            pdf.alias_nb_pages()
            pdf.add_page()
            pdf.add_summary_section()
            pdf.add_feature_section()
            
            # Guardar PDF            
            output_dir = os.path.join('outputs', 'pdfReports')
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"ReporteFeature_{feature_name}_{timestamp}.pdf"
            pdf.output(os.path.join(output_dir, pdf_filename))
            
            # Metadatos            
            pdf.set_author(author='AppWhere-2025')
            pdf.set_creator('Bancoppel - AppWhere')
            
            return pdf_filename
            
        except Exception as e:
            logging.error(f"Error crítico al generar reporte: {str(e)}")
            raise

    @staticmethod
    def generate_consolidated_report(feature_log_paths):
        """Nuevo método para informe consolidado.
        feature_log_paths: Lista de rutas de logs de features.
        """
        try:
            pdf = PDFFeatureReport()
            pdf.alias_nb_pages()
            pdf.add_page()
            
            # Parsear todos los logs y acumular datos
            all_scenarios = []
            feature_data_list = []
            total_duration = 0
            
            for log_path in feature_log_paths:
                log_data = PDFFeatureReport.parse_log_file(log_path)
                feature_data_list.append({
                    'name': log_data.get('feature', os.path.basename(log_path)),
                    'scenarios': log_data.get('scenarios', []),
                    'duration': log_data.get('duration', '0m0.000s')
                })
                all_scenarios.extend(log_data.get('scenarios', []))
            
            # Resumen global
            passed = sum(1 for s in all_scenarios if s.get('status', '').upper() in ['EXITOSO', 'PASSED'])
            failed = len(all_scenarios) - passed
            
            pdf.execution_date = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            pdf.duration = "Varios features"  # O calcular duración total si es posible
            
            # Título consolidado
            pdf.set_font('helvetica', 'B', 16)
            pdf.cell(0, 10, 'REPORTE CONSOLIDADO DE PRUEBAS', 0, 1, 'C')
            pdf.ln(10)
            
            pdf.add_summary_section(passed, failed)
            
            # Sección por feature
            for feature_data in feature_data_list:
                pdf.add_page()
                pdf.feature_name = feature_data['name']
                pdf.scenarios = feature_data['scenarios']
                pdf.add_feature_section()
            
            # Guardar PDF
            output_dir = os.path.join('outputs', 'pdfReports')
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"ReporteConsolidado_{timestamp}.pdf"
            pdf.output(os.path.join(output_dir, pdf_filename))
            
            pdf.set_author(author='Sir-Alek-2026')
            pdf.set_creator('BEE - Sir-Alek')
            
            return pdf_filename
            
        except Exception as e:
            logging.error(f"Error generando reporte consolidado: {str(e)}")
            raise
        
# if __name__ == "__main__":
#     import logging
#     logging.basicConfig(level=logging.INFO)
    
#     # Configuración para pruebas
#     TEST_FEATURE_NAME = "OA_R1"
#     TEST_LOG_PATH = "outputs/logs/OA_R1_feature.txt"  # Ruta a tu log existente
    
#     try:
#         print("=== Iniciando prueba del generador de PDF ===")
#         pdf_filename = PDFFeatureReport.generate_feature_report(
#             feature_name=TEST_FEATURE_NAME,
#             feature_log_path=TEST_LOG_PATH
#         )
#         print(f"Reporte generado exitosamente: {pdf_filename}")
#     except Exception as e:
#         print(f"Error generando reporte: {str(e)}")
#         logging.exception("Error detallado:")        
