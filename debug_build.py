#!/usr/bin/env python3
import os
import sys

def debug_build():
    """Script de diagnóstico para el sistema de desofuscación"""
    dist_path = os.path.join('dist', 'BEE')
    
    print("🔍 Iniciando diagnóstico...")
    print(f"Ruta de distribución: {dist_path}")
    
    # Verificar estructura de archivos
    print("\n📁 Estructura de archivos en core/:")
    core_path = os.path.join(dist_path, 'core')
    if os.path.exists(core_path):
        for item in os.listdir(core_path):
            item_path = os.path.join(core_path, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                print(f"  {item} ({size} bytes)")
            else:
                print(f"  {item}/ (directorio)")
    else:
        print("❌ No existe la carpeta core/")
        return False
    
    # Simular el entorno de PyInstaller
    print("\n🔧 Simulando entorno PyInstaller...")
    original_meipass = getattr(sys, '_MEIPASS', None)
    
    # Establecer _MEIPASS para simular
    sys._MEIPASS = dist_path
    
    try:
        # Probar desofuscación
        from core import get_core_file
        
        print("\n🧪 Probando desofuscación...")
        files_to_test = ['recorder.js', 'puppeteer_script_converter.py', 'step_by_step_converter.py', 'video_recorder.py']
        
        for file in files_to_test:
            try:
                print(f"  Probando: {file}")
                content = get_core_file(file)
                if content:
                    print(f"    ✅ OK - {len(content)} bytes")
                else:
                    print(f"    ❌ Contenido nulo")
            except Exception as e:
                print(f"    ❌ Error: {str(e)}")
                
    except Exception as e:
        print(f"❌ Error importando módulos: {e}")
        return False
    finally:
        # Restaurar _MEIPASS original
        if original_meipass is None:
            if hasattr(sys, '_MEIPASS'):
                delattr(sys, '_MEIPASS')
        else:
            sys._MEIPASS = original_meipass
    
    # Verificar archivo de debug
    debug_file = os.path.join(core_path, "debug_load.txt")
    if os.path.exists(debug_file):
        print(f"\n📋 Contenido de debug_load.txt:")
        with open(debug_file, 'r') as f:
            for line in f:
                print(f"  {line.strip()}")
    
    return True

if __name__ == '__main__':
    debug_build()