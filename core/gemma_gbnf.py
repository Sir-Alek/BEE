"""Resolución y carga de gramáticas GBNF empaquetadas con ELIA."""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)

_GBNF_DIRNAME = "gbnf"


def resolve_gbnf_path(filename: str) -> Optional[str]:
    """Localiza un `.gbnf` en desarrollo o bundle PyInstaller."""
    candidates: list[str] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        exe_dir = os.path.dirname(sys.executable)
        for base in filter(None, [meipass, exe_dir]):
            candidates.append(os.path.join(base, "resources", _GBNF_DIRNAME, filename))
    this_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(this_dir, "..", "resources", _GBNF_DIRNAME, filename))
    for path in candidates:
        norm = os.path.normpath(path)
        if os.path.isfile(norm):
            return norm
    return None


def load_llama_grammar(filename: str) -> Any:
    """Carga LlamaGrammar desde `resources/gbnf/{filename}` o None si falla."""
    try:
        from llama_cpp import LlamaGrammar  # type: ignore
    except ImportError:
        return None
    path = resolve_gbnf_path(filename)
    if path:
        try:
            return LlamaGrammar.from_file(path)
        except Exception as exc:
            logger.debug("GBNF load failed for %s: %s", filename, exc)
    return None
