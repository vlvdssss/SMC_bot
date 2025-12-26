"""
SMC Trading Control Center - Main Entry Point

This is the main application entry point for the GUI control center.
The application provides real-time monitoring and control for the
algorithmic trading system.

Usage:
    python main.py                    # Normal mode
    python main.py --readonly         # Read-only monitoring mode
    python main.py --mode demo        # Force demo mode
    python main.py --mode live        # Force live mode (requires confirmation)

Architecture:
    - UI layer: PySide6 widgets and views
    - Core layer: State management and business logic
    - Data layer: Bridge to BAZA trading system
"""

import sys
import argparse
from pathlib import Path
import os

# Determine if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = Path(sys.executable).parent
    project_root = application_path
else:
    # Running as script
    application_path = Path(__file__).parent
    project_root = Path(__file__).parent.parent

# Add parent directory to path for imports (for gui modules)
sys.path.insert(0, str(application_path))

# Add project root to path for imports (for mt5, strategies, etc.)
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from views.main_window import MainWindow
from core.app_state import AppState
from core.data_bridge import DataBridge
from core.logger import setup_logger


# Version info
APP_NAME = "SMC Control Center"
APP_VERSION = "1.0.0"
APP_AUTHOR = "SMC-framework"


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '--readonly',
        action='store_true',
        help='Launch in read-only mode (monitoring only, no control)',
    )
    
    parser.add_argument(
        '--mode',
        choices=['demo', 'live'],
        default='demo',
        help='Trading mode (default: demo)',
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging',
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/gui_config.json',
        help='Path to configuration file',
    )
    parser.add_argument(
        '--baza',
        type=str,
        default=None,
        help='Path to BAZA folder (overrides bundled lookup)',
    )
    
    return parser.parse_args()


def setup_application():
    """Configure Qt application settings."""
    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_AUTHOR)
    
    # Set application icon (if exists)
    icon_path = Path('gui/resources/icon.png')
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    return app


def main():
    """Main application entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Ensure logs directory exists
    logs_dir = application_path / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Setup logger
    logger = setup_logger(
        log_file=str(logs_dir / 'gui.log'),
        debug=args.debug
    )
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Mode: {args.mode.upper()}, Read-only: {args.readonly}")
    
    # Create Qt application
    app = setup_application()
    
    # Initialize core components
    logger.info("Initializing core components...")
    
    # App state manager (maintains current state)
    app_state = AppState(
        mode=args.mode,
        readonly=args.readonly,
    )
    
    # Data bridge (connects to BAZA system)
    # Determine BAZA path (CLI arg -> env var -> external BAZA folder -> bundle)
    baza_path_arg = args.baza
    env_baza = os.environ.get('BAZA_PATH')

    if baza_path_arg:
        baza_data_path = Path(baza_path_arg)
    elif env_baza:
        baza_data_path = Path(env_baza)
    else:
        # If running as bundle, prefer a sibling 'BAZA' folder next to the exe
        if getattr(sys, 'frozen', False):
            candidate = application_path.parent / 'BAZA'
            if candidate.exists():
                baza_data_path = candidate
            else:
                baza_data_path = application_path
        else:
            baza_data_path = Path('BAZA')
    data_bridge = DataBridge(
        baza_path=baza_data_path,
        update_interval=1000,  # 1 second
    )
    
    # Connect data bridge to state manager
    data_bridge.data_updated.connect(app_state.update_from_baza)
    
    # Create main window
    logger.info("Creating main window...")
    main_window = MainWindow(
        app_state=app_state,
        data_bridge=data_bridge,
    )
    
    # Apply dark theme
    from styles.dark_theme import apply_dark_theme
    apply_dark_theme(app)
    
    # Show window
    main_window.show()
    logger.info("Application started successfully")
    
    # Start data bridge
    data_bridge.start()
    
    # Run application
    exit_code = app.exec()
    
    # Cleanup
    logger.info("Shutting down...")
    data_bridge.stop()
    
    logger.info(f"Application closed with exit code {exit_code}")
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
