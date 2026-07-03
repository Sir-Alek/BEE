"""Traducción asistida Groovy JMeter → scripts Postman (subset ELIA)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_MENSAJES_PUT_RE = re.compile(
    r'vars\.put\s*\(\s*["\']([^"\']+)["\']\s*,\s*json\.mensajes\[(\d+)\]\.msg',
    re.MULTILINE,
)
_SIMPLE_PUT_RE = re.compile(
    r'vars\.put\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*\)',
    re.MULTILINE,
)
_VARS_GET_RE = re.compile(r'vars\.get\s*\(\s*["\']([^"\']+)["\']\s*\)')


@dataclass
class GroovyTranslation:
    status: str  # translated | stub | omitted
    pre_script: Optional[str] = None
    post_script: Optional[str] = None
    extractors: List[Dict[str, str]] = field(default_factory=list)
    message: str = ""


def _translate_mensajes_post(script: str, sampler_name: str) -> Optional[GroovyTranslation]:
    matches = _MENSAJES_PUT_RE.findall(script)
    if not matches:
        return None
    max_idx = max(int(idx) for _, idx in matches)
    lines = [
        "// Migrado desde Groovy JMeter — revisar",
        "const data = pm.response.json();",
        f"if (data && data.mensajes && data.mensajes.length >= {max_idx + 1}) {{",
    ]
    extractors: List[Dict[str, str]] = []
    seen_vars: set[str] = set()
    for var_name, idx in matches:
        if var_name in seen_vars:
            continue
        seen_vars.add(var_name)
        lines.append(
            f'  pm.variables.set("{var_name}", String((data.mensajes[{idx}] && data.mensajes[{idx}].msg) || ""));'
        )
        extractors.append(
            {
                "kind": "jsonpath",
                "expression": f"$.mensajes[{idx}].msg",
                "target_var": var_name,
            }
        )
    lines.append("}")
    return GroovyTranslation(
        status="translated",
        post_script="\n".join(lines),
        extractors=extractors,
        message=f"Post-procesador Groovy traducido en «{sampler_name}» ({len(seen_vars)} variables).",
    )


def _translate_simple_puts(script: str, *, phase: str, sampler_name: str) -> Optional[GroovyTranslation]:
    puts = _SIMPLE_PUT_RE.findall(script)
    if not puts:
        return None
    lines = ["// Migrado desde Groovy JMeter — revisar"]
    for var_name, value in puts:
        lines.append(f'pm.variables.set("{var_name}", "{value}");')
    target = "pre_script" if phase == "pre" else "post_script"
    return GroovyTranslation(
        status="translated",
        **{target: "\n".join(lines)},
        message=f"Script Groovy ({phase}) traducido en «{sampler_name}» ({len(puts)} vars.put).",
    )


def _stub_script(script: str, *, phase: str, sampler_name: str) -> GroovyTranslation:
    header = f"// Groovy JMeter ({phase}) en «{sampler_name}» — replicar manualmente"
    body_lines = [line.rstrip() for line in script.strip().splitlines()[:24]]
    if len(script.splitlines()) > 24:
        body_lines.append("// … script truncado …")
    commented = "\n".join(f"// {line}" if line.strip() else "//" for line in body_lines)
    target = "pre_script" if phase == "pre" else "post_script"
    return GroovyTranslation(
        status="stub",
        **{target: f"{header}\n{commented}"},
        message=f"Script Groovy ({phase}) en «{sampler_name}» convertido a stub comentado.",
    )


def translate_groovy_scripts(
    sampler_name: str,
    pre_scripts: List[str],
    post_scripts: List[str],
) -> List[GroovyTranslation]:
    out: List[GroovyTranslation] = []
    for script in pre_scripts:
        text = (script or "").strip()
        if not text:
            continue
        translated = _translate_simple_puts(text, phase="pre", sampler_name=sampler_name)
        if translated:
            if _VARS_GET_RE.search(text) or "MessageDigest" in text or "JsonOutput" in text:
                translated = _stub_script(text, phase="pre", sampler_name=sampler_name)
                translated.message = (
                    f"Pre-procesador Groovy complejo en «{sampler_name}» — stub comentado (revisar body/vars)."
                )
            out.append(translated)
        else:
            out.append(_stub_script(text, phase="pre", sampler_name=sampler_name))
    for script in post_scripts:
        text = (script or "").strip()
        if not text:
            continue
        translated = _translate_mensajes_post(text, sampler_name)
        if translated:
            out.append(translated)
            continue
        translated = _translate_simple_puts(text, phase="post", sampler_name=sampler_name)
        if translated:
            out.append(translated)
        else:
            out.append(_stub_script(text, phase="post", sampler_name=sampler_name))
    return out


def merge_groovy_translations(
    translations: List[GroovyTranslation],
) -> Tuple[Optional[str], Optional[str], List[Dict[str, str]], str, str]:
    pre_parts: List[str] = []
    post_parts: List[str] = []
    extractors: List[Dict[str, str]] = []
    statuses: List[str] = []
    messages: List[str] = []
    seen_extractor_keys: set[Tuple[str, str]] = set()

    for tr in translations:
        statuses.append(tr.status)
        if tr.message:
            messages.append(tr.message)
        if tr.pre_script:
            pre_parts.append(tr.pre_script)
        if tr.post_script:
            post_parts.append(tr.post_script)
        for ex in tr.extractors:
            key = (ex.get("target_var") or "", ex.get("expression") or "")
            if key in seen_extractor_keys:
                continue
            seen_extractor_keys.add(key)
            extractors.append(ex)

    overall = "translated" if all(s == "translated" for s in statuses) else ("stub" if statuses else "omitted")
    pre = "\n\n".join(pre_parts) if pre_parts else None
    post = "\n\n".join(post_parts) if post_parts else None
    summary = "; ".join(messages[:3])
    if len(messages) > 3:
        summary += f"; … y {len(messages) - 3} más"
    return pre, post, extractors, overall if statuses else "omitted", summary
