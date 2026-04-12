"""
Compila módulos críticos de core/ a extensiones nativas (.pyd / .so).

Uso (Windows, desde la raíz del repo, con MSVC build tools + Cython):
  pip install cython setuptools
  python setup_cython.py build_ext --inplace

Genera p.ej. core/puppeteer_script_converter.*.pyd junto al .py.
En el empaquetado de release, el script scripts/build_release.py puede apartar los .py
para que el ejecutable solo incluya los .pyd.
"""
from __future__ import annotations

import sys

from setuptools import Extension, setup

try:
    from Cython.Build import cythonize
except ImportError as e:
    raise SystemExit("Instala Cython: pip install cython") from e

from core._cython_build_manifest import CYTHON_REL_PATHS

# Módulos a compilar (rutas relativas al directorio del proyecto).
CYTHON_MODULES = list(CYTHON_REL_PATHS)

compiler_directives = {"language_level": "3", "embedsignature": False}

extensions = [
    Extension(
        name=".".join(path[:-3].split("/")),  # core.puppeteer_script_converter
        sources=[path],
    )
    for path in CYTHON_MODULES
]

setup(
    name="bee_cython_extensions",
    ext_modules=cythonize(
        extensions,
        compiler_directives=compiler_directives,
        annotate=False,
    ),
    zip_safe=False,
)
