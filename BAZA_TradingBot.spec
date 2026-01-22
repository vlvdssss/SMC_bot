# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('config', 'config'), ('data', 'data'), ('src', 'src')]
binaries = []
hiddenimports = ['MetaTrader5', 'openai', 'pandas', 'numpy', 'yaml', 'tkinter', 'customtkinter', 'PIL', 'matplotlib', 'sklearn', 'joblib', 'requests', 'dotenv', 'lightgbm', 'scipy', 'scipy._lib', 'scipy._lib.array_api_compat', 'scipy._lib.array_api_compat.numpy', 'scipy._lib.array_api_compat.numpy.fft', 'scipy.special', 'scipy.special._cdflib', 'src.ai.analyst_scheduler', 'src.ai.signal_manager', 'src.ai.market_analyst', 'src.ai.screenshot_analyzer', 'src.manual_trading.controller', 'src.manual_trading.ai_analyzer', 'src.manual_trading.calculator', 'src.manual_trading.validator']
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('matplotlib')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('scipy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('lightgbm')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib.tests', 'torch', 'scipy._lib.array_api_compat.torch'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BAZA_TradingBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
