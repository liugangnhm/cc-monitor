"""Claude Code Monitor GUI with PySide6."""

from enum import Enum

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cc_monitor.data import load_sessions, Session, Task

# ── 配色方案 ──────────────────────────────────────────────────────────────

COLORS = {
    "window_bg": "#eef1f5",
    "card_bg": "#ffffff",
    "card_border": "#e2e8f0",
    "title": "#0f172a",
    "subtitle": "#94a3b8",
    "separator": "#f1f5f9",
    "accent_busy": "#f59e0b",
    "accent_idle": "#3b82f6",
    "accent_dead": "#e2e8f0",
    "dot_done": "#22c55e",
    "dot_active": "#f59e0b",
    "dot_pending": "#cbd5e1",
    "badge_busy_bg": "#fef3c7",
    "badge_busy_text": "#b45309",
    "badge_idle_bg": "#dbeafe",
    "badge_idle_text": "#1e40af",
    "task_text": "#334155",
    "task_done_text": "#94a3b8",
    "empty_text": "#94a3b8",
    "header_bg": "#ffffff",
    "header_title": "#0f172a",
    "header_accent": "#6366f1",
    "status_text": "#64748b",
}

TASK_STYLES = {
    "completed":   {"dot": COLORS["dot_done"],   "text": COLORS["task_done_text"]},
    "in_progress": {"dot": COLORS["dot_active"],  "text": COLORS["task_text"]},
    "pending":     {"dot": COLORS["dot_pending"], "text": COLORS["subtitle"]},
}

SESSION_BADGE = {
    "busy": {"label": "工作中", "bg": COLORS["badge_busy_bg"], "color": COLORS["badge_busy_text"]},
    "idle": {"label": "就绪",   "bg": COLORS["badge_idle_bg"], "color": COLORS["badge_idle_text"]},
}


class ViewMode(Enum):
    COMPACT = "compact"
    DETAIL = "detail"


def _make_card(session: Session, blinking: bool = False, blink_phase: bool = False) -> QFrame:
    outer = QFrame()
    outer.setStyleSheet("QFrame { background: transparent; border: none; }")

    # Accent color based on status
    if session.is_alive and session.status == "busy":
        accent_color = COLORS["accent_busy"]
    elif session.is_alive:
        accent_color = COLORS["accent_idle"]
    else:
        accent_color = COLORS["accent_dead"]

    outer_layout = QHBoxLayout(outer)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    # Left accent strip
    strip = QFrame()
    strip.setFixedWidth(4)
    strip.setStyleSheet(
        f"QFrame {{ background: {accent_color}; border: none; border-radius: 2px; }}"
    )
    outer_layout.addWidget(strip)

    # Main card body
    card_bg = "#fef9c3" if blinking and blink_phase else COLORS["card_bg"]
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background: {card_bg}; border: none; "
        f"border-radius: 0 10px 10px 0; }}"
    )

    # Shadow on card
    shadow = QGraphicsDropShadowEffect(card)
    shadow.setBlurRadius(8)
    shadow.setXOffset(0)
    shadow.setYOffset(2)
    shadow.setColor(QColor(0, 0, 0, 15))
    card.setGraphicsEffect(shadow)

    body = QVBoxLayout(card)
    body.setContentsMargins(12, 10, 12, 10)
    body.setSpacing(6)

    # ── Header row ──
    header = QHBoxLayout()
    header.setSpacing(6)

    project_name = session.name or ""
    if not project_name and session.cwd:
        import os
        project_name = os.path.basename(session.cwd) or "Unknown"

    name = QLabel(project_name)
    name.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
    name.setStyleSheet(
        f"color: {COLORS['title']}; background: transparent; border: none;"
    )
    name.setWordWrap(True)
    header.addWidget(name, 1)

    if session.is_alive:
        badge_style = SESSION_BADGE.get(session.status, SESSION_BADGE["idle"])
        badge = QLabel(badge_style["label"])
        badge.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        badge.setStyleSheet(
            f"QLabel {{ background: {badge_style['bg']}; color: {badge_style['color']}; "
            f"border: none; border-radius: 10px; padding: 4px 14px; }}"
        )
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(24)
        header.addWidget(badge)

    body.addLayout(header)

    # ── Separator ──
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: {COLORS['separator']}; border: none;")
    body.addWidget(sep)

    # ── Tasks ──
    if session.tasks:
        for task in session.tasks[:8]:
            ts = TASK_STYLES.get(task.status, TASK_STYLES["pending"])
            row = QHBoxLayout()
            row.setSpacing(10)

            # Status dot
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"QLabel {{ background: {ts['dot']}; border-radius: 4px; }}"
            )
            row.addWidget(dot)

            text = QLabel(task.subject)
            text.setFont(QFont("Microsoft YaHei", 9))
            text.setStyleSheet(
                f"color: {ts['text']}; background: transparent; border: none;"
            )
            text.setWordWrap(True)
            row.addWidget(text, 1)
            body.addLayout(row)

        if len(session.tasks) > 8:
            more = QLabel(f"  +{len(session.tasks) - 8} 个任务")
            more.setFont(QFont("Microsoft YaHei", 8))
            more.setStyleSheet(
                f"color: {COLORS['subtitle']}; background: transparent; border: none;"
            )
            body.addWidget(more)
    else:
        empty_row = QHBoxLayout()
        empty_row.addStretch()
        empty_text = QLabel("暂无任务")
        empty_text.setFont(QFont("Microsoft YaHei", 9))
        empty_text.setStyleSheet(
            f"color: {COLORS['empty_text']}; background: transparent; border: none;"
        )
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_row.addWidget(empty_text)
        empty_row.addStretch()
        body.addLayout(empty_row)

    outer_layout.addWidget(card, 1)

    return outer


def _make_compact_row(session: Session, blinking: bool = False, blink_phase: bool = False) -> QFrame:
    row = QFrame()
    row.setFixedHeight(28)
    bg_color = "#fef9c3" if blinking and blink_phase else "transparent"
    row.setStyleSheet(f"QFrame {{ background: {bg_color}; border: none; }}")

    if session.is_alive and session.status == "busy":
        accent = COLORS["accent_busy"]
    elif session.is_alive:
        accent = COLORS["accent_idle"]
    else:
        accent = COLORS["accent_dead"]

    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    strip = QFrame()
    strip.setFixedWidth(4)
    strip.setStyleSheet(f"QFrame {{ background: {accent}; border: none; border-radius: 2px; }}")
    layout.addWidget(strip)
    layout.addSpacing(10)

    project_name = session.name or ""
    if not project_name and session.cwd:
        import os
        project_name = os.path.basename(session.cwd) or "Unknown"

    name = QLabel(project_name)
    name.setFont(QFont("Microsoft YaHei", 10))
    name.setStyleSheet(f"color: {COLORS['title']}; background: transparent; border: none;")
    layout.addWidget(name, 1)

    if session.is_alive:
        badge_style = SESSION_BADGE.get(session.status, SESSION_BADGE["idle"])
        task_count = len(session.tasks)
        status_text = f"{badge_style['label']} [{task_count}]"
    else:
        status_text = "已结束 [0]"

    status = QLabel(status_text)
    status.setFont(QFont("Microsoft YaHei", 9))
    status.setStyleSheet(f"color: {COLORS['status_text']}; background: transparent; border: none;")
    layout.addWidget(status)

    return row


class MonitorWindow(QWidget):
    REFRESH_MS = 2000
    CARD_MIN_WIDTH = 300

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCM")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        self.resize(260, 360)
        self.setMinimumSize(200, 180)

        self._last_sig: str = ""
        self._last_sessions: list[Session] = []
        self._drag_pos = None
        self._view_mode = ViewMode.COMPACT
        self._changed_sessions: set[str] = set()
        self._blink_phase = False
        self._flash_count = 0
        self._build_ui()
        self._start_timer()

        self._opacity_timer = QTimer(self)
        self._opacity_timer.setSingleShot(True)
        self._opacity_timer.timeout.connect(lambda: self.setWindowOpacity(0.3))
        self.setWindowOpacity(0.3)

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)

        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._do_flash)

        self.refresh()
        self._set_view_mode(ViewMode.COMPACT)

    def _build_ui(self):
        self.setStyleSheet(f"background: {COLORS['window_bg']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top accent line ──
        accent_line = QFrame()
        accent_line.setFixedHeight(3)
        accent_line.setStyleSheet(
            "QFrame { background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #6366f1, stop:0.5 #8b5cf6, stop:1 #a78bfa); "
            "border: none; }"
        )
        root.addWidget(accent_line)

        # ── Top header bar ──
        header_bar = QFrame()
        header_bar.setFixedHeight(40)
        header_bar.setStyleSheet(
            f"QFrame {{ background: {COLORS['header_bg']}; "
            f"border-bottom: 1px solid #e2e8f0; }}"
        )

        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("CCM")
        title.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        title.setStyleSheet(
            f"color: {COLORS['header_title']}; background: transparent; border: none;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet(
            f"color: {COLORS['status_text']}; background: transparent; border: none;"
        )
        header_layout.addWidget(self.status_label)

        # 视图切换按钮（合二为一）
        self.toggle_btn = QLabel("⊞")
        self.toggle_btn.setFont(QFont("Microsoft YaHei", 12))
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(f"color: {COLORS['header_accent']}; background: transparent; border: none; padding: 0 6px;")
        self.toggle_btn.mousePressEvent = lambda e: self._toggle_view_mode() if e.button() == Qt.MouseButton.LeftButton else None

        header_layout.addWidget(self.toggle_btn)

        # 关闭按钮
        close_btn = QLabel("×")
        close_btn.setFont(QFont("Microsoft YaHei", 14))
        close_btn.setStyleSheet("color: #94a3b8; background: transparent; border: none; padding: 0 8px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close() if e.button() == Qt.MouseButton.LeftButton else None
        header_layout.addWidget(close_btn)

        root.addWidget(header_bar)

        # ── Card grid area ──
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #c4c9d0; border-radius: 3px; min-height: 40px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
        )

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(6, 4, 6, 4)

        self.scroll.setWidget(self.grid_container)
        root.addWidget(self.scroll)

    def mousePressEvent(self, event):
        if self._flash_timer.isActive():
            self._stop_flash()
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 43:
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        if not self._flash_timer.isActive():
            self.setWindowOpacity(1.0)
            self._opacity_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._flash_timer.isActive():
            self._opacity_timer.start(500)
        super().leaveEvent(event)

    def _stop_flash(self):
        self._flash_timer.stop()
        if not self.underMouse():
            self.setWindowOpacity(0.3)
        else:
            self.setWindowOpacity(1.0)

    def _do_flash(self):
        self._flash_count += 1
        opacity = 0.35 if self._flash_count % 2 == 1 else 1.0
        self.setWindowOpacity(opacity)

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

        total_tasks = sum(len(s.tasks) for s in sessions)
        self.status_label.setText(f"{total_tasks} 任务")

        if sig == self._last_sig:
            return

        # 检测哪些 session 发生了变化（跳过首次刷新）
        if self._last_sessions:
            old_map = {s.session_id: s for s in self._last_sessions}
            for s in sessions:
                old = old_map.get(s.session_id)
                if old is None:
                    self._changed_sessions.add(s.session_id)
                elif s.status != old.status or s.is_alive != old.is_alive or len(s.tasks) != len(old.tasks):
                    self._changed_sessions.add(s.session_id)

        self._last_sessions = list(sessions)
        self._last_sig = sig

        has_changes = bool(self._changed_sessions)

        self.setWindowOpacity(1.0)
        self._opacity_timer.stop()
        self._opacity_timer.start(3000)

        self._rebuild_ui(sessions)

        if self._changed_sessions and not self._blink_timer.isActive():
            self._blink_timer.start(500)

        if has_changes and not self._flash_timer.isActive():
            self._flash_count = 0
            self._flash_timer.start(150)

    def _toggle_blink(self):
        self._blink_phase = not self._blink_phase
        sessions = load_sessions()
        self._rebuild_ui(sessions)

    def _acknowledge_change(self, session_id: str):
        self._changed_sessions.discard(session_id)
        if not self._changed_sessions:
            self._blink_timer.stop()
        sessions = load_sessions()
        self._rebuild_ui(sessions)

    def _toggle_view_mode(self):
        new_mode = ViewMode.DETAIL if self._view_mode == ViewMode.COMPACT else ViewMode.COMPACT
        self._set_view_mode(new_mode)

    def _set_view_mode(self, mode: ViewMode):
        if self._view_mode == mode:
            return
        self._view_mode = mode

        # 按钮显示要切换到的目标模式图标
        self.toggle_btn.setText("⊞" if mode == ViewMode.COMPACT else "≡")

        if mode == ViewMode.COMPACT:
            self.resize(260, 360)
            self.setMinimumSize(200, 180)
        else:
            self.resize(1100, 700)
            self.setMinimumSize(500, 400)

        sessions = load_sessions()
        self._rebuild_ui(sessions)

    def _rebuild_ui(self, sessions: list[Session]):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        if not sessions:
            empty = QLabel("未检测到活跃 Session")
            empty.setFont(QFont("Microsoft YaHei", 12))
            empty.setStyleSheet(
                f"color: {COLORS['empty_text']}; background: transparent; border: none;"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(empty, 0, 0)
            return

        if self._view_mode == ViewMode.COMPACT:
            for i, session in enumerate(sessions):
                blinking = session.session_id in self._changed_sessions
                row = _make_compact_row(session, blinking, self._blink_phase)
                if blinking:
                    row.mouseDoubleClickEvent = lambda e, sid=session.session_id: self._acknowledge_change(sid)
                self.grid_layout.addWidget(row, i, 0)
        else:
            width = self.scroll.viewport().width() - 48
            cols = max(1, width // self.CARD_MIN_WIDTH)
            for i, session in enumerate(sessions):
                row = i // cols
                col = i % cols
                blinking = session.session_id in self._changed_sessions
                card = _make_card(session, blinking, self._blink_phase)
                if blinking:
                    card.mouseDoubleClickEvent = lambda e, sid=session.session_id: self._acknowledge_change(sid)
                self.grid_layout.addWidget(card, row, col)
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
        if hasattr(self, "_last_sig") and self._last_sig and self._view_mode == ViewMode.DETAIL:
            sessions = load_sessions()
            self._rebuild_ui(sessions)
