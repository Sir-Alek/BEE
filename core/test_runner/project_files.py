"""Lectura/escritura segura de archivos editables en proyectos Behave."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

EDITABLE_SUFFIXES = (".feature", ".py", ".ini", ".json", ".txt")
EDITABLE_NAMES = frozenset({"locustfile.py", "behave.ini"})

# Archivos visibles en el panel «Ejecutar y editar» (el resto sigue en disco).
_RUNNER_ROOT_FILES = frozenset({"locustfile.py"})
_RUNNER_UTILS_FILES = frozenset({"utils/button_functions.py"})


def is_runner_workspace_file(rel_path: str) -> bool:
    """True si el archivo debe mostrarse en el árbol del runner (no incluye environment.py)."""
    rel = rel_path.replace("\\", "/").lstrip("/")
    lower = rel.lower()
    name = Path(rel).name.lower()

    if name == "environment.py":
        return False
    if rel in _RUNNER_ROOT_FILES or lower in _RUNNER_UTILS_FILES:
        return True
    if lower.startswith("features/steps/") and lower.endswith(".py"):
        return True
    if lower.startswith("pages/") and lower.endswith(".py"):
        return True
    if lower.startswith("features/") and lower.endswith(".feature"):
        return True
    if lower.startswith("resources/data/") and lower.endswith(".json"):
        return True
    return False


def list_runner_workspace_files(project_root: str | Path) -> List[dict]:
    return [f for f in list_editable_files(project_root) if is_runner_workspace_file(f["path"])]


def _resolve_safe(project_root: Path, rel_path: str) -> Path:
    rel = rel_path.replace("\\", "/").lstrip("/")
    target = (project_root / rel).resolve()
    root = project_root.resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("Ruta fuera del proyecto")
    return target


def is_editable(path: Path) -> bool:
    if path.name in EDITABLE_NAMES:
        return True
    return path.suffix.lower() in EDITABLE_SUFFIXES


def list_editable_files(project_root: str | Path) -> List[dict]:
    root = Path(project_root)
    if not root.is_dir():
        return []
    out: List[dict] = []
    skip_dirs = {"outputs", "__pycache__", ".git", "node_modules"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            p = Path(dirpath) / fn
            if not is_editable(p):
                continue
            rel = p.relative_to(root).as_posix()
            out.append({"path": rel, "name": fn, "size": p.stat().st_size})
    return sorted(out, key=lambda x: x["path"])


def read_project_file(project_root: str | Path, rel_path: str) -> str:
    path = _resolve_safe(Path(project_root), rel_path)
    if not path.is_file() or not is_editable(path):
        raise FileNotFoundError(rel_path)
    return path.read_text(encoding="utf-8")


def write_project_file(project_root: str | Path, rel_path: str, content: str) -> None:
    path = _resolve_safe(Path(project_root), rel_path)
    if not is_editable(path):
        raise ValueError("Tipo de archivo no editable")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
