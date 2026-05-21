"""
Manifiesto local de versión instalada (anti-downgrade sin servidor).

Persiste en %%LOCALAPPDATA%%\\ELIA\\install_manifest.json con HMAC.
Inno Setup compara semver en pre-install; ELIA.exe valida HMAC al arrancar.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_INSTALL_SEED = b"ELIA-INSTALL-MANIFEST-v1-REPLACE-IN-RELEASE-BUILD"

_MANIFEST_VERSION = 1
_MANIFEST_FILENAME = "install_manifest.json"
_BACKUP_FILENAME = ".install_state_cache"


class DowngradeBlockedError(RuntimeError):
    """Versión en ejecución inferior a la máxima registrada localmente."""


def _secret_key() -> bytes:
    return hashlib.sha256(_INSTALL_SEED).digest()


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    elia = Path(base) / "ELIA"
    elia.mkdir(parents=True, exist_ok=True)
    return elia


def manifest_path() -> Path:
    return _state_dir() / _MANIFEST_FILENAME


def _backup_path() -> Path:
    return _state_dir() / _BACKUP_FILENAME


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semver-like '0.5.3' → (0, 5, 3). Non-numeric suffixes ignored."""
    raw = (version or "").strip()
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", raw)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def compare_versions(a: str, b: str) -> int:
    """Return -1 if a<b, 0 if equal prefix, 1 if a>b."""
    ta = parse_version(a)
    tb = parse_version(b)
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def _manifest_message(max_version: str, updated_at: float) -> bytes:
    return f"{max_version}|{updated_at:.6f}|v{_MANIFEST_VERSION}".encode("ascii")


def _manifest_signature(max_version: str, updated_at: float) -> str:
    return hmac.new(
        _secret_key(),
        _manifest_message(max_version, updated_at),
        hashlib.sha256,
    ).hexdigest()


def _validate_payload(data: Dict[str, Any]) -> Optional[Tuple[str, float]]:
    if int(data.get("v", 0)) != _MANIFEST_VERSION:
        return None
    max_version = str(data.get("max_version", "")).strip()
    if not max_version:
        return None
    try:
        updated_at = float(data.get("updated_at", 0.0))
    except (TypeError, ValueError):
        return None
    sig = str(data.get("sig", "")).lower()
    expected = _manifest_signature(max_version, updated_at)
    if not hmac.compare_digest(sig, expected):
        return None
    return max_version, updated_at


def _read_manifest_file(path: Path) -> Optional[Tuple[str, float]]:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        return _validate_payload(raw)
    except Exception:
        return None


def read_installed_max_version() -> Optional[str]:
    """Versión máxima registrada (manifest principal o respaldo)."""
    row = _read_manifest_file(manifest_path())
    if row is not None:
        return row[0]
    row = _read_manifest_file(_backup_path())
    if row is not None:
        return row[0]
    return None


def write_manifest(max_version: str, *, updated_at: Optional[float] = None) -> None:
    ts = float(updated_at if updated_at is not None else time.time())
    payload = {
        "v": _MANIFEST_VERSION,
        "max_version": max_version.strip(),
        "updated_at": ts,
        "sig": _manifest_signature(max_version.strip(), ts),
    }
    text = json.dumps(payload, indent=2)
    manifest_path().write_text(text, encoding="utf-8")
    try:
        _backup_path().write_text(text, encoding="utf-8")
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.kernel32.SetFileAttributesW(str(_backup_path()), 0x02)
            except Exception:
                pass
    except OSError:
        pass


def record_version_if_newer(current_version: str) -> None:
    """Tras arranque OK: eleva max_version si la versión actual es mayor."""
    current = current_version.strip()
    existing = read_installed_max_version()
    if existing is None or compare_versions(current, existing) > 0:
        write_manifest(current)


def assert_not_downgrade(current_version: str) -> None:
    """
    Bloquea ejecución si current_version < max_version registrada.
    Respeta ELIA_ALLOW_DOWNGRADE=1 (solo desarrollo).
    """
    if (os.environ.get("ELIA_ALLOW_DOWNGRADE") or "").strip().lower() in ("1", "true", "yes"):
        return
    max_ver = read_installed_max_version()
    if not max_ver:
        return
    if compare_versions(current_version.strip(), max_ver) < 0:
        raise DowngradeBlockedError(
            f"ELIA v{current_version.strip()} no puede ejecutarse: "
            f"esta máquina ya registró v{max_ver} o superior. "
            f"Instala la versión más reciente o contacta soporte."
        )


def downgrade_blocked_message(current_version: str) -> str:
    max_ver = read_installed_max_version() or "?"
    return (
        f"No se permite usar ELIA v{current_version.strip()} porque ya se instaló o ejecutó "
        f"v{max_ver} en este equipo. Instala la versión más reciente."
    )
