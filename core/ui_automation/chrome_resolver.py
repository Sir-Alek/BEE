"""
Resolución de Google Chrome en Windows para grabación Puppeteer y apertura de la Web UI.

Requisito de producto: Chrome instalado. Chromium empaquetado (Puppeteer) solo si
ELIA_ALLOW_CHROMIUM_FALLBACK=1.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class ChromeResolveResult:
    ok: bool
    chrome_path: Optional[str] = None
    source: Optional[str] = None  # env | install | where | puppeteer-chromium
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "chrome_path": self.chrome_path,
            "source": self.source,
            "warnings": self.warnings,
            "errors": self.errors,
            "chrome_required": True,
            "chromium_fallback_enabled": chromium_fallback_allowed(),
            "platform": sys.platform,
        }


def chromium_fallback_allowed() -> bool:
    v = (os.environ.get("ELIA_ALLOW_CHROMIUM_FALLBACK") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _exists_exe(path: str) -> bool:
    p = (path or "").strip()
    return bool(p) and os.path.isfile(p)


def _env_candidate_paths() -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for key in ("ELIA_CHROME_PATH", "CHROME_PATH", "ELIA_BROWSER_PATH"):
        raw = (os.environ.get(key) or "").strip().strip('"')
        if raw:
            out.append((raw, "env"))
    return out


def _windows_standard_paths() -> List[str]:
    paths: List[str] = []
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    rel = r"Google\Chrome\Application\chrome.exe"
    for base in (pf, pf86):
        if base:
            paths.append(os.path.join(base, rel))
    if local:
        paths.append(os.path.join(local, rel))
    return paths


def _where_chrome_exe() -> Optional[str]:
    if sys.platform != "win32":
        return None
    try:
        proc = subprocess.run(
            ["where", "chrome"],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            return None
        for line in proc.stdout.splitlines():
            cand = line.strip().strip('"')
            if cand.lower().endswith(".exe") and _exists_exe(cand):
                return cand
    except Exception:
        return None
    return None


def _puppeteer_chromium_via_node(base_dir: str) -> Optional[str]:
    """Ruta al Chromium descargado por puppeteer (npm), vía Node en core/node."""
    node_modules = os.path.join(base_dir, "core", "node", "node_modules")
    if not os.path.isdir(os.path.join(node_modules, "puppeteer")) and not os.path.isdir(
        os.path.join(node_modules, "puppeteer-core")
    ):
        return None

    node_cmd = shutil.which("node")
    if not node_cmd:
        for name in ("node.exe", "node"):
            for folder in (
                os.path.join(base_dir, "core", "node"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "ELIA", "node_runtime", "node"),
            ):
                p = os.path.join(folder, name)
                if os.path.isfile(p):
                    node_cmd = p
                    break
            if node_cmd:
                break
    if not node_cmd:
        return None

    script = (
        "try { const p=require('puppeteer'); console.log(p.executablePath()); }"
        " catch (e) { try { const p=require('puppeteer-core'); console.log(p.executablePath()); }"
        " catch (e2) { process.exit(2); } }"
    )
    env = os.environ.copy()
    prev = env.get("NODE_PATH", "")
    env["NODE_PATH"] = node_modules + (os.pathsep + prev if prev else "")

    try:
        proc = subprocess.run(
            [node_cmd, "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.join(base_dir, "core", "node"),
            env=env,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            return None
        line = (proc.stdout or "").strip().splitlines()
        if not line:
            return None
        cand = line[-1].strip()
        return cand if _exists_exe(cand) else None
    except Exception:
        return None


def resolve_chrome_for_recording(
    base_dir: Optional[str] = None,
    *,
    allow_chromium_fallback: Optional[bool] = None,
) -> ChromeResolveResult:
    from core.tool_paths import get_tool_path

    override = get_tool_path("chrome")
    if override and _exists_exe(override):
        return ChromeResolveResult(ok=True, chrome_path=override, source="elia_config")
    return resolve_chrome_for_recording_auto(
        base_dir,
        allow_chromium_fallback=allow_chromium_fallback,
    )


def resolve_chrome_for_recording_auto(
    base_dir: Optional[str] = None,
    *,
    allow_chromium_fallback: Optional[bool] = None,
) -> ChromeResolveResult:
    """
    Orden: variables de entorno → rutas estándar Windows → where chrome →
    Chromium Puppeteer (solo si allow_chromium_fallback).
    """
    if sys.platform != "win32":
        return ChromeResolveResult(
            ok=False,
            errors=["La grabación con Chrome solo está soportada en Windows por ahora."],
        )

    root = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    allow_fb = chromium_fallback_allowed() if allow_chromium_fallback is None else allow_chromium_fallback
    warnings: List[str] = []
    errors: List[str] = []

    for path, source in _env_candidate_paths():
        if _exists_exe(path):
            return ChromeResolveResult(ok=True, chrome_path=path, source=source, warnings=warnings)

    for path in _windows_standard_paths():
        if _exists_exe(path):
            return ChromeResolveResult(ok=True, chrome_path=path, source="install", warnings=warnings)

    where_path = _where_chrome_exe()
    if where_path:
        return ChromeResolveResult(ok=True, chrome_path=where_path, source="where", warnings=warnings)

    if allow_fb:
        pup = _puppeteer_chromium_via_node(root)
        if pup:
            warnings.append(
                "No se detectó Google Chrome instalado; se usará Chromium interno de Puppeteer. "
                "Se recomienda instalar Chrome para grabaciones con el mismo motor y perfil que el usuario."
            )
            return ChromeResolveResult(
                ok=True,
                chrome_path=pup,
                source="puppeteer-chromium",
                warnings=warnings,
            )
        errors.append(
            "Chromium de respaldo no disponible. Ejecute: cd core\\node && npm install "
            "(o reinstale ELIA) y mantenga ELIA_ALLOW_CHROMIUM_FALLBACK=1."
        )
    else:
        errors.append(
            "Para usar Chromium empaquetado sin Chrome instalado, defina ELIA_ALLOW_CHROMIUM_FALLBACK=1 "
            "(solo entornos controlados; no sustituye el requisito oficial de Chrome)."
        )

    errors.extend(
        [
            "Instale Google Chrome: https://www.google.com/chrome/",
            "Microsoft Edge no sustituye a Chrome para la grabación.",
            "Si Chrome ya está instalado, defina ELIA_CHROME_PATH con la ruta completa a chrome.exe "
            '(ej: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe).',
        ]
    )
    return ChromeResolveResult(ok=False, errors=errors, warnings=warnings)


def candidate_chrome_executables() -> List[str]:
    """Rutas a probar al abrir la Web UI en el navegador (browser_launch)."""
    if sys.platform != "win32":
        return []
    seen: set[str] = set()
    out: List[str] = []
    for path, _ in _env_candidate_paths():
        if _exists_exe(path) and path not in seen:
            seen.add(path)
            out.append(path)
    for path in _windows_standard_paths():
        if _exists_exe(path) and path not in seen:
            seen.add(path)
            out.append(path)
    w = _where_chrome_exe()
    if w and w not in seen:
        out.append(w)
    return out
