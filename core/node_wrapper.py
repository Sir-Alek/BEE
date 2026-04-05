import os
import tempfile
import subprocess
import sys
import shutil

class NodeJSWrapper:
    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
    
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
            
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp(prefix='bee_')
            self.temp_dirs.append(temp_dir)
            
            # Escribir el contenido desofuscado en un archivo temporal
            temp_file = os.path.join(temp_dir, js_file_name)
            with open(temp_file, 'wb') as f:
                f.write(content)
            
            # COPIAR TODA la carpeta node completa
            node_src = os.path.join(os.path.dirname(__file__), 'node')
            node_dst = os.path.join(temp_dir, 'node')
            
            if os.path.exists(node_src):
                shutil.copytree(node_src, node_dst)
                print(f"✓ Carpeta node completa copiada a temporal")
            
            # Obtener ruta de Node.js
            node_path = self.get_node_path()
            
            # Configurar environment
            env = os.environ.copy()
            
            # Ejecutar el archivo JavaScript con los argumentos
            print(f"Ejecutando Node.js desde: {temp_dir}")
            cmd = [node_path, temp_file] + args
            print(f"Comando: {' '.join(cmd)}")

            if focus_automation_browser:
                from core.recorder_focus import run_subprocess_with_automation_focus

                result = run_subprocess_with_automation_focus(
                    cmd,
                    cwd=temp_dir,
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
                    cwd=temp_dir,
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