#!/usr/bin/env python3
"""
Pipeline de release: Cython (opcional) + ofuscación JS + PyInstaller + retirada de .py duplicados en dist/.

Uso (raíz del repo):
  python scripts/build_release.py              # solo JS + PyInstaller
  python scripts/build_release.py --cython     # compila .pyd antes
  python scripts/build_release.py --no-pyinstaller  # solo Cython + JS

Requisitos:
  - pip: pyinstaller, cython (si --cython)
  - npx javascript-obfuscator (o npm install en ./scripts con el paquete)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CORE = os.path.join(ROOT, "core")
OBFUSCATED_JS = os.path.join(CORE, "recorder.obfuscated.js")
SOURCE_RECORDER = os.path.join(CORE, "recorder.js")

# Mismos módulos que setup_cython.py; al empaquetar se pueden borrar los .py del dist si existe .pyd
CYTHON_SOURCE_PY = [
    "puppeteer_script_converter.py",
    "video_recorder.py",
    "step_by_step_converter.py",
]


def run(cmd: list[str], cwd: str | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def build_cython() -> None:
    run([sys.executable, "setup_cython.py", "build_ext", "--inplace"])


def obfuscate_recorder() -> None:
    if not os.path.isfile(SOURCE_RECORDER):
        print("⚠ No existe core/recorder.js; se omite ofuscación.")
        return
    # javascript-obfuscator vía npx (sin package.json obligatorio)
    npx = shutil.which("npx")
    if not npx:
        print("⚠ npx no encontrado; copiando recorder.js sin ofuscar -> recorder.obfuscated.js")
        shutil.copy2(SOURCE_RECORDER, OBFUSCATED_JS)
        return
    try:
        run(
            [
                npx,
                "--yes",
                "javascript-obfuscator",
                SOURCE_RECORDER,
                "--output",
                OBFUSCATED_JS,
                "--compact",
                "true",
                "--control-flow-flattening",
                "true",
                "--dead-code-injection",
                "true",
                "--string-array",
                "true",
            ]
        )
        print(f"✓ Generado {OBFUSCATED_JS}")
    except subprocess.CalledProcessError:
        print("⚠ javascript-obfuscator falló; copiando recorder.js sin ofuscar.")
        shutil.copy2(SOURCE_RECORDER, OBFUSCATED_JS)


def strip_py_from_dist_if_pyd() -> None:
    """Quita .py del paquete core en dist/ si hay .pyd del mismo nombre (release sin fuente duplicada)."""
    dist_core = os.path.join(ROOT, "dist", "BEE", "core")
    if not os.path.isdir(dist_core):
        return
    for name in CYTHON_SOURCE_PY:
        base = name[:-3]
        py_path = os.path.join(dist_core, name)
        if not os.path.isfile(py_path):
            continue
        # ¿Hay algún .pyd para este módulo?
        found_pyd = False
        for fn in os.listdir(dist_core):
            if fn.startswith(base + ".") and fn.endswith(".pyd"):
                found_pyd = True
                break
        if found_pyd:
            try:
                os.remove(py_path)
                print(f"✓ Retirado del bundle: core/{name} (existe extensión compilada)")
            except OSError as e:
                print(f"⚠ No se pudo eliminar {py_path}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build release: Cython + JS + PyInstaller")
    ap.add_argument("--cython", action="store_true", help="Ejecutar setup_cython.py build_ext --inplace")
    ap.add_argument("--no-pyinstaller", action="store_true", help="No ejecutar PyInstaller")
    ap.add_argument("--no-strip-py", action="store_true", help="No borrar .py del dist si hay .pyd")
    args = ap.parse_args()

    os.chdir(ROOT)

    if args.cython:
        build_cython()

    obfuscate_recorder()

    if not args.no_pyinstaller:
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", "BEE.spec"])
        if not args.no_strip_py:
            strip_py_from_dist_if_pyd()

    print("✅ build_release completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
