"""
Copyright (c) 2025 Alejandro Ramírez  
Bajo la Licencia de Autor Restringida (LAR) v1.0  
Más detalles en LICENSE
"""

import json
import os
import re
import textwrap
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
import concurrent.futures
import logging

logger = logging.getLogger(__name__)


class StoryGherkinBuilder:
    def __init__(self, input_dir: str, output_dir: str, use_ai: bool = False):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.use_ai = use_ai
        self.patterns = self._compile_patterns()
        self.processed_count = 0

        # Inicializar sistema adaptativo de palabras clave
        self._build_adaptive_keyword_system()

    # -------------------------------------------------------------------------
    # Sistema adaptativo de palabras clave
    # -------------------------------------------------------------------------

    def _build_adaptive_keyword_system(self):
        """Sistema adaptativo que aprende nuevos patrones de palabras clave."""
        self.adaptive_patterns = {
            'given_keywords': set([
                "dado que", "dada", "precondición", "haber concluido",
                "tener", "contar con", "estar en", "configurar", "inicializar"
            ]),
            'when_keywords': set([
                "cuando", "al", "hacer", "realizar", "seleccionar",
                "click", "clic", "presionar", "escribir", "ingresar",
                "deslizar", "capturar", "introducir"
            ]),
            'then_keywords': set([
                "entonces", "debería", "se debe", "resultado",
                "validar", "verificar", "confirmar", "mostrar",
                "aparecer", "visualizar", "observar"
            ])
        }

        self.learning_file = os.path.join(self.output_dir, "learned_patterns.json")
        self._load_learned_patterns()

    def _load_learned_patterns(self):
        """Cargar patrones aprendidos de ejecuciones anteriores."""
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    learned = json.load(f)
                    for key in self.adaptive_patterns:
                        self.adaptive_patterns[key].update(learned.get(key, []))
        except Exception as e:
            logger.warning(f"No se pudieron cargar patrones aprendidos: {str(e)}")

    def _save_learned_patterns(self):
        """Guardar nuevos patrones descubiertos."""
        try:
            learned_data = {key: list(values) for key, values in self.adaptive_patterns.items()}
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(learned_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"No se pudieron guardar patrones aprendidos: {str(e)}")

    def _analyze_and_learn_keywords(self, step_text: str):
        """Analiza el texto para aprender nuevas palabras clave."""
        words = re.findall(r'\b[a-zá-ú]{4,15}\b', step_text)
        for word in words:
            if any(ctx in step_text for ctx in ["presionar", "hacer clic", "seleccionar"]):
                self.adaptive_patterns['when_keywords'].add(word)
            elif any(ctx in step_text for ctx in ["verificar", "validar", "confirmar"]):
                self.adaptive_patterns['then_keywords'].add(word)
            elif any(ctx in step_text for ctx in ["configurar", "inicializar", "preparar"]):
                self.adaptive_patterns['given_keywords'].add(word)

    def _learning_pass(self, raw_steps: Dict) -> None:
        """
        Ejecuta la pasada de aprendizaje de palabras clave sin generar salida.
        Se llama siempre en process_file para que el sistema adaptativo funcione
        incluso cuando el camino IA genera los pasos finales.
        """
        try:
            sorted_steps = sorted(raw_steps.values(), key=lambda x: int(x.get('key', 0)))
        except Exception:
            sorted_steps = list(raw_steps.values())
        for step in sorted_steps:
            content = step.get('paso', '')
            if self._is_valid_step(content):
                self._analyze_and_learn_keywords(content.lower())

    # -------------------------------------------------------------------------
    # Patrones de dominio (regex)
    # -------------------------------------------------------------------------

    def _compile_patterns(self) -> Dict[str, list]:
        return {
            'beneficiary': [
                re.compile(r"(?:Ingresa|Ingresar|Capturar) (?:el )?(?:primer )?nombre del Cliente\b.*", re.IGNORECASE),
                re.compile(r"(?:Ingresa|Ingresar|Capturar) (?:el )?apellido paterno\b.*", re.IGNORECASE),
                re.compile(r"(?:Ingresa|Ingresar|Capturar) (?:el )?apellido materno\b.*", re.IGNORECASE),
                re.compile(r"Capturar el primer nombre del Cliente\b.*", re.IGNORECASE),
                re.compile(r"Nombre del Cliente:?\s*\*\*<.*>\*\*", re.IGNORECASE)
            ],
            'tarjeta': [
                re.compile(r"[Dd]eslizar? (?:una )?tarjeta\b", re.IGNORECASE),
                re.compile(r"[Dd]esliza (?:una )?tarjeta\b", re.IGNORECASE),
                re.compile(r"Operación con tarjeta.*", re.IGNORECASE)
            ],
            'cuenta': [
                re.compile(r"Capturar los siguientes datos:\s*\n?N[úu]mero de Cuenta \*\*<.*>\*\*", re.IGNORECASE),
                re.compile(r"Capturar los siguientes datos:\s*\n?N[úu]mero de Tarjeta \*\*<.*>\*\*", re.IGNORECASE),
                re.compile(r"Capturar (?:los siguientes datos|el):.*N[úu]mero de Cuenta.*", re.IGNORECASE),
                re.compile(r"N[úu]mero de cuenta:?\s*\*\*<.*>\*\*", re.IGNORECASE)
            ],
            'desglose': [
                re.compile(r"Capturar (?:el|registro|desglose) (?:total )?efectivo.*", re.IGNORECASE),
                re.compile(r"Registro de efectivo (?:que ingresa|sale).*", re.IGNORECASE),
                re.compile(r"Desglose monetario.*", re.IGNORECASE)
            ],
            'enter': [
                re.compile(r"Dar \"Enter\"", re.IGNORECASE),
                re.compile(r"Presionar tecla Enter", re.IGNORECASE),
                re.compile(r"Confirmar con Enter", re.IGNORECASE)
            ]
        }

    # -------------------------------------------------------------------------
    # Utilidades de texto
    # -------------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Limpieza de texto: normaliza URLs y elimina caracteres no deseados."""
        text = re.sub(r'(https?://[^\s]+)', lambda m: m.group(0).replace(' ', ''), text)
        text = re.sub(r'["\'"\u201c\u201d\u2018\u2019?]', '', text)
        return re.sub(r'[^\wá-úÁ-Ú \n\-:.,;¿¡!()/@]', '', text, flags=re.IGNORECASE).strip()

    def _is_valid_step(self, text: str) -> bool:
        return len(text.strip()) > 2 and not re.match(r'^[\d\W]+$', text)

    # -------------------------------------------------------------------------
    # Clasificación de pasos (sistema adaptativo con keywords)
    # -------------------------------------------------------------------------

    def _classify_step(self, step_text: str) -> Tuple[str, str]:
        """Clasificación adaptativa de pasos con aprendizaje de keywords."""
        step_text_lower = step_text.lower()
        self._analyze_and_learn_keywords(step_text_lower)

        given_score = sum(3 for kw in self.adaptive_patterns['given_keywords'] if kw in step_text_lower)
        when_score  = sum(3 for kw in self.adaptive_patterns['when_keywords']  if kw in step_text_lower)
        then_score  = sum(3 for kw in self.adaptive_patterns['then_keywords']  if kw in step_text_lower)

        if any(w in step_text_lower for w in ["url", "enlace", "dirección web"]):
            given_score += 2
        if any(w in step_text_lower for w in ["botón", "menú", "opción"]):
            when_score += 2
        if any(w in step_text_lower for w in ["mensaje", "error", "éxito"]):
            then_score += 2

        scores = {'given': given_score, 'when': when_score, 'then': then_score}
        best_match = max(scores.items(), key=lambda x: x[1])

        if best_match[1] > 0:
            return best_match[0], step_text

        return self._contextual_classification(step_text, step_text_lower)

    def _contextual_classification(self, step_text: str, step_text_lower: str) -> Tuple[str, str]:
        """Clasificación contextual para casos ambiguos."""
        if hasattr(self, 'last_step_type'):
            if self.last_step_type == 'given' and 'datos' in step_text_lower:
                return 'when', step_text
            elif self.last_step_type == 'when' and any(
                w in step_text_lower for w in ['resultado', 'pantalla', 'mensaje']
            ):
                return 'then', step_text

        if any(w in step_text_lower for w in ['campo', 'tecla', 'opción']):
            return 'when', step_text
        elif any(w in step_text_lower for w in ['correcto', 'incorrecto', 'error']):
            return 'then', step_text

        return 'and', step_text

    # -------------------------------------------------------------------------
    # Evaluación y mejora del clasificador adaptativo
    # -------------------------------------------------------------------------

    def _evaluate_and_improve_classification(self, original_steps: list, generated_steps: dict):
        """Evalúa la clasificación y mejora los patrones aprendidos."""
        flow_issues = self._detect_flow_issues(generated_steps)
        if flow_issues:
            logger.info(f"Problemas de flujo detectados: {flow_issues}")
            self._adjust_patterns_based_on_issues(flow_issues, original_steps)
        if self.processed_count % 10 == 0:
            self._save_learned_patterns()

    def _detect_flow_issues(self, generated_steps: dict) -> list:
        """Detecta problemas en el flujo generado."""
        issues = []
        if not generated_steps.get('When'):
            issues.append("Falta acción principal (When)")
        if not generated_steps.get('Then'):
            issues.append("Falta validación (Then)")
        if generated_steps.get('Then') and not generated_steps.get('When'):
            issues.append("Then sin When previo")
        return issues

    def _adjust_patterns_based_on_issues(self, issues: list, original_steps: list):
        """Ajusta los patrones adaptativos basado en problemas de flujo detectados."""
        for issue in issues:
            if "Falta acción principal" in issue:
                for step in original_steps:
                    content = step.get('paso', '').lower() if isinstance(step, dict) else ''
                    for word in re.findall(r'\b[a-zá-ú]{4,15}\b', content)[:3]:
                        self.adaptive_patterns['when_keywords'].add(word)
            elif "Falta validación" in issue:
                for step in original_steps:
                    val = step.get('validacion', '').lower() if isinstance(step, dict) else ''
                    for word in re.findall(r'\b[a-zá-ú]{4,15}\b', val)[:3]:
                        self.adaptive_patterns['then_keywords'].add(word)

    # -------------------------------------------------------------------------
    # Detección de patrones de dominio
    # -------------------------------------------------------------------------

    def _detect_patterns(self, steps: list) -> Dict[str, Any]:
        """Detecta patrones de dominio bancario en los pasos."""
        detected = {
            'beneficiary': False,
            'tarjeta': False,
            'cuenta': False,
            'desglose': False,
            'nombre_first': False,
            'direccion_after': False
        }

        for i, step in enumerate(steps):
            content = self._clean_text(step.get('paso', ''))
            valid_content = self._is_valid_step(content)

            detected['beneficiary'] |= any(p.search(content) for p in self.patterns['beneficiary']) if valid_content else False
            detected['tarjeta']     |= any(p.search(content) for p in self.patterns['tarjeta'])     if valid_content else False
            detected['cuenta']      |= any(p.search(content) for p in self.patterns['cuenta'])      if valid_content else False
            detected['desglose']    |= any(p.search(content) for p in self.patterns['desglose'])    if valid_content else False

            if detected['beneficiary'] and 'nombre' in content.lower() and detected['nombre_first'] is False:
                detected['nombre_first'] = i

            if detected['nombre_first'] is not False and i > detected['nombre_first']:
                detected['direccion_after'] |= 'direcci' in content.lower()

        return detected

    def _extract_key_elements(self, steps: list) -> Dict[str, Any]:
        """Extracción y clasificación de elementos clave del caso de prueba."""
        detected = self._detect_patterns(steps)
        results: Dict[str, list] = {'given': [], 'when': [], 'then': [], 'and': []}

        location_detected = False
        url_step = None

        for step in steps:
            content    = step.get('paso', '')
            validation = step.get('validacion', '')

            if self._is_valid_step(content):
                step_type, step_content = self._classify_step(content)
                clean_content = self._clean_text(step_content)

                if "ubicacion" in clean_content.lower() or "fuera de méxico" in clean_content.lower():
                    location_detected = True

                if "ingresar a la siguiente url" in clean_content.lower():
                    url_step = f"Acceder a la plataforma: {clean_content.split('URL:')[-1].strip()}"
                    continue

                if step_type == "given":
                    results['given'].append(clean_content)
                elif step_type == "when":
                    if "click" in clean_content.lower() or "clic" in clean_content.lower():
                        results['when' if not results['when'] else 'and'].append(clean_content)
                # then: se procesa vía validaciones

            if self._is_valid_step(validation):
                clean_validation = self._clean_text(validation)
                if "fuera del territorio mexicano" in clean_validation.lower():
                    results['then'].append("Mostrar mensaje de ubicación no soportada")
                elif "redirija" in clean_validation.lower():
                    results['then'].append("Redirigir a la landing page")

        if url_step:
            results['given'].append(url_step)
        elif not results['given']:
            results['given'].append("Iniciar flujo")

        if location_detected and not results['when']:
            results['when'].append("Detectar ubicación fuera de México")

        when_actions: List[str] = []
        if detected['tarjeta']:    when_actions.append("Deslizar tarjeta")
        if detected['cuenta']:     when_actions.append("Ingresar datos de cuenta/tarjeta")
        if detected['desglose']:   when_actions.append("Registrar desglose de efectivo")
        if detected['beneficiary']:
            when_actions.append("Ingresar datos del beneficiario")
            if detected['direccion_after']:
                when_actions.append("Verificar dirección asociada")

        if when_actions:
            results['when'] = when_actions[:1]
            results['and']  = when_actions[1:]

        validations = [self._clean_text(s.get('validacion', '')) for s in steps]
        last_validation = next(
            (v for v in reversed(validations) if self._is_valid_step(v)),
            'El sistema regresa a la pantalla inicial VENTANILLA con el campo Clave habilitado'
        )
        if not results['then']:
            results['then'] = [last_validation[:150]]

        return results

    def _consolidate_steps(self, steps: List[str]) -> List[str]:
        """Consolida pasos relacionados en uno solo."""
        if not steps:
            return []

        consolidated: List[str] = []
        i = 0
        while i < len(steps):
            current = steps[i]

            if "ingresar a la siguiente url" in current.lower() and i + 1 < len(steps):
                next_step = steps[i + 1]
                if "hacer click" in next_step.lower():
                    consolidated.append(f"{current} y {next_step.split(' ', 1)[1]}")
                    i += 2
                    continue

            if "clic" in current.lower() or "click" in current.lower():
                button_actions = [current]
                j = i + 1
                while j < len(steps) and ("clic" in steps[j].lower() or "click" in steps[j].lower()):
                    button_actions.append(steps[j])
                    j += 1
                if len(button_actions) > 1:
                    buttons = ", ".join([
                        a.split("en ")[-1].replace("el ", "").replace(" botón", "")
                        for a in button_actions
                    ])
                    consolidated.append(f"Interactuar con los botones: {buttons}")
                    i = j
                    continue

            consolidated.append(current)
            i += 1

        return consolidated

    # -------------------------------------------------------------------------
    # Integración con Gemma 4 (llama-cpp-python / GGUF)
    # -------------------------------------------------------------------------

    def _classify_step_with_ai(self, step_text: str) -> Optional[Tuple[str, str]]:
        """
        Clasifica un paso individual usando Gemma 4.
        Devuelve (keyword, texto) o None si el modelo no está disponible o falla.
        Se puede usar como refuerzo puntual del sistema adaptativo.
        """
        try:
            from core.gemma_inference import run_llama_json_prompt, is_ai_runtime_configured
        except ImportError:
            return None
        if not is_ai_runtime_configured():
            return None

        prompt = (
            "Clasifica este paso de caso de prueba BDD en español. "
            "Devuelve JSON: {\"keyword\": \"given\" | \"when\" | \"then\" | \"and\"}\n"
            f"Paso: {step_text[:200]}\n"
        )
        data = run_llama_json_prompt(prompt, max_tokens=32, temperature=0.05)
        if not data:
            return None
        kw = str(data.get("keyword", "")).strip().lower()
        if kw in ("given", "when", "then", "and"):
            return kw, step_text
        return None

    def _process_steps_with_ai(self, data: dict) -> Optional[Dict[str, Any]]:
        """
        Genera los pasos Given/When/And/Then del escenario usando Gemma 4.

        Recibe el dict completo del caso (con Modulo, Titulo, CasoPrueba) para que
        el modelo tenga contexto suficiente. Devuelve None si el modelo GGUF no está
        disponible, si la respuesta no es válida o si ocurre cualquier error.
        En ese caso process_file recae en la clasificación adaptativa de keywords.
        """
        try:
            from core.gemma_inference import run_llama_json_prompt, is_ai_runtime_configured
        except ImportError:
            return None
        if not is_ai_runtime_configured():
            return None

        raw_steps = data.get("CasoPrueba", {})
        try:
            sorted_steps = sorted(raw_steps.values(), key=lambda x: int(x.get('key', 0)))
        except Exception:
            sorted_steps = list(raw_steps.values())

        module = data.get("Modulo", "")
        title  = data.get("Titulo", "")

        steps_lines: List[str] = []
        for i, s in enumerate(sorted_steps[:20], 1):
            paso = self._clean_text(s.get("paso", ""))
            val  = self._clean_text(s.get("validacion", ""))
            if self._is_valid_step(paso):
                line = f"{i}. Acción: {paso}"
                if self._is_valid_step(val):
                    line += f" | Validación: {val}"
                steps_lines.append(line)

        if not steps_lines:
            return None

        prompt = (
            f"Módulo de prueba: {module}\n"
            f"Título: {title}\n"
            "Pasos del caso de prueba:\n"
            + "\n".join(steps_lines)
            + "\n\n"
            "Genera un escenario BDD en español de negocio (sin términos técnicos ni selectores). "
            "Responde ÚNICAMENTE con este JSON (sin texto adicional):\n"
            "{\"Given\": \"<precondición o null>\", \"When\": \"<acción principal>\", "
            "\"And\": [\"<paso intermedio>\"], \"Then\": \"<resultado verificable>\"}\n"
            "Reglas:\n"
            "- Given: contexto de acceso al sistema; usa null si no aplica\n"
            "- When: acción central del operador en lenguaje de negocio\n"
            "- And: lista de pasos intermedios relevantes ([] si no hay)\n"
            "- Then: resultado observable o validación esperada\n"
            "- Máximo 130 caracteres por campo de texto\n"
        )

        result = run_llama_json_prompt(prompt, max_tokens=350, temperature=0.1)
        if not result:
            return None

        when_text = str(result.get("When") or "").strip()
        then_text = str(result.get("Then") or "").strip()
        if not when_text or not then_text:
            return None

        given_raw  = result.get("Given")
        given_text = (
            str(given_raw).strip()
            if given_raw and str(given_raw).lower() not in ("null", "none", "")
            else ""
        )
        and_list = [str(a).strip() for a in (result.get("And") or []) if str(a).strip()]

        self.processed_count += 1
        if self.processed_count % 10 == 0:
            self._save_learned_patterns()

        logger.debug(f"Gemma 4 generó escenario: Given='{given_text}' When='{when_text}'")
        return {
            "Given": given_text or "Iniciar flujo",
            "When":  when_text[:130],
            "And":   and_list[:2],
            "Then":  then_text[:130],
        }

    # -------------------------------------------------------------------------
    # Procesamiento de pasos (camino adaptativo por keywords)
    # -------------------------------------------------------------------------

    def _process_steps(self, raw_steps: Dict) -> Dict[str, Any]:
        """Genera los pasos BDD usando el sistema adaptativo de keywords."""
        sorted_steps = sorted(
            raw_steps.values(),
            key=lambda x: int(x.get('key', 0))
        )

        extracted = self._extract_key_elements(sorted_steps)

        additional_steps: List[str] = []
        last_step_type = None

        for step in sorted_steps:
            content = step.get('paso', '')
            if not self._is_valid_step(content):
                continue
            step_type, step_content = self._classify_step(content)
            step_content = self._clean_text(step_content)
            if step_type == "when" and step_content not in extracted['when']:
                if last_step_type == "when":
                    additional_steps.append(step_content)
                last_step_type = step_type

        consolidated_and = self._consolidate_steps(additional_steps[:2])

        result = {
            'Given': extracted['given'][0] if extracted['given'] else "Iniciar flujo",
            'When':  extracted['when'][0]  if extracted['when']  else "Ejecutar proceso principal",
            'Then':  extracted['then'][0]  if extracted['then']  else "Validar resultado esperado",
            'And':   consolidated_and
        }

        self._evaluate_and_improve_classification(sorted_steps, result)
        self.processed_count += 1

        return result

    # -------------------------------------------------------------------------
    # Formato y generación del archivo .feature
    # -------------------------------------------------------------------------

    def _format_step(self, text: str) -> str:
        clean = re.sub(r'["\'"\u201c\u201d\u2018\u2019]', '', text)
        wrapped = textwrap.wrap(clean, width=150, break_long_words=False)
        return '\n      '.join(wrapped)

    def _generate_feature(self, module: str, title: str, steps: Dict) -> str:
        clean_module   = re.sub(r'\W+', '_', module.split('-')[-1]).strip('_')
        scenario_name  = re.sub(r'[\W_]+', ' ', title.split('_')[-1]).title()[:70]

        feature_lines = [
            f"Feature: {clean_module}",
            f"  Scenario: {scenario_name}",
            f"    Given {self._format_step(steps['Given'])}"
        ]

        if steps['When']:
            feature_lines.append(f"    When {self._format_step(steps['When'])}")
            for and_step in steps.get('And', []):
                feature_lines.append(f"    And {self._format_step(and_step)}")

        feature_lines.append(f"    Then {self._format_step(steps['Then'])}")

        return '\n'.join(feature_lines)

    def _normalize_filename(self, filename: str) -> str:
        name       = filename.rsplit('.json', 1)[0]
        normalized = unicodedata.normalize('NFKD', name)
        ascii_name = normalized.encode('ASCII', 'ignore').decode('utf-8')
        cleaned    = re.sub(r'[^\w\s-]', '', ascii_name)
        underscored = re.sub(r'[\s-]+', '_', cleaned)
        final_name  = re.sub(r'[._]+', '_', underscored).strip('_')
        return f"{final_name}.feature"

    # -------------------------------------------------------------------------
    # Conversión por lotes
    # -------------------------------------------------------------------------

    def convert(self):
        """Método principal de conversión por lotes."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        files = [f for f in os.listdir(self.input_dir) if f.endswith('.json')]
        total_files = len(files)
        logger.info(f"Iniciando conversión de {total_files} archivos (IA: {self.use_ai})")

        if self.use_ai:
            try:
                from core.gemma_inference import is_ai_runtime_configured
                ai_ready = is_ai_runtime_configured()
            except ImportError:
                ai_ready = False

            if ai_ready:
                # IA activa: procesamiento serial para respetar _INFERENCE_LOCK del modelo
                logger.info("Modo Gemma 4 activo: procesando archivos en serie.")
                for file in files:
                    self.process_file(file)
            else:
                logger.warning(
                    "use_ai=True pero el modelo GGUF no está disponible. "
                    "Usando clasificación adaptativa paralela."
                )
                with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
                    executor.map(self.process_file, files)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
                executor.map(self.process_file, files)

    def process_file(self, filename: str, data: dict = None):
        """
        Procesa un archivo JSON y genera su .feature correspondiente.

        Flujo cuando use_ai=True:
          1. Pasada de aprendizaje de keywords (siempre activa).
          2. Intento de generación con Gemma 4.
          3. Si Gemma falla o no está disponible → clasificación adaptativa.
        """
        try:
            if data is None:
                file_path = os.path.join(self.input_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # Pasada de aprendizaje adaptativo (siempre activa)
            self._learning_pass(data.get("CasoPrueba", {}))

            # Intentar generación con Gemma 4 si está habilitada
            processed: Optional[Dict[str, Any]] = None
            if self.use_ai:
                processed = self._process_steps_with_ai(data)
                if processed is None:
                    logger.debug(
                        f"Gemma 4 sin resultado para '{filename}'; "
                        "usando clasificación adaptativa de keywords."
                    )

            if processed is None:
                processed = self._process_steps(data.get("CasoPrueba", {}))

            feature_content = self._generate_feature(
                module=data.get("Modulo", "Modulo_Principal"),
                title=data.get("Titulo",  "Escenario_Principal"),
                steps=processed
            )

            feature_filename = self._normalize_filename(filename)
            output_file = os.path.join(self.output_dir, feature_filename)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(feature_content)
            logger.debug(f"Archivo generado: {output_file}")

        except Exception as e:
            logger.error(f"Error procesando {filename}: {str(e)}")
