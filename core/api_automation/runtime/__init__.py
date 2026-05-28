"""Motor de ejecución HTTP directo para el módulo API (sin Behave)."""

from core.api_automation.runtime.assertion_engine import evaluate_assertions
from core.api_automation.runtime.context_merge import build_effective_request
from core.api_automation.runtime.interpolation import interpolate_text, interpolate_value
from core.api_automation.runtime.request_executor import execute_request

__all__ = [
    "build_effective_request",
    "evaluate_assertions",
    "execute_request",
    "interpolate_text",
    "interpolate_value",
]
