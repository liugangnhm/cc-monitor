"""Claude Code Monitor entry point."""

import ttkbootstrap as ttkb

from cc_monitor.ui import MonitorApp


def main():
    app = ttkb.Window(themename="cosmo")
    MonitorApp(app)
    app.mainloop()


if __name__ == "__main__":
    main()
