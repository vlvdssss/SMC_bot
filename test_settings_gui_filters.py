"""
Quick test: Open Settings GUI and check Filters tab
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import tkinter as tk
from src.gui.dialogs_v2 import SettingsDialog

def test_settings_gui():
    """Open Settings dialog with Filters tab"""
    
    print("=" * 60)
    print("TEST: Settings GUI with Filters Tab")
    print("=" * 60)
    print()
    print("Opening Settings dialog...")
    print()
    print("Expected to see:")
    print("  • Trading tab")
    print("  • Risk tab")
    print("  • ✨ Filters tab (NEW!)")
    print("  • AI tab")
    print("  • Logging tab")
    print("  • Advanced tab")
    print()
    print("In Filters tab, should see 12 parameters:")
    print("  1. Trade Filters Enabled (checkbox)")
    print("  2. Min Confidence % (75)")
    print("  3. Min Setup Score (70)")
    print("  4. Min Risk/Reward (1.2)")
    print("  5. Max Spread pips (3.0)")
    print("  6. Daily Trade Limit (6)")
    print("  7. Cooldown After Win (15 min)")
    print("  8. Cooldown After Loss (90 min)")
    print("  9. Cooldown After 2 Losses (240 min)")
    print("  10. HTF Timeframe (M15)")
    print("  11. HTF EMA Fast (50)")
    print("  12. HTF EMA Slow (200)")
    print()
    print("=" * 60)
    print("Close the dialog when done reviewing")
    print("=" * 60)
    
    # Create root window
    root = tk.Tk()
    root.title("Settings GUI Test")
    root.geometry("400x300")
    
    # Open Settings dialog
    dialog = SettingsDialog(root, title="⚙️ Settings (with Filters)")
    
    # Wait for dialog to close
    root.wait_window(dialog)
    
    print()
    print("✅ Test completed - dialog closed")

if __name__ == '__main__':
    test_settings_gui()
