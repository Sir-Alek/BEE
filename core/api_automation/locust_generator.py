"""Generación de locustfile.py desde escenarios / flujos API.

Soporta:
- Think-time configurable (between / constant / constant_pacing / gaussian).
- Ramp-up por etapas mediante `LoadTestShape` (spike / stress / soak).
- Generación basada en flujo con controladores lógicos (if / loop / while).
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.api_automation.models import ApiRequest

_DEFAULT_THINK = {"kind": "between", "min": 0.5, "max": 2.0}


# --------------------------------------------------------------------------- #
# Bloques reutilizables (think-time + shape)
# --------------------------------------------------------------------------- #
def _wait_time_block(think_time: Optional[Dict[str, Any]]) -> str:
    cfg = think_time or _DEFAULT_THINK
    kind = str(cfg.get("kind") or "between").lower()
    if kind == "constant":
        return f"    wait_time = constant({float(cfg.get('value', 1.0))})"
    if kind == "constant_pacing":
        return f"    wait_time = constant_pacing({float(cfg.get('value', 1.0))})"
    if kind == "gaussian":
        mean = float(cfg.get("mean", 1.0))
        stddev = float(cfg.get("stddev", 0.3))
        return (
            f"    def wait_time(self):\n"
            f"        return max(0.0, random.gauss({mean}, {stddev}))"
        )
    lo = float(cfg.get("min", 0.5))
    hi = float(cfg.get("max", 2.0))
    return f"    wait_time = between({lo}, {hi})"


def _shape_block(stages: Optional[List[Dict[str, Any]]]) -> str:
    """Genera una clase LoadTestShape. `duration` de cada etapa es el tiempo
    ACUMULADO (segundos) hasta el que esa etapa está activa."""
    if not stages:
        return ""
    norm: List[Dict[str, Any]] = []
    for st in stages:
        if not isinstance(st, dict):
            continue
        norm.append(
            {
                "duration": int(st.get("duration") or 0),
                "users": int(st.get("users") or 1),
                "spawn_rate": float(st.get("spawn_rate") or 1.0),
            }
        )
    if not norm:
        return ""
    stages_repr = json.dumps(norm)
    return textwrap.dedent(
        f"""
        class EliaLoadShape(LoadTestShape):
            stages = {stages_repr}

            def tick(self):
                run_time = self.get_run_time()
                for stage in self.stages:
                    if run_time < stage["duration"]:
                        return (stage["users"], stage["spawn_rate"])
                return None
        """
    ).strip()


def _imports_block(think_time: Optional[Dict[str, Any]], stages: Optional[List[Dict[str, Any]]]) -> str:
    imports = ["from locust import HttpUser, task, between, constant, constant_pacing"]
    if stages:
        imports.append("from locust import LoadTestShape")
    kind = str((think_time or {}).get("kind") or "").lower()
    if kind == "gaussian":
        imports.append("import random")
    return "\n".join(imports)


# --------------------------------------------------------------------------- #
# Modo simple: una @task por escenario (con pesos)
# --------------------------------------------------------------------------- #
def generate_locustfile(
    requests: List[ApiRequest],
    *,
    host: str = "",
    weights: Optional[Dict[str, int]] = None,
    think_time: Optional[Dict[str, Any]] = None,
    stages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    base_host = host.rstrip("/") if host else ""
    tasks: List[str] = []
    for req in requests:
        url = req.url
        if base_host and url.startswith("/"):
            url = base_host + url
        method = req.method.upper()
        headers_repr = json.dumps(req.headers, ensure_ascii=False)
        body = req.body
        weight = max(1, int((weights or {}).get(req.id, req.weight or 1)))
        body_block = ""
        if body and method not in ("GET", "HEAD"):
            body_block = f"\n        payload = {json.dumps(body, ensure_ascii=False)!r}"
            send = f'self.client.request("{method}", {url!r}, headers=headers, data=payload)'
        else:
            send = f'self.client.request("{method}", {url!r}, headers=headers)'
        task_name = req.id.replace("-", "_").replace(".", "_")
        tasks.append(
            textwrap.dedent(
                f"""
                @task({weight})
                def task_{task_name}(self):
                    headers = {headers_repr}{body_block}
                    with {send} as response:
                        if response.status_code >= 400:
                            response.failure(f"HTTP {{response.status_code}}")
                """
            ).strip()
        )

    if tasks:
        body = "\n\n".join(tasks)
        tasks_src = textwrap.indent(body, "    ")
    else:
        tasks_src = "    pass"
    host_line = f"    host = {base_host!r}\n" if base_host else ""
    shape_block = _shape_block(stages)
    shape_src = f"\n\n{shape_block}\n" if shape_block else ""
    return (
        _imports_block(think_time, stages)
        + "\n\n\n"
        + "class EliaApiUser(HttpUser):\n"
        + _wait_time_block(think_time)
        + "\n"
        + host_line
        + "\n"
        + tasks_src
        + "\n"
        + shape_src
    ).strip() + "\n"


# --------------------------------------------------------------------------- #
# Modo flujo: un único task secuencial con controladores (if / loop / while)
# --------------------------------------------------------------------------- #
_COND_HELPERS = textwrap.dedent(
    '''
    import re as _re

    def _num(v):
        try:
            return float(str(v).strip())
        except Exception:
            return float("nan")

    def _cond(kind, expression, expected, negate, last, vars):
        status = getattr(last, "status_code", 0) if last is not None else 0
        text = (getattr(last, "text", "") if last is not None else "") or ""
        res = False
        if kind == "always":
            res = True
        elif kind == "status":
            res = str(status) == (expected or expression)
        elif kind == "status_lt":
            res = _num(status) < _num(expected or expression)
        elif kind == "status_gte":
            res = _num(status) >= _num(expected or expression)
        elif kind == "body_contains":
            res = bool(expected) and expected in text
        elif kind == "regex":
            try:
                res = _re.search(expression or expected, text) is not None
            except _re.error:
                res = False
        elif kind == "var_exists":
            res = bool(str(vars.get(expression, "")).strip())
        elif kind == "var_equals":
            res = str(vars.get(expression, "")) == expected
        return (not res) if negate else res
    '''
).strip()


_GRPC_HELPERS = textwrap.dedent(
    '''
    def _elia_grpc(cfg, vars):
        try:
            import grpc
            from google.protobuf import json_format
            from grpc_reflection.v1alpha.proto_reflection_descriptor_database import ProtoReflectionDescriptorDatabase
            from google.protobuf.descriptor_pool import DescriptorPool
            from google.protobuf.message_factory import GetMessageClass
        except ImportError as exc:
            return False, "gRPC no disponible: %s" % exc
        target = str(cfg.get("target") or "")
        service = str(cfg.get("service") or "")
        method = str(cfg.get("method") or "")
        if not target or not service or not method:
            return False, "Config gRPC incompleta"
        message = cfg.get("message") or {}
        metadata = [(str(k).lower(), str(v)) for k, v in (cfg.get("metadata") or {}).items()]
        timeout = float(cfg.get("timeout_sec") or 15)
        use_tls = bool(cfg.get("tls"))
        channel = grpc.secure_channel(target, grpc.ssl_channel_credentials()) if use_tls else grpc.insecure_channel(target)
        try:
            reflection_db = ProtoReflectionDescriptorDatabase(channel)
            pool = DescriptorPool(reflection_db)
            service_desc = pool.FindServiceByName(service)
            method_desc = service_desc.FindMethodByName(method)
            request_cls = GetMessageClass(method_desc.input_type)
            response_cls = GetMessageClass(method_desc.output_type)
            request_msg = json_format.ParseDict(message, request_cls())
            full_method = "/%s/%s" % (service, method)
            callable_ = channel.unary_unary(
                full_method,
                request_serializer=lambda m: m.SerializeToString(),
                response_deserializer=response_cls.FromString,
            )
            response = callable_(request_msg, timeout=timeout, metadata=metadata or None)
            as_dict = json_format.MessageToDict(response, preserving_proto_field_name=True)
            for spec in cfg.get("extract") or []:
                path = str(spec.get("jsonpath") or "")
                target_var = str(spec.get("target_var") or "")
                if path and target_var:
                    import json as _json
                    ok, val = _json.loads(_json.dumps(as_dict)), None
                    # extracción simple por clave de primer nivel
                    parts = [p for p in path.replace("$.", "").split(".") if p]
                    cur = as_dict
                    for p in parts:
                        if isinstance(cur, dict) and p in cur:
                            cur = cur[p]
                        else:
                            cur = None
                            break
                    if cur is not None:
                        vars[target_var] = str(cur)
            return True, as_dict
        except Exception as exc:
            return False, str(exc)
        finally:
            try:
                channel.close()
            except Exception:
                pass
    '''
).strip()


def generate_flow_locustfile(
    nodes: List[Dict[str, Any]],
    *,
    host: str = "",
    think_time: Optional[Dict[str, Any]] = None,
    stages: Optional[List[Dict[str, Any]]] = None,
    initial_vars: Optional[Dict[str, str]] = None,
) -> str:
    """Genera un locustfile que ejecuta un flujo con controladores lógicos.

    Nodos SQL se omiten en la tarea (ejecutar setup pre-carga aparte).
    Nodos gRPC se invocan en el flujo si grpcio está disponible.
    """
    base_host = host.rstrip("/") if host else ""
    body_lines: List[str] = []
    has_grpc = _tree_has_type(nodes, "grpc")
    _emit_nodes(nodes or [], base_host, body_lines, indent=2)
    if not body_lines:
        body_lines = ["        pass"]

    host_line = f'    host = {base_host!r}\n' if base_host else ""
    shape_block = _shape_block(stages)
    shape_src = f"\n\n{shape_block}\n" if shape_block else ""
    vars_init = json.dumps(initial_vars or {}, ensure_ascii=False)
    grpc_block = f"\n\n{_GRPC_HELPERS}\n" if has_grpc else ""
    return (
        _imports_block(think_time, stages)
        + "import json\n"
        + grpc_block
        + "\n\n"
        + _COND_HELPERS
        + "\n\n\n"
        + "class EliaApiUser(HttpUser):\n"
        + _wait_time_block(think_time)
        + "\n"
        + host_line
        + "\n"
        + "    @task\n"
        + "    def elia_flow(self):\n"
        + f"        vars = dict({vars_init})\n"
        + "        last = None\n"
        + "\n".join(body_lines)
        + "\n"
        + shape_src
    ).strip() + "\n"


def _tree_has_type(nodes: List[Dict[str, Any]], ntype: str) -> bool:
    target = ntype.lower()
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "request").lower() == target:
            return True
        for key in ("then", "else", "body"):
            if _tree_has_type(node.get(key) or [], ntype):
                return True
    return False


def _emit_nodes(nodes: List[Dict[str, Any]], base_host: str, out: List[str], indent: int) -> None:
    pad = "    " * indent
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ntype = str(node.get("type") or "request").lower()
        if ntype == "if":
            cond = node.get("condition") or {}
            out.append(f"{pad}if {_cond_call(cond)}:")
            then_nodes = node.get("then") or []
            if then_nodes:
                _emit_nodes(then_nodes, base_host, out, indent + 1)
            else:
                out.append(f"{pad}    pass")
            else_nodes = node.get("else") or []
            if else_nodes:
                out.append(f"{pad}else:")
                _emit_nodes(else_nodes, base_host, out, indent + 1)
        elif ntype == "loop":
            mode = str(node.get("mode") or "count").lower()
            max_iter = min(int(node.get("max_iterations") or 100), 10000)
            body = node.get("body") or []
            if mode == "while":
                cond = node.get("condition") or {}
                out.append(f"{pad}_i = 0")
                out.append(f"{pad}while _i < {max_iter} and {_cond_call(cond)}:")
                if body:
                    _emit_nodes(body, base_host, out, indent + 1)
                else:
                    out.append(f"{pad}    pass")
                out.append(f"{pad}    _i += 1")
            else:
                count = node.get("count")
                if isinstance(count, int):
                    count_expr = str(count)
                else:
                    var_name = str(count or "0").strip()
                    if var_name.startswith("{{") and var_name.endswith("}}"):
                        var_name = var_name[2:-2].strip()
                    count_expr = f"int(vars.get({var_name!r}, 0) or 0)"
                out.append(f"{pad}for _i in range(min({count_expr}, {max_iter})):")
                out.append(f"{pad}    vars['loop_index'] = str(_i)")
                if body:
                    _emit_nodes(body, base_host, out, indent + 1)
                else:
                    out.append(f"{pad}    pass")
        elif ntype == "sql":
            out.append(f"{pad}# SQL omitido en tarea de carga (use setup pre-carga)")
        elif ntype == "grpc":
            _emit_grpc(node, out, indent)
        else:
            _emit_request(node, base_host, out, indent)


def _emit_grpc(node: Dict[str, Any], out: List[str], indent: int) -> None:
    pad = "    " * indent
    cfg = node.get("grpc") or {}
    cfg_repr = json.dumps(cfg, ensure_ascii=False)
    name = f"gRPC {cfg.get('service', '')}/{cfg.get('method', '')}"[:80]
    out.append(f"{pad}ok_grpc, _grpc_resp = _elia_grpc({cfg_repr}, vars)")
    out.append(f"{pad}if not ok_grpc:")
    out.append(f'{pad}    raise Exception("gRPC falló (%s): %s" % ({name!r}, _grpc_resp))')


def _emit_request(node: Dict[str, Any], base_host: str, out: List[str], indent: int) -> None:
    pad = "    " * indent
    req = node.get("request") or {}
    method = str(req.get("method") or "GET").upper()
    url = str(req.get("url") or "")
    if base_host and url.startswith("/"):
        url = base_host + url
    headers = req.get("headers") or {}
    name = str(req.get("name") or url)[:80]
    body = req.get("body")
    out.append(f"{pad}headers = {json.dumps(headers, ensure_ascii=False)}")
    if body and method not in ("GET", "HEAD"):
        out.append(f"{pad}payload = {json.dumps(body, ensure_ascii=False)!r}")
        send = (
            f'self.client.request("{method}", {url!r}, headers=headers, '
            f"data=payload, name={name!r}, catch_response=True)"
        )
    else:
        send = (
            f'self.client.request("{method}", {url!r}, headers=headers, '
            f"name={name!r}, catch_response=True)"
        )
    out.append(f"{pad}with {send} as last:")
    out.append(f"{pad}    if last.status_code >= 400:")
    out.append(f'{pad}        last.failure("HTTP %s" % last.status_code)')


def _cond_call(cond: Dict[str, Any]) -> str:
    return (
        f"_cond({str(cond.get('kind') or 'always')!r}, "
        f"{str(cond.get('expression') or '')!r}, "
        f"{str(cond.get('expected') or '')!r}, "
        f"{bool(cond.get('negate'))!r}, last, vars)"
    )


# --------------------------------------------------------------------------- #
# Escritura a disco
# --------------------------------------------------------------------------- #
def write_locustfile(
    project_dir: str,
    requests: List[ApiRequest],
    *,
    host: str = "",
    weights: Optional[Dict[str, int]] = None,
    think_time: Optional[Dict[str, Any]] = None,
    stages: Optional[List[Dict[str, Any]]] = None,
    flow_nodes: Optional[List[Dict[str, Any]]] = None,
    initial_vars: Optional[Dict[str, str]] = None,
) -> str:
    path = Path(project_dir) / "locustfile.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    if flow_nodes:
        content = generate_flow_locustfile(
            flow_nodes, host=host, think_time=think_time, stages=stages, initial_vars=initial_vars
        )
    else:
        content = generate_locustfile(
            requests, host=host, weights=weights, think_time=think_time, stages=stages
        )
    path.write_text(content, encoding="utf-8")
    return str(path)


def inline_flow_requests(project: str, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Resuelve `scenario_id` → `request` inline en todo el árbol (para carga)."""
    from core.api_automation.traffic_store import load_scenario

    def _walk(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        for n in items or []:
            if not isinstance(n, dict):
                continue
            node = dict(n)
            ntype = str(node.get("type") or "request").lower()
            if ntype == "request" and not node.get("request") and node.get("scenario_id"):
                try:
                    node["request"] = load_scenario(project, node["scenario_id"]).to_dict()
                except Exception:
                    node["request"] = {}
            for key in ("then", "else", "body"):
                if isinstance(node.get(key), list):
                    node[key] = _walk(node[key])
            resolved.append(node)
        return resolved

    return _walk(nodes)
