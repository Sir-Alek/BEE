"""
Descubrimiento de entorno Android (adb, SDK, AVD, Appium) para grabación móvil.

Alcance: Android únicamente. iOS no está soportado en Windows.
"""
from __future__ import annotations

import http.client
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_appium_proc: Optional[subprocess.Popen] = None
_appium_started_by_elia: bool = False
_appium_lock = threading.Lock()


@dataclass
class AndroidTool:
    name: str
    path: Optional[str] = None
    source: Optional[str] = None
    version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "source": self.source,
            "version": self.version,
            "ok": bool(self.path),
        }


@dataclass
class MobileDevice:
    id: str
    state: str
    kind: str  # physical | emulator
    model: Optional[str] = None
    product: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state,
            "kind": self.kind,
            "model": self.model,
            "product": self.product,
        }


@dataclass
class MobilePreflightResult:
    ok: bool
    platform: str = sys.platform
    items: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    env: Dict[str, Optional[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "platform": self.platform,
            "items": self.items,
            "warnings": self.warnings,
            "errors": self.errors,
            "env": self.env,
            "android_only": True,
        }


def _subprocess_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_cmd(
    argv: List[str],
    *,
    timeout: float = 30.0,
    text: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        capture_output=True,
        text=text,
        timeout=timeout,
        creationflags=_subprocess_flags(),
    )


def _expand_win_env(value: str, env: Dict[str, str]) -> str:
    if sys.platform != "win32" or not value:
        return value
    out = str(value)
    for _ in range(12):
        match = re.search(r"%([^%]+)%", out)
        if not match:
            break
        key = match.group(1)
        rep = env.get(key) or os.environ.get(key) or ""
        out = out.replace(f"%{key}%", rep, 1)
    return out


def _read_windows_env_var(name: str) -> Optional[str]:
    if sys.platform != "win32" or not name:
        return None
    import winreg

    targets = [
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
    ]
    for hive, subkey in targets:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                try:
                    val, _ = winreg.QueryValueEx(key, name)
                except OSError:
                    continue
                if val is not None and str(val).strip():
                    return str(val).strip()
        except OSError:
            continue
    return None


def _get_env_var(name: str) -> Optional[str]:
    """Lee variable del proceso; en Windows también del registro (HKCU/HKLM)."""
    raw = os.environ.get(name)
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    if sys.platform != "win32":
        return None
    reg_val = _read_windows_env_var(name)
    if not reg_val:
        return None
    merged = dict(os.environ)
    return _expand_win_env(reg_val, merged).strip() or None


def _path_env_keys(env: Dict[str, str]) -> List[str]:
    return [k for k in env.keys() if k.lower() == "path"]


def _prepend_path(env: Dict[str, str], folder: str) -> None:
    folder = (folder or "").strip()
    if not folder or not os.path.isdir(folder):
        return
    keys = _path_env_keys(env) or ["PATH"]
    for key in keys:
        existing = env.get(key, "")
        parts = [p for p in existing.split(os.pathsep) if p]
        norm_folder = os.path.normcase(os.path.normpath(folder))
        if any(os.path.normcase(os.path.normpath(p)) == norm_folder for p in parts):
            continue
        env[key] = folder + (os.pathsep + existing if existing else "")


def _validate_emulator_layout(exe_path: str) -> Optional[str]:
    emulator_dir = _emulator_home_dir(exe_path)
    if _basename_lower(exe_path) not in ("emulator.exe", "emulator"):
        return (
            f"Ruta inválida (use emulator.exe, no qemu): {exe_path}"
        )
    required_dlls = (
        "libandroid-emu-metrics.dll",
        "libglib2_windows_msvc-x86_64.dll",
    )
    missing = [dll for dll in required_dlls if not os.path.isfile(os.path.join(emulator_dir, dll))]
    if missing:
        return (
            f"Instalación incompleta del Android Emulator en {emulator_dir}. "
            f"Faltan: {', '.join(missing)}. Reinstale el paquete «Android Emulator» en SDK Manager."
        )
    return None


def _basename_lower(path: str) -> str:
    return os.path.basename(path or "").lower()


def _is_qemu_engine_binary(path: str) -> bool:
    name = _basename_lower(path)
    return name.startswith("qemu-system") or name == "qemu.exe"


def _sdk_root_from_emulator_exe(exe_path: str) -> Optional[str]:
    """.../Android/Sdk/emulator/emulator.exe -> .../Android/Sdk"""
    emulator_dir = os.path.dirname(os.path.abspath(exe_path))
    if _basename_lower(emulator_dir) != "emulator":
        return None
    sdk_root = os.path.dirname(emulator_dir)
    return sdk_root if sdk_root and os.path.isdir(sdk_root) else None


def _emulator_home_dir(exe_path: str) -> str:
    """Directorio raíz del paquete emulator (donde viven las DLL en Windows)."""
    return os.path.dirname(os.path.abspath(exe_path))


def _canonical_emulator_exe(path: str) -> Optional[str]:
    """
    Normaliza rutas al wrapper oficial emulator.exe.
    Rechaza binarios internos qemu-system-* que no cargan DLLs sin el entorno del wrapper.
    """
    if not path or not os.path.isfile(path):
        return None
    norm = os.path.normpath(path)
    if _is_qemu_engine_binary(norm):
        parts = norm.split(os.sep)
        try:
            idx = parts.index("emulator")
        except ValueError:
            return None
        emulator_dir = os.sep.join(parts[: idx + 1])
        wrapper_name = "emulator.exe" if sys.platform == "win32" else "emulator"
        wrapper = os.path.join(emulator_dir, wrapper_name)
        return wrapper if os.path.isfile(wrapper) else None
    name = _basename_lower(norm)
    if name in ("emulator.exe", "emulator"):
        return norm
    return None


def _emulator_child_env(exe_path: str) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items()}
    if sys.platform == "win32":
        for key in (
            "ELIA_EMULATOR_PATH",
            "ELIA_ANDROID_HOME",
            "ANDROID_HOME",
            "ANDROID_SDK_ROOT",
            "ANDROID_AVD_HOME",
        ):
            reg_val = _read_windows_env_var(key)
            if reg_val and not (env.get(key) or "").strip():
                env[key] = _expand_win_env(reg_val, env)
    sdk_root = _sdk_root_from_emulator_exe(exe_path)
    if not sdk_root:
        for key in ("ELIA_ANDROID_HOME", "ANDROID_HOME", "ANDROID_SDK_ROOT"):
            val = _get_env_var(key)
            if val and os.path.isdir(val):
                sdk_root = val
                break
    emulator_dir = _emulator_home_dir(exe_path)
    if sdk_root:
        env["ANDROID_HOME"] = sdk_root
        env["ANDROID_SDK_ROOT"] = sdk_root
    env["ANDROID_EMULATOR_HOME"] = emulator_dir
    _prepend_path(env, emulator_dir)
    for sub in ("lib64", "lib", os.path.join("qemu", "windows-x86_64")):
        _prepend_path(env, os.path.join(emulator_dir, sub))
    if sdk_root:
        _prepend_path(env, os.path.join(sdk_root, "platform-tools"))
    return env


def _run_emulator_cmd(
    exe_path: str,
    args: List[str],
    *,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess:
    cwd = _emulator_home_dir(exe_path)
    return subprocess.run(
        [exe_path, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
        env=_emulator_child_env(exe_path),
        creationflags=_subprocess_flags(),
    )


def _popen_emulator(exe_path: str, args: List[str]) -> subprocess.Popen:
    cwd = _emulator_home_dir(exe_path)
    env = _emulator_child_env(exe_path)
    if sys.platform == "win32":
        # cmd + cd /d: garantiza cwd y PATH de DLLs para el wrapper y el qemu hijo.
        cmd_line = f'cd /d "{cwd}" && {subprocess.list2cmdline([exe_path, *args])}'
        return subprocess.Popen(
            cmd_line,
            shell=True,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_subprocess_flags(),
        )
    return subprocess.Popen(
        [exe_path, *args],
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_subprocess_flags(),
        close_fds=True,
    )


def resolve_android_sdk() -> Tuple[Optional[str], Optional[str]]:
    from core.tool_paths import get_tool_path

    override = get_tool_path("android_sdk")
    if override and os.path.isdir(override):
        return override, "elia_config"
    return resolve_android_sdk_auto()


def resolve_android_sdk_auto() -> Tuple[Optional[str], Optional[str]]:
    for env_name in ("ELIA_ANDROID_HOME", "ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = _get_env_var(env_name)
        if val and os.path.isdir(val):
            return val, env_name.lower()
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local:
        candidate = os.path.join(local, "Android", "Sdk")
        if os.path.isdir(candidate):
            return candidate, "localappdata"
    return None, None


def _resolve_from_env_or_sdk(
    env_names: Tuple[str, ...],
    sdk_relative: str,
    which_name: str,
    *,
    config_key: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    if config_key:
        from core.tool_paths import get_tool_path

        override = get_tool_path(config_key)
        if override and os.path.isfile(override):
            return override, "elia_config"
    for env_name in env_names:
        val = _get_env_var(env_name)
        if val and os.path.isfile(val):
            return val, env_name.lower()
    sdk_root, sdk_src = resolve_android_sdk()
    if sdk_root:
        candidate = os.path.join(sdk_root, *sdk_relative.replace("/", os.sep).split(os.sep))
        if os.path.isfile(candidate):
            return candidate, sdk_src or "sdk"
    found = shutil.which(which_name)
    if found:
        return found, "path"
    return None, None


def resolve_adb() -> AndroidTool:
    path, source = _resolve_from_env_or_sdk(
        ("ELIA_ADB_PATH",),
        os.path.join("platform-tools", "adb.exe" if sys.platform == "win32" else "adb"),
        "adb",
        config_key="adb",
    )
    version = None
    if path:
        try:
            proc = _run_cmd([path, "version"], timeout=10)
            if proc.returncode == 0:
                version = (proc.stdout or proc.stderr or "").strip().splitlines()[0]
        except Exception:
            pass
    return AndroidTool(name="adb", path=path, source=source, version=version)


def resolve_emulator() -> AndroidTool:
    path, source = _resolve_from_env_or_sdk(
        ("ELIA_EMULATOR_PATH",),
        os.path.join("emulator", "emulator.exe" if sys.platform == "win32" else "emulator"),
        "emulator",
        config_key="emulator",
    )
    canonical = _canonical_emulator_exe(path) if path else None
    if path and not canonical:
        path, source = None, None
    elif canonical:
        if path and _is_qemu_engine_binary(path):
            source = (source or "sdk") + "+wrapper"
        path = canonical
    version = None
    if path:
        try:
            proc = _run_emulator_cmd(path, ["-version"], timeout=10)
            out = ((proc.stdout or "") + (proc.stderr or "")).strip()
            if out:
                version = out.splitlines()[0]
        except Exception:
            pass
    return AndroidTool(name="emulator", path=path, source=source, version=version)


def check_appium_server(host: str = "localhost", port: int = 4723) -> bool:
    try:
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request("GET", "/status")
        resp = conn.getresponse()
        return resp.status == 200
    except Exception:
        return False


def appium_endpoint() -> Tuple[str, int]:
    host = (os.environ.get("ELIA_APPIUM_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    port_raw = (os.environ.get("ELIA_APPIUM_PORT") or "4723").strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = 4723
    return host, port


def appium_url(host: Optional[str] = None, port: Optional[int] = None) -> str:
    h, p = appium_endpoint()
    return f"http://{host or h}:{port if port is not None else p}"


def resolve_appium(*, skip_config: bool = False) -> AndroidTool:
    if not skip_config:
        from core.tool_paths import get_tool_path

        override = get_tool_path("appium")
        if override and os.path.isfile(override):
            return AndroidTool(name="appium", path=override, source="elia_config")
    candidates: List[Tuple[str, str]] = []
    env_path = (os.environ.get("ELIA_APPIUM_PATH") or "").strip()
    if env_path:
        candidates.append((env_path, "env"))
    which = shutil.which("appium")
    if which:
        candidates.append((which, "path"))
    if sys.platform == "win32":
        appdata = (os.environ.get("APPDATA") or "").strip()
        pf = (os.environ.get("ProgramFiles") or "").strip()
        for path in (
            os.path.join(appdata, "npm", "appium.cmd") if appdata else "",
            os.path.join(pf, "nodejs", "appium.cmd") if pf else "",
        ):
            if path and os.path.isfile(path):
                candidates.append((path, "npm"))
    seen: set[str] = set()
    path: Optional[str] = None
    source: Optional[str] = None
    for cand, src in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if os.path.isfile(cand):
            path, source = cand, src
            break
    version = None
    if path:
        try:
            proc = _run_cmd([path, "--version"], timeout=15)
            out = ((proc.stdout or "") + (proc.stderr or "")).strip()
            if out:
                version = out.splitlines()[0]
        except Exception:
            pass
    return AndroidTool(name="appium", path=path, source=source, version=version)


def get_appium_status() -> Dict[str, Any]:
    host, port = appium_endpoint()
    url = appium_url(host, port)
    tool = resolve_appium()
    running = check_appium_server(host, port)
    managed = bool(_appium_started_by_elia and _appium_proc and _appium_proc.poll() is None)
    return {
        "ok": running or bool(tool.path),
        "running": running,
        "installed": bool(tool.path),
        "managed_by_elia": managed,
        "url": url,
        "host": host,
        "port": port,
        "path": tool.path,
        "source": tool.source,
        "version": tool.version,
        "android_only": True,
    }


def start_appium_server(*, timeout_sec: float = 60.0) -> Dict[str, Any]:
    host, port = appium_endpoint()
    url = appium_url(host, port)
    if check_appium_server(host, port):
        return {
            "ok": True,
            "running": True,
            "message": "Appium ya está en ejecución.",
            "url": url,
            "reused": True,
            "managed_by_elia": False,
        }

    tool = resolve_appium()
    if not tool.path:
        return {
            "ok": False,
            "running": False,
            "message": "Appium no encontrado.",
            "url": url,
            "hint": "Instálalo con: npm install -g appium && appium driver install uiautomator2",
        }

    with _appium_lock:
        global _appium_proc, _appium_started_by_elia
        if _appium_proc and _appium_proc.poll() is None and check_appium_server(host, port):
            return {
                "ok": True,
                "running": True,
                "message": "Appium ya está en ejecución.",
                "url": url,
                "reused": True,
                "managed_by_elia": _appium_started_by_elia,
            }

        argv = [tool.path, "--address", host, "--port", str(port)]
        try:
            _appium_proc = subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=sys.platform != "win32",
                creationflags=_subprocess_flags(),
            )
            _appium_started_by_elia = True
        except Exception as exc:
            _appium_proc = None
            _appium_started_by_elia = False
            return {
                "ok": False,
                "running": False,
                "message": f"No se pudo iniciar Appium: {exc}",
                "url": url,
            }

        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if check_appium_server(host, port):
                return {
                    "ok": True,
                    "running": True,
                    "message": "Appium iniciado.",
                    "url": url,
                    "pid": _appium_proc.pid,
                    "managed_by_elia": True,
                }
            if _appium_proc.poll() is not None:
                _appium_started_by_elia = False
                return {
                    "ok": False,
                    "running": False,
                    "message": "Appium terminó al arrancar. Revisa que Node.js y el driver uiautomator2 estén instalados.",
                    "url": url,
                }
            time.sleep(0.5)

        return {
            "ok": False,
            "running": False,
            "message": "Tiempo de espera agotado: Appium no respondió en /status.",
            "url": url,
        }


def stop_appium_server(*, only_if_started_by_elia: bool = True) -> Dict[str, Any]:
    global _appium_proc, _appium_started_by_elia
    host, port = appium_endpoint()
    url = appium_url(host, port)

    with _appium_lock:
        if only_if_started_by_elia and not _appium_started_by_elia:
            return {
                "ok": True,
                "running": check_appium_server(host, port),
                "message": "Appium no fue iniciado por ELIA; no se detuvo.",
                "url": url,
            }
        proc = _appium_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=8)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        _appium_proc = None
        _appium_started_by_elia = False

    return {
        "ok": True,
        "running": check_appium_server(host, port),
        "message": "Appium detenido." if not check_appium_server(host, port) else "Appium sigue activo (otro proceso).",
        "url": url,
    }


def ensure_appium_running(*, auto_start: bool = True, timeout_sec: float = 60.0) -> Dict[str, Any]:
    host, port = appium_endpoint()
    if check_appium_server(host, port):
        return {
            "ok": True,
            "running": True,
            "message": "Appium accesible.",
            "url": appium_url(host, port),
            "reused": True,
        }
    if not auto_start:
        tool = resolve_appium()
        return {
            "ok": False,
            "running": False,
            "message": "Appium no responde en localhost:4723.",
            "url": appium_url(host, port),
            "installed": bool(tool.path),
        }
    return start_appium_server(timeout_sec=timeout_sec)


def parse_adb_devices_output(text: str) -> List[MobileDevice]:
    devices: List[MobileDevice] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        props: Dict[str, str] = {}
        for token in parts[2:]:
            if ":" in token:
                key, val = token.split(":", 1)
                props[key] = val
        kind = "emulator" if serial.startswith("emulator-") else "physical"
        devices.append(
            MobileDevice(
                id=serial,
                state=state,
                kind=kind,
                model=props.get("model"),
                product=props.get("product"),
            )
        )
    return devices


def list_devices(*, adb_tool: Optional[AndroidTool] = None) -> Tuple[List[MobileDevice], Optional[str]]:
    tool = adb_tool or resolve_adb()
    if not tool.path:
        return [], "adb no encontrado. Instala Android SDK platform-tools o define ELIA_ADB_PATH."
    try:
        proc = _run_cmd([tool.path, "devices", "-l"], timeout=15)
    except Exception as exc:
        return [], f"No se pudo ejecutar adb devices: {exc}"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return [], err or "adb devices falló"
    return parse_adb_devices_output(proc.stdout or ""), None


def list_avds(*, emulator_tool: Optional[AndroidTool] = None) -> Tuple[List[str], Optional[str]]:
    tool = emulator_tool or resolve_emulator()
    if not tool.path:
        return [], "emulator no encontrado. Instala Android Emulator o define ANDROID_HOME."
    try:
        proc = _run_emulator_cmd(tool.path, ["-list-avds"], timeout=20)
    except Exception as exc:
        return [], f"No se pudo listar AVDs: {exc}"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return [], err or "emulator -list-avds falló"
    avds = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return avds, None


def device_boot_completed(device_id: str, *, adb_tool: Optional[AndroidTool] = None) -> bool:
    tool = adb_tool or resolve_adb()
    if not tool.path or not device_id.strip():
        return False
    try:
        proc = _run_cmd(
            [tool.path, "-s", device_id.strip(), "shell", "getprop", "sys.boot_completed"],
            timeout=10,
        )
        return proc.returncode == 0 and (proc.stdout or "").strip() == "1"
    except Exception:
        return False


def wait_for_emulator_device(
    *,
    timeout_sec: float = 180.0,
    poll_sec: float = 2.0,
    adb_tool: Optional[AndroidTool] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Espera a que aparezca un emulador online en adb. Devuelve (device_id, error)."""
    deadline = time.monotonic() + timeout_sec
    last_err: Optional[str] = None
    while time.monotonic() < deadline:
        devices, err = list_devices(adb_tool=adb_tool)
        if err:
            last_err = err
        for dev in devices:
            if dev.kind == "emulator" and dev.state == "device":
                return dev.id, None
        time.sleep(poll_sec)
    return None, last_err or "Tiempo de espera agotado: ningún emulador visible en adb devices"


def wait_for_boot(
    device_id: str,
    *,
    timeout_sec: float = 180.0,
    poll_sec: float = 2.0,
    adb_tool: Optional[AndroidTool] = None,
) -> Tuple[bool, Optional[str]]:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        devices, _ = list_devices(adb_tool=adb_tool)
        match = next((d for d in devices if d.id == device_id), None)
        if match and match.state != "device":
            time.sleep(poll_sec)
            continue
        if device_boot_completed(device_id, adb_tool=adb_tool):
            return True, None
        time.sleep(poll_sec)
    return False, "El emulador no terminó de arrancar (sys.boot_completed ≠ 1)"


def start_emulator(
    avd: str,
    *,
    wait_boot: bool = True,
    timeout_sec: float = 180.0,
) -> Dict[str, Any]:
    avd = (avd or "").strip()
    if not avd:
        return {"ok": False, "message": "Nombre de AVD requerido", "device_id": None}

    emulator_tool = resolve_emulator()
    if not emulator_tool.path:
        return {
            "ok": False,
            "message": "No se encontró el ejecutable emulator.",
            "device_id": None,
            "hint": "Instala Android Emulator desde Android Studio y define ANDROID_HOME o ELIA_ANDROID_HOME.",
        }

    layout_err = _validate_emulator_layout(emulator_tool.path)
    if layout_err:
        return {
            "ok": False,
            "message": layout_err,
            "device_id": None,
            "emulator_exe": emulator_tool.path,
        }

    launch_meta = {
        "emulator_exe": emulator_tool.path,
        "emulator_cwd": _emulator_home_dir(emulator_tool.path),
        "emulator_source": emulator_tool.source,
        "launcher": "cmd_cd" if sys.platform == "win32" else "direct",
        "elia_emulator_path": _get_env_var("ELIA_EMULATOR_PATH"),
        "android_home": _get_env_var("ANDROID_HOME"),
    }

    adb_tool = resolve_adb()
    devices, _ = list_devices(adb_tool=adb_tool)
    online_emulators = [d for d in devices if d.kind == "emulator" and d.state == "device"]
    if online_emulators:
        device_id = online_emulators[0].id
        if wait_boot:
            boot_ok, boot_err = wait_for_boot(device_id, timeout_sec=timeout_sec, adb_tool=adb_tool)
            if not boot_ok:
                return {"ok": False, "message": boot_err or "Boot incompleto", "device_id": device_id}
        return {
            "ok": True,
            "message": "Emulador ya conectado en adb.",
            "device_id": device_id,
            "reused": True,
            "launch": launch_meta,
        }

    try:
        _popen_emulator(emulator_tool.path, ["-avd", avd])
    except Exception as exc:
        return {
            "ok": False,
            "message": f"No se pudo iniciar el emulador: {exc}",
            "device_id": None,
            "launch": launch_meta,
        }

    device_id, wait_err = wait_for_emulator_device(timeout_sec=timeout_sec, adb_tool=adb_tool)
    if not device_id:
        return {
            "ok": False,
            "message": wait_err or "Emulador no detectado",
            "device_id": None,
            "launch": launch_meta,
            "hint": (
                "Si aparecen errores de DLL de qemu-system-x86_64.exe, reinicie ELIA tras "
                "guardar variables de entorno y verifique emulator.exe (no el binario qemu)."
            ),
        }

    if wait_boot:
        boot_ok, boot_err = wait_for_boot(device_id, timeout_sec=timeout_sec, adb_tool=adb_tool)
        if not boot_ok:
            return {"ok": False, "message": boot_err or "Boot incompleto", "device_id": device_id}

    return {
        "ok": True,
        "message": "Emulador listo.",
        "device_id": device_id,
        "reused": False,
        "launch": launch_meta,
    }


def stop_emulator(device_id: Optional[str] = None) -> Dict[str, Any]:
    adb_tool = resolve_adb()
    if not adb_tool.path:
        return {"ok": False, "message": "adb no encontrado", "stopped": []}

    targets: List[str] = []
    if device_id and device_id.strip():
        targets = [device_id.strip()]
    else:
        devices, _ = list_devices(adb_tool=adb_tool)
        targets = [d.id for d in devices if d.kind == "emulator" and d.state == "device"]

    if not targets:
        return {"ok": True, "message": "No hay emuladores activos.", "stopped": []}

    stopped: List[str] = []
    errors: List[str] = []
    for dev in targets:
        try:
            proc = _run_cmd([adb_tool.path, "-s", dev, "emu", "kill"], timeout=15)
            if proc.returncode == 0:
                stopped.append(dev)
            else:
                errors.append((proc.stderr or proc.stdout or "").strip() or f"emu kill falló para {dev}")
        except Exception as exc:
            errors.append(str(exc))

    ok = bool(stopped) and not errors
    msg = "Emulador detenido." if ok else ("; ".join(errors) if errors else "No se pudo detener el emulador.")
    return {"ok": ok or bool(stopped), "message": msg, "stopped": stopped, "errors": errors}


def assert_device_online(device_id: str) -> Optional[Tuple[str, str]]:
    """Devuelve (message, details) si el dispositivo no está listo; None si OK."""
    dev_id = (device_id or "").strip()
    if not dev_id:
        return ("Dispositivo requerido", "Indica un ID de adb devices (físico o emulador).")

    adb_tool = resolve_adb()
    if not adb_tool.path:
        return (
            "adb no encontrado",
            "Instala Android SDK platform-tools o define ELIA_ADB_PATH / ANDROID_HOME.",
        )

    devices, err = list_devices(adb_tool=adb_tool)
    if err:
        return ("Error al listar dispositivos", err)

    match = next((d for d in devices if d.id == dev_id), None)
    if not match:
        known = ", ".join(d.id for d in devices) or "(ninguno)"
        return (
            "Dispositivo no encontrado",
            f"No aparece «{dev_id}» en adb devices.\n\nConectados: {known}",
        )
    if match.state != "device":
        return (
            "Dispositivo no listo",
            f"«{dev_id}» está en estado «{match.state}». Autoriza depuración USB o espera a que el emulador termine de arrancar.",
        )
    if match.kind == "emulator" and not device_boot_completed(dev_id, adb_tool=adb_tool):
        return (
            "Emulador arrancando",
            "Espera a que el emulador termine de iniciar (sys.boot_completed = 1) e inténtalo de nuevo.",
        )
    return None


_LAUNCHER_PACKAGES = frozenset(
    {
        "com.android.launcher",
        "com.android.launcher3",
        "com.google.android.apps.nexuslauncher",
        "com.sec.android.app.launcher",
        "com.miui.home",
        "com.huawei.android.launcher",
        "com.oppo.launcher",
        "com.bbk.launcher2",
    }
)


def _is_launcher_or_system_shell(package: str) -> bool:
    pkg = (package or "").strip().lower()
    if not pkg:
        return True
    if pkg in _LAUNCHER_PACKAGES:
        return True
    if pkg.startswith("com.android.systemui"):
        return True
    return False


def _parse_focus_candidates(text: str) -> List[Tuple[str, str]]:
    """Extrae pares (package, activity) de salidas dumpsys (varias versiones Android)."""
    candidates: List[Tuple[str, str]] = []
    patterns = (
        r"topResumedActivity=ActivityRecord\{[^ ]+ u\d+ ([^\s/]+)/([^\s}\]]+)",
        r"mResumedActivity: ActivityRecord\{[^ ]+ u\d+ ([^\s/]+)/([^\s}\]]+)",
        r"ResumedActivity: ActivityRecord\{[^ ]+ u\d+ ([^\s/]+)/([^\s}\]]+)",
        r"mFocusedApp=ActivityRecord\{[^ ]+ u\d+ ([^\s/]+)/([^\s}\]]+)",
        r"mCurrentFocus=Window\{[^ ]+ u\d+ ([^\s/]+)/([^\s}\]]+)",
    )
    for pat in patterns:
        for match in re.finditer(pat, text or ""):
            pkg = match.group(1).strip()
            act = match.group(2).strip()
            if pkg and act:
                candidates.append((pkg, act))
    return candidates


def _pick_foreground_candidate(candidates: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    for pkg, act in candidates:
        if not _is_launcher_or_system_shell(pkg):
            return pkg, act
    return candidates[0] if candidates else None


def detect_foreground_package(device_id: str) -> Dict[str, Any]:
    """
    Detecta la app en primer plano vía adb dumpsys.
    Devuelve {ok, package, activity, error, source}.
    """
    dev_id = (device_id or "").strip()
    if not dev_id:
        return {
            "ok": False,
            "package": None,
            "activity": None,
            "error": "Indica el dispositivo adb.",
            "source": None,
        }

    device_err = assert_device_online(dev_id)
    if device_err:
        msg, details = device_err
        return {
            "ok": False,
            "package": None,
            "activity": None,
            "error": f"{msg}. {details}" if details else msg,
            "source": None,
        }

    adb_tool = resolve_adb()
    if not adb_tool.path:
        return {
            "ok": False,
            "package": None,
            "activity": None,
            "error": "adb no encontrado.",
            "source": None,
        }

    adb_base = [adb_tool.path, "-s", dev_id, "shell"]
    blobs: List[str] = []
    for args in (["dumpsys", "activity", "activities"], ["dumpsys", "window"]):
        try:
            proc = _run_cmd(adb_base + args, timeout=20)
            chunk = (proc.stdout or "") + (proc.stderr or "")
            if chunk.strip():
                blobs.append(chunk)
        except Exception:
            continue

    if not blobs:
        return {
            "ok": False,
            "package": None,
            "activity": None,
            "error": "No se pudo leer dumpsys del dispositivo.",
            "source": None,
        }

    picked = _pick_foreground_candidate(_parse_focus_candidates("\n".join(blobs)))
    if not picked:
        return {
            "ok": False,
            "package": None,
            "activity": None,
            "error": (
                "No se detectó ninguna app en primer plano. "
                "Abre la app en el móvil (no la pantalla de inicio) o indica el paquete manualmente."
            ),
            "source": None,
        }

    pkg, act = picked
    if _is_launcher_or_system_shell(pkg):
        return {
            "ok": False,
            "package": None,
            "activity": None,
            "error": (
                f"Solo se detectó el launcher ({pkg}). "
                "Abre la app que quieres grabar y vuelve a intentarlo."
            ),
            "source": "launcher",
        }

    return {
        "ok": True,
        "package": pkg,
        "activity": act,
        "error": None,
        "source": "dumpsys",
    }


def collect_env_hints() -> Dict[str, Optional[str]]:
    sdk, sdk_src = resolve_android_sdk()
    adb = resolve_adb()
    emulator = resolve_emulator()
    emu_dir = _emulator_home_dir(emulator.path) if emulator.path else None
    layout_err = _validate_emulator_layout(emulator.path) if emulator.path else None
    return {
        "elia_android_home": _get_env_var("ELIA_ANDROID_HOME"),
        "android_home": _get_env_var("ANDROID_HOME"),
        "android_sdk_root": _get_env_var("ANDROID_SDK_ROOT"),
        "elia_adb_path": _get_env_var("ELIA_ADB_PATH"),
        "elia_emulator_path": _get_env_var("ELIA_EMULATOR_PATH"),
        "resolved_sdk": sdk,
        "resolved_sdk_source": sdk_src,
        "resolved_adb": adb.path,
        "resolved_emulator": emulator.path,
        "resolved_emulator_cwd": emu_dir,
        "emulator_layout_ok": layout_err is None,
        "emulator_layout_error": layout_err,
        "elia_appium_path": _get_env_var("ELIA_APPIUM_PATH"),
        "appium_url": appium_url(),
    }


def run_diagnostics() -> Dict[str, Any]:
    sdk, sdk_src = resolve_android_sdk()
    adb = resolve_adb()
    emulator = resolve_emulator()
    devices, devices_err = list_devices(adb_tool=adb)
    avds, avds_err = list_avds(emulator_tool=emulator)
    appium_tool = resolve_appium()
    host, port = appium_endpoint()
    appium_running = check_appium_server(host, port)
    return {
        "ok": bool(adb.path) and appium_running and any(d.state == "device" for d in devices),
        "platform": sys.platform,
        "android_only": True,
        "sdk": {"path": sdk, "source": sdk_src},
        "tools": {
            "adb": adb.to_dict(),
            "emulator": emulator.to_dict(),
            "appium": appium_tool.to_dict(),
        },
        "appium": {
            "ok": appium_running,
            "installed": bool(appium_tool.path),
            "url": appium_url(host, port),
        },
        "devices": [d.to_dict() for d in devices],
        "devices_error": devices_err,
        "avds": avds,
        "avds_error": avds_err,
        "env": collect_env_hints(),
    }


def run_preflight() -> MobilePreflightResult:
    env = collect_env_hints()
    warnings: List[str] = []
    errors: List[str] = []
    items: List[Dict[str, Any]] = []

    sdk, sdk_src = resolve_android_sdk()
    sdk_ok = bool(sdk)
    items.append(
        {
            "id": "android_sdk",
            "label": "Android SDK",
            "ok": sdk_ok,
            "message": sdk or "No detectado",
            "hint": "Define ANDROID_HOME, ELIA_ANDROID_HOME o instala Android Studio.",
        }
    )
    if not sdk_ok:
        errors.append("Android SDK no detectado.")

    adb = resolve_adb()
    items.append(
        {
            "id": "adb",
            "label": "adb (platform-tools)",
            "ok": bool(adb.path),
            "message": adb.path or "No encontrado",
            "hint": "Añade platform-tools al PATH o define ELIA_ADB_PATH.",
        }
    )
    if not adb.path:
        errors.append("adb no encontrado.")

    emulator = resolve_emulator()
    items.append(
        {
            "id": "emulator",
            "label": "Android Emulator",
            "ok": bool(emulator.path),
            "message": emulator.path or "No encontrado",
            "hint": "Instala el paquete Emulator en Android Studio SDK Manager.",
        }
    )
    if not emulator.path:
        warnings.append(
            "No se detectó Android Emulator: solo podrás usar dispositivo físico. "
            "Instala Android Emulator o define ANDROID_HOME."
        )

    appium_tool = resolve_appium()
    host, port = appium_endpoint()
    appium_running = check_appium_server(host, port)
    items.append(
        {
            "id": "appium",
            "label": "Appium Server (:4723)",
            "ok": appium_running,
            "message": (
                "Accesible"
                if appium_running
                else (appium_tool.path or "No responde en :4723")
            ),
            "hint": (
                "Pulsa «Iniciar Appium» en esta pantalla."
                if appium_tool.path and not appium_running
                else "npm install -g appium && appium driver install uiautomator2"
            ),
            "installed": bool(appium_tool.path),
            "running": appium_running,
        }
    )
    if not appium_tool.path:
        errors.append("Appium no instalado o no encontrado en PATH.")
    elif not appium_running:
        warnings.append("Appium instalado pero no responde en :4723. Inícialo desde ELIA o manualmente.")

    devices, devices_err = list_devices(adb_tool=adb)
    online = [d for d in devices if d.state == "device"]
    avds, avds_err = list_avds(emulator_tool=emulator)
    device_ok = bool(online)
    items.append(
        {
            "id": "device",
            "label": "Dispositivo adb online",
            "ok": device_ok,
            "message": ", ".join(d.id for d in online) if online else (devices_err or "Ninguno"),
            "hint": "Conecta USB/Wi‑Fi adb o inicia un emulador.",
        }
    )
    if emulator.path:
        from core.ui_automation.mobile_avd_wizard import cmdline_tools_ready

        ct = cmdline_tools_ready()
        items.append(
            {
                "id": "cmdline_tools",
                "label": "SDK Command-line Tools",
                "ok": ct["ok"],
                "message": "sdkmanager + avdmanager" if ct["ok"] else "No detectados",
                "hint": "Android Studio → SDK Manager → SDK Tools → Android SDK Command-line Tools.",
            }
        )
        avd_catalog_ok = bool(avds)
        items.append(
            {
                "id": "avd_catalog",
                "label": "Catálogo AVD (SDK)",
                "ok": avd_catalog_ok,
                "message": (
                    ", ".join(avds[:5]) + ("…" if len(avds) > 5 else "")
                    if avds
                    else (avds_err or "Vacío")
                ),
                "hint": "Usa «Asistente AVD», abre Android Studio o pulsa «Comprobar de nuevo».",
            }
        )
        if not avd_catalog_ok and not device_ok:
            warnings.append(
                "No hay AVDs en el catálogo del SDK ni dispositivos adb online. "
                "Crea un AVD o conecta un dispositivo físico."
            )
        elif avds_err and not avds:
            warnings.append(avds_err)

    if sdk_src == "localappdata":
        warnings.append("SDK detectado en %LOCALAPPDATA%\\Android\\Sdk.")

    ok = not errors
    return MobilePreflightResult(ok=ok, items=items, warnings=warnings, errors=errors, env=env)
