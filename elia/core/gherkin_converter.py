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
# import torch
from typing import Dict, Any, List, Tuple
import concurrent.futures
# from transformers import (
#     AutoTokenizer,
#     AutoModelForCausalLM
# )
import logging

logger = logging.getLogger(__name__)

class UltimateGherkinConverter:
    def __init__(self, input_dir: str, output_dir: str, use_ai: bool = False):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.use_ai = use_ai
        self.patterns = self._compile_patterns()
        self.tokenizer = None
        self.model = None
        self.batch_size = 4
        self.processed_count = 0  
        
        # Inicializar sistema adaptativo
        self._build_adaptive_keyword_system()
        
        # if self.use_ai:
        #     self._load_ai_model()
            
    def _build_adaptive_keyword_system(self):
        """Sistema adaptativo que aprende nuevos patrones de palabras clave"""
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
        
        # Archivo para persistir palabras aprendidas
        self.learning_file = os.path.join(self.output_dir, "learned_patterns.json")
        self._load_learned_patterns()

    def _load_learned_patterns(self):
        """Cargar patrones aprendidos de ejecuciones anteriores"""
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    learned = json.load(f)
                    for key in self.adaptive_patterns:
                        self.adaptive_patterns[key].update(learned.get(key, []))
        except Exception as e:
            logger.warning(f"No se pudieron cargar patrones aprendidos: {str(e)}")

    def _save_learned_patterns(self):
        """Guardar nuevos patrones descubiertos"""
        try:
            learned_data = {key: list(values) for key, values in self.adaptive_patterns.items()}
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(learned_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"No se pudieron guardar patrones aprendidos: {str(e)}")            

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

    # def _load_ai_model(self):
    #     """Carga el modelo de IA con configuración optimizada"""
    #     try:
    #         model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
                    
    #         self.tokenizer = AutoTokenizer.from_pretrained(
    #             model_name,
    #             use_fast=True,
    #             trust_remote_code=True
    #         )
            
    #         self.model = AutoModelForCausalLM.from_pretrained(
    #             model_name,
    #             device_map="auto",
    #             torch_dtype=torch.float32,
    #             low_cpu_mem_usage=True,
    #             trust_remote_code=True
    #         ).eval()
            
    #         logger.info("Modelo de IA cargado exitosamente")
            
    #     except Exception as e:
    #         logger.error(f"Error cargando modelo IA: {str(e)}")
    #         self.use_ai = False
    #         logger.warning("Optimización con IA desactivada debido a errores de carga")

    def _clean_text(self, text: str) -> str:
        """Limpieza mejorada de texto combinando ambas versiones"""
        # Primero normalizar URLs
        text = re.sub(r'(https?://[^\s]+)', lambda m: m.group(0).replace(' ', ''), text)
        
        # Eliminar comillas y caracteres no deseados
        text = re.sub(r'["\'”“‘’?]', '', text)
        
        # Limpiar otros caracteres especiales pero mantener puntuación básica
        return re.sub(r'[^\wá-úÁ-Ú \n\-:.,;¿¡!()/@]', '', text, flags=re.IGNORECASE).strip()

    def _is_valid_step(self, text: str) -> bool:    
        return len(text.strip()) > 2 and not re.match(r'^[\d\W]+$', text)

    def _classify_step(self, step_text: str) -> Tuple[str, str]:
        """Clasificación adaptativa de pasos con aprendizaje"""
        step_text_lower = step_text.lower()
        
        # Detectar y aprender nuevas palabras clave
        self._analyze_and_learn_keywords(step_text_lower)
        
        # Given: Configuración inicial con puntuación
        given_score = sum(3 for keyword in self.adaptive_patterns['given_keywords'] 
                        if keyword in step_text_lower)
        
        # When: Acciones con puntuación ponderada
        when_score = sum(3 for keyword in self.adaptive_patterns['when_keywords'] 
                        if keyword in step_text_lower)
        
        # Then: Validaciones con puntuación
        then_score = sum(3 for keyword in self.adaptive_patterns['then_keywords'] 
                        if keyword in step_text_lower)
        
        # Puntos adicionales por patrones específicos
        if any(word in step_text_lower for word in ["url", "enlace", "dirección web"]):
            given_score += 2
            
        if any(word in step_text_lower for word in ["botón", "menú", "opción"]):
            when_score += 2
            
        if any(word in step_text_lower for word in ["mensaje", "error", "éxito"]):
            then_score += 2
        
        # Decisión basada en puntuación
        scores = {'given': given_score, 'when': when_score, 'then': then_score}
        best_match = max(scores.items(), key=lambda x: x[1])
        
        if best_match[1] > 0:
            return best_match[0], step_text
        
        # Fallback: análisis de contexto para casos ambiguos
        return self._contextual_classification(step_text, step_text_lower)

    def _analyze_and_learn_keywords(self, step_text: str):
        """Analiza el texto para aprender nuevas palabras clave"""
        words = re.findall(r'\b[a-zá-ú]{4,15}\b', step_text)
        
        for word in words:
            # Aprender de contextos específicos
            if any(ctx in step_text for ctx in ["presionar", "hacer clic", "seleccionar"]):
                self.adaptive_patterns['when_keywords'].add(word)
            elif any(ctx in step_text for ctx in ["verificar", "validar", "confirmar"]):
                self.adaptive_patterns['then_keywords'].add(word)
            elif any(ctx in step_text for ctx in ["configurar", "inicializar", "preparar"]):
                self.adaptive_patterns['given_keywords'].add(word)

    def _contextual_classification(self, step_text: str, step_text_lower: str) -> Tuple[str, str]:
        """Clasificación contextual para casos ambiguos"""
        # Por posición en el flujo (si está disponible el contexto)
        if hasattr(self, 'last_step_type'):
            if self.last_step_type == 'given' and 'datos' in step_text_lower:
                return 'when', step_text
            elif self.last_step_type == 'when' and any(word in step_text_lower 
                                                    for word in ['resultado', 'pantalla', 'mensaje']):
                return 'then', step_text
        
        # Por contenido específico
        if any(word in step_text_lower for word in ['campo', 'tecla', 'opción']):
            return 'when', step_text
        elif any(word in step_text_lower for word in ['correcto', 'incorrecto', 'error']):
            return 'then', step_text
        
        # Por defecto
        return 'and', step_text
    
    def _evaluate_and_improve_classification(self, original_steps: list, generated_steps: dict):
        """Evalúa la clasificación y mejora los patrones"""
        # Analizar coherencia del flujo
        flow_issues = self._detect_flow_issues(generated_steps)
        
        if flow_issues:
            logger.info(f"Problemas de flujo detectados: {flow_issues}")
            # Ajustar patrones basado en problemas detectados
            self._adjust_patterns_based_on_issues(flow_issues, original_steps)
        
        # Guardar patrones aprendidos periódicamente
        if hasattr(self, 'processed_count') and self.processed_count % 10 == 0:
            self._save_learned_patterns()

    def _detect_flow_issues(self, generated_steps: dict) -> list:
        """Detecta problemas en el flujo generado"""
        issues = []
        
        # Verificar que haya al menos un When y Then
        if not generated_steps.get('When'):
            issues.append("Falta acción principal (When)")
        
        if not generated_steps.get('Then'):
            issues.append("Falta validación (Then)")
        
        # Verificar coherencia temporal
        if generated_steps.get('Then') and not generated_steps.get('When'):
            issues.append("Then sin When previo")
        
        return issues    

    def _detect_patterns(self, steps: list) -> Dict[str, Any]:
        """Detección de patrones"""
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
            detected['tarjeta'] |= any(p.search(content) for p in self.patterns['tarjeta']) if valid_content else False
            detected['cuenta'] |= any(p.search(content) for p in self.patterns['cuenta']) if valid_content else False
            detected['desglose'] |= any(p.search(content) for p in self.patterns['desglose']) if valid_content else False

            if detected['beneficiary'] and 'nombre' in content.lower() and detected['nombre_first'] is False:
                detected['nombre_first'] = i
            
            if detected['nombre_first'] is not False and i > detected['nombre_first']:
                detected['direccion_after'] |= 'direcci' in content.lower()

        return detected

    def _extract_key_elements(self, steps: list) -> Dict[str, Any]:
        """Extracción de elementos clave"""
        detected = self._detect_patterns(steps)
        results = {
            'given': [],
            'when': [],
            'then': [],
            'and': []
        }
        
        location_detected = False
        url_step = None
        
        for step in steps:
            content = step.get('paso', '')
            validation = step.get('validacion', '')
            
            if self._is_valid_step(content):
                step_type, step_content = self._classify_step(content)
                clean_content = self._clean_text(step_content)
                
                # Detectar flujo de ubicación
                if "ubicacion" in clean_content.lower() or "fuera de méxico" in clean_content.lower():
                    location_detected = True
                
                # Capturar URL como Given especial
                if "ingresar a la siguiente url" in clean_content.lower():
                    url_step = f"Acceder a la plataforma: {clean_content.split('URL:')[-1].strip()}"
                    continue
                    
                if step_type == "given":
                    results['given'].append(clean_content)
                elif step_type == "when":
                    if "click" in clean_content.lower() or "clic" in clean_content.lower():
                        results['when' if not results['when'] else 'and'].append(clean_content)
                elif step_type == "then":
                    pass  # Las validaciones se procesan aparte
            
            if self._is_valid_step(validation):
                clean_validation = self._clean_text(validation)
                if "fuera del territorio mexicano" in clean_validation.lower():
                    results['then'].append("Mostrar mensaje de ubicación no soportada")
                elif "redirija" in clean_validation.lower():
                    results['then'].append("Redirigir a la landing page")
        
        # Construcción inteligente del Given basada en patrones detectados
        if url_step:
            results['given'].append(url_step)
        elif not results['given']:
            results['given'].append("Iniciar flujo")
        
        # Manejo especial para flujo de ubicación
        if location_detected and not results['when']:
            results['when'].append("Detectar ubicación fuera de México")
        
        # Incorpora detección de patrones
        when_actions = []
        if detected['tarjeta']: when_actions.append("Deslizar tarjeta")
        if detected['cuenta']: when_actions.append("Ingresar datos de cuenta/tarjeta")
        if detected['desglose']: when_actions.append("Registrar desglose de efectivo")
        if detected['beneficiary']: 
            when_actions.append("Ingresar datos del beneficiario")
            if detected['direccion_after']:
                when_actions.append("Verificar dirección asociada")
        
        if when_actions:
            results['when'] = when_actions[:1]  # Tomar la primera acción principal
            results['and'] = when_actions[1:]  # Las demás como pasos adicionales
        
        # Procesar validaciones
        validations = [self._clean_text(s.get('validacion', '')) for s in steps]
        last_validation = next((v for v in reversed(validations) if self._is_valid_step(v)), 
            'El sistema regresa a la pantalla inicial VENTANILLA con el campo Clave habilitado')
        
        if not results['then']:
            results['then'] = [last_validation[:150]]
        
        return results

    def _consolidate_steps(self, steps: List[str]) -> List[str]:
        """Consolida pasos relacionados en uno solo"""
        if not steps:
            return []
        
        consolidated = []
        i = 0
        
        while i < len(steps):
            current = steps[i]
            
            # Consolidar pasos de URL + acciones
            if "ingresar a la siguiente url" in current.lower() and i+1 < len(steps):
                next_step = steps[i+1]
                if "hacer click" in next_step.lower():
                    consolidated.append(f"{current} y {next_step.split(' ', 1)[1]}")
                    i += 2
                    continue
            
            # Consolidar pasos de botones consecutivos
            if "clic" in current.lower() or "click" in current.lower():
                button_actions = [current]
                j = i + 1
                while j < len(steps) and ("clic" in steps[j].lower() or "click" in steps[j].lower()):
                    button_actions.append(steps[j])
                    j += 1
                
                if len(button_actions) > 1:
                    buttons = ", ".join([action.split("en ")[-1].replace("el ", "").replace(" botón", "") 
                                for action in button_actions])
                    consolidated.append(f"Interactuar con los botones: {buttons}")
                    i = j
                    continue
            
            consolidated.append(current)
            i += 1
        
        return consolidated

    def _optimize_text_batch(self, texts: List[str]) -> List[str]:
        """Procesamiento por lotes para optimización con IA"""
        if not self.use_ai or not self.model:
            return texts
            
        try:
            prompts = [
                f"<|system|>Optimiza este texto técnico manteniendo formato Gherkin</s>"
                f"<|user|>{text}</s><|assistant|>"
                for text in texts
            ]
            
            inputs = self.tokenizer(
                prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128
            ).to(self.model.device)

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.3,
                top_p=0.95,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            return [
                self.tokenizer.decode(out, skip_special_tokens=True)
                .split("<|assistant|>")[-1]
                .strip()
                for out in outputs
            ]
            
        except Exception as e:
            logger.error(f"Error en optimización por lotes: {str(e)}")
            return texts

    # def _optimize_text_with_ai(self, text: str) -> str:
    #     """Optimización individual de texto con IA"""
    #     if not self.use_ai or not self.model:
    #         return text
            
    #     try:
    #         prompt = f"""<|system|>
    #         Mejora este texto manteniendo su significado técnico y formato Gherkin.
    #         <|user|>
    #         Genera la versión mejorada:</s>
    #         <|assistant|>"""
            
    #         inputs = self.tokenizer(
    #             prompt,
    #             return_tensors="pt",
    #             return_attention_mask=False
    #         ).to(self.model.device)

    #         outputs = self.model.generate(
    #             **inputs,
    #             max_new_tokens=100,
    #             temperature=0.3,
    #             do_sample=True
    #         )
            
    #         full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
    #         optimized_text = full_response.split("<|assistant|>")[-1].strip()
            
    #         return optimized_text if 10 < len(optimized_text) <= 150 else text
            
    #     except Exception as e:
    #         logger.error(f"Error en optimización individual: {str(e)}")
    #         return text

    def _process_steps(self, raw_steps: Dict) -> Dict[str, Any]:
        sorted_steps = sorted(
            raw_steps.values(),
            key=lambda x: int(x.get('key', 0)))
        
        extracted = self._extract_key_elements(sorted_steps)
        
        # Procesar pasos adicionales para evitar repeticiones
        additional_steps = []
        last_step_type = None
        
        for step in sorted_steps:
            content = step.get('paso', '')
            if not self._is_valid_step(content):
                continue
                
            step_type, step_content = self._classify_step(content)
            step_content = self._clean_text(step_content)
            
            # Evitar duplicados y agregar solo pasos relevantes
            if step_type == "when" and step_content not in extracted['when']:
                if last_step_type == "when":
                    additional_steps.append(step_content)
                last_step_type = step_type
        
        # Limitar pasos adicionales y consolidar
        consolidated_and = self._consolidate_steps(additional_steps[:2])
        
        result = {
            'Given': extracted['given'][0] if extracted['given'] else "Iniciar flujo",
            'When': extracted['when'][0] if extracted['when'] else "Ejecutar proceso principal",
            'Then': extracted['then'][0] if extracted['then'] else "Validar resultado esperado",
            'And': consolidated_and
        }
        
        # Evaluar y mejorar (nuevo)
        self._evaluate_and_improve_classification(sorted_steps, result)
        self.processed_count += 1
        
        return result

    def _format_step(self, text: str) -> str:
        # optimized_text = self._optimize_text_with_ai(text) if self.use_ai else text
        # Asegurarse de eliminar cualquier comilla residual
        optimized_text = re.sub(r'["\'”“‘’]', '', optimized_text)
        wrapped = textwrap.wrap(optimized_text, width=150, break_long_words=False)
        return '\n      '.join(wrapped)

    def _generate_feature(self, module: str, title: str, steps: Dict) -> str:
        clean_module = re.sub(r'\W+', '_', module.split('-')[-1]).strip('_')
        scenario_name = re.sub(r'[\W_]+', ' ', title.split('_')[-1]).title()[:70]
        
        feature_lines = [
            f"Feature: {clean_module}",
            f"  Scenario: {scenario_name}",
            f"    Given {self._format_step(steps['Given'])}"
        ]

        if steps['When']:
            feature_lines.append(f"    When {self._format_step(steps['When'])}")
            for and_step in steps['And']:
                feature_lines.append(f"    And {self._format_step(and_step)}")

        feature_lines.append(f"    Then {self._format_step(steps['Then'])}")
        
        return '\n'.join(feature_lines)

    def _normalize_filename(self, filename: str) -> str:
        name = filename.rsplit('.json', 1)[0]
        normalized = unicodedata.normalize('NFKD', name)
        ascii_name = normalized.encode('ASCII', 'ignore').decode('utf-8')
        cleaned = re.sub(r'[^\w\s-]', '', ascii_name)
        underscored = re.sub(r'[\s-]+', '_', cleaned)
        final_name = re.sub(r'[._]+', '_', underscored).strip('_')
        return f"{final_name}.feature"

    def convert(self):
        """Método principal de conversión"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        files = [f for f in os.listdir(self.input_dir) if f.endswith('.json')]
        total_files = len(files)
        logger.info(f"Iniciando conversión de {total_files} archivos (IA: {self.use_ai})")

        if self.use_ai and self.model:
            # Procesamiento con IA - Versión corregida
            for i in range(0, total_files, self.batch_size):
                batch_files = files[i:i+self.batch_size]
                
                # 1. Cargar datos originales
                original_data = []
                for file in batch_files:
                    try:
                        with open(os.path.join(self.input_dir, file), 'r', encoding='utf-8') as f:
                            original_data.append((file, json.load(f)))  # Guardar datos originales
                    except Exception as e:
                        logger.error(f"Error cargando {file}: {str(e)}")
                        original_data.append((file, None))

                # 2. Extraer textos a optimizar
                texts_to_optimize = []
                for file, data in original_data:
                    if data:
                        try:
                            # Extraer solo los textos relevantes
                            texts = [
                                data.get("Modulo", ""),
                                data.get("Titulo", ""),
                                *[step.get("paso", "") for step in data.get("CasoPrueba", {}).values()],
                                *[step.get("validacion", "") for step in data.get("CasoPrueba", {}).values()]
                            ]
                            texts_to_optimize.append("\n".join(filter(None, texts)))
                        except Exception as e:
                            logger.error(f"Error procesando {file}: {str(e)}")
                            texts_to_optimize.append("")

                # 3. Optimizar en batch
                optimized_texts = self._optimize_text_batch(texts_to_optimize)

                # 4. Reconstruir JSONs con textos optimizados
                for idx, (file, data) in enumerate(original_data):
                    if data and optimized_texts[idx]:
                        try:
                            # Dividir textos optimizados
                            parts = optimized_texts[idx].split("\n")
                            
                            # Reconstruir estructura manteniendo formato original
                            data["Modulo"] = parts[0] if len(parts) > 0 else data["Modulo"]
                            data["Titulo"] = parts[1] if len(parts) > 1 else data["Titulo"]
                            
                            steps = data["CasoPrueba"].values()
                            step_index = 2
                            for step in steps:
                                if step_index < len(parts):
                                    step["paso"] = parts[step_index]
                                    step_index += 1
                                if step_index < len(parts):
                                    step["validacion"] = parts[step_index]
                                    step_index += 1
                            
                            # Procesar normalmente con los textos optimizados
                            self.process_file(file, data)  # Se requiere modificar process_file para aceptar data
                            
                        except Exception as e:
                            logger.error(f"Error reconstruyendo {file}: {str(e)}")
                            # Fallback: procesar versión original
                            self.process_file(file, original_data[idx][1])
        else:
            # Procesamiento paralelo sin IA
            with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
                executor.map(self.process_file, files)

    def process_file(self, filename: str, data: dict = None):
        """Versión modificada para aceptar datos pre-cargados"""
        try:
            if data is None:
                file_path = os.path.join(self.input_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            processed = self._process_steps(data.get("CasoPrueba", {}))
            feature_content = self._generate_feature(
                module=data.get("Modulo", "Modulo_Principal"),
                title=data.get("Titulo", "Escenario_Principal"),
                steps=processed
            )

            feature_filename = self._normalize_filename(filename)
            output_file = os.path.join(self.output_dir, feature_filename)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(feature_content)
            logger.debug(f"Archivo generado: {output_file}")

        except Exception as e:
            logger.error(f"Error procesando {filename}: {str(e)}")