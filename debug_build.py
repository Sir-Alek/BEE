#!/usr/bin/env python3
import os
import sys


def debug_build():
    """Diagnóstico: archivos en dist/ELIA/core y carga de recorder (plano / ofuscado)."""
    dist_path = os.path.join("dist", "ELIA")

    print("🔍 Iniciando diagnóstico...")
    print(f"Ruta de distribución: {dist_path}")

    print("\n📁 Archivos en core/:")
    core_path = os.path.join(dist_path, "core")
    if os.path.exists(core_path):
        for item in sorted(os.listdir(core_path))[:80]:
            item_path = os.path.join(core_path, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                print(f"  {item} ({size} bytes)")
            else:
                print(f"  {item}/ (directorio)")
                # Listar subcarpetas relevantes (ui_automation, req_intelligence)
                if item in ("ui_automation", "req_intelligence"):
                    try:
                        for sub in sorted(os.listdir(item_path))[:40]:
                            sub_path = os.path.join(item_path, sub)
                            sub_size = os.path.getsize(sub_path) if os.path.isfile(sub_path) else 0
                            indicator = "✅" if sub.endswith((".pyd", ".so")) else ("⚠" if sub.endswith(".py") else " ")
                            print(f"    {indicator} {sub} ({sub_size} bytes)")
                    except OSError:
                        pass
    else:
        print("❌ No existe la carpeta core/")
        return False

    original_meipass = getattr(sys, "_MEIPASS", None)
    sys._MEIPASS = dist_path

    try:
        from core import get_core_file

        print("\n🧪 get_core_file('recorder.js')...")
        try:
            content = get_core_file("recorder.js")
            print(f"  ✅ OK - {len(content)} bytes")
        except Exception as e:
            print(f"  ❌ {e}")
    except Exception as e:
        print(f"❌ Error importando: {e}")
        return False
    finally:
        if original_meipass is None:
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = original_meipass

    return True


if __name__ == "__main__":
    debug_build()
