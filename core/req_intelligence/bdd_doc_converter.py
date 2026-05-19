"""
Conversor de documentos a BDD usando LLM local (Gemma + llama.cpp).

Características:
  - GBNF Grammar: restricción a nivel de inferencia para garantizar output Gherkin válido.
  - Few-Shot Prompting: ejemplos calibran el modelo para replicar el formato sin "pensar".
  - Silent error handling: errores se registran en _elia_errors.log y el proceso continúa.
  - Fallback heurístico: si LLM no está disponible, genera BDD básico desde el contenido.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

from core.req_intelligence.doc_ingestion import DocChunk

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    features_created: int
    scenarios_generated: int
    errors_logged: int


# ---------------------------------------------------------------------------
# Few-shot examples
# ---------------------------------------------------------------------------
_FEW_SHOT_EXAMPLES = """
=== EJEMPLO 1 ===
ENTRADA:
Historia: Como usuario bancario quiero hacer login para acceder a mi cuenta.
Criterios: El usuario puede ingresar usuario y contraseña. Si son correctos accede al dashboard.

SALIDA ESPERADA:
Feature: Login Bancario
  Scenario: Login exitoso con credenciales válidas
    Given el usuario está en la página de inicio de sesión
    When ingresa usuario y contraseña correctos
    Then accede al dashboard principal

=== EJEMPLO 2 ===
ENTRADA:
Descripción: Consulta de saldo de cuenta corriente
Pasos: El usuario accede a la sección Mis Cuentas y selecciona Cuenta Corriente
Resultado esperado: Se muestra el saldo actual y los últimos 5 movimientos

SALIDA ESPERADA:
Feature: Consulta de Saldo
  Scenario: El usuario consulta el saldo de su cuenta corriente
    Given el usuario está autenticado en la aplicación
    When accede a la sección Mis Cuentas y selecciona Cuenta Corriente
    Then se muestra el saldo actual
    And se muestran los últimos 5 movimientos

=== EJEMPLO 3 ===
ENTRADA:
Historia: Como administrador quiero crear nuevos usuarios para gestionar el acceso al sistema.
Criterios: Debe ingresar nombre, email y rol. El sistema valida que el email no exista. Se envía confirmación.

SALIDA ESPERADA:
Feature: Gestión de Usuarios
  Scenario: Creación exitosa de nuevo usuario
    Given el administrador está en el módulo de gestión de usuarios
    When ingresa nombre, email y rol del nuevo usuario
    And el email no existe en el sistema
    Then el sistema crea el usuario correctamente
    And envía un email de confirmación al nuevo usuario
""".strip()

_SYSTEM_PROMPT = (
    "Eres un SDET experto en Behavior-Driven Development (BDD). "
    "Tu tarea es convertir requerimientos de software en escenarios BDD estrictos en formato Gherkin en español. "
    "REGLAS OBLIGATORIAS:\n"
    "1. Usa ÚNICAMENTE las palabras clave: Feature:, Scenario:, Given, When, Then, And, But\n"
    "2. Indenta 2 espacios para Scenario: y 4 espacios para los pasos\n"
    "3. Escribe en lenguaje de negocio (sin términos técnicos, sin selectores HTML/CSS)\n"
    "4. Máximo 120 caracteres por línea de paso\n"
    "5. Given: contexto/precondición; When: acción principal; Then: resultado verificable\n"
    "6. NO incluyas texto explicativo, comentarios ni markdown — solo el bloque Gherkin\n\n"
    f"EJEMPLOS DE REFERENCIA:\n{_FEW_SHOT_EXAMPLES}\n"
)


def _resolve_gbnf_path() -> Optional[str]:
    """Localiza el archivo .gbnf tanto en desarrollo como en bundle PyInstaller."""
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        exe_dir = os.path.dirname(sys.executable)
        for base in filter(None, [meipass, exe_dir]):
            candidates.append(os.path.join(base, "resources", "gbnf", "gherkin.gbnf"))
    # Desarrollo: buscar relativo a este módulo
    this_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(this_dir, "..", "..", "resources", "gbnf", "gherkin.gbnf"))
    for p in candidates:
        p = os.path.normpath(p)
        if os.path.isfile(p):
            return p
    return None


def _build_prompt(chunk: DocChunk) -> str:
    """Construye el prompt para un DocChunk específico."""
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        "=== NUEVO REQUERIMIENTO A CONVERTIR ===\n"
        f"Título: {chunk.title}\n"
        f"{chunk.content}\n\n"
        "=== SALIDA GHERKIN (solo el bloque, sin texto adicional) ===\n"
    )


def _validate_gherkin(text: str) -> bool:
    """Validación básica: debe tener Feature: y al menos un Scenario:."""
    text = text.strip()
    return bool(re.search(r"Feature:", text) and re.search(r"Scenario:", text))


def _heuristic_gherkin(chunk: DocChunk) -> str:
    """
    Generador heurístico de Gherkin como fallback cuando el LLM no está disponible.
    Produce un escenario simple pero válido desde el contenido del chunk.
    """
    title = chunk.title[:80].strip()
    content = chunk.content

    # Intentar extraer pasos del contenido
    given_line = "el sistema está disponible y el usuario está autenticado"
    when_line = "el usuario realiza la acción descrita"
    then_line = "el sistema responde según lo esperado"

    # Para matrices de prueba, usar el row_data directamente
    if chunk.chunk_type == "test_matrix" and chunk.row_data:
        rd = chunk.row_data
        if rd.get("steps"):
            when_line = rd["steps"][:100]
        if rd.get("expected"):
            then_line = rd["expected"][:100]
        if rd.get("description"):
            given_line = f"el contexto es: {rd['description'][:80]}"

    feature_name = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9 _\-]", "", title).strip() or "Funcionalidad"
    scenario_name = f"Verificar: {title[:60]}"

    return (
        f"Feature: {feature_name}\n"
        f"  Scenario: {scenario_name}\n"
        f"    Given {given_line}\n"
        f"    When {when_line}\n"
        f"    Then {then_line}\n"
    )


class BDDDocConverter:
    """
    Convierte listas de DocChunks a archivos .feature usando LLM + GBNF.

    Flujo por chunk:
    1. Construir prompt con few-shot examples
    2. Llamar LLM con gramática GBNF (garantiza Gherkin válido)
    3. Validar output con regex
    4. Si falla → registrar en _elia_errors.log y usar heurístico como fallback
    5. Ensamblar features: uno por documento fuente
    """

    def __init__(self, use_ai: bool = True) -> None:
        self._use_ai = use_ai

    def convert_chunks(self, chunks: List[DocChunk], output_dir: str) -> ConversionResult:
        os.makedirs(output_dir, exist_ok=True)
        error_log_path = os.path.join(output_dir, "_elia_errors.log")

        # Agrupar chunks por documento fuente
        by_source: dict[str, List[DocChunk]] = {}
        for chunk in chunks:
            key = os.path.basename(chunk.source_file)
            by_source.setdefault(key, []).append(chunk)

        features_created = 0
        scenarios_generated = 0
        errors_logged = 0

        # Intentar cargar grammar GBNF
        grammar = None
        if self._use_ai:
            grammar = self._load_grammar()

        for source_name, source_chunks in by_source.items():
            feature_name = os.path.splitext(source_name)[0]
            # Sanitize para nombre de archivo
            safe_name = re.sub(r"[^\w\-_]", "_", feature_name)
            out_path = os.path.join(output_dir, f"{safe_name}.feature")

            scenario_blocks: List[str] = []

            for chunk in source_chunks:
                try:
                    if self._use_ai:
                        gherkin = self._convert_with_llm(chunk, grammar)
                    else:
                        gherkin = None

                    if not gherkin or not _validate_gherkin(gherkin):
                        gherkin = _heuristic_gherkin(chunk)

                    # Extraer solo los bloques Scenario: (sin el Feature: header)
                    scenario_text = self._extract_scenarios(gherkin, chunk)
                    if scenario_text:
                        scenario_blocks.append(scenario_text)
                        scenarios_generated += 1

                except Exception as e:
                    errors_logged += 1
                    self._log_error(error_log_path, chunk, str(e))
                    # Fallback heurístico silencioso
                    try:
                        gherkin = _heuristic_gherkin(chunk)
                        scenario_text = self._extract_scenarios(gherkin, chunk)
                        if scenario_text:
                            scenario_blocks.append(scenario_text)
                            scenarios_generated += 1
                    except Exception:
                        pass

            if scenario_blocks:
                feature_header = f"Feature: {feature_name}\n"
                full_feature = feature_header + "\n".join(scenario_blocks) + "\n"

                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(full_feature)
                features_created += 1

        # Resumen final en el log de errores
        if errors_logged > 0:
            with open(error_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"\n=== RESUMEN ===\n"
                    f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Features creados: {features_created}\n"
                    f"Escenarios generados: {scenarios_generated}\n"
                    f"Errores registrados: {errors_logged}\n"
                )

        return ConversionResult(
            features_created=features_created,
            scenarios_generated=scenarios_generated,
            errors_logged=errors_logged,
        )

    def _load_grammar(self):
        """Carga la gramática GBNF de Gherkin para llama-cpp-python."""
        try:
            from llama_cpp import LlamaGrammar  # type: ignore
            gbnf_path = _resolve_gbnf_path()
            if gbnf_path:
                return LlamaGrammar.from_file(gbnf_path)
            # Inline grammar como fallback si no se encuentra el archivo
            gbnf_inline = (
                'root ::= feature-block\n'
                'feature-block ::= "Feature: " text newline scenario+\n'
                'scenario ::= newline "  Scenario: " text newline step+\n'
                'step ::= "    " keyword " " text newline\n'
                'keyword ::= "Given" | "When" | "Then" | "And" | "But"\n'
                'text ::= [^\\n\\r]+\n'
                'newline ::= "\\n"\n'
            )
            return LlamaGrammar.from_string(gbnf_inline)
        except (ImportError, Exception) as e:
            logger.debug(f"GBNF grammar no disponible: {e}")
            return None

    def _convert_with_llm(self, chunk: DocChunk, grammar) -> Optional[str]:
        """Llama al LLM con el prompt del chunk y opcionalmente con la gramática GBNF."""
        try:
            from core.gemma_inference import _get_llama, is_ai_runtime_configured, _INFERENCE_LOCK  # type: ignore
        except ImportError:
            return None

        if not is_ai_runtime_configured():
            return None

        prompt = _build_prompt(chunk)

        try:
            llm = _get_llama()
        except Exception:
            return None

        call_kwargs = {
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.1,
            "top_p": 0.9,
        }
        if grammar is not None:
            call_kwargs["grammar"] = grammar

        with _INFERENCE_LOCK:
            try:
                result = llm.create_completion(**call_kwargs)
            except Exception as e:
                logger.debug(f"LLM inference error for chunk {chunk.id}: {e}")
                return None

        try:
            choices = result.get("choices") if isinstance(result, dict) else None
            if choices and isinstance(choices[0], dict):
                return str(choices[0].get("text", "") or "").strip()
        except Exception:
            pass
        return None

    def _extract_scenarios(self, gherkin_text: str, chunk: DocChunk) -> str:
        """
        Extrae los bloques Scenario: del texto Gherkin.
        Si no tiene Feature:, lo trata como si el contenido entero son escenarios.
        """
        text = gherkin_text.strip()

        # Remover el Feature: header para el ensamblado (se agrega externamente)
        feature_match = re.match(r"Feature:[^\n]*\n", text)
        if feature_match:
            text = text[feature_match.end():]

        text = text.strip()
        if not text:
            return ""

        # Asegurar indentación correcta
        lines = text.splitlines()
        fixed: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                fixed.append("")
            elif re.match(r"Scenario:", stripped):
                fixed.append(f"  {stripped}")
            elif re.match(r"(Given|When|Then|And|But)\s", stripped):
                fixed.append(f"    {stripped}")
            else:
                fixed.append(f"  {stripped}")

        return "\n".join(fixed)

    def _log_error(self, log_path: str, chunk: DocChunk, error: str) -> None:
        """Registra silenciosamente un error de conversión."""
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"\n--- ERROR [{time.strftime('%H:%M:%S')}] ---\n"
                    f"Chunk: {chunk.id}\n"
                    f"Fuente: {chunk.source_file}\n"
                    f"Título: {chunk.title}\n"
                    f"Error: {error}\n"
                )
        except Exception:
            pass
