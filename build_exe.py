"""
Сборка BAZA Trading Bot в exe файл.

Запуск: python build_exe.py
Результат: dist/BAZA.exe
"""

import PyInstaller.__main__
import os
import shutil

def build():
    print("=" * 50)
    print("СБОРКА BAZA TRADING BOT")
    print("=" * 50)

    # Очищаем старые сборки
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # Параметры сборки
    PyInstaller.__main__.run([
        'main.py',
        '--name=BAZA',
        '--onefile',
        '--windowed',
        '--icon=assets/icon.ico',  # Если есть иконка
        '--add-data=config;config',
        '--add-data=src;src',
        '--hidden-import=src.gui.app',
        '--hidden-import=src.live.live_trader',
        '--hidden-import=src.strategies',
        '--hidden-import=src.ml',
        '--hidden-import=src.ai',
        '--clean',
    ])

    print("\n" + "=" * 50)
    print("✅ ГОТОВО!")
    print("Файл: dist/BAZA.exe")
    print("=" * 50)


if __name__ == '__main__':
    build()