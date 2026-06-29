"""
Memoria local de ejemplos script → feature (para enriquecer prompts de Gemma).
Persistencia cifrada en elia_memory.enc (Fernet + huella de máquina).
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from core import elia_paths
from core.elia_memory_crypto import (
    EXPORT_FORMAT,
    decrypt_local_blob,
    decrypt_team_import,
    encrypt_local_document,
    encrypt_team_export,
)

_LOCK = threading.Lock()
_MAX_ENTRIES = 80
_PROMPT_EXAMPLES_LIMIT = 3
_KEEP_RECENT = 12
ImportMode = Literal["merge", "replace"]
MemorySource = Literal["doc_to_bdd", "web_capture", "unknown"]


def _empty_document() -> Dict[str, Any]:
    return {"version": 1, "entries": []}


def _legacy_json_path() -> Path:
    return elia_paths.elia_memory_path()


def _enc_path() -> Path:
    return elia_paths.ensure_user_data_root() / "elia_memory.enc"


def _legacy_bee_json_path() -> Path:
    return elia_paths.ensure_user_data_root() / "bee_memory.json"


def _normalize_document(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict) or "entries" not in data:
        return _empty_document()
    entries = data.get("entries")
    if not isinstance(entries, list):
        return _empty_document()
    return {"version": int(data.get("version") or 1), "entries": list(entries)}


def _load_plain_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return _empty_document()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _normalize_document(json.load(f))
    except Exception:
        return _empty_document()


def _migrate_legacy_plaintext_if_needed() -> None:
    enc = _enc_path()
    if enc.is_file():
        return

    legacy = _legacy_json_path()
    bee = _legacy_bee_json_path()
    source: Optional[Path] = None
    if legacy.is_file():
        source = legacy
    elif bee.is_file():
        source = bee

    if source is None:
        return

    data = _load_plain_json(source)
    enc.parent.mkdir(parents=True, exist_ok=True)
    enc.write_bytes(encrypt_local_document(data))
    backup = source.with_suffix(source.suffix + ".bak")
    try:
        if backup.is_file():
            backup.unlink()
        source.replace(backup)
    except OSError:
        pass


def _load_unlocked() -> Dict[str, Any]:
    _migrate_legacy_plaintext_if_needed()
    enc = _enc_path()
    if not enc.is_file():
        return _empty_document()
    try:
        return _normalize_document(decrypt_local_blob(enc.read_bytes()))
    except Exception:
        return _empty_document()


def _save_unlocked(data: Dict[str, Any]) -> None:
    enc = _enc_path()
    enc.parent.mkdir(parents=True, exist_ok=True)
    tmp = enc.with_suffix(enc.suffix + ".tmp")
    tmp.write_bytes(encrypt_local_document(data))
    tmp.replace(enc)


def _trim_script(script: str, max_chars: int = 12000) -> str:
    s = (script or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 20] + "\n... [truncado]"


def _fingerprint(script: str) -> str:
    return hashlib.sha256(_trim_script(script).encode("utf-8", errors="replace")).hexdigest()[:16]


def _normalize_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    script = _trim_script(str(entry.get("script", "")))
    feature = str(entry.get("feature", "")).strip()
    if not script or not feature:
        return None
    fp = str(entry.get("script_fp") or _fingerprint(script))
    source = str(entry.get("source") or "unknown").strip().lower()
    if source not in ("doc_to_bdd", "web_capture", "unknown"):
        source = "unknown"
    return {
        "ts": float(entry.get("ts") or time.time()),
        "script_fp": fp,
        "script": script,
        "feature": feature,
        "source": source,
    }


def _trim_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(entries) <= _MAX_ENTRIES:
        return entries
    return entries[-_MAX_ENTRIES:]


def memory_status() -> Dict[str, Any]:
    with _LOCK:
        data = _load_unlocked()
    entries = list(data.get("entries") or [])
    updated_at: Optional[float] = None
    enc = _enc_path()
    if enc.is_file():
        try:
            updated_at = enc.stat().st_mtime
        except OSError:
            updated_at = None
    if updated_at is None and entries:
        updated_at = max(float(e.get("ts") or 0.0) for e in entries)
    return {
        "entries": len(entries),
        "max_entries": _MAX_ENTRIES,
        "prompt_examples_limit": _PROMPT_EXAMPLES_LIMIT,
        "encrypted": enc.is_file(),
        "updated_at": updated_at,
        "export_format": EXPORT_FORMAT,
    }


def should_learn_correction(
    *,
    edited: bool,
    content_changed: bool,
    attempt: int = 1,
    preferences: Optional[Dict[str, Any]] = None,
) -> bool:
    """Decide si persistir un par script/feature según preferencias de usuario."""
    if preferences is None:
        try:
            from core.ai_policy import load_preferences

            preferences = load_preferences()
        except Exception:
            preferences = {}
    if not bool(preferences.get("memory_auto_learn", True)):
        return False
    if edited or content_changed:
        return True
    if attempt > 1 and bool(preferences.get("memory_learn_after_retry", False)):
        return True
    return False


def append_correction(
    *,
    script_snippet: str,
    feature_text: str,
    source: MemorySource = "unknown",
) -> None:
    """Guarda un par script/feature tras aceptación (especialmente si el usuario editó el feature)."""
    script_snippet = _trim_script(script_snippet)
    feature_text = (feature_text or "").strip()
    if not script_snippet or not feature_text:
        return

    with _LOCK:
        data = _load_unlocked()
        entries: List[Dict[str, Any]] = list(data.get("entries") or [])
        entry = {
            "ts": time.time(),
            "script_fp": _fingerprint(script_snippet),
            "script": script_snippet,
            "feature": feature_text,
            "source": source,
        }
        entries.append(entry)
        data["entries"] = _trim_entries(entries)
        _save_unlocked(data)


def recent_examples_for_prompt(*, limit: int = _PROMPT_EXAMPLES_LIMIT) -> List[Dict[str, str]]:
    """Últimas correcciones para inyectar en el prompt (más recientes primero)."""
    with _LOCK:
        data = _load_unlocked()
    entries: List[Dict[str, Any]] = list(data.get("entries") or [])
    entries.sort(key=lambda e: float(e.get("ts", 0.0)), reverse=True)
    out: List[Dict[str, str]] = []
    seen_fp: set[str] = set()
    for e in entries[: max(limit, _KEEP_RECENT)]:
        if len(out) >= limit:
            break
        s = str(e.get("script", "")).strip()
        f = str(e.get("feature", "")).strip()
        fp = str(e.get("script_fp") or "")
        if not s or not f:
            continue
        if fp and fp in seen_fp:
            continue
        if fp:
            seen_fp.add(fp)
        out.append({"script": s, "feature": f})
    return out


def _preview(text: str, max_len: int = 120) -> str:
    t = (text or "").strip().replace("\r\n", "\n")
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def list_entries(*, limit: int = 40) -> List[Dict[str, Any]]:
    """Lista entradas recientes para la UI (metadatos + extractos truncados)."""
    with _LOCK:
        data = _load_unlocked()
    entries: List[Dict[str, Any]] = list(data.get("entries") or [])
    entries.sort(key=lambda e: float(e.get("ts", 0.0)), reverse=True)
    out: List[Dict[str, Any]] = []
    for e in entries[: max(1, min(limit, _MAX_ENTRIES))]:
        norm = _normalize_entry(e) if isinstance(e, dict) else None
        if not norm:
            continue
        out.append(
            {
                "script_fp": norm["script_fp"],
                "ts": norm["ts"],
                "source": norm.get("source") or "unknown",
                "script_preview": _preview(norm["script"]),
                "feature_preview": _preview(norm["feature"]),
            }
        )
    return out


def delete_entry(script_fp: str) -> bool:
    fp = (script_fp or "").strip()
    if not fp:
        return False
    with _LOCK:
        data = _load_unlocked()
        entries: List[Dict[str, Any]] = list(data.get("entries") or [])
        kept = [e for e in entries if str(e.get("script_fp") or "") != fp]
        if len(kept) == len(entries):
            return False
        data["entries"] = kept
        _save_unlocked(data)
    return True


def clear_entries() -> int:
    with _LOCK:
        data = _load_unlocked()
        count = len(list(data.get("entries") or []))
        data["entries"] = []
        _save_unlocked(data)
    return count


def export_for_team(team_passphrase: str) -> Tuple[bytes, str]:
    """Descifra memoria local y re-cifra con frase de equipo para compartir."""
    with _LOCK:
        data = _load_unlocked()
    blob = encrypt_team_export(data, team_passphrase)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return blob, f"elia_memory_team_{stamp}.enc"


def _merge_documents(
    local: Dict[str, Any],
    imported: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    local_entries: List[Dict[str, Any]] = []
    for raw in list(local.get("entries") or []):
        if isinstance(raw, dict):
            norm = _normalize_entry(raw)
            if norm:
                local_entries.append(norm)

    by_fp: Dict[str, Dict[str, Any]] = {}
    for entry in local_entries:
        by_fp[str(entry["script_fp"])] = entry

    added = 0
    updated = 0
    for raw in list(imported.get("entries") or []):
        if not isinstance(raw, dict):
            continue
        norm = _normalize_entry(raw)
        if not norm:
            continue
        fp = str(norm["script_fp"])
        if fp in by_fp:
            by_fp[fp] = norm
            updated += 1
        else:
            by_fp[fp] = norm
            added += 1

    merged_list = sorted(by_fp.values(), key=lambda e: float(e.get("ts", 0.0)))
    merged_list = _trim_entries(merged_list)
    merged = {"version": 1, "entries": merged_list}
    return merged, {"added": added, "updated": updated, "total": len(merged_list)}


def import_from_team(
    blob: bytes,
    team_passphrase: str,
    mode: ImportMode,
) -> Dict[str, Any]:
    """Importa memoria de equipo y la persiste cifrada con la clave local."""
    imported = _normalize_document(decrypt_team_import(blob, team_passphrase))

    with _LOCK:
        if mode == "replace":
            normalized_entries: List[Dict[str, Any]] = []
            for raw in list(imported.get("entries") or []):
                if isinstance(raw, dict):
                    norm = _normalize_entry(raw)
                    if norm:
                        normalized_entries.append(norm)
            normalized_entries.sort(key=lambda e: float(e.get("ts", 0.0)))
            data = {"version": 1, "entries": _trim_entries(normalized_entries)}
            _save_unlocked(data)
            return {
                "mode": "replace",
                "added": len(data["entries"]),
                "updated": 0,
                "total": len(data["entries"]),
            }

        local = _load_unlocked()
        merged, stats = _merge_documents(local, imported)
        _save_unlocked(merged)
        return {"mode": "merge", **stats}
