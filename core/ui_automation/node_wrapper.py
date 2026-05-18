import os
import tempfile
import subprocess
import sys
import shutil
import time
import uuid

class NodeJSWrapper:
    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
        self._runtime_dir = None
        self._runtime_prepared = False
    
    def _get_runtime_dir(self) -> str:
        """
        Runtime dir for executing bundled Node + node_modules.
        In frozen builds, copying the ~100MB+ node folder per run is very slow,
        so we prepare a cached runtime directory once and reuse it.
        """
        if self._runtime_dir:
            return self._runtime_dir

        # Prefer a stable per-user cache location.
        base = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or os.path.join(tempfile.gettempdir(), "elia-cache")
        )
        d = os.path.join(base, "ELIA", "node_runtime")
        os.makedirs(d, exist_ok=True)
        self._runtime_dir = d
        return d

    def _ensure_runtime_prepared(self) -> str:
        """
        Ensure the node runtime folder exists and contains `node/` with node.exe and node_modules.
        Returns the working directory for running JS (the runtime dir).
        """
        runtime_dir = self._get_runtime_dir()
        if self._runtime_prepared:
            return runtime_dir

        # node/ lives at core/node/ — one level above core/ui_automation/ (this file's location).
        # os.path.dirname(__file__) = .../core/ui_automation/
        # os.path.dirname(os.path.dirname(__file__)) = .../core/
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        node_src = os.path.join(os.path.dirname(_this_dir), "node")
        # Fallback: if packaged differently, also check same directory
        if not os.path.isdir(node_src):
            node_src = os.path.join(_this_dir, "node")
        node_dst = os.path.join(runtime_dir, "node")

        # If already prepared (e.g. previous run), skip heavy copy.
        if os.path.exists(os.path.join(node_dst, "node.exe")) and os.path.isdir(os.path.join(node_dst, "node_modules")):
            # Sanity-check: puppeteer must exist; otherwise runtime is incomplete/corrupted.
            if os.path.exists(os.path.join(node_dst, "node_modules", "puppeteer")) or os.path.exists(
                os.path.join(node_dst, "node_modules", "puppeteer-core")
            ):
                self._runtime_prepared = True
                return runtime_dir
            # Corrupted/incomplete runtime cache -> rebuild.
            try:
                shutil.rmtree(node_dst, ignore_errors=True)
            except Exception:
                pass
            self._runtime_prepared = True
            return runtime_dir

        # Fresh prepare (heavy copy once).
        if os.path.exists(node_src):
            # Remove partial destination to avoid corrupted runtimes.
            try:
                shutil.rmtree(node_dst, ignore_errors=True)
            except Exception:
                pass
            start = time.perf_counter()
            shutil.copytree(node_src, node_dst)
            elapsed = time.perf_counter() - start
            print(f"✓ Runtime Node preparado en: {node_dst}")
            print(f"⏱ Preparación runtime Node: {elapsed:.2f}s")
        else:
            # Fallback: will try system node later.
            print("⚠ No se encontró core/node; se intentará usar Node.js del sistema.")

        # Install npm dependencies (puppeteer, webdriver-manager) if not present.
        # This runs once and the result is cached in runtime_dir.
        self._install_node_dependencies(node_dst)

        self._runtime_prepared = True
        return runtime_dir

    def _install_node_dependencies(self, node_dst: str) -> None:
        """
        Runs `npm install` inside node_dst if puppeteer is not already present.
        This is a one-time setup step; the result is cached in the runtime dir.
        """
        puppeteer_dir = os.path.join(node_dst, "node_modules", "puppeteer")
        puppeteer_core_dir = os.path.join(node_dst, "node_modules", "puppeteer-core")
        if os.path.isdir(puppeteer_dir) or os.path.isdir(puppeteer_core_dir):
            return  # Already installed

        pkg_json = os.path.join(node_dst, "package.json")
        if not os.path.isfile(pkg_json):
            print("⚠ No se encontró package.json en el runtime Node; omitiendo npm install.")
            return

        # Prefer system npm (the bundled npm.cmd needs its own node_modules/npm).
        system_npm = shutil.which("npm")
        npm_candidates = [c for c in [system_npm] if c]

        if not npm_candidates:
            print("⚠ npm no encontrado en el sistema. Instala Node.js LTS para habilitar la grabación.")
            return

        npm_cmd = npm_candidates[0]
        print("⏳ Instalando dependencias Node (puppeteer) por primera vez…")
        print(f"   Directorio: {node_dst}")
        print("   Esto puede tardar varios minutos la primera vez.")
        try:
            env = os.environ.copy()
            env["PATH"] = node_dst + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                [npm_cmd, "install", "--no-audit", "--no-fund"],
                cwd=node_dst,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,  # 10 min máx
            )
            if result.returncode == 0:
                print("✓ Dependencias Node instaladas correctamente.")
            else:
                print(f"⚠ npm install terminó con código {result.returncode}:")
                if result.stderr:
                    print(result.stderr[:1000])
        except subprocess.TimeoutExpired:
            print("⚠ npm install tardó demasiado (>10 min). Reintenta manualmente:")
            print(f"   cd \"{node_dst}\" && npm install")
        except Exception as exc:
            print(f"⚠ npm install falló: {exc}")
            print(f"   Ejecuta manualmente: cd \"{node_dst}\" && npm install")

    def run_obfuscated_js(
        self,
        js_file_name,
        args=None,
        *,
        subprocess_timeout=180,
        focus_automation_browser: bool = False,
    ):
        """Ejecuta un archivo JavaScript ofuscado.

        subprocess_timeout: None = sin límite (recomendado para recorder largo).
        focus_automation_browser: intenta enfocar el navegador que abre Puppeteer (Windows).
        """
        if args is None:
            args = []
        
        try:
            # Usar el sistema de desofuscación para obtener el contenido
            from core import get_core_file
            content = get_core_file(js_file_name)
            
            if not content:
                # Fallback para desarrollo
                original_path = os.path.join(os.path.dirname(__file__), js_file_name)
                if os.path.exists(original_path):
                    with open(original_path, 'rb') as f:
                        content = f.read()
                else:
                    raise FileNotFoundError(f"Archivo JavaScript '{js_file_name}' no encontrado")

            # Preparar runtime (caché) para evitar copiar core/node en cada ejecución.
            runtime_dir = self._ensure_runtime_prepared()
            node_modules_dir = os.path.join(runtime_dir, "node", "node_modules")

            # Escribir el JS en runtime_dir/ui_automation/ de modo que __dirname sea
            # ese subdirectorio y `path.join(__dirname, '..', 'node', ...)` resuelva
            # correctamente a runtime_dir/node/ (igual que en desarrollo donde
            # recorder.js está en core/ui_automation/ y node/ está en core/node/).
            _js_subdir = os.path.join(runtime_dir, "ui_automation")
            os.makedirs(_js_subdir, exist_ok=True)
            temp_file = os.path.join(_js_subdir, f"_elia_{uuid.uuid4().hex}_{js_file_name}")
            with open(temp_file, "wb") as f:
                f.write(content)
            self.temp_files.append(temp_file)
            
            # Obtener ruta de Node.js
            node_path = self.get_node_path()
            
            # Configurar environment
            env = os.environ.copy()
            # Ensure Node can resolve puppeteer from the cached runtime.
            # Node's module resolution is based on the script location, not cwd; use NODE_PATH.
            if os.path.isdir(node_modules_dir):
                prev_node_path = env.get("NODE_PATH", "")
                env["NODE_PATH"] = node_modules_dir + (os.pathsep + prev_node_path if prev_node_path else "")
                # Some setups require explicit NODE_PATH enabling.
                env.setdefault("NODE_OPTIONS", "")
                if "--preserve-symlinks" not in env["NODE_OPTIONS"]:
                    env["NODE_OPTIONS"] = (env["NODE_OPTIONS"] + " --preserve-symlinks").strip()
            # Also add bundled node folder to PATH (helps in some Windows setups).
            node_bin_dir = os.path.join(runtime_dir, "node")
            if os.path.isdir(node_bin_dir):
                prev_path = env.get("PATH", "")
                env["PATH"] = node_bin_dir + (os.pathsep + prev_path if prev_path else "")
            
            # Ejecutar el archivo JavaScript con los argumentos
            # For frozen/runtime: execute with cwd=runtime_dir so node_modules resolve.
            print(f"Ejecutando Node.js desde runtime: {runtime_dir}")
            cmd = [node_path, temp_file] + args
            print(f"Comando: {' '.join(cmd)}")

            if focus_automation_browser:
                from core.ui_automation.recorder_focus import run_subprocess_with_automation_focus

                result = run_subprocess_with_automation_focus(
                    cmd,
                    cwd=runtime_dir,
                    env=env,
                    timeout=subprocess_timeout,
                )
            else:
                run_kw = dict(
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    cwd=runtime_dir,
                )
                if subprocess_timeout is not None:
                    run_kw["timeout"] = subprocess_timeout
                result = subprocess.run(cmd, **run_kw)
        
            
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print("Node:", line.strip())
            
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip() and "MODULE_NOT_FOUND" not in line:
                        print("Node Error:", line.strip())
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Error desconocido en Node.js"
                if "MODULE_NOT_FOUND" in error_msg:
                    runtime_node = os.path.join(self._get_runtime_dir(), "node")
                    error_msg = (
                        "Puppeteer no está instalado. "
                        f"Ejecuta: cd \"{runtime_node}\" && npm install"
                    )
                raise Exception(f"Error en Node.js: {error_msg}")
            
            return result
            
        except subprocess.TimeoutExpired:
            raise Exception("Timeout: Puppeteer tardó demasiado en ejecutarse (ajusta subprocess_timeout o usa None para grabaciones largas)")
        except Exception as e:
            raise Exception(f"Error ejecutando Node.js: {str(e)}")
    
    def get_node_path(self):
        """Obtener la ruta de node.exe"""
        # Prefer cached runtime node.exe when available
        try:
            runtime_dir = self._ensure_runtime_prepared()
            cached_node = os.path.join(runtime_dir, "node", "node.exe")
            if os.path.exists(cached_node):
                return cached_node
        except Exception:
            pass

        # core/node/ is one level above core/ui_automation/ (this file)
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        core_node_path = os.path.join(os.path.dirname(_this_dir), 'node', 'node.exe')
        if os.path.exists(core_node_path):
            return core_node_path

        # Fallback: node.exe in same directory as this file
        local_node_path = os.path.join(_this_dir, 'node', 'node.exe')
        if os.path.exists(local_node_path):
            return local_node_path

        alt_node_path = os.path.join(_this_dir, 'node.exe')
        if os.path.exists(alt_node_path):
            return alt_node_path
        
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return 'node'
        except:
            pass
        
        raise FileNotFoundError("Node.js no encontrado")
    
    def cleanup(self):
        """Limpiar archivos temporales"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
        
        self.temp_files = []
        self.temp_dirs = []

# Instancia global
node_wrapper = NodeJSWrapper()