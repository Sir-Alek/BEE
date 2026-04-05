# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import glob
from PyInstaller.utils.hooks import collect_submodules

enc_datas = [(p, 'core') for p in glob.glob('core/*.enc')]

# Web UI deps are imported conditionally and need help for PyInstaller.
web_hidden = []
for pkg in ("fastapi", "uvicorn", "starlette", "pydantic", "httpx"):
    try:
        web_hidden += collect_submodules(pkg)
    except Exception:
        web_hidden.append(pkg)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('core/node', 'core/node'),
        ('behave', 'behave'),
        ('frontend/dist', 'frontend/dist'),
        ('resources', 'resources'),
        ('step_by_step', 'step_by_step')
    ] + enc_datas,
    hiddenimports=['mss', 'cv2', 'numpy'] + web_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='BEE',
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
    icon='resources/logo_bee_png_transparente.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BEE',
)