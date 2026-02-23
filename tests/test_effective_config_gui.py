"""
Визуальный тест диалога Effective Config с отображением конфликтов
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import tkinter as tk
from tkinter import ttk
from src.core.config_manager import get_config_manager
from src.gui.dialogs_v2 import EffectiveConfigDialog

def test_gui():
    """Показать диалог Effective Config с конфликтами"""
    
    print("=" * 60)
    print("VISUAL TEST: EffectiveConfig with Conflict Detection")
    print("=" * 60)
    print()
    print("Opening dialog...")
    print()
    print("Expected to see:")
    print("  ⚠️  CONFLICTS DETECTED (2) - at the top")
    print("    🔴 min_confidence")
    print("      ✅ ai.yaml: 75 (ACTIVE)")
    print("      ❌ trading.yaml: 50 (IGNORED)")
    print("      📌 Winner: ai.yaml - TradeFilters reads from ai.yaml")
    print()
    print("    🔴 max_spread_pips")
    print("      ✅ ai.yaml: 3.0 (ACTIVE)")
    print("      ❌ trading.yaml: 0.5 (IGNORED)")
    print("      📌 Winner: ai.yaml - TradeFilters reads from ai.yaml")
    print()
    print("  📄 ai.yaml")
    print("    📁 market_analyst")
    print("      📁 trade_filters")
    print("        min_confidence: 75")
    print("        max_spread_pips: 3.0")
    print("        ...")
    print()
    print("  📄 trading.yaml")
    print("    📁 signal_quality")
    print("      min_confidence: 50")
    print("    📁 risk")
    print("      max_spread_pips: 0.5")
    print("        ...")
    print()
    print("=" * 60)
    print("Close the dialog window when done reviewing")
    print("=" * 60)
    
    # Create root window
    root = tk.Tk()
    root.title("Effective Config GUI Test")
    root.geometry("800x600")
    
    # Get ConfigManager
    config_manager = get_config_manager()
    
    # Create dialog
    dialog = EffectiveConfigDialog(root, config_manager)
    
    # Show dialog (modal)
    root.wait_window(dialog)
    
    print()
    print("✅ Test completed - dialog closed")

if __name__ == '__main__':
    test_gui()
