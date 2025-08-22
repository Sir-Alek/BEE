import os
import base64
import zlib
import importlib.util
import sys

class Deobfuscator:
    _instance = None
    _cache = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_file(self, relative_path):
        """Carga y desofusca archivos con ZLIB + B64 - Versión mejorada para PyInstaller"""
        if relative_path in self._cache:
            return self._cache[relative_path]
        
        try:
            # Para PyInstaller - manejar rutas correctamente
            if getattr(sys, 'frozen', False):
                # En modo empaquetado, los archivos están en sys._MEIPASS
                base_path = getattr(sys, '_MEIPASS', '')
                
                # DEBUG: Información del entorno
                debug_info = [
                    f"FROZEN: {getattr(sys, 'frozen', False)}",
                    f"_MEIPASS: {getattr(sys, '_MEIPASS', 'No definido')}",
                    f"executable: {getattr(sys, 'executable', 'No definido')}",
                    f"argv[0]: {sys.argv[0] if len(sys.argv) > 0 else 'No argv'}",
                    f"cwd: {os.getcwd()}"
                ]
                
                # Buscar en múltiples ubicaciones posibles
                possible_locations = [
                    # 1. En _MEIPASS/core/
                    os.path.join(base_path, 'core', relative_path + '.enc'),
                    # 2. En _MEIPASS/ directamente
                    os.path.join(base_path, relative_path + '.enc'),
                    # 3. Junto al ejecutable en core/
                    os.path.join(os.path.dirname(sys.executable), 'core', relative_path + '.enc'),
                    # 4. En el directorio de trabajo en core/
                    os.path.join(os.getcwd(), 'core', relative_path + '.enc'),
                ]
                
                # Añadir ubicaciones de desarrollo para debug
                dev_locations = [
                    os.path.join(os.path.dirname(__file__), relative_path + '.enc'),
                    os.path.join(os.path.dirname(__file__), relative_path),
                ]
                possible_locations.extend(dev_locations)
                
                enc_file_path = None
                for location in possible_locations:
                    if os.path.exists(location):
                        enc_file_path = location
                        debug_info.append(f"ENCONTRADO: {location}")
                        break
                    else:
                        debug_info.append(f"NO ENCONTRADO: {location}")
                
                # Escribir información de debug
                # try:
                #     debug_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
                #     debug_file = os.path.join(debug_dir, "deobfuscator_debug.txt")
                #     with open(debug_file, "a", encoding='utf-8') as f:
                #         f.write(f"\n=== Buscando: {relative_path} ===\n")
                #         for line in debug_info:
                #             f.write(line + "\n")
                #         f.write(f"Archivo seleccionado: {enc_file_path}\n")
                # except Exception as debug_error:
                #     pass
                
                if not enc_file_path:
                    raise FileNotFoundError(f"No se encontró {relative_path} en ninguna ubicación posible")
                
            else:
                # Modo desarrollo
                enc_file_path = os.path.join(os.path.dirname(__file__), relative_path + '.enc')
            
            # Leer y desofuscar el archivo
            if os.path.exists(enc_file_path):
                with open(enc_file_path, 'rb') as f:
                    lines = f.readlines()
                    if len(lines) >= 2 and b'BEE_PROTECTED' in lines[0]:
                        encoded_content = lines[1].strip()
                        # 1. Decodificar base64
                        decoded_b64 = base64.b64decode(encoded_content)
                        # 2. Descomprimir zlib
                        original_content = zlib.decompress(decoded_b64)
                        self._cache[relative_path] = original_content
                        return original_content
            
            # Si llegamos aquí, no se encontró el archivo
            raise FileNotFoundError(f"No se pudo encontrar o desofuscar: {relative_path}")
                    
        except Exception as e:
            # Log del error para diagnóstico
            try:
                debug_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
                error_file = os.path.join(debug_dir, "deobfuscator_error.txt")
                with open(error_file, "a", encoding='utf-8') as f:
                    f.write(f"Error loading {relative_path}: {str(e)}\n")
                    f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                    f.write(f"MEIPASS: {getattr(sys, '_MEIPASS', 'None')}\n")
                    f.write(f"Executable: {getattr(sys, 'executable', 'None')}\n")
            except:
                pass
            raise
        
        return None

# Funciones globales
def get_core_file(file_name):
    return Deobfuscator.get_instance().load_file(file_name)