from fpdf import FPDF
import os
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import re

class PDFFeatureReport(FPDF):
    def __init__(self):
        super().__init__()
        self.feature_name = ""
        self.execution_date = ""
        self.duration = ""
        self.scenarios = []
    
    def header(self):
            # 1. Construimos la ruta absoluta al logo para evitar errores de "file not found"
            base_path = os.getcwd() 
            logo_path = os.path.join(base_path, 'resources', 'resourcesPDF', 'logo-servicios-financieros.jpg')
            
            # Verificamos si existe antes de intentar ponerlo
            if os.path.exists(logo_path):
                self.image(logo_path, x=70, y=15, w=60, h=15)
            else:
                # Si no encuentra la imagen, ponemos un texto de fallback para que no falle el reporte
                self.set_font('helvetica', 'I', 8)
                self.cell(0, 10, f'Logo no encontrado en: {logo_path}', 0, 1, 'C')

            # Título
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
        """
        Genera la gráfica y guarda el archivo físico temporalmente
        para evitar el error 'BytesIO object has no attribute rfind'
        """
        # Usamos subplots para limpiar la figura correctamente
        fig, ax = plt.subplots(figsize=(6, 6))
        
        sizes = [passed, failed]
        labels = ['Exitosos', 'Fallidos']
        colors = ['#4CAF50', '#F44336']
        
        if passed + failed == 0:
            sizes = [1]
            labels = ['Sin datos']
            colors = ['#CCCCCC']
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
        
        ax.axis('equal')
        
        # Guardamos la imagen en la carpeta 'outputs' temporalmente en lugar de memoria
        output_dir = os.path.join(os.getcwd(), 'outputs')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        temp_chart_path = os.path.join(output_dir, "temp_dynamic_chart.png")
        
        plt.savefig(temp_chart_path, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig) # Cerramos figura para liberar memoria
        
        return temp_chart_path # Devolvemos STRING (Ruta) en vez de BytesIO
    
    def add_summary_section(self, passed=None, failed=None):
        if passed is None or failed is None:
            total = len(self.scenarios)
            passed = sum(1 for s in self.scenarios if s.get('status', '').upper() in ['EXITOSO', 'PASSED'])
            failed = total - passed
        
        success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0.0
        
        # 1. Obtenemos la RUTA del archivo generado
        chart_path = self.create_pie_chart(passed, failed)
        
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'Resumen de Resultados', 0, 1, 'C')
        
        # 2. Insertamos la imagen usando la ruta física
        # FPDF verá que es un string que termina en .png y funcionará correctamente
        try:
            self.image(chart_path, x=60, y=self.get_y(), w=80, h=80)
        except Exception as e:
            self.set_text_color(255, 0, 0)
            self.cell(0, 10, f'Error mostrando gráfica: {str(e)}', 0, 1, 'C')
            self.set_text_color(0, 0, 0)
        
        # 3. Limpieza: Borramos el archivo temporal
        if os.path.exists(chart_path):
            try:
                os.remove(chart_path)
            except:
                pass 
            
        self.ln(85)
        
        # Estadísticas
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(0, 128, 0)
        self.cell(0, 10, f'Exitosos: {passed} ({success_rate:.1f}%)', 0, 1, 'C')
        self.set_text_color(255, 0, 0)
        self.cell(0, 10, f'Fallidos: {failed} ({100 - success_rate:.1f}%)', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(10)       
     
    def _print_table_headers(self, col_widths):
        """Método auxiliar para imprimir los encabezados azules de la tabla."""
        self.set_font('helvetica', 'B', 11)
        self.set_fill_color(23, 124, 214)
        self.set_text_color(255, 255, 255)
        
        self.cell(col_widths[0], 10, 'Escenario', 1, 0, 'L', fill=True)
        self.cell(col_widths[1], 10, 'Estado', 1, 1, 'C', fill=True)
        
        # Restaurar fuente y color para el contenido de las filas
        self.set_font('helvetica', '', 8)
        self.set_text_color(0, 0, 0)

    def add_feature_section(self):
        # Título principal del Feature
        self.set_font('helvetica', 'B', 14)
        self.cell(0, 10, f'Feature: {self.feature_name}', 0, 1)
        self.ln(8)
        
        col_widths = [140, 50] 
        line_height = 7 # Altura base de cada línea de texto
        
        # Imprimir encabezados por primera vez en esta hoja
        self._print_table_headers(col_widths)
        
        for scenario in self.scenarios:
            scenario_name = scenario.get('name', 'N/A')
            status = scenario.get('status', 'N/A').upper()
            
            # Calculamos cuántas líneas ocupará el texto
            lines = self._count_text_lines(scenario_name, col_widths[0] - 2)
            row_height = lines * line_height
            
            # Control dinámico de salto de página:
            # Si la posición actual + la altura total de la fila supera el límite (270)
            if self.get_y() + row_height > 270:
                self.add_page()
                
                # Reimprimir el nombre del Feature indicando que es continuación
                self.set_font('helvetica', 'B', 10)
                self.set_text_color(128, 128, 128) # Tono gris
                self.cell(0, 10, f'Feature: {self.feature_name} (Continuación)', 0, 1)
                self.ln(3)
                
                # Volver a imprimir los encabezados azules
                self._print_table_headers(col_widths)
                
            # Guardamos la posición (X, Y) inicial de la fila
            x_start = self.get_x()
            y_start = self.get_y()
            
            # 1. Dibujar celda del Escenario (multi_cell hace el salto de línea automático)
            self.multi_cell(col_widths[0], line_height, scenario_name, 1, 'L')
            
            # Capturamos dónde terminó "Y" después del texto largo
            y_end = self.get_y()
            actual_row_height = y_end - y_start # La altura real que tomó el bloque
            
            # 2. Nos movemos a la posición exacta de la columna "Estado"
            self.set_xy(x_start + col_widths[0], y_start)
            
            if status in ['EXITOSO', 'PASSED']:
                self.set_text_color(0, 128, 0)
            else:
                self.set_text_color(255, 0, 0)
                
            # 3. Dibujamos la celda de Estado usando la altura real para que el borde cierre perfecto
            self.cell(col_widths[1], actual_row_height, status, 1, 1, 'C')
            self.set_text_color(0, 0, 0)
            
            # 4. Regresamos el cursor a la siguiente línea para el próximo escenario
            self.set_xy(x_start, y_end)
    
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
            'end_time': None,
            'execution_id': None
        }
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
                
                # Extraer feature name
                feature_match = re.search(r'==== INICIO DE FEATURE:\s*(.+?)\s*====', log_content)
                if feature_match:
                    data['feature'] = feature_match.group(1).strip()
                    
                # Extraer timestamp de ejecución
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}', log_content)
                if timestamp_match:
                    data['start_time'] = timestamp_match.group(1)
                
                # Extraer duración                
                duration_match = re.search(r'Took\s(.+?)$', log_content, re.MULTILINE)
                if duration_match:
                    data['duration'] = duration_match.group(1).strip()
                
                # Extraer escenarios con su timestamp
                scenario_pattern = re.compile(
                    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?Iniciando escenario:\s*(.+?)\s*$.*?'
                    r'Escenario completado:.*?\|\s*Estado:\s*(passed|failed)',
                    re.DOTALL | re.MULTILINE
                )
                
                for match in scenario_pattern.finditer(log_content):
                    timestamp = match.group(1)
                    scenario_name = match.group(2).strip()
                    status = 'EXITOSO' if match.group(3).lower() == 'passed' else 'FALLIDO'
                    
                    data['scenarios'].append({
                        'name': scenario_name,
                        'status': status,
                        'timestamp': timestamp
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
            pdf.set_author(author='AppWhere-2026')
            pdf.set_creator('Bancoppel - AppWhere')
            
            return pdf_filename
            
        except Exception as e:
            logging.error(f"Error crítico al generar reporte: {str(e)}")
            raise

    @staticmethod
    def generate_consolidated_report(feature_log_paths):
        """Genera un único reporte global para toda la ejecución con duraciones dinámicas."""
        try:
            pdf = PDFFeatureReport()
            pdf.alias_nb_pages()
            
            all_scenarios = []
            feature_data_list = []
            total_seconds = 0.0
            
            # 1. Parsear todos los logs
            for log_path in feature_log_paths:
                log_data = PDFFeatureReport.parse_log_file(log_path)
                scenarios = log_data.get('scenarios', [])
                
                if scenarios:
                    dur_str = log_data.get('duration', '0m0.000s')
                    feature_data_list.append({
                        'name': log_data.get('feature', os.path.basename(log_path)),
                        'scenarios': scenarios,
                        'duration': dur_str
                    })
                    all_scenarios.extend(scenarios)
                    
                    match = re.match(r'(?:(\d+)m)?([\d\.]+)s', dur_str.replace('Took ', '').strip())
                    if match:
                        mins = int(match.group(1)) if match.group(1) else 0
                        secs = float(match.group(2))
                        total_seconds += (mins * 60) + secs
            
            # 2. Calcular Métricas Globales
            total_features = len(feature_data_list)
            total_scenarios = len(all_scenarios)
            passed = sum(1 for s in all_scenarios if s.get('status', '').upper() in ['EXITOSO', 'PASSED'])
            failed = total_scenarios - passed
            
            total_minutes, total_secs_remainder = divmod(total_seconds, 60)
            total_duration_formatted = f"{int(total_minutes)}m{total_secs_remainder:.3f}s"
            
            # 3. SETEAR DURACIÓN GLOBAL PARA LA PRIMERA PÁGINA
            pdf.execution_date = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            pdf.duration = total_duration_formatted
            
            pdf.add_page()
            
            # 4. Portada
            pdf.set_font('helvetica', '', 12)
            pdf.cell(0, 10, f'Total de Features ejecutados: {total_features} ', 0, 1, 'C')
            pdf.cell(0, 10, f'Total de Escenarios evaluados: {total_scenarios} ', 0, 1, 'C')
            pdf.ln(3)
            
            # 5. Gráfica
            pdf.add_summary_section(passed, failed)
            
            # 6. Desglose detallado por Feature
            for feature_data in feature_data_list:
                # Cambiamos la duración a la del Feature actual
                # Al hacer add_page(), el header leerá este nuevo valor
                pdf.duration = feature_data['duration']
                
                pdf.add_page()
                pdf.feature_name = feature_data['name']
                pdf.scenarios = feature_data['scenarios']
                pdf.add_feature_section()
            
            # 7. Guardado
            output_dir = os.path.join('outputs', 'pdfReports')
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"ReporteGlobal_Ejecucion_{timestamp}.pdf"
            
            pdf.set_author(author='AppWhere-2026')
            pdf.set_creator('Bancoppel - AppWhere')
            
            pdf.output(os.path.join(output_dir, pdf_filename))
            
            return pdf_filename
            
        except Exception as e:
            logging.error(f"Error generando reporte consolidado: {str(e)}")
            raise
        
# if __name__ == "__main__":
    # import logging
    # logging.basicConfig(level=logging.INFO)
    
    # # Configuración para pruebas
    # TEST_FEATURE_NAME = "OA_R2"
    # TEST_LOG_PATH = "outputs/logs/OA_R2_feature.txt"  # Ruta a tu log existente
    
    # try:
    #     print("=== Iniciando prueba del generador de PDF ===")
    #     pdf_filename = PDFFeatureReport.generate_feature_report(
    #         feature_name=TEST_FEATURE_NAME,
    #         feature_log_path=TEST_LOG_PATH
    #     )
    #     print(f"Reporte generado exitosamente: {pdf_filename}")
    # except Exception as e:
    #     print(f"Error generando reporte: {str(e)}")
    #     logging.exception("Error detallado:")        