"""Claude Code Monitor GUI with PySide6."""

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cc_monitor.data import load_sessions, Session, Task

TASK_STYLES = {
    "completed":   {"icon": "✅", "color": "#2e7d32"},
    "in_progress": {"icon": "🔄", "color": "#e65100"},
    "pending":     {"icon": "⏳", "color": "#757575"},
}

SESSION_STYLES = {
    "busy": {"text": "⚡ 工作中", "bg": "#fff3e0", "color": "#e65100", "border": "#ff9800"},
    "idle": {"text": "● 就绪",   "bg": "#e3f2fd", "color": "#1565c0", "border": "#2196f3"},
}

CARD_CSS = """
QFrame {{
    background: {bg};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 12px;
}}
QFrame:hover {{
    border-color: {hover};
}}
"""


def _make_card(session: Session) -> QFrame:
    card = QFrame()
    card.setStyleSheet(CARD_CSS.format(
        bg="#ffffff", border="#e0e0e0", hover="#bdbdbd",
    ))

    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)

    # Header: project name + status badge
    header = QHBoxLayout()
    header.setSpacing(8)

    project_name = session.name or ""
    if not project_name and session.cwd:
        import os
        project_name = os.path.basename(session.cwd) or "Unknown"

    name_label = QLabel(project_name)
    name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
    name_label.setStyleSheet("border: none; background: transparent;")
    header.addWidget(name_label)

    header.addStretch()

    if session.is_alive:
        style = SESSION_STYLES.get(session.status, SESSION_STYLES["idle"])
        badge = QLabel(style["text"])
        badge.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        badge.setStyleSheet(
            f"border: none; background: {style['bg']}; color: {style['color']}; "
            f"border-radius: 4px; padding: 2px 8px;"
        )
        header.addWidget(badge)

    layout.addLayout(header)

    # Separator
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet("border: none; background: #eeeeee; max-height: 1px;")
    layout.addWidget(sep)

    # Tasks
    if session.tasks:
        for task in session.tasks:
            ts = TASK_STYLES.get(task.status, TASK_STYLES["pending"])
            row = QHBoxLayout()
            row.setSpacing(6)

            icon = QLabel(ts["icon"])
            icon.setStyleSheet("border: none; background: transparent;")
            icon.setFont(QFont("Segoe UI Emoji", 10))
            row.addWidget(icon)

            text = QLabel(task.subject)
            text.setFont(QFont("Microsoft YaHei", 9))
            text.setStyleSheet(f"border: none; background: transparent; color: #333333;")
            row.addWidget(text)
            row.addStretch()

            layout.addLayout(row)
    else:
        no_task = QLabel("暂无任务")
        no_task.setFont(QFont("Microsoft YaHei", 9))
        no_task.setStyleSheet("border: none; background: transparent; color: #999999;")
        layout.addWidget(no_task)

    return card


class MonitorWindow(QWidget):
    REFRESH_MS = 2000
    CARD_MIN_WIDTH = 260

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Claude Code Monitor")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.resize(1200, 700)
        self.setMinimumSize(500, 400)

        self._cards: list[tuple[str, QFrame]] = []
        self._last_sig: str = ""

        self._build_ui()
        self._start_timer()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 8)
        root.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("Claude Code Monitor")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet("color: #333333;")
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet("color: #999999;")
        header.addWidget(self.status_label)
        root.addLayout(header)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { border: none; background: #f5f5f5; border-radius: 8px; }"
            "QScrollBar:vertical { width: 8px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #cccccc; border-radius: 4px; min-height: 30px; }"
        )

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)

        self.scroll.setWidget(self.grid_container)
        root.addWidget(self.scroll)

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(self.REFRESH_MS)

    def _session_sig(self, sessions: list[Session]) -> str:
        parts = []
        for s in sessions:
            tasks = "|".join(f"{t.id}:{t.status}:{t.subject}" for t in s.tasks)
            parts.append(f"{s.session_id}:{s.status}:{s.is_alive}:{tasks}")
        return "||".join(parts)

    def refresh(self):
        sessions = load_sessions()
        sig = self._session_sig(sessions)

        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(f"最后刷新: {now} | 共 {len(sessions)} sessions")

        if sig == self._last_sig:
            return

        self._last_sig = sig
        self._rebuild_cards(sessions)

    def _rebuild_cards(self, sessions: list[Session]):
        # Clear old cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        if not sessions:
            empty = QLabel("未检测到活跃 Session")
            empty.setFont(QFont("Microsoft YaHei", 12))
            empty.setStyleSheet("color: #999999; border: none; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(empty, 0, 0)
            return

        # Calculate columns based on current width
        width = self.scroll.viewport().width() - 24
        cols = max(1, width // self.CARD_MIN_WIDTH)

        for i, session in enumerate(sessions):
            row = i // cols
            col = i % cols
            card = _make_card(session)
            self.grid_layout.addWidget(card, row, col)

        # Make columns stretch equally
        for col in range(cols):
            self.grid_layout.setColumnStretch(col, 1)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Recalculate columns on resize
        if hasattr(self, "_last_sig") and self._last_sig:
            sessions = load_sessions()
            self._rebuild_cards(sessions)
