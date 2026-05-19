# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import glob
import os
import sys

# SPECPATH is the directory that contains the spec file (set by PyInstaller).
# Do NOT apply os.path.dirname — it is already the project root.
# Fallback: cwd, which build_release.py forces to ROOT before calling PyInstaller.
_spec_root = os.path.abspath(globals().get("SPECPATH", os.getcwd()))
sys.path.insert(0, _spec_root)

from PyInstaller.utils.hooks import collect_all, collect_submodules

from core._cython_build_manifest import CYTHON_REL_PATHS

# Extensiones Cython (tras: python setup_cython.py build_ext --inplace)
_cython_globs = sorted(
    set(
        glob.glob(os.path.join(_spec_root, "core", "*.pyd"))
        + glob.glob(os.path.join(_spec_root, "core", "*.so"))
        + glob.glob(os.path.join(_spec_root, "core", "**", "*.pyd"), recursive=True)
        + glob.glob(os.path.join(_spec_root, "core", "**", "*.so"), recursive=True)
    )
)
cython_binaries = []
for _cyd in _cython_globs:
    _rel = os.path.relpath(_cyd, _spec_root).replace("\\", "/")
    _parent = os.path.dirname(_rel)
    _bundle_dest = _parent.replace("\\", "/") if _parent else "core"
    cython_binaries.append((_rel, _bundle_dest))

# Recorder: en release usar solo el ofuscado (el plano queda en el repo para desarrollo, no en el exe).
# recorder.js ahora vive en core/ui_automation/ → se bundlea en core/ui_automation/ dentro del exe.
_obf = os.path.join('core', 'ui_automation', 'recorder.obfuscated.js')
if os.path.isfile(_obf):
    js_obf = [(_obf, 'core/ui_automation')]
else:
    # Sin build de ofuscación: incluir recorder.js como respaldo para que el exe no quede sin motor.
    _plain = os.path.join('core', 'ui_automation', 'recorder.js')
    js_obf = [(_plain, 'core/ui_automation')] if os.path.isfile(_plain) else []


def _datas_if_exists(*entries):
    """
    Incluye cada (src, dst) en datas solo si la ruta src existe en el repo.
    Si falta, emite un aviso y la omite para no abortar el build.
    Esto permite compilar sin el build del frontend (frontend/dist) u otros
    artefactos opcionales que se generan en pasos separados del pipeline.
    """
    result = []
    for src, dst in entries:
        full = os.path.join(_spec_root, src.replace("/", os.sep))
        if os.path.exists(full):
            result.append((src, dst))
        else:
            print(f"[ELIA.spec] AVISO: omitiendo datas faltante → {src}")
    return result

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

integrations_hidden = [
    # core raíz — módulos Cython compilados directamente en core/
    "core.elia_paths",
    "core.elia_license",
    "core.elia_memory",
    "core.modules_config",
    # core/ui_automation/ — módulos Cython compilados
    "core.ui_automation",
    "core.ui_automation.puppeteer_script_converter",
    "core.ui_automation.step_by_step_converter",
    "core.ui_automation.flow_analyzer",
    "core.ui_automation.locator_healer",
    "core.ui_automation.node_wrapper",
    "core.ui_automation.recorder_focus",
    "core.ui_automation.video_recorder",
    "core.ui_automation.mobile_recorder",
    "core.ui_automation.legacy_recorder",
    # core/req_intelligence/ — módulos Cython compilados
    "core.req_intelligence",
    "core.req_intelligence.jira_extractor",
    "core.req_intelligence.value_edge_extractor",
    "core.req_intelligence.gherkin_converter",
    "core.req_intelligence.integrations_config_loader",
    "core.req_intelligence.connectors_profiles_store",
    "core.req_intelligence.integrations_service",
    "core.req_intelligence.doc_ingestion",
    "core.req_intelligence.bdd_doc_converter",
    "core.req_intelligence.feature_scanner",
    # NOTA: los alias retrocompatibles (core.jira_extractor, core.flow_analyzer, etc.)
    # son proxies lazy registrados en sys.modules por core/__init__.py en tiempo de
    # ejecución. NO son archivos .pyd reales; PyInstaller no puede encontrarlos
    # estáticamente, por lo que NO deben listarse aquí.
]

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
    datas=_datas_if_exists(
        ('core/node',       'core/node'),
        ('frontend/dist',   'frontend/dist'),   # generado con: npm run build (en frontend/)
        ('resources',       'resources'),
    ) + llama_datas + js_obf,
    hiddenimports=['mss', 'cv2', 'numpy', 'core.elia_license'] + web_hidden + llama_hidden + integrations_hidden + crypto_hidden,
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