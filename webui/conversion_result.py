"""Utilidades para reportar archivos generados en la UI web (message_ack + job progress)."""
from __future__ import annotations

import glob
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

_PREVIEW_EXT = {".feature", ".py", ".json", ".js", ".txt", ".md", ".gherkin"}
_MAX_PREVIEW = 3500


def read_text_preview(path: str, max_chars: int = _MAX_PREVIEW) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext not in _PREVIEW_EXT:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read(max_chars + 1)
        if len(text) > max_chars:
            return text[:max_chars] + "\n…"
        return text
    except OSError:
        return ""


def file_entry(path: str, label: Optional[str] = None) -> Dict[str, Any]:
    abspath = os.path.abspath(path)
    return {
        "path": abspath,
        "label": label or os.path.basename(abspath),
        "preview": read_text_preview(abspath),
    }


def conversion_result(
    *,
    project_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    files: Iterable[Tuple[str, str]],
) -> Dict[str, Any]:
    """Construye payload para WebUIAdapter.info(..., result=...)."""
    root = project_dir or output_dir
    entries: List[Dict[str, Any]] = []
    for label, path in files:
        if path and os.path.isfile(path):
            entries.append(file_entry(path, label))
    abs_root = os.path.abspath(root) if root else None
    return {
        "project_dir": abs_root,
        "output_dir": os.path.abspath(output_dir) if output_dir else abs_root,
        "generated_files": entries,
    }


def files_from_paths_map(paths: Dict[str, str], project_dir: str) -> Dict[str, Any]:
    return conversion_result(
        project_dir=project_dir,
        files=[(name, path) for name, path in paths.items()],
    )


def files_in_directory(
    output_dir: str,
    *,
    patterns: Tuple[str, ...] = ("*.feature", "*.py"),
    max_files: int = 16,
) -> Dict[str, Any]:
    """Lista archivos recientes bajo output_dir para doc-to-bdd y similares."""
    found: List[Tuple[str, str]] = []
    seen: set[str] = set()
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(output_dir, "**", pattern), recursive=True)):
            if not os.path.isfile(path):
                continue
            norm = os.path.normcase(path)
            if norm in seen:
                continue
            seen.add(norm)
            rel = os.path.relpath(path, output_dir)
            found.append((str(rel), path))
            if len(found) >= max_files:
                break
        if len(found) >= max_files:
            break
    return conversion_result(output_dir=output_dir, files=found)
