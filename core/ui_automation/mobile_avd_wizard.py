"""Asistente AVD: cmdline-tools (Architect) + fallback Android Studio (todos los tiers)."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.entitlements import TIER_ARCHITECT, normalize_tier
from core.ui_automation.mobile_android import (
    _subprocess_flags,
    list_avds,
    list_devices,
    resolve_android_sdk,
    resolve_emulator,
)

AVD_TEMPLATES: Dict[str, Dict[str, str]] = {
    "standard": {
        "label": "Estándar (recomendada)",
        "description": "Pixel 6 · Android 14 (API 34) · Google APIs · x86_64",
        "package": "system-images;android-34;google_apis;x86_64",
        "device": "pixel_6",
        "avd_name": "ELIA_Pixel_API34",
        "estimated_gb": "4",
    },
    "lite": {
        "label": "Ligera",
        "description": "Pixel 4 · Android 11 (API 30) · Google APIs · x86_64",
        "package": "system-images;android-30;google_apis;x86_64",
        "device": "pixel_4",
        "avd_name": "ELIA_Pixel_API30",
        "estimated_gb": "2.5",
    },
}

_job_lock = threading.Lock()
_job_state: Dict[str, Any] = {
    "active": False,
    "phase": "",
    "message": "",
    "done": False,
    "ok": False,
    "error": None,
    "avd_name": None,
}


def cmdline_tools_ready() -> Dict[str, Any]:
    sdkmanager, _ = _resolve_cmdline_bin("sdkmanager")
    avdmanager, _ = _resolve_cmdline_bin("avdmanager")
    return {
        "ok": bool(sdkmanager and avdmanager),
        "sdkmanager": sdkmanager,
        "avdmanager": avdmanager,
    }


def orchestration_allowed(tier: Optional[str], *, is_beta: bool = False) -> bool:
    if is_beta:
        return True
    return normalize_tier(tier or "") == TIER_ARCHITECT


def _reset_job() -> None:
    _job_state.update(
        {
            "active": True,
            "phase": "starting",
            "message": "Iniciando asistente AVD…",
            "done": False,
            "ok": False,
            "error": None,
            "avd_name": None,
        }
    )


def get_job_status() -> Dict[str, Any]:
    with _job_lock:
        return dict(_job_state)


def _resolve_cmdline_bin(name: str) -> Tuple[Optional[str], Optional[str]]:
    """Resuelve sdkmanager / avdmanager en cmdline-tools."""
    sdk, sdk_src = resolve_android_sdk()
    if not sdk:
        return None, None
    win = sys.platform == "win32"
    exe = f"{name}.bat" if win else name
    candidates = [
        os.path.join(sdk, "cmdline-tools", "latest", "bin", exe),
        os.path.join(sdk, "cmdline-tools", "bin", exe),
        os.path.join(sdk, "tools", "bin", exe),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path, sdk_src or "sdk"
    found = shutil.which(name)
    if found:
        return found, "path"
    return None, None


def _toolbox_studio_candidates() -> List[Tuple[str, str]]:
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if not local:
        return []
    out: List[Tuple[str, str]] = []
    patterns = (
        os.path.join(local, "JetBrains", "Toolbox", "apps", "AndroidStudio", "*", "bin", "studio64.exe"),
        os.path.join(local, "JetBrains", "Toolbox", "apps", "AndroidStudio", "*", "bin", "studio.exe"),
    )
    seen: set[str] = set()
    for pattern in patterns:
        for path in sorted(glob.glob(pattern), reverse=True):
            norm = os.path.normcase(path)
            if norm in seen:
                continue
            seen.add(norm)
            out.append((path, "jetbrains_toolbox"))
    return out


def _where_studio_executable() -> Tuple[Optional[str], Optional[str]]:
    if sys.platform != "win32":
        return None, None
    for name in ("studio64.exe", "studio.exe", "studio"):
        found = shutil.which(name)
        if found and os.path.isfile(found):
            return found, "path"
    try:
        proc = subprocess.run(
            ["where", "studio64.exe"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_subprocess_flags(),
        )
        if proc.returncode == 0:
            for line in (proc.stdout or "").splitlines():
                cand = line.strip()
                if cand and os.path.isfile(cand):
                    return cand, "where"
    except Exception:
        pass
    return None, None


def resolve_studio_executable_auto() -> Tuple[Optional[str], Optional[str]]:
    """Auto-detección sin override de tool_paths.json."""
    env = os.environ.get("ELIA_ANDROID_STUDIO") or os.environ.get("ANDROID_STUDIO")
    if env:
        for suffix in (r"bin\studio64.exe", r"bin\studio.exe", r"bin\studio"):
            candidate = env if env.lower().endswith(".exe") else os.path.join(env, *suffix.split("\\"))
            if os.path.isfile(candidate):
                return candidate, "env"
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local:
        for rel in (
            r"Programs\Android\Android Studio\bin\studio64.exe",
            r"Programs\Android\Android Studio\bin\studio.exe",
        ):
            candidate = os.path.join(local, *rel.split("\\"))
            if os.path.isfile(candidate):
                return candidate, "localappdata"
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if not root:
            continue
        candidate = os.path.join(root, "Android", "Android Studio", "bin", "studio64.exe")
        if os.path.isfile(candidate):
            return candidate, env_name.lower()
    for candidate, source in _toolbox_studio_candidates():
        if os.path.isfile(candidate):
            return candidate, source
    return _where_studio_executable()


def resolve_studio_executable() -> Tuple[Optional[str], Optional[str]]:
    """Ruta a studio64.exe / studio si está instalado."""
    from core.tool_paths import get_tool_path, validate_studio_path

    saved = get_tool_path("android_studio")
    if saved:
        ok, resolved, _ = validate_studio_path(saved)
        if ok and resolved:
            return resolved, "elia_config"
    return resolve_studio_executable_auto()


def list_studio_search_candidates() -> List[str]:
    """Todas las rutas que ELIA prueba al buscar Android Studio."""
    out: List[str] = []
    env = os.environ.get("ELIA_ANDROID_STUDIO") or os.environ.get("ANDROID_STUDIO")
    if env:
        out.append(env if env.lower().endswith(".exe") else os.path.join(env, "bin", "studio64.exe"))
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local:
        out.append(os.path.join(local, "Programs", "Android", "Android Studio", "bin", "studio64.exe"))
        out.append(os.path.join(local, "Programs", "Android", "Android Studio", "bin", "studio.exe"))
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if root:
            out.append(os.path.join(root, "Android", "Android Studio", "bin", "studio64.exe"))
    for path, _src in _toolbox_studio_candidates():
        out.append(path)
    where, _ = _where_studio_executable()
    if where:
        out.append(where)
    return out


def studio_search_candidates() -> List[str]:
    return list_studio_search_candidates()


def studio_configured_by(studio_path: Optional[str], studio_source: Optional[str]) -> Optional[str]:
    from core.tool_paths import get_tool_path

    if get_tool_path("android_studio"):
        return "elia_config"
    if not studio_path:
        return None
    if studio_source in ("env",):
        return "env"
    return "auto"


def suggest_default_android_sdk() -> Optional[str]:
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local:
        candidate = os.path.join(local, "Android", "Sdk")
        if os.path.isdir(candidate):
            return candidate
    return None


def _open_studio_failure_payload(message: str, **extra: Any) -> Dict[str, Any]:
    sdk, _ = resolve_android_sdk()
    payload: Dict[str, Any] = {
        "ok": False,
        "message": message,
        "searched_paths": studio_search_candidates(),
        "sdk_ok": bool(sdk),
        "settings_hint": "Configuración → Entorno local",
    }
    if bool(sdk) and extra.get("studio_missing"):
        payload["hint"] = (
            "El SDK Android está detectado. Solo falta indicar Android Studio en Entorno local."
        )
    payload.update(extra)
    return payload


def _disk_free_gb(path: str) -> Optional[float]:
    try:
        usage = shutil.disk_usage(path)
        return round(usage.free / (1024**3), 2)
    except Exception:
        return None


def _run_sdkmanager(args: List[str], *, timeout: float = 3600.0) -> Tuple[int, str, str]:
    tool, _ = _resolve_cmdline_bin("sdkmanager")
    if not tool:
        return 1, "", "sdkmanager no encontrado"
    sdk, _ = resolve_android_sdk()
    env = os.environ.copy()
    if sdk:
        env["ANDROID_HOME"] = sdk
        env["ANDROID_SDK_ROOT"] = sdk
    try:
        proc = subprocess.run(
            [tool, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            creationflags=_subprocess_flags(),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out, ""
    except subprocess.TimeoutExpired:
        return 1, "", "Tiempo de espera agotado en sdkmanager"
    except Exception as exc:
        return 1, "", str(exc)


def _run_avdmanager(args: List[str], *, timeout: float = 120.0) -> Tuple[int, str, str]:
    tool, _ = _resolve_cmdline_bin("avdmanager")
    if not tool:
        return 1, "", "avdmanager no encontrado"
    sdk, _ = resolve_android_sdk()
    env = os.environ.copy()
    if sdk:
        env["ANDROID_HOME"] = sdk
        env["ANDROID_SDK_ROOT"] = sdk
    try:
        proc = subprocess.run(
            [tool, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            creationflags=_subprocess_flags(),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out, ""
    except subprocess.TimeoutExpired:
        return 1, "", "Tiempo de espera agotado en avdmanager"
    except Exception as exc:
        return 1, "", str(exc)


def _accept_licenses() -> Tuple[bool, str]:
    tool, _ = _resolve_cmdline_bin("sdkmanager")
    if not tool:
        return False, "sdkmanager no encontrado. Instala Android SDK Command-line Tools."
    sdk, _ = resolve_android_sdk()
    env = os.environ.copy()
    if sdk:
        env["ANDROID_HOME"] = sdk
        env["ANDROID_SDK_ROOT"] = sdk
    try:
        proc = subprocess.run(
            [tool, "--licenses"],
            input="y\n" * 40,
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
            creationflags=_subprocess_flags(),
        )
        if proc.returncode == 0:
            return True, "Licencias aceptadas."
        err = (proc.stderr or proc.stdout or "").strip()
        return False, err or "No se pudieron aceptar las licencias."
    except Exception as exc:
        return False, str(exc)


def _install_system_image(package: str) -> Tuple[bool, str]:
    code, out, err = _run_sdkmanager(["--install", package], timeout=3600.0)
    if code == 0:
        return True, "System image instalada."
    detail = err or out.strip() or "sdkmanager --install falló"
    return False, detail[:800]


def _create_avd(template_id: str) -> Tuple[bool, str, Optional[str]]:
    tpl = AVD_TEMPLATES.get(template_id)
    if not tpl:
        return False, "Plantilla no válida.", None
    avd_name = tpl["avd_name"]
    existing, _ = list_avds()
    if avd_name in existing:
        return True, f"AVD «{avd_name}» ya existía.", avd_name
    code, out, err = _run_avdmanager(
        [
            "create",
            "avd",
            "-n",
            avd_name,
            "-k",
            tpl["package"],
            "-d",
            tpl["device"],
            "--force",
        ],
    )
    if code == 0:
        return True, f"AVD «{avd_name}» creado.", avd_name
    detail = err or out.strip() or "avdmanager create avd falló"
    return False, detail[:800], None


def _job_worker(template_id: str) -> None:
    try:
        with _job_lock:
            _job_state["phase"] = "licenses"
            _job_state["message"] = "Aceptando licencias de Google…"
        ok, msg = _accept_licenses()
        if not ok:
            raise RuntimeError(msg)

        tpl = AVD_TEMPLATES[template_id]
        with _job_lock:
            _job_state["phase"] = "install"
            _job_state["message"] = f"Descargando system image ({tpl['estimated_gb']} GB aprox.)…"
        ok, msg = _install_system_image(tpl["package"])
        if not ok:
            raise RuntimeError(msg)

        with _job_lock:
            _job_state["phase"] = "create"
            _job_state["message"] = "Creando dispositivo virtual…"
        ok, msg, avd_name = _create_avd(template_id)
        if not ok:
            raise RuntimeError(msg)

        verify = verify_avd_in_catalog(avd_name)
        if not verify.get("ok"):
            with _job_lock:
                _job_state.update(
                    {
                        "active": False,
                        "phase": "done",
                        "message": msg + " Comprueba el catálogo AVD en ELIA.",
                        "done": True,
                        "ok": True,
                        "error": None,
                        "avd_name": avd_name,
                        "verified": False,
                    }
                )
            return

        with _job_lock:
            _job_state.update(
                {
                    "active": False,
                    "phase": "done",
                    "message": msg,
                    "done": True,
                    "ok": True,
                    "error": None,
                    "avd_name": avd_name,
                    "verified": True,
                }
            )
    except Exception as exc:
        with _job_lock:
            _job_state.update(
                {
                    "active": False,
                    "phase": "error",
                    "message": str(exc),
                    "done": True,
                    "ok": False,
                    "error": str(exc),
                }
            )


def start_orchestration(template_id: str) -> Dict[str, Any]:
    if template_id not in AVD_TEMPLATES:
        return {"ok": False, "message": "Plantilla no válida."}
    with _job_lock:
        if _job_state.get("active"):
            return {"ok": False, "message": "Ya hay un asistente AVD en curso.", "status": get_job_status()}
    _reset_job()
    thread = threading.Thread(target=_job_worker, args=(template_id,), daemon=True)
    thread.start()
    return {"ok": True, "started": True, "status": get_job_status()}


def open_android_studio(*, path: Optional[str] = None, save: bool = False) -> Dict[str, Any]:
    from core.tool_paths import save_tool_paths, validate_studio_path

    resolved_path: Optional[str] = None
    source = "manual"
    if path and str(path).strip():
        ok, resolved, msg = validate_studio_path(str(path).strip())
        if not ok or not resolved:
            return _open_studio_failure_payload(msg or "Ruta de Android Studio no válida.")
        resolved_path = resolved
        if save:
            save_tool_paths({"android_studio": path.strip()})
            source = "elia_config"
    else:
        resolved_path, source = resolve_studio_executable()
    if not resolved_path:
        return _open_studio_failure_payload(
            (
                "No se encontró Android Studio. Indica la ruta manualmente o configúrala en "
                "Configuración → Entorno local."
            ),
            hint="Device Manager: More Actions → Virtual Device Manager.",
            studio_missing=True,
        )
    try:
        subprocess.Popen(
            [resolved_path],
            cwd=os.path.dirname(resolved_path),
            creationflags=_subprocess_flags(),
            close_fds=False,
        )
        return {
            "ok": True,
            "message": "Android Studio abierto. Crea un AVD en Device Manager y vuelve a ELIA.",
            "path": resolved_path,
            "source": source,
        }
    except Exception as exc:
        return _open_studio_failure_payload(
            f"No se pudo abrir Android Studio: {exc}",
            path=resolved_path,
        )


def verify_avd_in_catalog(avd_name: Optional[str]) -> Dict[str, Any]:
    """Comprueba que un AVD aparece en emulator -list-avds."""
    if not avd_name:
        return {"ok": False, "message": "Sin nombre de AVD."}
    avds, err = list_avds()
    if avd_name in avds:
        return {"ok": True, "avd_name": avd_name, "avds": avds, "message": f"AVD «{avd_name}» en catálogo."}
    return {
        "ok": False,
        "avd_name": avd_name,
        "avds": avds,
        "error": err,
        "message": f"AVD «{avd_name}» aún no aparece en el catálogo del SDK.",
    }


def wizard_capabilities(*, tier: Optional[str], is_beta: bool = False) -> Dict[str, Any]:
    sdk, sdk_src = resolve_android_sdk()
    sdkmanager, _ = _resolve_cmdline_bin("sdkmanager")
    avdmanager, _ = _resolve_cmdline_bin("avdmanager")
    emulator = resolve_emulator()
    avds, avds_err = list_avds(emulator_tool=emulator)
    devices, _ = list_devices()
    online = [d for d in devices if d.state == "device"]
    studio, studio_src = resolve_studio_executable()
    disk_gb = _disk_free_gb(sdk or os.path.expanduser("~"))
    suggested_sdk = suggest_default_android_sdk() if not sdk else None

    templates = [
        {
            "id": tid,
            "label": tpl["label"],
            "description": tpl["description"],
            "estimated_gb": tpl["estimated_gb"],
            "avd_name": tpl["avd_name"],
        }
        for tid, tpl in AVD_TEMPLATES.items()
    ]

    return {
        "orchestration_allowed": orchestration_allowed(tier, is_beta=is_beta),
        "orchestration_tier": TIER_ARCHITECT,
        "sdk_path": sdk,
        "sdk_source": sdk_src,
        "cmdline_tools_ok": bool(sdkmanager and avdmanager),
        "sdkmanager_path": sdkmanager,
        "avdmanager_path": avdmanager,
        "emulator_path": emulator.path,
        "avd_count": len(avds),
        "avds": avds,
        "avds_error": avds_err,
        "online_devices": [{"id": d.id, "kind": d.kind, "state": d.state} for d in online],
        "has_online_emulator": any(d.kind == "emulator" for d in online),
        "studio_path": studio,
        "studio_source": studio_src,
        "studio_available": bool(studio),
        "studio_configured_by": studio_configured_by(studio, studio_src),
        "sdk_ok": bool(sdk),
        "studio_missing_sdk_ok": bool(sdk) and not studio,
        "suggested_sdk_path": suggested_sdk,
        "disk_free_gb": disk_gb,
        "disk_ok": disk_gb is None or disk_gb >= 8.0,
        "templates": templates,
        "job": get_job_status(),
    }
