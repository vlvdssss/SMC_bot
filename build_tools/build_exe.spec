# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for SMC Trading Framework GUI

import sys
from pathlib import Path

# Get the project root directory
project_root = Path('c:/Users/kamsa/Desktop/SMC-framework')

block_cipher = None

# Analysis - collect all Python files and dependencies
a = Analysis(
    [str(project_root / 'gui' / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include data directories
        (str(project_root / 'gui' / 'data'), 'gui/data'),
        # Include any other resources if needed
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'MetaTrader5',
        'pandas',
        'numpy',
        'logging',
        'json',
        'datetime',
        'threading',
        'queue',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'jupyter',
        'IPython',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SMC_Trading_Framework',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window - GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'build_tools' / 'app_icon.ico'),  # Application icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SMC_Trading_Framework',
)
