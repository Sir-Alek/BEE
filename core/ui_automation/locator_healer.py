"""
Self-Healing Locator Generator — ELIA

Toma un action_record del _elia_meta.json enriquecido (generado por web_capture_engine.js)
y usa Gemma 4 (via gemma_inference) para proponer locators más estables.

Estrategia híbrida:
  1. Capa algorítmica — resuelve la mayoría de casos sin LLM usando el fingerprint.
  2. Capa Gemma      — usa el DOM podado + fingerprint para locators complejos.
  3. Fallback        — devuelve el selector original grabado si todo falla.

Copyright (c) 2025 Alejandro Ramírez — LAR v1.0
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Orden de preferencia de atributos para la capa algorítmica.
# Los primeros son los más estables ante cambios de UI.
_STABLE_ATTR_PRIORITY = [
    "data-testid",
    "data-qa",
    "data-cy",
    "data-test",
    "data-id",
    "data-name",
    "aria-label",
    "aria-labelledby",
]

# Umbral mínimo de stability_score para aceptar la propuesta de Gemma.
_MIN_STABILITY_SCORE = 0.65


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def heal_locator(
    action_record: Dict[str, Any],
    *,
    use_ai: bool = True,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Dado un action_record del _elia_meta.json, devuelve un dict con:
      {
        "primary":         str,    # locator recomendado
        "fallbacks":       [str],  # alternativas ordenadas por estabilidad
        "strategy":        str,    # "data-testid" | "aria" | "id" | "text" | "xpath" | "shadow" | "original"
        "stability_score": float,  # 0.0-1.0
        "shadow":          dict,   # información de shadow DOM (si aplica)
        "healed":          bool,   # True si se mejoró respecto al original
      }

    Nunca lanza excepción: en caso de fallo devuelve el selector original.
    """
    original = str(action_record.get("selector") or "")
    shadow_info: Dict[str, Any] = action_record.get("shadow") or {}

    try:
        result = _algorithmic_heal(action_record)
        if result and result.get("stability_score", 0) >= _MIN_STABILITY_SCORE:
            result["healed"] = result["primary"] != original
            result["shadow"] = shadow_info
            return result
    except Exception as e:
        logger.debug(f"locator_healer: capa algorítmica falló: {e}")

    if use_ai:
        try:
            ai_result = _gemma_heal(action_record, temperature=temperature)
            if ai_result and ai_result.get("stability_score", 0) >= _MIN_STABILITY_SCORE:
                ai_result["healed"] = ai_result["primary"] != original
                ai_result["shadow"] = shadow_info
                return ai_result
        except Exception as e:
            logger.debug(f"locator_healer: capa Gemma falló: {e}")

    return _original_fallback(action_record)


def heal_recording_meta(
    meta: Dict[str, Any],
    *,
    use_ai: bool = True,
) -> Dict[str, Any]:
    """
    Procesa el _elia_meta.json completo y devuelve una versión con locators sanados.
    Itera sobre cada action_record y aplica heal_locator.
    """
    actions = meta.get("actions") if isinstance(meta, dict) else None
    if not isinstance(actions, list):
        return meta

    healed_actions: List[Dict[str, Any]] = []
    for rec in actions:
        if not isinstance(rec, dict):
            healed_actions.append(rec)
            continue
        healed = heal_locator(rec, use_ai=use_ai)
        merged = dict(rec)
        merged["healed_locator"] = healed
        healed_actions.append(merged)

    out = dict(meta)
    out["actions"] = healed_actions
    out["healed"] = True
    return out


# ---------------------------------------------------------------------------
# Capa 1 — Algorítmica (sin LLM)
# ---------------------------------------------------------------------------

def _algorithmic_heal(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Intenta generar locators estables a partir del fingerprint sin invocar al modelo.
    Devuelve None si no puede producir nada mejor que el selector original.
    """
    fp: Dict[str, Any] = record.get("fingerprint") or {}
    tag: str = str(record.get("tag") or "*")
    rid: str = str(record.get("id") or "")
    shadow: Dict[str, Any] = record.get("shadow") or {}
    ancestors: List[Dict[str, Any]] = record.get("ancestors") or []

    candidates: List[tuple[str, float, str]] = []  # (selector, score, strategy)

    # --- data-* y aria-label (más estables) ---
    data_attrs: Dict[str, str] = fp.get("data_attrs") or {}
    for attr in _STABLE_ATTR_PRIORITY:
        val = data_attrs.get(attr) or fp.get(attr.replace("-", "_")) or ""
        if not val and attr == "aria-label":
            val = fp.get("aria_label") or ""
        if val:
            css = f'[{attr}="{_css_escape(val)}"]'
            score = 0.95 if attr.startswith("data-") else 0.88
            candidates.append((css, score, attr))
            # Versión con tag para mayor especificidad
            candidates.append((f'{tag}[{attr}="{_css_escape(val)}"]', score - 0.01, attr))

    # --- id estable (sin generados por frameworks) ---
    if rid and not re.search(r'\d{4,}|:[a-z0-9]{6,}|ng-|ember|__', rid):
        candidates.append((f"#{_css_escape(rid)}", 0.93, "id"))

    # --- name attribute ---
    name_val = fp.get("name_attr") or ""
    if name_val:
        candidates.append((f'{tag}[name="{_css_escape(name_val)}"]', 0.80, "name"))

    # --- texto visible corto + tag (solo para botones/links) ---
    text = (fp.get("text_content") or "").strip()
    role = (fp.get("role") or "").lower()
    if text and len(text) <= 40 and role in ("button", "link", "a", "button", "submit"):
        xpath_text = f'//{tag}[normalize-space(text())="{_xpath_escape(text)}"]'
        candidates.append((xpath_text, 0.75, "text"))

    # --- Anclaje en ancestro con id/data-testid estable ---
    for anc in ancestors[:2]:
        anc_id = anc.get("id") or ""
        anc_dt = anc.get("data_testid") or ""
        if anc_id and not re.search(r'\d{4,}', anc_id):
            anchor = f'#{_css_escape(anc_id)}'
            if candidates:
                best_inner, best_score, best_strat = candidates[0]
                if not best_inner.startswith("#"):
                    anchored = f'{anchor} {best_inner}'
                    candidates.insert(0, (anchored, min(best_score + 0.03, 0.99), best_strat))
        elif anc_dt:
            anchor = f'[data-testid="{_css_escape(anc_dt)}"]'
            if candidates:
                best_inner, best_score, best_strat = candidates[0]
                anchored = f'{anchor} {best_inner}'
                candidates.insert(0, (anchored, min(best_score + 0.02, 0.99), best_strat))

    if not candidates:
        return None

    # Ordenar por score desc
    candidates.sort(key=lambda x: x[1], reverse=True)
    primary, score, strategy = candidates[0]
    fallbacks = [c[0] for c in candidates[1:5]]

    # Agregar xpath original como último fallback
    original_xpath = str(record.get("xpath") or "")
    if original_xpath and original_xpath not in fallbacks:
        fallbacks.append(original_xpath)

    # Shadow DOM: anotar la estrategia
    if shadow.get("is_shadow_child"):
        strategy = f"shadow:{strategy}"

    return {
        "primary":         primary,
        "fallbacks":       fallbacks,
        "strategy":        strategy,
        "stability_score": round(score, 3),
    }


# ---------------------------------------------------------------------------
# Capa 2 — Gemma 4 (LLM)
# ---------------------------------------------------------------------------

def _gemma_heal(
    record: Dict[str, Any],
    *,
    temperature: float = 0.1,
) -> Optional[Dict[str, Any]]:
    """
    Usa Gemma 4 para proponer locators a partir del contexto DOM podado.
    Devuelve None si el modelo no está disponible o la respuesta no es válida.
    """
    try:
        from core.gemma_inference import run_llama_json_prompt, is_ai_runtime_configured
    except ImportError:
        return None
    if not is_ai_runtime_configured():
        return None

    fp: Dict[str, Any]          = record.get("fingerprint") or {}
    ancestors: List[Dict]       = record.get("ancestors")   or []
    shadow: Dict[str, Any]      = record.get("shadow")      or {}
    pruned_dom: str             = str(record.get("pruned_dom") or "")
    original_selector: str      = str(record.get("selector") or "")
    original_xpath: str         = str(record.get("xpath")    or "")
    kind: str                   = str(record.get("kind")     or "click")

    # Limitar DOM podado para no saturar el contexto del modelo
    dom_excerpt = pruned_dom[:2000] if len(pruned_dom) > 2000 else pruned_dom

    prompt = (
        "You are a test automation expert generating stable Selenium/Puppeteer locators.\n"
        "Analyze the element context below and return ONE JSON object (no extra text):\n"
        '{"primary": "<css or xpath>", "fallbacks": ["<alt1>", "<alt2>"], '
        '"strategy": "<data-testid|aria|id|text|xpath|shadow>", "stability_score": <0.0-1.0>}\n\n'
        f"Action kind: {kind}\n"
        f"Element fingerprint: {_compact_json(fp)}\n"
        f"Ancestor chain (nearest first): {_compact_json(ancestors[:3])}\n"
        f"Shadow DOM: {_compact_json(shadow)}\n"
        f"Original selector: {original_selector}\n"
        f"Original XPath: {original_xpath}\n"
        f"Pruned DOM context:\n{dom_excerpt}\n\n"
        "Rules:\n"
        "- Prefer data-testid, aria-label, role+name over fragile selectors.\n"
        "- If shadow.is_shadow_child=true, use shadow host selector + inner selector pattern.\n"
        "- Avoid nth-child, dynamic class names, auto-generated ids (contain 4+ digits).\n"
        "- stability_score: 1.0=perfect (data-testid), 0.5=fragile (nth-child), 0.0=invalid.\n"
    )

    data = run_llama_json_prompt(prompt, max_tokens=256, temperature=temperature)
    if not data:
        return None

    primary = str(data.get("primary") or "").strip()
    if not primary:
        return None

    score = float(data.get("stability_score") or 0)
    strategy = str(data.get("strategy") or "gemma").strip()
    fallbacks_raw = data.get("fallbacks") or []
    fallbacks = [str(f).strip() for f in fallbacks_raw if str(f).strip()]

    # Agregar original xpath como último fallback de seguridad
    if original_xpath and original_xpath not in fallbacks:
        fallbacks.append(original_xpath)

    return {
        "primary":         primary,
        "fallbacks":       fallbacks,
        "strategy":        strategy,
        "stability_score": round(min(max(score, 0.0), 1.0), 3),
    }


# ---------------------------------------------------------------------------
# Fallback final — devuelve el selector original intacto
# ---------------------------------------------------------------------------

def _original_fallback(record: Dict[str, Any]) -> Dict[str, Any]:
    selector = str(record.get("selector") or "")
    xpath    = str(record.get("xpath")    or "")
    shadow   = record.get("shadow") or {}
    fallbacks: List[str] = []
    if xpath and xpath != selector:
        fallbacks.append(xpath)
    return {
        "primary":         selector,
        "fallbacks":       fallbacks,
        "strategy":        "original",
        "stability_score": 0.4,
        "shadow":          shadow,
        "healed":          False,
    }


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _css_escape(value: str) -> str:
    """Escapa caracteres problemáticos para valores en selectores CSS."""
    return (value or "").replace('"', '\\"').replace("'", "\\'")


def _xpath_escape(value: str) -> str:
    """Escapa texto para expresiones XPath."""
    return (value or "").replace('"', "&quot;").replace("'", "\\'")


def _compact_json(obj: Any) -> str:
    """Serialización JSON compacta (sin espacios extra)."""
    import json
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(obj)
