#!/usr/bin/env python3
"""
Test GUI initialization (without mainloop)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_gui():
    print("[GUI] TESTING GUI")
    print("=" * 30)

    try:
        from src.gui.app import BazaApp

        print("[APP] Creating GUI application...")
        app = BazaApp()

        print("[OK] GUI initialized")
        print(f"[STATS] Statistics loaded: {len(app.app_state.stats)} parameters")
        print(f"[AI] GPT setting: {'Enabled' if app.enable_gpt else 'Disabled'}")

        # Проверяем лицензию
        from src.core.license import license_manager
        valid, msg = license_manager.is_valid()
        status = "[VALID] Valid" if valid else "[INVALID] Invalid"
        print(f"[LICENSE] License: {status}")

        print("\n[SUCCESS] GUI READY TO WORK!")

        # Не запускаем mainloop, просто проверяем инициализацию
        return True

    except Exception as e:
        print(f"[ERROR] GUI Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_gui()