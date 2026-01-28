"""
Тест Settings Dialog с новыми вкладками GPT API и Telegram
"""
import tkinter as tk
import sys
from pathlib import Path

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.gui.settings_dialog import SettingsDialog

def main():
    """Тест диалога настроек"""
    root = tk.Tk()
    root.withdraw()  # Скрыть главное окно
    
    print("Opening Settings Dialog...")
    print("Check all 5 tabs: Trading, AI, Strategy, GPT API, Telegram")
    
    def on_save():
        print("Settings saved callback!")
    
    dialog = SettingsDialog(root, on_save_callback=on_save)
    
    print("Dialog closed")
    root.destroy()

if __name__ == "__main__":
    main()
