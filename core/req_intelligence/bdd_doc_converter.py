"""
Conversor de documentos a BDD usando LLM local (Gemma + llama.cpp).

Características:
  - GBNF JSON (bdd_response.gbnf): Chain-of-Thought + steps estructurados → Gherkin en Python.
  - Few-Shot Prompting: ejemplos calibran el modelo.
  - ELIA_AI_COT_MODE=two_pass: análisis libre + steps con GBNF.
  - Silent error handling + fallback heurístico.
"""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.req_intelligence.doc_ingestion import DocChunk
from ui.interfaces import BDDUserCancelled, IUI

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    features_created: int
    scenarios_generated: int
    errors_logged: int
    scenarios_linked: int = 0


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
    "Conviertes requerimientos de software en escenarios BDD en español.\n"
    "IMPORTANTE — responde SOLO con un JSON válido con estos campos:\n"
    '  "analisis_previo": texto breve donde mapeas requerimientos → pasos de negocio (Chain of Thought).\n'
    '  "scenario_title": nombre del escenario sin prefijos «Verificar:» ni IDs de caso.\n'
    '  "steps": lista de objetos {"keyword":"Given|When|Then|And|But","text":"..."}\n'
    "REGLAS para steps:\n"
    "1. Lenguaje de negocio; PROHIBIDO selectores HTML, ids técnicos o nombres de botones del DOM.\n"
    "2. Estructura: ≤1 Given, exactamente 1 When, ≤1 And, exactamente 1 Then; orden Given→When→And?→Then.\n"
    "3. Máximo 120 caracteres por paso.\n"
    "4. Usa analisis_previo para razonar ANTES de redactar los steps.\n\n"
    f"EJEMPLOS DE REFERENCIA:\n{_FEW_SHOT_EXAMPLES}\n"
)


def _resolve_gbnf_path() -> Optional[str]:
    """Localiza bdd_response.gbnf (desarrollo o bundle PyInstaller)."""
    from core.gemma_gbnf import resolve_gbnf_path

    return resolve_gbnf_path("bdd_response.gbnf")


def _trim_doc_excerpt(source_chunks: List[DocChunk], max_chars: int = 10000) -> str:
    parts: List[str] = []
    total = 0
    for ch in source_chunks:
        block = f"### {ch.title}\n{ch.content}\n"
        if total + len(block) > max_chars:
            parts.append(block[: max_chars - total - 20] + "\n... [truncado]")
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts).strip()


def _memory_few_shot_block(examples: List[Dict[str, str]]) -> str:
    if not examples:
        return ""
    parts: List[str] = []
    for i, ex in enumerate(examples[:3], start=1):
        req = (ex.get("script") or "").strip()
        ft = (ex.get("feature") or "").strip()
        if req and ft:
            parts.append(
                f"[EJEMPLO DE ESTILO {i} — Requerimiento]\n{req}\n"
                f"[EJEMPLO DE ESTILO {i} — Feature BDD]\n{ft}\n"
            )
    if not parts:
        return ""
    return (
        "Imita el estilo de redacción de estos ejemplos del usuario "
        "(lenguaje de negocio, sin tecnicismos):\n"
        + "\n".join(parts)
        + "\n"
    )


def _build_prompt(chunk: DocChunk, *, memory_block: str = "") -> str:
    """Construye el prompt para un DocChunk específico."""
    mem = f"{memory_block}\n" if memory_block else ""
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"{mem}"
        "=== NUEVO REQUERIMIENTO A CONVERTIR ===\n"
        f"Título: {chunk.title}\n"
        f"{chunk.content}\n\n"
        "=== SALIDA JSON (analisis_previo + scenario_title + steps) ===\n"
    )


def _validate_gherkin(text: str) -> bool:
    """Validación básica: debe tener Feature: y al menos un Scenario:."""
    text = text.strip()
    return bool(re.search(r"Feature:", text) and re.search(r"Scenario:", text))


def _scenario_display_name(chunk: DocChunk) -> str:
    """Nombre legible del escenario sin prefijos «Caso CP001» ni «Verificar:»."""
    if chunk.row_data:
        name = str(chunk.row_data.get("name") or "").strip()
        if name:
            return name[:80]
        desc = str(chunk.row_data.get("description") or "").strip()
        if desc:
            return desc[:80]
    title = chunk.title.strip()
    title = re.sub(r"^\[[^\]]+\]\s*", "", title)
    title = re.sub(r"^Verificar:\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^Caso\s+[A-Z0-9_-]+:\s*", "", title, flags=re.IGNORECASE)
    return (title or "Escenario")[:80]


def _sanitize_gherkin_text(text: str) -> str:
    """Quita prefijos redundantes en Scenario: y Given producidos por heurística o LLM."""
    out: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        indent = line[: len(line) - len(line.lstrip())]
        m_sc = re.match(r"(Scenario:)\s*(.+)", stripped, re.IGNORECASE)
        if m_sc:
            name = m_sc.group(2).strip()
            name = re.sub(r"^Verificar:\s*", "", name, flags=re.IGNORECASE)
            name = re.sub(r"^Caso\s+[A-Z0-9_-]+:\s*", "", name, flags=re.IGNORECASE)
            out.append(f"{indent}Scenario: {name}")
            continue
        m_given = re.match(r"(Given)\s+(.+)", stripped, re.IGNORECASE)
        if m_given:
            body = m_given.group(2).strip()
            body = re.sub(r"^el contexto es:\s*", "", body, flags=re.IGNORECASE)
            body = re.sub(r"^que el contexto es\s*", "", body, flags=re.IGNORECASE)
            out.append(f"{indent}Given {body}")
            continue
        out.append(line)
    result = "\n".join(out)
    return result + ("\n" if text.endswith("\n") else "")


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
            when_line = str(rd["steps"])[:120]
        if rd.get("expected"):
            then_line = str(rd["expected"])[:120]
        pre = str(rd.get("preconditions") or "").strip()
        desc = str(rd.get("description") or "").strip()
        if pre:
            given_line = pre[:120]
        elif desc:
            given_line = desc[:120]

    feature_name = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9 _\-]", "", title).strip() or "Funcionalidad"
    scenario_name = _scenario_display_name(chunk)

    return _sanitize_gherkin_text(
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

    def __init__(self, use_ai: bool = True, ui: Optional[IUI] = None) -> None:
        self._use_ai = use_ai
        self.ui = ui

    def convert_chunks(
        self,
        chunks: List[DocChunk],
        output_dir: str,
        *,
        link_scenario: Optional[str] = None,
        link_scenario_by_doc: Optional[Dict[str, str]] = None,
        link_recording: Optional[str] = None,
        link_recording_by_doc: Optional[Dict[str, str]] = None,
        projects_dir: Optional[str] = None,
    ) -> ConversionResult:
        os.makedirs(output_dir, exist_ok=True)
        error_log_path = os.path.join(output_dir, "_elia_errors.log")
        from core.ui_automation.recording_linkage import (
            annotate_scenario_recording,
            apply_link_to_existing_scenario,
            decode_scenario_link,
            link_map_for_doc_paths,
            resolve_recording_basename_for_doc,
        )

        # Agrupar chunks por documento fuente
        by_source: dict[str, List[DocChunk]] = {}
        for chunk in chunks:
            key = os.path.basename(chunk.source_file)
            by_source.setdefault(key, []).append(chunk)

        features_created = 0
        scenarios_generated = 0
        scenarios_linked = 0
        errors_logged = 0

        # Intentar cargar grammar GBNF
        grammar = None
        if self._use_ai:
            grammar = self._load_grammar()

        memory_block = ""
        if self._use_ai:
            try:
                from core.elia_memory import recent_examples_for_prompt

                memory_block = _memory_few_shot_block(recent_examples_for_prompt(limit=3))
            except Exception:
                memory_block = ""

        for source_name, source_chunks in by_source.items():
            feature_name = os.path.splitext(source_name)[0]
            # Sanitize para nombre de archivo
            safe_name = re.sub(r"[^\w\-_]", "_", feature_name)
            out_path = os.path.join(output_dir, f"{safe_name}.feature")

            full_feature, doc_scenarios, doc_errors = self._assemble_document_feature(
                feature_name,
                source_chunks,
                grammar,
                memory_block=memory_block,
                error_log_path=error_log_path,
                temperature=0.1,
            )
            scenarios_generated += doc_scenarios
            errors_logged += doc_errors

            if not full_feature.strip():
                continue

            try:
                full_feature = self._review_document_feature(
                    full_feature,
                    source_chunks,
                    feature_name,
                    grammar,
                    memory_block=memory_block,
                    error_log_path=error_log_path,
                )
            except BDDUserCancelled:
                raise

            if full_feature.strip():
                source_path = source_chunks[0].source_file if source_chunks else source_name
                encoded_link = link_map_for_doc_paths(
                    link_scenario_by_doc, source_path, link_scenario
                )
                decoded = decode_scenario_link(encoded_link)

                if decoded:
                    ff, sn = decoded
                    if apply_link_to_existing_scenario(
                        full_feature, ff, sn, mode="append", prefer_named_scenario=False
                    ):
                        scenarios_linked += 1
                        rec_explicit = link_map_for_doc_paths(
                            link_recording_by_doc, source_path, link_recording
                        )
                        if projects_dir:
                            rec_name = resolve_recording_basename_for_doc(
                                source_path, projects_dir, rec_explicit
                            )
                            if rec_name:
                                annotate_scenario_recording(ff, sn, rec_name)
                    else:
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(full_feature)
                        features_created += 1
                else:
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
            scenarios_linked=scenarios_linked,
        )

    def _assemble_document_feature(
        self,
        feature_name: str,
        source_chunks: List[DocChunk],
        grammar,
        *,
        memory_block: str,
        error_log_path: str,
        temperature: float = 0.1,
        use_llm: bool = True,
    ) -> Tuple[str, int, int]:
        """Ensambla Feature + scenarios desde chunks. Devuelve (texto, nº escenarios, errores)."""
        scenario_blocks: List[str] = []
        errors = 0
        count = 0

        for chunk in source_chunks:
            try:
                gherkin: Optional[str] = None
                if self._use_ai and use_llm:
                    gherkin = self._convert_with_llm(
                        chunk, grammar, memory_block=memory_block, temperature=temperature
                    )
                if not gherkin or not _validate_gherkin(gherkin):
                    gherkin = _heuristic_gherkin(chunk)
                else:
                    gherkin = _sanitize_gherkin_text(gherkin)

                scenario_text = self._extract_scenarios(gherkin, chunk)
                if scenario_text:
                    scenario_blocks.append(scenario_text)
                    count += 1
            except Exception as e:
                errors += 1
                self._log_error(error_log_path, chunk, str(e))
                try:
                    gherkin = _heuristic_gherkin(chunk)
                    scenario_text = self._extract_scenarios(gherkin, chunk)
                    if scenario_text:
                        scenario_blocks.append(scenario_text)
                        count += 1
                except Exception:
                    pass

        if not scenario_blocks:
            return "", count, errors

        header = f"Feature: {feature_name}\n"
        return header + "\n".join(scenario_blocks) + "\n", count, errors

    def _review_document_feature(
        self,
        full_feature: str,
        source_chunks: List[DocChunk],
        feature_name: str,
        grammar,
        *,
        memory_block: str,
        error_log_path: str,
    ) -> str:
        """Revisión interactiva (aceptar / rechazar / editar) con memoria de correcciones."""
        if not self.ui or not self._use_ai:
            return full_feature

        try:
            from core import gemma_inference
            from core.elia_memory import append_correction, recent_examples_for_prompt
            from core.elia_memory_crypto import MANUAL_EDIT_FROM_ATTEMPT, MAX_AI_REVIEW_ATTEMPTS

            if not gemma_inference.is_ai_runtime_configured():
                return full_feature
        except ImportError:
            return full_feature

        excerpt = _trim_doc_excerpt(source_chunks)
        ai_temps = [0.1, 0.4, 0.7]
        last_rendered = full_feature.strip()
        examples = recent_examples_for_prompt(limit=3)
        mem = memory_block or _memory_few_shot_block(examples)

        for attempt in range(1, MAX_AI_REVIEW_ATTEMPTS + 1):
            can_manual = attempt >= MANUAL_EDIT_FROM_ATTEMPT
            if attempt > 1:
                temp = ai_temps[min(attempt - 1, 2)]
                last_rendered, _, _ = self._assemble_document_feature(
                    feature_name,
                    source_chunks,
                    grammar,
                    memory_block=mem,
                    error_log_path=error_log_path,
                    temperature=temp,
                    use_llm=True,
                )

            try:
                review = self.ui.bdd_preview_review(
                    feature_text=last_rendered,
                    attempt=attempt,
                    max_attempts=MAX_AI_REVIEW_ATTEMPTS,
                    script_excerpt=excerpt,
                    can_manual=can_manual,
                )
            except BDDUserCancelled:
                raise
            action = str(review.get("action") or "")
            if action == "accept":
                ft = str(review.get("feature_text") or last_rendered).strip()
                if not ft:
                    ft = last_rendered
                edited = bool(review.get("edited"))
                if edited or ft != last_rendered.strip():
                    append_correction(script_snippet=excerpt, feature_text=ft)
                return ft
            if action == "reject":
                if attempt >= MAX_AI_REVIEW_ATTEMPTS:
                    break
                continue
            if action == "use_heuristic":
                heuristic, _, _ = self._assemble_document_feature(
                    feature_name,
                    source_chunks,
                    grammar,
                    memory_block="",
                    error_log_path=error_log_path,
                    use_llm=False,
                )
                return heuristic or last_rendered

        return last_rendered

    def _load_grammar(self):
        """Carga la gramática GBNF JSON para Doc-to-BDD."""
        try:
            from core.gemma_gbnf import load_llama_grammar

            grammar = load_llama_grammar("bdd_response.gbnf")
            if grammar is not None:
                return grammar
            from llama_cpp import LlamaGrammar  # type: ignore

            gbnf_inline = (
                'root ::= "{" ws "\\"analisis_previo\\"" ":" ws string "," ws "\\"scenario_title\\"" ":" ws string "," '
                'ws "\\"steps\\"" ":" ws steps-array ws "}" ws\n'
                'steps-array ::= "[" ws step-object ("," ws step-object)* "]"\n'
                'step-object ::= "{" ws "\\"keyword\\"" ":" ws keyword "," ws "\\"text\\"" ":" ws string "}"\n'
                'keyword ::= "\\"Given\\"" | "\\"When\\"" | "\\"Then\\"" | "\\"And\\"" | "\\"But\\""\n'
                'string ::= "\\"" char* "\\""\n'
                'char ::= [^"\\\\] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])\n'
                'ws ::= [ \\t\\n\\r]*\n'
            )
            return LlamaGrammar.from_string(gbnf_inline)
        except (ImportError, Exception) as e:
            logger.debug(f"GBNF grammar no disponible: {e}")
            return None

    def _convert_with_llm_two_pass(
        self,
        chunk: DocChunk,
        *,
        memory_block: str = "",
        temperature: float = 0.1,
    ) -> Optional[str]:
        """ELIA_AI_COT_MODE=two_pass: análisis JSON libre + steps con GBNF."""
        from core.bdd_llm_response import extract_json_object, render_gherkin_from_bdd_response
        from core.gemma_inference import is_ai_runtime_configured, run_llama_gbnf_completion, run_llama_json_prompt

        if not is_ai_runtime_configured():
            return None

        analysis_prompt = (
            f"{_SYSTEM_PROMPT}\n\n{memory_block}"
            "Analiza el requerimiento y responde SOLO con JSON: "
            '{"analisis_previo":"..."}\n\n'
            f"Título: {chunk.title}\n{chunk.content}\n"
        )
        analysis_data = run_llama_json_prompt(analysis_prompt, max_tokens=320, temperature=temperature)
        analysis = str((analysis_data or {}).get("analisis_previo") or "").strip()

        steps_prompt = (
            f"{memory_block}"
            f"Análisis previo del requerimiento:\n{analysis or '(sin análisis)'}\n\n"
            f"Título: {chunk.title}\n{chunk.content}\n\n"
            "Genera steps BDD en español (lenguaje de negocio). "
            f'Escenario sugerido: "{_scenario_display_name(chunk)}"\n'
        )
        steps_text = run_llama_gbnf_completion(
            steps_prompt,
            gbnf_file="bdd_steps.gbnf",
            max_tokens=512,
            temperature=temperature,
        )
        if not steps_text:
            return None
        steps_data = extract_json_object(steps_text) or {}
        merged = {
            "analisis_previo": analysis,
            "scenario_title": _scenario_display_name(chunk),
            "steps": steps_data.get("steps"),
        }
        return render_gherkin_from_bdd_response(merged, feature_name=_scenario_display_name(chunk))

    def _convert_with_llm(
        self,
        chunk: DocChunk,
        grammar,
        memory_block: str = "",
        temperature: float = 0.1,
    ) -> Optional[str]:
        """Llama al LLM con GBNF JSON (CoT + steps) y renderiza Gherkin en Python."""
        try:
            from core.gemma_inference import ai_cot_mode, is_ai_runtime_configured, run_llama_gbnf_completion
        except ImportError:
            return None

        if not is_ai_runtime_configured():
            return None

        if ai_cot_mode() == "two_pass":
            return self._convert_with_llm_two_pass(
                chunk, memory_block=memory_block, temperature=temperature
            )

        from core.bdd_llm_response import parse_bdd_llm_text

        prompt = _build_prompt(chunk, memory_block=memory_block)
        text = run_llama_gbnf_completion(
            prompt,
            gbnf_file="bdd_response.gbnf",
            grammar=grammar,
            max_tokens=768,
            temperature=temperature,
        )
        if not text:
            return None
        gherkin = parse_bdd_llm_text(text, feature_name=_scenario_display_name(chunk))
        if gherkin and _validate_gherkin(gherkin):
            return gherkin
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
