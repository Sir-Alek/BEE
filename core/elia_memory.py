"""
Memoria local de ejemplos script → feature (para enriquecer prompts de Gemma).
No modifica el GGUF; solo JSON en la carpeta de datos del usuario.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import elia_paths

_LOCK = threading.Lock()
_MAX_ENTRIES = 80
_KEEP_RECENT = 12


def _resolved_memory_path() -> Path:
    p = elia_paths.elia_memory_path()
    legacy = elia_paths.ensure_user_data_root() / "bee_memory.json"
    if not p.is_file() and legacy.is_file():
        try:
            shutil.copy2(legacy, p)
        except OSError:
            pass
    return p


def _trim_script(script: str, max_chars: int = 12000) -> str:
    s = (script or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 20] + "\n... [truncado]"


def _fingerprint(script: str) -> str:
    return hashlib.sha256(_trim_script(script).encode("utf-8", errors="replace")).hexdigest()[:16]


def _load(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "entries": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "entries" not in data:
            return {"version": 1, "entries": []}
        return data
    except Exception:
        return {"version": 1, "entries": []}


def _save(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def append_correction(*, script_snippet: str, feature_text: str) -> None:
    """Guarda un par script/feature tras aceptación (especialmente si el usuario editó el feature)."""
    script_snippet = _trim_script(script_snippet)
    feature_text = (feature_text or "").strip()
    if not script_snippet or not feature_text:
        return

    path = _resolved_memory_path()
    with _LOCK:
        data = _load(path)
        entries: List[Dict[str, Any]] = list(data.get("entries") or [])
        fp = _fingerprint(script_snippet)
        entry = {
            "ts": time.time(),
            "script_fp": fp,
            "script": script_snippet,
            "feature": feature_text,
        }
        entries.append(entry)

        if len(entries) > _MAX_ENTRIES:
            entries = entries[-_MAX_ENTRIES:]
        data["entries"] = entries
        _save(path, data)


def recent_examples_for_prompt(*, limit: int = 3) -> List[Dict[str, str]]:
    """Últimas correcciones para inyectar en el prompt (más recientes primero)."""
    path = _resolved_memory_path()
    with _LOCK:
        data = _load(path)
    entries: List[Dict[str, Any]] = list(data.get("entries") or [])
    entries.sort(key=lambda e: float(e.get("ts", 0.0)), reverse=True)
    out: List[Dict[str, str]] = []
    for e in entries[: max(limit, _KEEP_RECENT)]:
        if len(out) >= limit:
            break
        s = str(e.get("script", "")).strip()
        f = str(e.get("feature", "")).strip()
        if s and f:
            out.append({"script": s, "feature": f})
    return out
