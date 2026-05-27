from fpdf import FPDF
import os
import re
from collections import defaultdict

class PdfReportDocument(FPDF):

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
    def _extract_step_key_from_image_name(filename: str):
        """
        Extrae la clave base del paso desde nombres como:
        - 01_given.png
        - 01_given_img_01.png
        - evidencia_01_and_img_02.png
        - algo_02_then_otro.png

        Devuelve:
        - '01_given'
        - '01_and'
        - '02_then'
        """
        name = os.path.splitext(os.path.basename(filename))[0].lower()

        # Acepta terminación, separador "_" o cualquier texto posterior.
        # Ejemplos válidos:
        # 01_given
        # 01_given_img_01
        # evidencia_01_and_img_02
        # prueba_02_then_extra
        match = re.search(r'(?<!\d)(\d{2})_(given|when|then|and)(?=_|$)', name)
        if match:
            return f"{match.group(1)}_{match.group(2)}"
        return None

    @staticmethod
    def _image_sort_key(filename: str):
        """
        Ordena las imágenes de un mismo paso respetando:
        1) sufijo _img_NN si existe
        2) nombre base como desempate
        """
        base = os.path.splitext(os.path.basename(filename))[0].lower()
        match = re.search(r'_img_(\d+)\b', base)
        img_index = int(match.group(1)) if match else 999999
        return (img_index, base)

    @staticmethod
    def genReport(featureName, testName, dt_format, dt_formatFin, screenshots=None):
        BASE_DIR = os.getcwd()
        statusTest = ''
        durationTest = ''
        txtDuration = 'Took'
        txtGiven = 'Given'
        txtWhen = 'When'
        txtThen = 'Then'
        txtAnd = 'And'
        txtResult = 'Resultado:'

        tstName = testName.replace(" ", "")
        moduloName = featureName

        log_errors = {}
        failure_screenshots = {}
        real_steps = {}
        step_status = {}

        if screenshots:
            failure_screenshots = {
                idx: os.path.basename(path)
                for idx, path in enumerate(screenshots.values())
            }

        current_step = -1
        error_buffer = []
        logFile = os.path.join(BASE_DIR, 'outputs', 'logs', tstName + '.txt')
        step_names_to_remove = ['Given', 'When', 'Then', 'And']

        try:
            with open(logFile, 'r', encoding='utf-8') as f:
                for line in f:
                    if txtDuration in line:
                        durationTest = line.replace('Took: ', '')[:-5]
                    if txtResult in line:
                        statusTest = 'FAILED' if "FAILED" in line else 'OK'

                    if '[Step] PASADO:' in line or '[Step] FALLIDO:' in line:
                        current_step += 1

                        if '[Step] PASADO:' in line:
                            step_part = line.split('[Step] PASADO:')[1].strip()
                        else:
                            step_part = line.split('[Step] FALLIDO:')[1].strip()

                        step_clean = step_part
                        for step_name in step_names_to_remove:
                            if step_clean.startswith(step_name + ' '):
                                step_clean = step_clean[len(step_name):].strip()
                                break

                        finales_a_quitar = [
                            ' - Error desconocido',
                            ' - Error de Selenium - revisar stacktrace completo'
                        ]
                        for final in finales_a_quitar:
                            if step_clean.endswith(final):
                                step_clean = step_clean[:-len(final)].strip()

                        real_steps[current_step] = step_clean
                        step_status[current_step] = 'PASSED' if '[Step] PASADO:' in line else 'FAILED'

                        if error_buffer:
                            error_msg = None
                            ignored_errors = [
                                lambda e: e.startswith('- Input') or (e.startswith('Input') and ':' in e and '{' in e),
                                lambda e: "Error de Selenium - revisar stacktrace completo" in e
                            ]
                            for err in reversed(error_buffer):
                                if not any(fn(err) for fn in ignored_errors):
                                    error_msg = err
                                    break
                            if error_msg is None and error_buffer:
                                error_msg = error_buffer[-1]
                            if error_msg:
                                log_errors[current_step] = error_msg
                            error_buffer = []

                    if 'ERROR:' in line:
                        error_line = line.split("ERROR: ")[-1].strip()
                        ignored_errors = [
                            lambda e: e.startswith('- Input') or (e.startswith('Input') and ':' in e and '{' in e),
                            lambda e: "Error de Selenium - revisar stacktrace completo" in e
                        ]
                        if not any(fn(error_line) for fn in ignored_errors):
                            error_buffer.append(error_line)

                    if 'Captura de fallo guardada:' in line:
                        screenshot_name = line.split(": ")[-1].strip()
                        failure_screenshots[current_step] = screenshot_name

        except FileNotFoundError:
            print(f"ADVERTENCIA: No se encontró el archivo de log {logFile}")

        file_path = os.path.join(BASE_DIR, 'features', featureName + ".feature")
        steps = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            in_target_scenario = False

            if ' -- @' in testName:
                scenario_base_name = testName.split(' -- @')[0].strip()
            else:
                scenario_base_name = testName.strip()

            for line in lines:
                line = line.strip()

                if line.startswith('Scenario:') or line.startswith('Scenario Outline:'):
                    current_scenario = line.split(':', 1)[1].strip()

                    if '<' in current_scenario:
                        scenario_template_base = current_scenario.split('<')[0].strip()
                        in_target_scenario = scenario_template_base in scenario_base_name
                    else:
                        in_target_scenario = (
                            current_scenario == scenario_base_name or
                            current_scenario == testName or
                            scenario_base_name in current_scenario
                        )

                if in_target_scenario and line.startswith(('Given', 'When', 'Then', 'And')):
                    steps.append(line)

                if in_target_scenario and line and not line.startswith(('Given', 'When', 'Then', 'And', '#')):
                    if (
                        line.startswith('Scenario') or
                        line.startswith('Examples:') or
                        line.startswith('Feature:') or
                        line.startswith('Background:')
                    ):
                        if not (line.startswith('Scenario:') or line.startswith('Scenario Outline:')):
                            break

        except FileNotFoundError:
            print(f"ADVERTENCIA: No se encontró el archivo feature {file_path}")

        lastFolderURL = os.path.join(BASE_DIR, 'outputs', 'evidences')
        evidence_dir = None
        step_images_map = defaultdict(list)
        fail_images = {}

        try:
            listFolder = [
                os.path.join(lastFolderURL, folder)
                for folder in os.listdir(lastFolderURL)
                if os.path.isdir(os.path.join(lastFolderURL, folder))
            ]

            if listFolder:
                latest_folder = max(listFolder, key=os.path.getmtime)
                evidence_dir = latest_folder

                for img in os.listdir(evidence_dir):
                    if not img.lower().endswith(('.png', '.jpg', '.jpeg')):
                        continue

                    if img.startswith('FAIL_'):
                        for step_idx, screenshot_name in failure_screenshots.items():
                            if screenshot_name == img:
                                fail_images[step_idx] = img
                                break

                        if img not in fail_images.values():
                            for step_idx in range(len(real_steps)):
                                if (
                                    step_idx in step_status and
                                    step_status[step_idx] == 'FAILED' and
                                    step_idx not in fail_images
                                ):
                                    fail_images[step_idx] = img
                                    break
                    else:
                        step_key = PDF._extract_step_key_from_image_name(img)
                        if step_key:
                            step_images_map[step_key].append(img)

                for step_key in step_images_map:
                    step_images_map[step_key].sort(
                        key=lambda x: (
                            PDF._image_sort_key(x),
                            os.path.getmtime(os.path.join(evidence_dir, x))
                        )
                    )

        except (FileNotFoundError, OSError) as e:
            print(f"ADVERTENCIA: No se encontraron evidencias visuales: {e}")

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
        pdf.multi_cell(0, 5, testName, align='C')

        logo_path = os.path.join(BASE_DIR, 'resources', 'logo_elia.png')
        if not os.path.exists(logo_path):
            logo_path = os.environ.get('ELIA_LOGO_PATH') or logo_path
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, 70, 19, 60, 15)

        fechaIni = dt_format[0:10]
        fechatFin = dt_formatFin[0:10]
        horaIni = dt_format[-8:].replace("-", ":")
        horaFin = dt_formatFin[-8:].replace("-", ":")
        dtformat = fechaIni + " " + horaIni
        dtformatFin = fechatFin + " " + horaFin

        pdf.set_xy(5, 40)
        pdf.set_font('helvetica', '', 9.0)
        pdf.set_fill_color(23, 124, 214)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(w=50, h=8, txt='Estatus', border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt='Duración', border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt='Inicio', border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt='Fin', border=0, align='C', fill=True)
        pdf.set_xy(5, 49)
        pdf.set_font('helvetica', 'B', 11.0)
        pdf.set_fill_color(255, 255, 255)
        if statusTest == 'OK':
            pdf.set_text_color(0, 147, 57)
        elif statusTest == 'FAILED':
            pdf.set_text_color(255, 0, 0)
        else:
            pdf.set_text_color(0, 0, 0)
        pdf.cell(w=50, h=8, txt=statusTest, border=0, align='C', fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w=50, h=8, txt=durationTest, border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt=dtformat, border=0, align='C', fill=True)
        pdf.cell(w=50, h=8, txt=dtformatFin, border=0, align='C', fill=True)

        pdf.set_draw_color(52, 152, 219)
        pdf.set_line_width(0.2)
        pdf.line(5, 57, 204, 57)

        pdf.set_xy(0, 65)
        pdf.set_font('helvetica', 'B', 12.0)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, 'Evidencia de Ejecución del Test', align='C')

        marginTop = 80
        pdf.set_xy(15, marginTop)

        if not steps:
            pdf.set_font('helvetica', 'I', 11.0)
            pdf.set_text_color(255, 0, 0)
            pdf.multi_cell(0, 5, f"ADVERTENCIA: No se encontraron pasos para el escenario '{testName}'", align='C')
            pdf.set_text_color(0, 0, 0)

        step_occurrence = defaultdict(int)

        for step_index, paso_text in enumerate(steps):
            txtHeader = 'STEP'
            step_type = ''

            if txtGiven in paso_text:
                txtHeader = 'GIVEN'
                paso_text = paso_text.replace('Given', '').strip()
                step_type = 'given'
            elif txtWhen in paso_text:
                txtHeader = 'WHEN'
                paso_text = paso_text.replace('When', '').strip()
                step_type = 'when'
            elif txtThen in paso_text:
                txtHeader = 'THEN'
                paso_text = paso_text.replace('Then', '').strip()
                step_type = 'then'
            elif txtAnd in paso_text:
                txtHeader = 'AND'
                paso_text = paso_text.replace('And', '').strip()
                step_type = 'and'

            paso_text = real_steps.get(step_index, paso_text)

            if step_type:
                step_occurrence[step_type] += 1
                step_key = f"{step_occurrence[step_type]:02d}_{step_type}"
            else:
                step_key = None

            current_images = step_images_map.get(step_key, []) if step_key else []

            if pdf.get_y() + 20 > pdf.h - pdf.b_margin:
                pdf.add_page()

            pdf.set_font('helvetica', 'B', 13.0)
            pdf.set_text_color(52, 152, 219)
            pdf.multi_cell(0, 5, txtHeader + '\n', align='C')
            pdf.set_font('helvetica', '', 11.0)

            if " - ERROR: " in paso_text:
                desc_limpia, msg_error = paso_text.split(" - ERROR: ", 1)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 5, desc_limpia.strip() + '\n', align='C')
                pdf.set_text_color(255, 0, 0)
                pdf.multi_cell(0, 5, f"ERROR: {msg_error.strip()}\n", align='C')
                pdf.set_text_color(0, 0, 0)
                if step_index in log_errors:
                    del log_errors[step_index]
            else:
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 5, paso_text + '\n', align='C')

            images_displayed = 0
            for img_name in current_images:
                if evidence_dir:
                    imagen_path = os.path.join(evidence_dir, img_name)
                    if os.path.exists(imagen_path):
                        if pdf.get_y() + 60 > pdf.h - pdf.b_margin:
                            pdf.add_page()
                        x1 = (210 - 110) / 2
                        y1 = pdf.get_y()
                        pdf.set_x(x1)
                        pdf.set_draw_color(8, 51, 162)
                        pdf.set_line_width(0.5)
                        pdf.image(imagen_path, x=x1, y=y1, w=110, h=60)
                        pdf.rect(x1, y1, 110, 60)
                        pdf.ln(65)
                        images_displayed += 1

            if step_index in log_errors:
                pdf.set_text_color(255, 0, 0)
                pdf.multi_cell(0, 5, f"ERROR: {log_errors[step_index]}\n", align='C')
                pdf.set_text_color(0, 0, 0)

            if step_index in fail_images:
                fail_img_name = fail_images[step_index]
                if evidence_dir:
                    fail_img_path = os.path.join(evidence_dir, fail_img_name)
                    if os.path.exists(fail_img_path):
                        if pdf.get_y() + 60 > pdf.h - pdf.b_margin:
                            pdf.add_page()
                        pdf.set_text_color(255, 0, 0)
                        pdf.multi_cell(0, 5, "Captura de error:", align='C')
                        pdf.set_text_color(0, 0, 0)
                        x1 = (210 - 110) / 2
                        y1 = pdf.get_y()
                        pdf.set_x(x1)
                        pdf.set_draw_color(255, 0, 0)
                        pdf.set_line_width(0.8)
                        pdf.image(fail_img_path, x=x1, y=y1, w=110, h=60)
                        pdf.rect(x1, y1, 110, 60)
                        pdf.ln(65)
                        pdf.set_draw_color(8, 51, 162)
                        pdf.set_line_width(0.5)
                        images_displayed += 1

            if images_displayed == 0:
                pdf.set_font('helvetica', 'I', 10.0)
                pdf.set_text_color(128, 128, 128)
                pdf.multi_cell(0, 5, "(Sin evidencia visual para este paso)\n", align='C')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('helvetica', '', 11.0)
                pdf.ln(5)

        pdf.set_author(author='Sir-Alek-2026')
        pdf.set_title(title=testName)
        pdf.set_creator('ELIA - Sir-Alek')

        output_dir = os.path.join(BASE_DIR, 'outputs', 'pdfReports')
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{testName}_{dt_format}.pdf")
        pdf.output(output_path, 'F')

        return output_path
