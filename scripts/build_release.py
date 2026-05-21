#!/usr/bin/env python3
"""
Pipeline de release: Cython + ofuscación JS + PyInstaller + sin .py de core en dist/.

Uso (raíz del repo):
  python scripts/build_release.py              # Cython + JS + PyInstaller (recomendado)
  python scripts/build_release.py --no-cython  # solo JS + PyInstaller (no para entregas)
  python scripts/build_release.py --no-pyinstaller  # solo Cython + JS

Requisitos:
  - pip: pyinstaller, cython
  - MSVC build tools (Windows) para Cython
  - npx javascript-obfuscator (opcional)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CORE = os.path.join(ROOT, "core")
CORE_UI = os.path.join(CORE, "ui_automation")
OBFUSCATED_JS = os.path.join(CORE_UI, "recorder.obfuscated.js")
SOURCE_RECORDER = os.path.join(CORE_UI, "recorder.js")

from core._cython_build_manifest import CYTHON_REL_PATHS

# Solo estos .py pueden quedar en dist/ELIA/.../core (marcadores de paquete).
_KEEP_PY_NAMES = frozenset({"__init__.py"})


def run(cmd: list[str], cwd: str | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def _native_extension_exists(py_path: str) -> bool:
    parent = os.path.dirname(py_path)
    base_noext = os.path.splitext(os.path.basename(py_path))[0]
    try:
        names = os.listdir(parent)
    except OSError:
        return False
    for fn in names:
        stem, ext = os.path.splitext(fn)
        if stem.split(".")[0] != base_noext:
            continue
        if ext.lower() in (".pyd", ".so"):
            return True
    return False


def build_cython() -> None:
    run([sys.executable, "setup_cython.py", "build_ext", "--inplace"])
    remove_stale_version_native()


def remove_stale_version_native() -> None:
    """version.py no se compila; un .pyd antiguo oculta bumps de ELIA_VERSION."""
    import glob

    for pattern in (
        os.path.join(CORE, "version*.pyd"),
        os.path.join(CORE, "version*.so"),
    ):
        for path in glob.glob(pattern):
            try:
                os.remove(path)
                print(f"OK Eliminado (version no va a Cython): {os.path.relpath(path, ROOT)}")
            except OSError as e:
                print(f"AVISO: no se pudo eliminar {path}: {e}", file=sys.stderr)


def verify_cython_artifacts(strict: bool = True) -> list[str]:
    """Comprueba que cada módulo del manifiesto tenga .pyd/.so junto al .py en el repo."""
    missing: list[str] = []
    for rel_py in CYTHON_REL_PATHS:
        src = os.path.join(ROOT, rel_py.replace("/", os.sep))
        if not os.path.isfile(src):
            missing.append(f"{rel_py} (fuente .py no encontrada)")
            continue
        if not _native_extension_exists(src):
            missing.append(rel_py)
    if missing and strict:
        print("ERROR: Faltan extensiones Cython (.pyd/.so) para:", file=sys.stderr)
        for m in missing:
            print(f"   - {m}", file=sys.stderr)
        print(
            "   Ejecuta: python setup_cython.py build_ext --inplace",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return missing


def obfuscate_recorder() -> None:
    if not os.path.isfile(SOURCE_RECORDER):
        print("AVISO: No existe core/ui_automation/recorder.js; se omite ofuscación.")
        return
    npx = shutil.which("npx")
    if not npx:
        print("AVISO: npx no encontrado; copiando recorder.js sin ofuscar -> recorder.obfuscated.js")
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
                "false",
                "--dead-code-injection",
                "false",
                "--string-array",
                "false",
                "--identifier-names-generator",
                "hexadecimal",
                "--rename-globals",
                "false",
            ]
        )
        print(f"OK Generado {OBFUSCATED_JS}")
    except subprocess.CalledProcessError:
        print("AVISO: javascript-obfuscator falló; copiando recorder.js sin ofuscar.")
        shutil.copy2(SOURCE_RECORDER, OBFUSCATED_JS)


def _dist_core_roots() -> list[str]:
    """PyInstaller 6+ usa dist/ELIA/_internal/core; versiones antiguas dist/ELIA/core."""
    roots: list[str] = []
    for sub in ("_internal/core", "core"):
        p = os.path.join(ROOT, "dist", "ELIA", sub.replace("/", os.sep))
        if os.path.isdir(p):
            roots.append(p)
    return roots


def strip_py_from_dist() -> None:
    """
    Elimina del bundle todos los .py de core/ que tengan extensión nativa compilada.
    Conserva solo __init__.py. Retira _cython_build_manifest.py si se coló en el dist.
    """
    manifest_py_names = {os.path.basename(p) for p in CYTHON_REL_PATHS}
    removed = 0
    warned_missing_native: list[str] = []

    for dist_core in _dist_core_roots():
        for dirpath, _dirnames, filenames in os.walk(dist_core):
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                if fn in _KEEP_PY_NAMES:
                    continue
                py_path = os.path.join(dirpath, fn)
                if fn == "_cython_build_manifest.py":
                    try:
                        os.remove(py_path)
                        print(f"OK Retirado del bundle: {py_path}")
                        removed += 1
                    except OSError as e:
                        print(f"AVISO: No se pudo eliminar {py_path}: {e}")
                    continue
                if _native_extension_exists(py_path):
                    try:
                        os.remove(py_path)
                        rel = os.path.relpath(py_path, ROOT)
                        print(f"OK Retirado del bundle: {rel} (existe .pyd/.so)")
                        removed += 1
                    except OSError as e:
                        print(f"AVISO: No se pudo eliminar {py_path}: {e}")
                elif fn in manifest_py_names:
                    warned_missing_native.append(py_path)

    if warned_missing_native:
        print(
            "AVISO: En dist/ quedaron .py del manifiesto Cython sin .pyd/.so emparejado:",
            file=sys.stderr,
        )
        for p in warned_missing_native[:12]:
            print(f"   - {os.path.relpath(p, ROOT)}", file=sys.stderr)
        if len(warned_missing_native) > 12:
            print(f"   ... y {len(warned_missing_native) - 12} más", file=sys.stderr)

    print(f"OK strip_py_from_dist: {removed} archivo(s) .py retirado(s) del bundle.")


def report_manifest() -> None:
    print(f"Manifiesto Cython: {len(CYTHON_REL_PATHS)} módulo(s) en core/")
    for rel in CYTHON_REL_PATHS:
        print(f"  · {rel}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build release: Cython + JS + PyInstaller")
    ap.add_argument(
        "--no-cython",
        action="store_true",
        help="No compilar Cython (solo desarrollo; el exe llevará .py de core)",
    )
    ap.add_argument("--no-pyinstaller", action="store_true", help="No ejecutar PyInstaller")
    ap.add_argument(
        "--no-strip-py",
        action="store_true",
        help="No borrar .py del dist (depuración)",
    )
    args = ap.parse_args()

    os.chdir(ROOT)
    report_manifest()

    if not args.no_cython:
        build_cython()
        verify_cython_artifacts(strict=True)
    else:
        print("AVISO: --no-cython: el ejecutable puede incluir fuentes .py de core.")

    obfuscate_recorder()

    if not args.no_pyinstaller:
        if not args.no_cython:
            verify_cython_artifacts(strict=True)
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", "ELIA.spec"])
        if not args.no_strip_py and not args.no_cython:
            strip_py_from_dist()
        elif args.no_cython:
            print("AVISO: Sin strip: --no-cython activo.")

    print("build_release completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
