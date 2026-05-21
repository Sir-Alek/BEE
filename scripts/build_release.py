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

from core._cython_build_manifest import (
    CYTHON_REL_PATHS,
    NON_CYTHON_PY_FILENAMES,
    NON_CYTHON_RUNTIME_REL_PATHS,
    verify_core_manifest_coverage,
)

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
    remove_stale_non_cython_native()


def remove_stale_non_cython_native() -> None:
    """Borra .pyd/.so obsoletos de módulos excluidos del manifiesto Cython."""
    import glob

    for py_name in sorted(NON_CYTHON_PY_FILENAMES):
        base = os.path.splitext(py_name)[0]
        patterns = [
            os.path.join(CORE, f"{base}*.pyd"),
            os.path.join(CORE, f"{base}*.so"),
            os.path.join(CORE, "**", f"{base}*.pyd"),
            os.path.join(CORE, "**", f"{base}*.so"),
        ]
        for pattern in patterns:
            for path in glob.glob(pattern, recursive=True):
                try:
                    os.remove(path)
                    print(f"OK Eliminado (no va a Cython): {os.path.relpath(path, ROOT)}")
                except OSError as e:
                    print(f"AVISO: no se pudo eliminar {path}: {e}", file=sys.stderr)


def remove_stale_version_native() -> None:
    """Compatibilidad: delega en remove_stale_non_cython_native()."""
    remove_stale_non_cython_native()


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


def verify_manifest_covers_core(strict: bool = True) -> list[str]:
    """Cada .py de core/ debe estar en CYTHON o en la lista de exclusión."""
    missing = verify_core_manifest_coverage()
    if missing and strict:
        print("ERROR: Módulos core/ sin clasificar en el manifiesto:", file=sys.stderr)
        for rel in missing:
            print(f"   - {rel}", file=sys.stderr)
        raise SystemExit(1)
    return missing


def _find_in_dist(rel_posix: str) -> list[str]:
    """Busca un archivo relativo al repo dentro de dist/ELIA/ (core o _internal/core)."""
    hits: list[str] = []
    rel_os = rel_posix.replace("/", os.sep)
    for core_root in _dist_core_roots():
        candidate = os.path.join(core_root, os.path.relpath(rel_os, "core"))
        if os.path.isfile(candidate):
            hits.append(candidate)
    return hits


def verify_dist_bundle(strict: bool = True) -> None:
    """
    Tras PyInstaller + strip:
      - Los módulos Cython no deben quedar como .py (solo .pyd/.so + __init__.py).
      - Los módulos runtime excluidos de Cython deben conservar su .py.
      - Cada módulo Cython debe tener extensión nativa en dist/.
    """
    roots = _dist_core_roots()
    if not roots:
        msg = "dist/ELIA/.../core no encontrado; ejecuta PyInstaller antes de verificar."
        if strict:
            print(f"ERROR: {msg}", file=sys.stderr)
            raise SystemExit(1)
        print(f"AVISO: {msg}")
        return

    errors: list[str] = []

    for rel_py in CYTHON_REL_PATHS:
        for hit in _find_in_dist(rel_py):
            errors.append(f"Quedó .py de módulo Cython en el bundle: {os.path.relpath(hit, ROOT)}")
        rel_native = os.path.splitext(rel_py)[0]
        native_hits: list[str] = []
        for core_root in roots:
            parent = os.path.join(core_root, os.path.relpath(rel_native, "core"))
            parent_dir = os.path.dirname(parent)
            base = os.path.basename(parent)
            if not os.path.isdir(parent_dir):
                continue
            for fn in os.listdir(parent_dir):
                stem, ext = os.path.splitext(fn)
                if stem.split(".")[0] == base and ext.lower() in (".pyd", ".so"):
                    native_hits.append(os.path.join(parent_dir, fn))
        if not native_hits:
            errors.append(f"Falta extensión nativa en dist/ para {rel_py}")

    for rel_py in NON_CYTHON_RUNTIME_REL_PATHS:
        if not _find_in_dist(rel_py):
            errors.append(f"Falta .py runtime (no Cython) en dist/: {rel_py}")

    if errors and strict:
        print("ERROR: Verificación del bundle dist/ELIA:", file=sys.stderr)
        for err in errors:
            print(f"   - {err}", file=sys.stderr)
        raise SystemExit(1)
    elif errors:
        for err in errors:
            print(f"AVISO bundle: {err}")


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
                if fn in NON_CYTHON_PY_FILENAMES:
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
    verify_manifest_covers_core(strict=True)
    print(f"Manifiesto Cython: {len(CYTHON_REL_PATHS)} modulo(s) -> .pyd/.so en el exe")
    for rel in CYTHON_REL_PATHS:
        print(f"  · {rel}")
    print(
        f"Runtime sin Cython: {len(NON_CYTHON_RUNTIME_REL_PATHS)} modulo(s) -> .py en el exe"
    )
    for rel in NON_CYTHON_RUNTIME_REL_PATHS:
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
            verify_dist_bundle(strict=True)
        elif args.no_cython:
            print("AVISO: Sin strip: --no-cython activo.")

    print("build_release completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
