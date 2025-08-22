import os
import base64
import zlib
import glob

def advanced_obfuscate(file_path):
    """Ofuscación avanzada con compresión + base64"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 1. Comprimir
        compressed = zlib.compress(content, level=9)
        # 2. Codificar en base64
        obfuscated = base64.b64encode(compressed)
        
        # Escribir archivo ofuscado
        with open(file_path + '.enc', 'wb') as f:
            f.write(b'# BEE_PROTECTED\n')
            f.write(obfuscated)
        
        # No eliminar el archivo original durante el desarrollo
        # os.remove(file_path)
        print(f"✓ {file_path} protegido")
        
    except Exception as e:
        print(f"✗ Error: {file_path} - {str(e)}")


def protect_core_advanced():
    """Protección avanzada de toda la carpeta core"""
    files_to_protect = []
    files_to_protect.extend(glob.glob('core/**/*.py', recursive=True))
    files_to_protect.extend(glob.glob('core/**/*.js', recursive=True))
    
    # Excluir archivos del sistema
    exclude = ['__init__.py', 'node_wrapper.py', '__loader.py']
    files_to_protect = [f for f in files_to_protect if os.path.basename(f) not in exclude]
    
    # Asegurar que los archivos críticos están incluidos
    critical_files = [
        'core/puppeteer_script_converter.py',
        'core/video_recorder.py',
        'core/recorder.js',
        'core/__dynamic_importer.py'  # Si decides ofuscarlo también
    ]
    
    for file in critical_files:
        if os.path.exists(file) and file not in files_to_protect:
            files_to_protect.append(file)
    
    for file_path in files_to_protect:
        advanced_obfuscate(file_path)
    
    print("✅ Protección avanzada completada")

if __name__ == '__main__':
    protect_core_advanced()