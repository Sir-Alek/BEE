import os
import tempfile
import subprocess
import sys
import shutil
import time

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
            or os.path.join(tempfile.gettempdir(), "bee-cache")
        )
        d = os.path.join(base, "BEE", "node_runtime")
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

        node_src = os.path.join(os.path.dirname(__file__), "node")
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

        self._runtime_prepared = True
        return runtime_dir

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

            # Escribir el JS dentro del runtime para que Node resuelva require() desde ahí
            # (NODE_PATH puede ignorarse/filtrarse en algunas instalaciones corporativas).
            js_run_dir = os.path.join(runtime_dir, "_js")
            os.makedirs(js_run_dir, exist_ok=True)
            temp_file = os.path.join(js_run_dir, js_file_name)
            with open(temp_file, "wb") as f:
                f.write(content)
            
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
                from core.recorder_focus import run_subprocess_with_automation_focus

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
                # Filtrar errores de módulo no encontrado
                if "MODULE_NOT_FOUND" in error_msg:
                    error_msg = "Puppeteer no está instalado correctamente. Ejecuta install_puppeteer.bat"
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

        core_node_path = os.path.join(os.path.dirname(__file__), 'node', 'node.exe')
        if os.path.exists(core_node_path):
            return core_node_path
        
        local_node_path = os.path.join(os.path.dirname(__file__), 'node.exe')
        if os.path.exists(local_node_path):
            return local_node_path
        
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