"""
EdgeMind NPU - Application Entry Point
Launch the desktop AI assistant.

Copyright (c) 2024 Sadroddin Aghaei. All rights reserved.
"""

import sys
import os
import logging
from pathlib import Path

# Ensure src is in the path
sys.path.insert(0, str(Path(__file__).parent))


def setup_logging():
    """Configure application logging."""
    from src.config import LOGS_DIR

    log_file = LOGS_DIR / "edgemind.log"

    # In windowed (frozen) builds sys.stdout is None; only attach a
    # console handler when a real stream is available.
    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    if sys.stdout is not None or sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stdout or sys.stderr))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _console_print(message: str):
    """Print to the console if one exists; never crash in windowed mode."""
    try:
        stream = sys.stdout or sys.stderr
        if stream is None:
            return
        print(message, file=stream)
    except (OSError, ValueError, UnicodeEncodeError):
        pass


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []

    required = {
        'PySide6': 'PySide6',
        'psutil': 'psutil',
        'requests': 'requests',
    }

    optional = {
        'llama_cpp': 'llama-cpp-python',
        'openvino': 'openvino',
        'PyPDF2': 'PyPDF2',
        'docx': 'python-docx',
        'PIL': 'Pillow',
    }

    # Check required
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    # Check optional (warn only)
    for module, package in optional.items():
        try:
            __import__(module)
        except ImportError:
            logging.warning(f"Optional dependency not installed: {package}")

    if missing:
        _console_print("=" * 60)
        _console_print("Missing required dependencies:")
        for pkg in missing:
            _console_print(f"   - {pkg}")
        _console_print("\nInstall with:")
        _console_print(f"   pip install {' '.join(missing)}")
        _console_print("=" * 60)
        return False

    return True


def main():
    """Main application entry point."""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("EdgeMind NPU v1.0.0 Starting...")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info("=" * 60)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Create data directories
    from src.config import APP_DATA_DIR, MODELS_DIR, CACHE_DIR, EXPORTS_DIR, LOGS_DIR
    for d in [APP_DATA_DIR, MODELS_DIR, CACHE_DIR, EXPORTS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Initialize database
    try:
        from src.database.db_manager import DatabaseManager
        DatabaseManager()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

    # Create Qt application
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont

        # High DPI support
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

        app = QApplication(sys.argv)
        app.setApplicationName("EdgeMind NPU")
        app.setOrganizationName("Sadroddin Aghaei")
        app.setApplicationVersion("1.0.0")

        # Set default font
        font = QFont("Segoe UI", 14)
        app.setFont(font)

        # Set application palette for dark mode
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e4e4f0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#252536"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2d2d44"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#252536"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e4e4f0"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#e4e4f0"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#2d2d44"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e4e4f0"))
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#f44336"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#7c6ff7"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        app.setPalette(palette)

        # Create and show main window
        from src.ui.main_window import MainWindow
        window = MainWindow()
        window.show()

        logger.info("Application window displayed")

        # Run application
        exit_code = app.exec()

        logger.info(f"Application exiting with code: {exit_code}")
        sys.exit(exit_code)

    except ImportError as e:
        logger.error(f"Failed to import PySide6: {e}")
        _console_print("\nPySide6 is required. Install with:\n   pip install PySide6")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
