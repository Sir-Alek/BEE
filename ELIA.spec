# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import glob
import os
import sys

# SPECPATH is set by PyInstaller when loading the .spec file.
_spec_root = os.path.dirname(os.path.abspath(globals().get("SPECPATH", os.path.join(os.getcwd(), "ELIA.spec"))))
sys.path.insert(0, _spec_root)

from PyInstaller.utils.hooks import collect_all, collect_submodules

from core._cython_build_manifest import CYTHON_REL_PATHS

# Extensiones Cython (tras: python setup_cython.py build_ext --inplace)
_cython_globs = glob.glob(os.path.join('core', '*.pyd')) + glob.glob(os.path.join('core', '*.so'))
cython_binaries = [(p, 'core') for p in _cython_globs]

# Recorder: en release usar solo el ofuscado (el plano queda en el repo para desarrollo, no en el exe).
_obf = os.path.join('core', 'recorder.obfuscated.js')
if os.path.isfile(_obf):
    js_obf = [(_obf, 'core')]
else:
    # Sin build de ofuscación: incluir recorder.js como respaldo para que el exe no quede sin motor.
    _plain = os.path.join('core', 'recorder.js')
    js_obf = [(_plain, 'core')] if os.path.isfile(_plain) else []

# Si hay .pyd, no empaquetar el mismo módulo como .py en el archivo (preferir nativo).
_cython_excludes = []
if cython_binaries:
    _cython_excludes = [p.replace("\\", "/").removesuffix(".py").replace("/", ".") for p in CYTHON_REL_PATHS]

# Web UI deps are imported conditionally and need help for PyInstaller.
web_hidden = []
for pkg in ("fastapi", "uvicorn", "starlette", "pydantic", "httpx"):
    try:
        web_hidden += collect_submodules(pkg)
    except Exception:
        web_hidden.append(pkg)

elia_hidden = []
try:
    elia_hidden = collect_submodules("elia")
except Exception:
    elia_hidden = ["elia", "elia.core", "elia.config_loader", "elia.connectors_store", "elia.service"]

crypto_hidden = []
try:
    crypto_hidden = collect_submodules("cryptography")
except Exception:
    crypto_hidden = ["cryptography", "cryptography.fernet"]

# llama-cpp-python: native libs + package data
llama_datas, llama_binaries, llama_hidden = [], [], []
try:
    llama_datas, llama_binaries, llama_hidden = collect_all("llama_cpp")
except Exception:
    llama_hidden = ["llama_cpp", "llama_cpp.lib"]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=llama_binaries + cython_binaries,
    datas=[
        ('core/node', 'core/node'),
        ('behave', 'behave'),
        ('frontend/dist', 'frontend/dist'),
        ('resources', 'resources'),
        ('step_by_step', 'step_by_step')
    ] + llama_datas + js_obf,
    hiddenimports=['mss', 'cv2', 'numpy', 'core.bee_license'] + web_hidden + llama_hidden + elia_hidden + crypto_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_cython_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Para PyInstaller >= 4.0
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Para PyInstaller < 4.0 (si la línea anterior falla)
# pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ELIA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/logo_elia.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ELIA',
)