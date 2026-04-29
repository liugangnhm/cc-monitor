"""Claude Code Monitor entry point."""

import sys

from PySide6.QtWidgets import QApplication

from cc_monitor.ui import MonitorWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MonitorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
