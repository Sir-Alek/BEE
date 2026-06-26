"""Paso gRPC para suites API.

Invoca métodos gRPC unarios usando ``grpcio``. Para construir el mensaje sin
tener stubs precompilados, se apoya en la **reflexión del servidor** (cuando el
servidor la expone) a través de ``grpc_reflection`` + ``protobuf``; si el equipo
provee un módulo de stubs compilado, también puede indicarse por config.

Todas las dependencias son OPCIONALES y se importan de forma perezosa: si no
están instaladas, el paso falla con un mensaje claro sin romper el resto de ELIA.

Config (dict ``grpc`` del nodo)::

    {
      "target": "localhost:50051",
      "service": "paquete.Servicio",
      "method": "MiMetodo",
      "message": {"campo": "{{valor}}"},   # JSON -> protobuf (interpolado)
      "metadata": {"authorization": "Bearer {{token}}"},
      "tls": false,
      "timeout_sec": 15,
      "extract": [{"jsonpath": "$.id", "target_var": "grpc_id"}]
    }
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from core.api_automation.runtime.interpolation import interpolate_text
from core.api_automation.runtime.jsonpath_utils import get_json_path, parse_json_body


def run_grpc_step(
    config: Dict[str, Any],
    *,
    variables: Dict[str, str],
) -> Dict[str, Any]:
    target = interpolate_text(str(config.get("target") or ""), variables)
    service = str(config.get("service") or "").strip()
    method = str(config.get("method") or "").strip()
    if not target or not service or not method:
        return _fail("gRPC requiere 'target', 'service' y 'method'")

    try:
        import grpc  # type: ignore  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depende del entorno
        return _fail("gRPC no disponible. Ejecuta: pip install grpcio grpcio-reflection protobuf")

    message_raw = config.get("message") or {}
    message = _interpolate_obj(message_raw, variables)
    metadata = [
        (str(k).lower(), interpolate_text(str(v), variables))
        for k, v in (config.get("metadata") or {}).items()
    ]
    timeout = float(config.get("timeout_sec") or 15)
    use_tls = bool(config.get("tls"))

    try:
        response_obj, raw_text = _invoke_unary(
            target=target,
            service=service,
            method=method,
            message=message,
            metadata=metadata,
            timeout=timeout,
            use_tls=use_tls,
        )
    except _GrpcDepMissing as exc:
        return _fail(str(exc))
    except Exception as exc:  # noqa: BLE001 — el error gRPC es informativo
        return _fail(f"Error gRPC: {exc}")

    extract_results = _apply_extract(config.get("extract") or [], raw_text, variables)
    return {
        "ok": True,
        "target": target,
        "service": service,
        "method": method,
        "response": response_obj,
        "extractors": extract_results,
    }


class _GrpcDepMissing(RuntimeError):
    pass


def _invoke_unary(*, target, service, method, message, metadata, timeout, use_tls):
    """Invoca un método unario por reflexión del servidor.

    Usa la API de reflexión gRPC para descubrir el descriptor del método,
    serializa el dict ``message`` al tipo de entrada y deserializa la respuesta
    a dict via protobuf json_format.
    """
    try:
        import grpc  # type: ignore
        from google.protobuf import json_format, symbol_database  # type: ignore
        from grpc_reflection.v1alpha.proto_reflection_descriptor_database import (  # type: ignore
            ProtoReflectionDescriptorDatabase,
        )
        from google.protobuf.descriptor_pool import DescriptorPool  # type: ignore
        from google.protobuf.message_factory import GetMessageClass  # type: ignore
    except ImportError as exc:
        raise _GrpcDepMissing(
            "Falta soporte de reflexión gRPC. Ejecuta: "
            "pip install grpcio grpcio-reflection protobuf"
        ) from exc

    channel = (
        grpc.secure_channel(target, grpc.ssl_channel_credentials())
        if use_tls
        else grpc.insecure_channel(target)
    )
    try:
        reflection_db = ProtoReflectionDescriptorDatabase(channel)
        pool = DescriptorPool(reflection_db)
        service_desc = pool.FindServiceByName(service)
        method_desc = service_desc.FindMethodByName(method)

        request_cls = GetMessageClass(method_desc.input_type)
        response_cls = GetMessageClass(method_desc.output_type)
        request_msg = json_format.ParseDict(message or {}, request_cls())

        full_method = f"/{service}/{method}"
        callable_ = channel.unary_unary(
            full_method,
            request_serializer=lambda m: m.SerializeToString(),
            response_deserializer=response_cls.FromString,
        )
        response = callable_(request_msg, timeout=timeout, metadata=metadata or None)
        as_dict = json_format.MessageToDict(response, preserving_proto_field_name=True)
        return as_dict, json.dumps(as_dict, ensure_ascii=False)
    finally:
        try:
            channel.close()
        except Exception:
            pass


def _apply_extract(extract_specs, raw_text, variables) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    valid, data = parse_json_body(raw_text)
    for spec in extract_specs:
        if not isinstance(spec, dict):
            continue
        target = str(spec.get("target_var") or "").strip()
        path = str(spec.get("jsonpath") or "").strip()
        ok, value = (False, None)
        if valid and path:
            ok, value = get_json_path(data, path)
        if ok and target and value is not None:
            variables[target] = str(value)
        out.append({"target_var": target, "jsonpath": path, "passed": bool(ok), "value": value})
    return out


def _interpolate_obj(obj: Any, variables: Dict[str, str]) -> Any:
    if isinstance(obj, dict):
        return {k: _interpolate_obj(v, variables) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_interpolate_obj(v, variables) for v in obj]
    if isinstance(obj, str):
        return interpolate_text(obj, variables)
    return obj


def grpc_preflight(config: Dict[str, Any], *, variables: Dict[str, str]) -> Dict[str, Any]:
    """Valida dependencias, conectividad y reflexión del servidor sin invocar el método."""
    target = interpolate_text(str(config.get("target") or ""), variables)
    service = str(config.get("service") or "").strip()
    method = str(config.get("method") or "").strip()
    if not target:
        return _fail("Indica 'target' (host:puerto)")

    try:
        import grpc  # type: ignore  # noqa: F401
    except ImportError:
        return _fail("gRPC no disponible. Ejecuta: pip install grpcio grpcio-reflection protobuf")

    use_tls = bool(config.get("tls"))
    timeout = float(config.get("timeout_sec") or 10)

    channel = None
    try:
        import grpc  # type: ignore
        from google.protobuf.descriptor_pool import DescriptorPool  # type: ignore
        from grpc_reflection.v1alpha.proto_reflection_descriptor_database import (  # type: ignore
            ProtoReflectionDescriptorDatabase,
        )

        channel = (
            grpc.secure_channel(target, grpc.ssl_channel_credentials())
            if use_tls
            else grpc.insecure_channel(target)
        )
        reflection_db = ProtoReflectionDescriptorDatabase(channel)
        pool = DescriptorPool(reflection_db)
        grpc.channel_ready_future(channel).result(timeout=timeout)

        out: Dict[str, Any] = {
            "ok": True,
            "target": target,
            "service": service,
            "method": method,
            "reflection": True,
        }
        if service:
            service_desc = pool.FindServiceByName(service)
            out["service_found"] = True
            if method:
                service_desc.FindMethodByName(method)
                out["method_found"] = True
        return out
    except _GrpcDepMissing as exc:
        return _fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Preflight gRPC: {exc}")
    finally:
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass


def _fail(message: str) -> Dict[str, Any]:
    return {"ok": False, "response": None, "error": message}
