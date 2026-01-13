#!/usr/bin/env python3
"""
Build BAZA Trading Bot EXE
"""

import PyInstaller.__main__
import shutil
from pathlib import Path

print("=" * 60)
print("Building BAZA Trading Bot EXE...")
print("=" * 60)

# Clean old build (ignore errors if locked by Windows)
try:
    if Path("build").exists():
        shutil.rmtree("build")
except Exception as e:
    print(f"Warning: Could not remove build folder: {e}")

# Remove old EXE file only
try:
    exe_file = Path("dist/BAZA_TradingBot.exe")
    if exe_file.exists():
        exe_file.unlink()
        print("Removed old EXE")
except Exception as e:
    print(f"Warning: Could not remove old EXE: {e}")

# Build EXE
PyInstaller.__main__.run([
    'main.py',
    '--name=BAZA_TradingBot',
    '--onefile',
    '--windowed',
    '--icon=icon.ico',
    '--exclude-module=matplotlib.tests',
    '--exclude-module=torch',
    '--exclude-module=scipy._lib.array_api_compat.torch',
    '--add-data=config;config',
    '--add-data=data;data',
    '--add-data=src;src',
    '--hidden-import=MetaTrader5',
    '--hidden-import=openai',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=yaml',
    '--hidden-import=tkinter',
    '--hidden-import=customtkinter',
    '--hidden-import=PIL',
    '--hidden-import=matplotlib',
    '--hidden-import=sklearn',
    '--hidden-import=joblib',
    '--hidden-import=requests',
    '--hidden-import=dotenv',
    '--hidden-import=lightgbm',
    '--hidden-import=scipy',
    '--hidden-import=scipy._lib',
    '--hidden-import=scipy._lib.array_api_compat',
    '--hidden-import=scipy._lib.array_api_compat.numpy',
    '--hidden-import=scipy._lib.array_api_compat.numpy.fft',
    '--hidden-import=scipy.special',
    '--hidden-import=scipy.special._cdflib',
    '--hidden-import=src.ai.analyst_scheduler',
    '--hidden-import=src.ai.signal_manager',
    '--hidden-import=src.ai.market_analyst',
    '--hidden-import=src.ai.screenshot_analyzer',
    '--hidden-import=src.manual_trading.controller',
    '--hidden-import=src.manual_trading.ai_analyzer',
    '--hidden-import=src.manual_trading.calculator',
    '--hidden-import=src.manual_trading.validator',
    '--collect-all=customtkinter',
    '--collect-all=PIL',
    '--collect-all=matplotlib',
    '--collect-all=scipy',
    '--collect-all=lightgbm',
    '--noconfirm',
])

print("\n" + "=" * 60)
print("✓ Build complete!")
print("EXE location: dist/BAZA_TradingBot.exe")
print("=" * 60)
