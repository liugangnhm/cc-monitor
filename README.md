# CC Monitor

A desktop GUI tool that monitors [Claude Code](https://docs.anthropic.com/en/docs/claude-code) sessions and tasks in real time.

![](assets/icon.png)

## Features

- **Session Dashboard** — Displays all active Claude Code sessions as cards
- **Task Tracking** — Shows tasks within each session with real-time status updates (pending / in progress / completed)
- **Color-coded Status** — Left accent strip and badges indicate session state at a glance (working / ready)
- **Always on Top** — Window stays above other applications so you never miss a status change
- **Responsive Layout** — Cards auto-arrange into a grid that adapts to window width
- **Flicker-free Refresh** — Only re-renders when data actually changes
- **Standalone EXE** — Package as a single executable, no Python installation required

## Quick Start

### Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) package manager
- Claude Code CLI (generates the session/task data that this tool reads)

### Run from Source

```bash
git clone https://github.com/liugangnhm/cc-monitor.git
cd cc-monitor
uv sync
uv run cc-monitor
```

### Build EXE

```bash
uv run cc-monitor-build
```

The executable will be at `dist/cc-monitor.exe`.

## How It Works

CC Monitor reads Claude Code's local data files:

| Data | Path |
|------|------|
| Sessions | `~/.claude/sessions/*.json` |
| Tasks | `~/.claude/tasks/<sessionId>/*.json` |

It detects whether a session is **busy** (LLM generating response) or **idle** (waiting for input) by checking the session status and process liveness via `psutil`.

The UI refreshes every 2 seconds with signature-based change detection — no flicker, no unnecessary re-renders.

## Project Structure

```
cc-monitor/
├── assets/                  # App icon (.ico, .png)
├── scripts/
│   └── gen_icon.py          # Icon generator (Pillow)
├── src/cc_monitor/
│   ├── main.py              # Entry point
│   ├── ui.py                # PySide6 GUI — cards, layout, styling
│   ├── data.py              # Data layer — load sessions & tasks
│   └── build.py             # PyInstaller build script
├── tests/
│   └── test_data.py         # Unit tests for data layer
└── pyproject.toml
```

## Tech Stack

- **GUI** — [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python)
- **Process Monitoring** — [psutil](https://github.com/giampaolo/psutil)
- **Packaging** — [PyInstaller](https://pyinstaller.org/)
- **Package Manager** — [uv](https://docs.astral.sh/uv/)

## License

MIT
