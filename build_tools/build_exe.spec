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
        # Include telegram_bot config
        (str(project_root / 'telegram_bot' / 'config.json'), 'telegram_bot'),
        # Include telegram library
        ('D:\\Lib\\site-packages\\telegram', 'telegram'),
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
        # Telegram bot dependencies
        'telegram',
        'telegram.ext',
        'telegram._bot',
        'telegram._update',
        'telegram.ext._application',
        'telegram.ext._commandhandler',
        'telegram.ext._contexttypes',
        'asyncio',
        'httpx',
        'httpcore',
        'h11',
        'anyio',
        'certifi',
    ],
    hookspath=[str(project_root / 'build_tools')],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SMC_Trading_Framework',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'build_tools' / 'app_icon.ico'),  # Application icon
)

# COLLECT removed - using onefile mode
