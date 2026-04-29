"""Claude Code Monitor entry point."""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from cc_monitor.ui import MonitorWindow


def _icon_path() -> Path:
    """Resolve icon path (works both in dev and PyInstaller bundle)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "cc-monitor.ico"
    return Path(__file__).resolve().parent.parent.parent / "assets" / "cc-monitor.ico"


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    icon_path = _icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MonitorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
