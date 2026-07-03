"""Parser XML de planes JMeter (.jmx) — hashTree y elementos core."""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_JMETER_FUNC_RE = re.compile(r"\$\{__[^}]+\}")


@dataclass
class ParsedArgument:
    name: str
    value: str


@dataclass
class ParsedCsvDataSet:
    filename: str
    variable_names: List[str]
    enabled: bool
    delimiter: str = ","


@dataclass
class ParsedThreadGroup:
    index: int
    name: str
    enabled: bool
    num_threads: str
    ramp_time: str
    duration: str
    on_sample_error: str
    subtree: Optional[ET.Element]


@dataclass
class ParsedSampler:
    name: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[str]
    enabled: bool
    extractors: List[Dict[str, str]] = field(default_factory=list)
    jsr223_pre: List[str] = field(default_factory=list)
    jsr223_post: List[str] = field(default_factory=list)
    warnings: List[Tuple[str, str]] = field(default_factory=list)  # (kind, message)


@dataclass
class ParsedJmxPlan:
    source_name: str
    arguments: List[ParsedArgument]
    csv_datasets: List[ParsedCsvDataSet]
    thread_groups: List[ParsedThreadGroup]
    skipped_elements: List[Tuple[str, str, str]] = field(default_factory=list)  # kind, name, reason


def _local_tag(elem: ET.Element) -> str:
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


def _is_enabled(elem: ET.Element) -> bool:
    val = (elem.get("enabled") or "true").strip().lower()
    return val != "false"


def _prop_text(elem: ET.Element, name: str, default: str = "") -> str:
    for child in elem:
        if _local_tag(child) != "stringProp":
            continue
        if child.get("name") == name:
            return (child.text or default).strip()
    for child in elem:
        if _local_tag(child) != "boolProp":
            continue
        if child.get("name") == name:
            return "true" if (child.text or "").strip().lower() == "true" else "false"
    return default


def _bool_prop(elem: ET.Element, name: str, default: bool = False) -> bool:
    raw = _prop_text(elem, name, "true" if default else "false")
    return raw.lower() == "true"


def _iter_hashtree_pairs(hashtree: ET.Element) -> List[Tuple[ET.Element, Optional[ET.Element]]]:
    if _local_tag(hashtree) != "hashTree":
        return []
    children = list(hashtree)
    pairs: List[Tuple[ET.Element, Optional[ET.Element]]] = []
    i = 0
    while i < len(children):
        child = children[i]
        if _local_tag(child) == "hashTree":
            i += 1
            continue
        subtree = children[i + 1] if i + 1 < len(children) and _local_tag(children[i + 1]) == "hashTree" else None
        pairs.append((child, subtree))
        i += 2 if subtree is not None else 1
    return pairs


def _find_plan_hashtree(root: ET.Element) -> ET.Element:
    if _local_tag(root) == "jmeterTestPlan":
        for child in root:
            if _local_tag(child) == "hashTree":
                for sub in child:
                    if _local_tag(sub) == "hashTree":
                        return sub
    raise ValueError("Archivo .jmx no válido: estructura hashTree no encontrada")


def _parse_arguments(elem: ET.Element) -> List[ParsedArgument]:
    out: List[ParsedArgument] = []
    for child in elem:
        if _local_tag(child) != "collectionProp" or child.get("name") != "Arguments.arguments":
            continue
        for arg in child:
            if _local_tag(arg) != "elementProp":
                continue
            name = _prop_text(arg, "Argument.name")
            value = _prop_text(arg, "Argument.value")
            if name:
                out.append(ParsedArgument(name=name, value=value))
    return out


def _parse_csv(elem: ET.Element) -> ParsedCsvDataSet:
    raw_path = _prop_text(elem, "filename")
    basename = os.path.basename(raw_path.replace("\\", "/")) if raw_path else ""
    vars_raw = _prop_text(elem, "variableNames")
    names = [v.strip() for v in vars_raw.split(",") if v.strip()] if vars_raw else []
    return ParsedCsvDataSet(
        filename=basename or raw_path,
        variable_names=names,
        enabled=_is_enabled(elem),
        delimiter=_prop_text(elem, "delimiter", ",") or ",",
    )


def _build_url(elem: ET.Element) -> str:
    protocol = _prop_text(elem, "HTTPSampler.protocol", "http").rstrip(":/")
    domain = _prop_text(elem, "HTTPSampler.domain")
    path = _prop_text(elem, "HTTPSampler.path")
    if not domain and not path:
        return ""
    if path and not path.startswith("/"):
        path = "/" + path
    return f"{protocol}://{domain}{path}"


def _parse_body(elem: ET.Element) -> Optional[str]:
    if not _bool_prop(elem, "HTTPSampler.postBodyRaw", False):
        args = []
        for child in elem.iter():
            if _local_tag(child) == "elementProp" and child.get("elementType") == "HTTPArgument":
                val = _prop_text(child, "Argument.value")
                if val:
                    args.append(val)
        if not args:
            return None
        return "&".join(args)
    for child in elem.iter():
        if _local_tag(child) == "elementProp" and child.get("elementType") == "HTTPArgument":
            val = _prop_text(child, "Argument.value")
            if val:
                return val
    return None


def _parse_headers(elem: ET.Element) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for child in elem:
        if _local_tag(child) != "collectionProp" or child.get("name") != "HeaderManager.headers":
            continue
        for header in child:
            if _local_tag(header) != "elementProp":
                continue
            key = _prop_text(header, "Header.name")
            val = _prop_text(header, "Header.value")
            if key:
                headers[key] = val
    return headers


def _collect_sampler_children(
    subtree: Optional[ET.Element], sampler_name: str
) -> Tuple[Dict[str, str], List[Dict[str, str]], List[str], List[str], List[Tuple[str, str]]]:
    headers: Dict[str, str] = {}
    extractors: List[Dict[str, str]] = []
    jsr223_pre: List[str] = []
    jsr223_post: List[str] = []
    warnings: List[Tuple[str, str]] = []
    if subtree is None:
        return headers, extractors, jsr223_pre, jsr223_post, warnings

    for elem, child_tree in _iter_hashtree_pairs(subtree):
        tag = _local_tag(elem)
        if tag == "HeaderManager" and _is_enabled(elem):
            headers.update(_parse_headers(elem))
        elif tag == "RegexExtractor" and _is_enabled(elem):
            extractors.append(
                {
                    "refname": _prop_text(elem, "RegexExtractor.refname"),
                    "regex": _prop_text(elem, "RegexExtractor.regex"),
                    "match_number": _prop_text(elem, "RegexExtractor.match_number", "1"),
                }
            )
        elif tag in ("JSR223PreProcessor", "JSR223PostProcessor", "BeanShellPreProcessor", "BeanShellPostProcessor") and _is_enabled(elem):
            script = _prop_text(elem, "script")
            if script.strip():
                if tag.endswith("PreProcessor"):
                    jsr223_pre.append(script)
                else:
                    jsr223_post.append(script)
            else:
                lang = _prop_text(elem, "scriptLanguage", "groovy")
                warnings.append(
                    (
                        tag,
                        f"Script {lang} vacío en «{sampler_name}».",
                    )
                )
        elif tag == "ResponseAssertion" and _is_enabled(elem):
            warnings.append(("ResponseAssertion", f"Aserción JMeter omitida en «{sampler_name}»."))
        elif tag not in ("hashTree", "HeaderManager", "RegexExtractor") and _is_enabled(elem):
            if tag not in ("DebugSampler", "ConstantTimer", "UniformRandomTimer", "GaussianRandomTimer"):
                warnings.append((tag, f"Elemento «{elem.get('testname') or tag}» omitido bajo «{sampler_name}»."))
        if child_tree is not None and tag in ("IfController", "WhileController", "LoopController", "GenericController"):
            warnings.append((tag, f"Controlador lógico «{elem.get('testname') or tag}» no migrado; revisa el orden manualmente."))
    return headers, extractors, jsr223_pre, jsr223_post, warnings


def _walk_samplers(
    subtree: Optional[ET.Element],
    out: List[ParsedSampler],
    skipped: List[Tuple[str, str, str]],
    *,
    include_disabled_controllers: bool = False,
) -> None:
    if subtree is None:
        return
    for elem, child_tree in _iter_hashtree_pairs(subtree):
        tag = _local_tag(elem)
        if tag == "HTTPSamplerProxy":
            if not _is_enabled(elem):
                skipped.append(("HTTPSamplerProxy", elem.get("testname") or "HTTP", "deshabilitado"))
                continue
            name = elem.get("testname") or "HTTP"
            url = _build_url(elem)
            if not url:
                skipped.append(("HTTPSamplerProxy", name, "sin URL"))
                continue
            headers, extractors, jsr223_pre, jsr223_post, child_warnings = _collect_sampler_children(child_tree, name)
            body = _parse_body(elem)
            sampler_warnings = list(child_warnings)
            for field in (url, body or ""):
                if _JMETER_FUNC_RE.search(field):
                    sampler_warnings.append(
                        ("JMeterFunction", f"Función JMeter en «{name}»; revisa variables o scripts ELIA.")
                    )
            out.append(
                ParsedSampler(
                    name=name,
                    method=_prop_text(elem, "HTTPSampler.method", "GET").upper(),
                    url=url,
                    headers=headers,
                    body=body,
                    enabled=True,
                    extractors=extractors,
                    jsr223_pre=jsr223_pre,
                    jsr223_post=jsr223_post,
                    warnings=sampler_warnings,
                )
            )
        elif tag in ("GenericController", "LoopController", "IfController", "WhileController", "TransactionController"):
            if _is_enabled(elem):
                _walk_samplers(child_tree, out, skipped, include_disabled_controllers=include_disabled_controllers)
            elif include_disabled_controllers:
                _walk_samplers(child_tree, out, skipped, include_disabled_controllers=include_disabled_controllers)
            else:
                skipped.append((tag, elem.get("testname") or tag, "deshabilitado"))
        elif tag == "ThreadGroup":
            continue
        elif tag in ("ResultCollector", "CookieManager"):
            continue
        elif _is_enabled(elem):
            skipped.append((tag, elem.get("testname") or tag, "no soportado en importación"))


def parse_jmx_bytes(data: bytes, *, source_name: str = "plan.jmx") -> ParsedJmxPlan:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise ValueError(f"XML .jmx inválido: {e}") from e

    plan_tree = _find_plan_hashtree(root)
    arguments: List[ParsedArgument] = []
    csv_datasets: List[ParsedCsvDataSet] = []
    thread_groups: List[ParsedThreadGroup] = []
    skipped: List[Tuple[str, str, str]] = []
    tg_index = 0

    for elem, subtree in _iter_hashtree_pairs(plan_tree):
        tag = _local_tag(elem)
        if tag == "Arguments" and _is_enabled(elem):
            arguments.extend(_parse_arguments(elem))
        elif tag == "CSVDataSet":
            csv_datasets.append(_parse_csv(elem))
        elif tag == "ThreadGroup":
            thread_groups.append(
                ParsedThreadGroup(
                    index=tg_index,
                    name=elem.get("testname") or f"Thread Group {tg_index + 1}",
                    enabled=_is_enabled(elem),
                    num_threads=_prop_text(elem, "ThreadGroup.num_threads", "1"),
                    ramp_time=_prop_text(elem, "ThreadGroup.ramp_time", "1"),
                    duration=_prop_text(elem, "ThreadGroup.duration", "60"),
                    on_sample_error=_prop_text(elem, "ThreadGroup.on_sample_error", "continue"),
                    subtree=subtree,
                )
            )
            tg_index += 1
        elif tag == "ResultCollector":
            continue
        elif _is_enabled(elem):
            skipped.append((tag, elem.get("testname") or tag, "elemento de plan no importado"))

    if not thread_groups:
        raise ValueError("No se encontró ningún Thread Group en el .jmx")

    return ParsedJmxPlan(
        source_name=source_name,
        arguments=arguments,
        csv_datasets=csv_datasets,
        thread_groups=thread_groups,
        skipped_elements=skipped,
    )


def extract_thread_group_samplers(
    plan: ParsedJmxPlan,
    thread_group_index: int,
    *,
    include_disabled_controllers: bool = False,
) -> Tuple[ParsedThreadGroup, List[ParsedSampler], List[Tuple[str, str, str]]]:
    if thread_group_index < 0 or thread_group_index >= len(plan.thread_groups):
        raise ValueError(f"Thread Group index inválido: {thread_group_index}")
    tg = plan.thread_groups[thread_group_index]
    if not tg.enabled:
        raise ValueError(f"El Thread Group «{tg.name}» está deshabilitado")
    samplers: List[ParsedSampler] = []
    skipped: List[Tuple[str, str, str]] = list(plan.skipped_elements)
    _walk_samplers(tg.subtree, samplers, skipped, include_disabled_controllers=include_disabled_controllers)
    return tg, samplers, skipped
