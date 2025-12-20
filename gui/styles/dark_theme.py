"""
Dark Theme Styles for SMC Control Center

Custom dark theme with professional trading aesthetic.
Color palette optimized for long-term viewing and clarity.

Color Scheme:
    Background:   #1a1d23  (dark graphite)
    Panel:        #252930  (slightly lighter)
    Border:       #3a3f4a  (subtle)
    
    Green:        #00c896  (profit/success)
    Red:          #ff5555  (loss/risk)
    Yellow:       #ffc107  (warning)
    Blue:         #4a9eff  (info/neutral)
    
    Text Primary: #e8e9ed
    Text Secondary: #8b92a0
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


# Color palette constants
class Colors:
    """Application color constants."""
    
    # Backgrounds
    BG_DARK = "#1a1d23"
    BG_PANEL = "#252930"
    BG_WIDGET = "#2d323a"
    BG_HOVER = "#353a44"
    
    # Borders
    BORDER = "#3a3f4a"
    BORDER_LIGHT = "#4a5060"
    
    # Status colors (SOFTER, LESS ACID)
    GREEN = "#00c896"       # Soft success green
    GREEN_BRIGHT = "#10d8a6"  # Hover state
    RED = "#ff5555"         # Warm red, not harsh
    RED_BRIGHT = "#ff6565"  # Hover state
    YELLOW = "#ffc107"      # Amber warning
    BLUE = "#4a9eff"        # Calm info blue
    PURPLE = "#bd93f9"
    
    # Text
    TEXT_PRIMARY = "#e8e9ed"
    TEXT_SECONDARY = "#8b92a0"
    TEXT_DISABLED = "#5a5f6a"
    
    # Accent
    ACCENT = "#4a9eff"
    ACCENT_HOVER = "#6ab0ff"


def apply_dark_theme(app: QApplication) -> None:
    """
    Apply custom dark theme to the application.
    
    Args:
        app: QApplication instance
    """
    # Set style
    app.setStyle("Fusion")
    
    # Create custom palette
    palette = QPalette()
    
    # Base colors
    palette.setColor(QPalette.Window, QColor(Colors.BG_PANEL))
    palette.setColor(QPalette.WindowText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.Base, QColor(Colors.BG_DARK))
    palette.setColor(QPalette.AlternateBase, QColor(Colors.BG_WIDGET))
    palette.setColor(QPalette.ToolTipBase, QColor(Colors.BG_WIDGET))
    palette.setColor(QPalette.ToolTipText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.Text, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.Button, QColor(Colors.BG_WIDGET))
    palette.setColor(QPalette.ButtonText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.BrightText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.Link, QColor(Colors.ACCENT))
    palette.setColor(QPalette.Highlight, QColor(Colors.ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor(Colors.BG_DARK))
    
    # Disabled colors
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(Colors.TEXT_DISABLED))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(Colors.TEXT_DISABLED))
    
    app.setPalette(palette)
    
    # Apply stylesheet for fine-grained control
    stylesheet = get_stylesheet()
    app.setStyleSheet(stylesheet)


def get_stylesheet() -> str:
    """
    Get complete application stylesheet.
    
    Returns:
        CSS-like stylesheet string
    """
    return f"""
    
    /* === GLOBAL === */
    
    QWidget {{
        background-color: {Colors.BG_PANEL};
        color: {Colors.TEXT_PRIMARY};
        font-family: "Segoe UI", "Roboto", sans-serif;
        font-size: 11pt;
    }}
    
    /* === MAIN WINDOW === */
    
    QMainWindow {{
        background-color: {Colors.BG_DARK};
    }}
    
    /* === STATUS BAR === */
    
    QStatusBar {{
        background-color: {Colors.BG_PANEL};
        border-top: 1px solid {Colors.BORDER};
        padding: 4px;
    }}
    
    QStatusBar::item {{
        border: none;
    }}
    
    /* === BUTTONS === */
    
    QPushButton {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        padding: 8px 16px;
        color: {Colors.TEXT_PRIMARY};
        font-weight: bold;
    }}
    
    QPushButton:hover {{
        background-color: {Colors.BG_HOVER};
        border-color: {Colors.BORDER_LIGHT};
    }}
    
    QPushButton:pressed {{
        background-color: {Colors.BG_DARK};
    }}
    
    QPushButton:disabled {{
        color: {Colors.TEXT_DISABLED};
        border-color: {Colors.BORDER};
    }}
    
    QPushButton#startButton {{
        background-color: {Colors.GREEN};
        color: {Colors.BG_DARK};
        border: none;
    }}
    
    QPushButton#startButton:hover {{
        background-color: #10d8a6;
    }}
    
    QPushButton#stopButton {{
        background-color: {Colors.RED};
        color: {Colors.BG_DARK};
        border: none;
    }}
    
    QPushButton#stopButton:hover {{
        background-color: #ff6565;
    }}
    
    QPushButton#pauseButton {{
        background-color: {Colors.YELLOW};
        color: {Colors.BG_DARK};
        border: none;
    }}
    
    /* === LABELS === */
    
    QLabel {{
        background-color: transparent;
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QLabel#valueLabel {{
        font-size: 18pt;
        font-weight: bold;
        font-family: "Consolas", "Courier New", monospace;
    }}
    
    QLabel#titleLabel {{
        font-size: 10pt;
        color: {Colors.TEXT_SECONDARY};
        font-weight: normal;
    }}
    
    /* === FRAMES/CARDS === */
    
    QFrame {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
    }}
    
    QFrame#equityCard {{
        background-color: {Colors.BG_WIDGET};
        border: 2px solid {Colors.BORDER};
    }}
    
    QFrame#portfolioCard {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
    }}
    
    /* === TAB WIDGET === */
    
    QTabWidget::pane {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        top: -1px;
    }}
    
    QTabBar::tab {{
        background-color: {Colors.BG_PANEL};
        border: 1px solid {Colors.BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 10px 20px;
        margin-right: 2px;
        color: {Colors.TEXT_SECONDARY};
    }}
    
    QTabBar::tab:selected {{
        background-color: {Colors.BG_WIDGET};
        color: {Colors.TEXT_PRIMARY};
        font-weight: bold;
    }}
    
    QTabBar::tab:hover {{
        background-color: {Colors.BG_HOVER};
        color: {Colors.TEXT_PRIMARY};
    }}
    
    /* === TABLE === */
    
    QTableWidget {{
        background-color: {Colors.BG_DARK};
        alternate-background-color: {Colors.BG_PANEL};
        gridline-color: {Colors.BORDER};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
    }}
    
    QTableWidget::item {{
        padding: 6px;
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QTableWidget::item:selected {{
        background-color: {Colors.ACCENT};
        color: {Colors.BG_DARK};
    }}
    
    QHeaderView::section {{
        background-color: {Colors.BG_WIDGET};
        color: {Colors.TEXT_PRIMARY};
        font-weight: bold;
        padding: 8px;
        border: none;
        border-bottom: 1px solid {Colors.BORDER};
        border-right: 1px solid {Colors.BORDER};
    }}
    
    /* === SCROLL BAR === */
    
    QScrollBar:vertical {{
        background-color: {Colors.BG_PANEL};
        width: 12px;
        border: none;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {Colors.BG_HOVER};
        min-height: 20px;
        border-radius: 6px;
        margin: 2px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {Colors.BORDER_LIGHT};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background-color: {Colors.BG_PANEL};
        height: 12px;
        border: none;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {Colors.BG_HOVER};
        min-width: 20px;
        border-radius: 6px;
        margin: 2px;
    }}
    
    /* === COMBO BOX === */
    
    QComboBox {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        padding: 6px 12px;
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QComboBox:hover {{
        border-color: {Colors.BORDER_LIGHT};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
        selection-background-color: {Colors.ACCENT};
        color: {Colors.TEXT_PRIMARY};
    }}
    
    /* === LINE EDIT === */
    
    QLineEdit {{
        background-color: {Colors.BG_DARK};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        padding: 8px;
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QLineEdit:focus {{
        border-color: {Colors.ACCENT};
    }}
    
    /* === SLIDER === */
    
    QSlider::groove:horizontal {{
        background-color: {Colors.BG_DARK};
        height: 6px;
        border-radius: 3px;
    }}
    
    QSlider::handle:horizontal {{
        background-color: {Colors.ACCENT};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background-color: {Colors.ACCENT_HOVER};
    }}
    
    /* === PROGRESS BAR === */
    
    QProgressBar {{
        background-color: {Colors.BG_DARK};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        text-align: center;
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QProgressBar::chunk {{
        background-color: {Colors.ACCENT};
        border-radius: 3px;
    }}
    
    /* === TOOLTIP === */
    
    QToolTip {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
        color: {Colors.TEXT_PRIMARY};
        padding: 6px;
        border-radius: 4px;
    }}
    
    /* === MENU === */
    
    QMenuBar {{
        background-color: {Colors.BG_PANEL};
        color: {Colors.TEXT_PRIMARY};
        border-bottom: 1px solid {Colors.BORDER};
    }}
    
    QMenuBar::item:selected {{
        background-color: {Colors.BG_HOVER};
    }}
    
    QMenu {{
        background-color: {Colors.BG_WIDGET};
        border: 1px solid {Colors.BORDER};
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QMenu::item:selected {{
        background-color: {Colors.ACCENT};
        color: {Colors.BG_DARK};
    }}
    
    /* === CUSTOM CLASSES === */
    
    .profitLabel {{
        color: {Colors.GREEN};
        font-weight: bold;
    }}
    
    .lossLabel {{
        color: {Colors.RED};
        font-weight: bold;
    }}
    
    .warningLabel {{
        color: {Colors.YELLOW};
        font-weight: bold;
    }}
    
    """


# Export colors for use in widgets
__all__ = ['apply_dark_theme', 'Colors']
