"""
Visual test of Settings Dialog - показывает диалог на 30 секунд
"""
import tkinter as tk
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gui.settings_dialog import SettingsDialog

def main():
    """Визуальный тест диалога настроек"""
    root = tk.Tk()
    root.title("BAZA Trading Bot - Settings Test")
    root.geometry("400x300")
    
    label = tk.Label(root, text="Click button to open Settings Dialog\n\nCheck all 5 tabs:\n• Trading\n• AI\n• Strategy\n• GPT API\n• Telegram", 
                    font=('Arial', 12), pady=20)
    label.pack()
    
    def open_settings():
        print("\n=== Opening Settings Dialog ===")
        print("✓ Trading tab - risk management")
        print("✓ AI tab - GPT model, schedule")
        print("✓ Strategy tab - stop loss, take profit")
        print("✓ GPT API tab - OpenAI API key")
        print("✓ Telegram tab - bot token, notifications")
        print("================================\n")
        
        def on_save():
            print("\n[CALLBACK] Settings saved!")
            print("[CALLBACK] Configs updated:")
            print("  - ai.yaml")
            print("  - portfolio.yaml")
            print("  - telegram.yaml")
            print("  - .env (OPENAI_API_KEY)\n")
        
        SettingsDialog(root, on_save_callback=on_save)
        print("\n=== Dialog closed ===\n")
    
    button = tk.Button(root, text="Open Settings", 
                      font=('Arial', 14, 'bold'),
                      command=open_settings,
                      bg='#2196F3', fg='white',
                      padx=20, pady=10)
    button.pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    main()
