from fpdf import FPDF
import os
import json
import pandas as pd
from datetime import datetime
import unicodedata


class PDF(FPDF):

    def texts(self, name):
        with open(name, 'rb') as xy:
            txt = xy.read().decode('latin-1')
        self.set_xy(10.0, 80.0)
        self.set_text_color(76.0, 32.0, 250.0)
        self.multi_cell(0, 10, txt)
    
    def footer(self):
        self.set_y(-10)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.1)
        self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(52, 152, 219)
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
        
    @staticmethod
    def normalize_text(text):
        return unicodedata.normalize('NFKD', text).encode('latin-1', 'ignore').decode('latin-1')

    @staticmethod
    def get_project_paths(testName, project_name):
        """Obtiene todas las rutas del proyecto de manera dinámica"""
        # Obtener la ruta base del proyecto step_by_step
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Buscar la ruta de step_by_step subiendo niveles si es necesario
        base_dir = current_file_dir
        while os.path.basename(base_dir) != 'step_by_step' and os.path.dirname(base_dir) != base_dir:
            base_dir = os.path.dirname(base_dir)
        
        if os.path.basename(base_dir) != 'step_by_step':
            # Si no encuentra step_by_step, usar la ruta actual
            base_dir = os.getcwd()
            if 'step_by_step' in base_dir:
                base_dir = base_dir.split('step_by_step')[0] + 'step_by_step'
            else:
                raise FileNotFoundError("No se pudo encontrar el directorio 'step_by_step'")
        
        PROJECT_DIR = os.path.join(base_dir, 'proyectos', project_name)
        
        paths = {
            'base_dir': base_dir,
            'project_dir': PROJECT_DIR,
            'json_steps_dir': os.path.join(PROJECT_DIR, 'resources', 'info_steps'),
            'evidences_base_dir': os.path.join(PROJECT_DIR, 'outputs', 'evidences'),
            'log_dir': os.path.join(PROJECT_DIR, 'outputs', 'logs'),
            'pdf_reports_dir': os.path.join(PROJECT_DIR, 'outputs', 'pdfReports')
        }
        
        return paths

    @staticmethod
    def find_latest_evidence_dir(evidences_base_dir, test_name):
        """Encuentra la carpeta de evidencias más reciente para el test"""
        if not os.path.exists(evidences_base_dir):
            raise FileNotFoundError(f"Directorio base de evidencias no encontrado: {evidences_base_dir}")
        
        # Buscar todas las carpetas que comiencen con el nombre del test
        test_folders = [f for f in os.listdir(evidences_base_dir) 
                       if os.path.isdir(os.path.join(evidences_base_dir, f)) and f.startswith(test_name)]
        
        if not test_folders:
            raise FileNotFoundError(f"No se encontraron carpetas de evidencias para: {test_name}")
        
        # Encontrar la carpeta más reciente por fecha de modificación
        latest_folder = max(test_folders, key=lambda x: os.path.getmtime(os.path.join(evidences_base_dir, x)))
        return os.path.join(evidences_base_dir, latest_folder)

    @staticmethod
    def genReportFromLog(testName, project_name):
        """Genera reporte leyendo toda la información del archivo de log"""
        # Obtener rutas dinámicas
        paths = PDF.get_project_paths(testName, project_name)
        
        # Verificar si el directorio de logs existe
        if not os.path.exists(paths['log_dir']):
            raise FileNotFoundError(f"Directorio de logs no encontrado: {paths['log_dir']}")
        
        # Buscar archivo de log más reciente para este test
        log_files = [f for f in os.listdir(paths['log_dir']) if f.startswith(testName) and f.endswith('.txt')]
        if not log_files:
            raise FileNotFoundError(f"No se encontró archivo de log para: {testName}")
        
        # Tomar el log más reciente
        latest_log = max(log_files, key=lambda x: os.path.getctime(os.path.join(paths['log_dir'], x)))
        log_file_path = os.path.join(paths['log_dir'], latest_log)
        
        # Leer datos del log
        statusTest = ''
        durationTest = ''
        dt_format = ''
        dt_formatFin = ''
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                if 'Hora de inicio:' in line:
                    dt_format = line.split('Hora de inicio: ')[1].strip()
                elif 'Hora de finalización:' in line:
                    dt_formatFin = line.split('Hora de finalización: ')[1].strip()
                elif 'Duración:' in line:
                    durationTest = line.split('Duración: ')[1].strip()
                elif 'Estado:' in line:
                    statusTest = line.split('Estado: ')[1].strip()
        
        # Llamar al método original con los datos del log
        PDF.genReport(testName, dt_format, dt_formatFin, project_name, statusTest, durationTest)

    @staticmethod
    def genReport(testName, dt_format, dt_formatFin, project_name, statusTest='', durationTest=''):
        """Genera el reporte PDF con los datos proporcionados"""
        # Obtener rutas dinámicas
        paths = PDF.get_project_paths(testName, project_name)
        
        # Crear directorios si no existen
        os.makedirs(paths['pdf_reports_dir'], exist_ok=True)
        
        # Buscar archivo JSON de pasos
        json_files = [f for f in os.listdir(paths['json_steps_dir']) if f.endswith('.json') and testName in f]
        if not json_files:
            raise FileNotFoundError(f"No se encontró archivo JSON para el test: {testName}")
        
        json_file_path = os.path.join(paths['json_steps_dir'], json_files[0])
        
        # Cargar pasos desde JSON
        with open(json_file_path, 'r', encoding='utf-8') as f:
            steps_data = json.load(f)
        
        pasosList = steps_data.get('steps', [])
        
        # Encontrar la carpeta de evidencias más reciente
        evidence_dir = PDF.find_latest_evidence_dir(paths['evidences_base_dir'], testName)
        
        # Buscar imágenes de evidencias
        listIMG = [f for f in os.listdir(evidence_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        listIMG.sort()

        if not listIMG:
            raise FileNotFoundError(f"No se encontraron imágenes de evidencias en: {evidence_dir}")

        # Buscar archivo de log para datos adicionales si faltan
        if not statusTest or not durationTest:
            log_files = [f for f in os.listdir(paths['log_dir']) if f.startswith(testName) and f.endswith('.txt')]
            if log_files:
                latest_log = max(log_files, key=lambda x: os.path.getctime(os.path.join(paths['log_dir'], x)))
                log_file_path = os.path.join(paths['log_dir'], latest_log)
                
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        if not statusTest and 'Estado:' in line:
                            statusTest = line.split('Estado: ')[1].strip()
                        if not durationTest and 'Duración:' in line:
                            durationTest = line.split('Duración: ')[1].strip()

        # Obtener información del test desde JSON
        with open(json_file_path) as json_file:
            developer = json.load(json_file)
        
        moduloName = 'MODULO ' + developer.get("Modulo", '')
        tstName = developer.get("Titulo", testName).replace("test_", "")

        # Creating the PDF
        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.set_xy(0, 5)
        pdf.set_font('helvetica', '', 11.0)
        pdf.set_text_color(52, 152, 219)
        pdf.multi_cell(0, 5, 'Reporte de ejecucion de Test', align='C')

        pdf.set_xy(0, 10)
        pdf.set_font('helvetica', 'B', 13.0)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, tstName, align='C')

        pdf.set_xy(0, 25)
        pdf.set_font('helvetica', 'B', 12.0)
        pdf.set_text_color(52, 152, 219)
        pdf.multi_cell(0, 5, '\n' + moduloName, align='C')

        # Logo - buscar en resources generales
        logo_path = os.path.join(paths['base_dir'], 'resources', 'logo_bee_png_transparente.png')
        if os.path.exists(logo_path):
            pdf.image(logo_path, 70, 19, 60, 15)
        
        fechaIni = dt_format[0:10]
        fechatFin = dt_formatFin[0:10]

        horaIni = dt_format[-8:]
        horaFin = dt_formatFin[-8:]
        # horaIni = horaIni.replace("-",":")
        # horaFin = horaFin.replace("-",":")
        dtformat = fechaIni +" "+ horaIni
        dtformatFin = fechatFin +" "+ horaFin               
        
        #--------------- Table Headers
        pdf.set_xy(5,40)
        pdf.set_font('helvetica', '', 9.0)
        pdf.set_fill_color(23, 124, 214)
        pdf.set_text_color(255,255,255)
        pdf.cell(w=50, h=8, txt='Estatus',border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt='Duración',border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt='Inicio',border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt='Fin',border=0, align='C', fill=True)
        pdf.set_xy(5,49)
        pdf.set_font('helvetica', 'B', 11.0)
        pdf.set_fill_color(255, 255, 255)
        
        # Color del estatus
        if statusTest == 'OK':
            pdf.set_text_color(0, 147, 57)
        elif statusTest == 'FAILED':
            pdf.set_text_color(255, 0, 0)
        pdf.cell(w=50, h=8, txt=statusTest,border=0, align='C', fill=True)
        pdf.set_text_color(0,0,0)
        pdf.cell(w=50, h=8, txt=durationTest,border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt=dt_format,border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt=dt_formatFin,border=0, align='C', fill=True)

        # Linea horizontal debajo del nombre del modulo
        pdf.set_draw_color(52, 152, 219)
        pdf.set_line_width(0.2)
        pdf.line(5, 57, 204, 57)
        
        #--------------- Table Content

        pdf.set_xy(0, 65)
        pdf.set_font('helvetica', 'B', 12.0)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, 'Evidencia de Ejecución de Test', align='C')

        marginTop = 99 if statusTest == 'FAILED' else 80
        pdf.set_xy(15, marginTop)
        
        # Mostrar una imagen por paso
        for i, paso in enumerate(pasosList, 1):
            if i > len(listIMG):
                break
                
            paso_text = paso.get('description', '')
            normalized_text = PDF.normalize_text(paso_text)
            
            # Verificar espacio para texto del paso
            required_space_text = 20
            if pdf.get_y() + required_space_text > pdf.h - pdf.b_margin:
                pdf.add_page()
                
            pdf.set_font('helvetica', '', 11.0)
            pdf.set_text_color(52, 152, 219)
            pdf.multi_cell(0, 5, f'PASO: {i}\n', align='C')
            pdf.set_font('helvetica', '', 9.0)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, normalized_text + '\n', align='L')
            pdf.multi_cell(0, 5, ' ')

            # Verificar espacio para la imagen
            required_space_image = 60
            if pdf.get_y() + required_space_image > pdf.h - pdf.b_margin:
                pdf.add_page()

            # Agregar la imagen del paso
            x = (210 - 110) / 2
            y = pdf.get_y()
            pdf.set_x(x)
            pdf.set_draw_color(8, 51, 162)
            pdf.set_line_width(0.5)
            
            img_path = os.path.join(evidence_dir, listIMG[i-1])
            pdf.image(img_path, x=x, y=y, w=110, h=60)
            pdf.rect(x, y, 110, 60)
            pdf.ln(65)

        # Metadatos
        pdf.set_author(author='Sir-Alek-2026')
        pdf.set_title(title=testName)
        pdf.set_creator('BEE - Sir-Alek')

        # Finalizar PDF
        safe_dt_format = dt_format.replace(" ", "_").replace(":", "-").replace(".", "-")
        output_file = os.path.join(paths['pdf_reports_dir'], f"{testName}_{safe_dt_format}.pdf")
        pdf.output(output_file, 'F')
        print(f"Reporte generado: {output_file}")
