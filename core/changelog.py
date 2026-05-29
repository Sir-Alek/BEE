"""Parser del CHANGELOG.md orientado al usuario (Keep a Changelog, secciones en español)."""
from __future__ import annotations

import os
import re
from typing import Any

# Entradas mostradas en Configuración → Acerca de → Ver novedades.
CHANGELOG_UI_ENTRY_LIMIT = 5

_VERSION_HEADER_RE = re.compile(
    r"^##\s+\[([^\]]+)\]\s*(?:-\s*(\d{4}-\d{2}-\d{2}))?\s*$"
)
_SECTION_HEADER_RE = re.compile(r"^###\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^-\s+(.+?)\s*$")

_SECTION_KEYS = {
    "añadido": "added",
    "corregido": "fixed",
    "cambiado": "changed",
}


def _empty_entry(version: str, date: str | None) -> dict[str, Any]:
    return {
        "version": version,
        "date": date,
        "added": [],
        "fixed": [],
        "changed": [],
    }


def parse_changelog_markdown(text: str) -> list[dict[str, Any]]:
    """Parsea CHANGELOG.md y devuelve entradas más recientes primero."""
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    section_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("# "):
            continue

        version_match = _VERSION_HEADER_RE.match(line)
        if version_match:
            if current is not None:
                entries.append(current)
            current = _empty_entry(version_match.group(1).strip(), version_match.group(2))
            section_key = None
            continue

        section_match = _SECTION_HEADER_RE.match(line)
        if section_match and current is not None:
            normalized = section_match.group(1).strip().lower()
            section_key = _SECTION_KEYS.get(normalized)
            continue

        bullet_match = _BULLET_RE.match(line)
        if bullet_match and current is not None and section_key:
            current[section_key].append(bullet_match.group(1).strip())

    if current is not None:
        entries.append(current)

    return entries


def load_changelog(repo_root: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    path = os.path.join(repo_root, "CHANGELOG.md")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            entries = parse_changelog_markdown(f.read())
    except OSError:
        return []
    if limit is not None and limit > 0:
        return entries[:limit]
    return entries
