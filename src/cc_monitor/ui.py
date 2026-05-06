"""Claude Code Monitor GUI with PySide6."""

import json
import os
from enum import Enum

from PySide6.QtCore import Qt, QTimer, QEvent, QObject
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTextEdit,
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

# ── 预设配置持久化 ────────────────────────────────────────────────────────


def _history_file() -> str:
    return os.path.join(os.path.expanduser("~"), ".claude", "cc-monitor", "history.json")


def load_history() -> list[str]:
    filepath = _history_file()
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f).get("workspaces", [])
    except (json.JSONDecodeError, OSError):
        return []


def save_history(workspaces: list[str]):
    filepath = _history_file()
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"workspaces": workspaces}, f, ensure_ascii=False, indent=2)


def load_presets() -> list[dict]:
    """Scan ~/.claude/settings.json.* files as presets."""
    claude_dir = os.path.join(os.path.expanduser("~"), ".claude")
    presets: list[dict] = []
    if not os.path.isdir(claude_dir):
        return presets
    for filename in sorted(os.listdir(claude_dir)):
        if not filename.startswith("settings.json.") or filename == "settings.json":
            continue
        filepath = os.path.join(claude_dir, filename)
        if not os.path.isfile(filepath):
            continue
        name = filename[len("settings.json."):].strip()
        if not name:
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        presets.append(
            {
                "name": name,
                "cli_args": ["--allow-dangerously-skip-permissions", "--settings", filepath],
                "settings": settings,
                "_filepath": filepath,
            }
        )
    return presets


class HoverShowHelper(QObject):
    def __init__(self, watched, widget_to_show):
        super().__init__(watched)
        self._widget = widget_to_show
        watched.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            self._widget.setVisible(True)
        elif event.type() == QEvent.Type.Leave:
            self._widget.setVisible(False)
        return False


class ViewMode(Enum):
    COMPACT = "compact"
    DETAIL = "detail"


def _make_card(session: Session, blinking: bool = False, blink_phase: bool = False, is_new: bool = False, on_locate=None) -> QFrame:
    outer = QFrame()
    outer.setStyleSheet("QFrame { background: transparent; border: none; }")

    # Accent color based on status
    if is_new:
        accent_color = COLORS["dot_done"]  # green for new sessions
    elif session.is_alive and session.status == "busy":
        accent_color = COLORS["accent_busy"]
    elif session.is_alive:
        accent_color = COLORS["accent_idle"]
    else:
        accent_color = COLORS["accent_dead"]

    outer_layout = QHBoxLayout(outer)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    # Left accent strip (wider for new sessions)
    strip = QFrame()
    strip.setFixedWidth(6 if is_new else 4)
    strip.setStyleSheet(
        f"QFrame {{ background: {accent_color}; border: none; border-radius: 2px; }}"
    )
    outer_layout.addWidget(strip)

    # Main card body
    if blinking and blink_phase:
        card_bg = "#dcfce7" if is_new else "#fef9c3"
    else:
        card_bg = COLORS["card_bg"]
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
        if on_locate:
            locate_btn = QLabel("⬍")
            locate_btn.setFont(QFont("Microsoft YaHei", 10))
            locate_btn.setStyleSheet("color: #94a3b8; background: transparent; border: none; padding: 0 4px;")
            locate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            locate_btn.mousePressEvent = lambda e: on_locate() if e.button() == Qt.MouseButton.LeftButton else None
            header.addWidget(locate_btn)

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


def _make_compact_row(session: Session, blinking: bool = False, blink_phase: bool = False, is_new: bool = False, on_locate=None) -> QFrame:
    row = QFrame()
    row.setFixedHeight(28)
    if blinking and blink_phase:
        bg_color = "#dcfce7" if is_new else "#fef9c3"
    else:
        bg_color = "transparent"
    row.setStyleSheet(f"QFrame {{ background: {bg_color}; border: none; }}")

    if is_new:
        accent = COLORS["dot_done"]  # green for new sessions
    elif session.is_alive and session.status == "busy":
        accent = COLORS["accent_busy"]
    elif session.is_alive:
        accent = COLORS["accent_idle"]
    else:
        accent = COLORS["accent_dead"]

    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    strip = QFrame()
    strip.setFixedWidth(6 if is_new else 4)
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

    locate_btn = None
    if session.is_alive and on_locate:
        locate_btn = QLabel("⬍")
        locate_btn.setFont(QFont("Microsoft YaHei", 9))
        locate_btn.setStyleSheet("color: #94a3b8; background: transparent; border: none; padding: 0 4px;")
        locate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        locate_btn.mousePressEvent = lambda e: on_locate() if e.button() == Qt.MouseButton.LeftButton else None
        locate_btn.setVisible(False)
        layout.addWidget(locate_btn)

    if locate_btn:
        HoverShowHelper(row, locate_btn)

    return row


class SessionDetailWindow(QWidget):
    def __init__(self, session: Session, on_acknowledge=None, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.session = session
        self._on_acknowledge = on_acknowledge
        self._drag_pos = None
        self.resize(280, 360)
        self._build_ui()
        self._center_on_parent()

    def _center_on_parent(self):
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.center().x() - self.width() // 2
            y = parent_geo.center().y() - self.height() // 2
            self.move(x, y)

    def _build_ui(self):
        self.setStyleSheet(f"background: {COLORS['window_bg']}; border-radius: 8px;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(36)
        header.setStyleSheet(f"background: {COLORS['header_bg']}; border-bottom: 1px solid #e2e8f0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)

        project_name = self.session.name or ""
        if not project_name and self.session.cwd:
            import os
            project_name = os.path.basename(session.cwd) or "Unknown"

        title = QLabel(project_name)
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['title']};")
        hl.addWidget(title)
        hl.addStretch()

        close_btn = QLabel("×")
        close_btn.setFont(QFont("Microsoft YaHei", 14))
        close_btn.setStyleSheet("color: #94a3b8; background: transparent; padding: 0 4px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close() if e.button() == Qt.MouseButton.LeftButton else None
        hl.addWidget(close_btn)

        root.addWidget(header)

        # Content
        content = QVBoxLayout()
        content.setContentsMargins(16, 12, 16, 12)
        content.setSpacing(8)

        def add_field(label_text, value_text):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Microsoft YaHei", 9))
            lbl.setStyleSheet(f"color: {COLORS['subtitle']};")
            val = QLabel(value_text)
            val.setFont(QFont("Microsoft YaHei", 9))
            val.setStyleSheet(f"color: {COLORS['title']};")
            val.setWordWrap(True)
            row.addWidget(lbl)
            row.addWidget(val, 1)
            content.addLayout(row)

        add_field("Session ID:", self.session.session_id[:16] + "...")
        add_field("PID:", str(self.session.pid))
        add_field("目录:", self.session.cwd)
        status_label = "工作中" if self.session.status == "busy" else "就绪" if self.session.status == "idle" else self.session.status
        add_field("状态:", status_label)
        add_field("存活:", "是" if self.session.is_alive else "否")

        # Tasks
        if self.session.tasks:
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background: {COLORS['separator']};")
            content.addWidget(sep)

            tasks_title = QLabel(f"任务 ({len(self.session.tasks)})")
            tasks_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            tasks_title.setStyleSheet(f"color: {COLORS['title']};")
            content.addWidget(tasks_title)

            for task in self.session.tasks:
                ts = TASK_STYLES.get(task.status, TASK_STYLES["pending"])
                row = QHBoxLayout()
                dot = QLabel()
                dot.setFixedSize(6, 6)
                dot.setStyleSheet(f"background: {ts['dot']}; border-radius: 3px;")
                row.addWidget(dot)
                text = QLabel(task.subject)
                text.setFont(QFont("Microsoft YaHei", 9))
                text.setStyleSheet(f"color: {ts['text']};")
                text.setWordWrap(True)
                row.addWidget(text, 1)
                content.addLayout(row)

        # Acknowledge button
        if self._on_acknowledge:
            content.addSpacing(8)
            btn = QLabel("确认变化")
            btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn.setFixedHeight(32)
            btn.setStyleSheet(
                f"background: {COLORS['header_accent']}; color: white; "
                f"border-radius: 6px; padding: 4px 16px;"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            def _on_btn_click(event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self._on_acknowledge(self.session.session_id)
                    self.close()
            btn.mousePressEvent = _on_btn_click
            content.addWidget(btn)

        root.addLayout(content)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 36:
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


class PresetEditWindow(QWidget):
    def __init__(self, preset=None, on_save=None, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._preset = preset or {"name": "", "cli_args": [], "settings": {}}
        self._on_save = on_save
        self._drag_pos = None
        self.resize(340, 520)
        self._build_ui()
        self._center_on_parent()

    def _center_on_parent(self):
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.center().x() - self.width() // 2
            y = parent_geo.center().y() - self.height() // 2
            self.move(x, y)

    def _build_ui(self):
        self.setStyleSheet(f"background: {COLORS['window_bg']}; border-radius: 8px;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(36)
        header.setStyleSheet(f"background: {COLORS['header_bg']}; border-bottom: 1px solid #e2e8f0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        is_new = not self._preset.get("name")
        title = QLabel("添加预设" if is_new else "编辑预设")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['title']};")
        hl.addWidget(title)
        hl.addStretch()
        close_btn = QLabel("×")
        close_btn.setFont(QFont("Microsoft YaHei", 14))
        close_btn.setStyleSheet("color: #94a3b8; background: transparent; padding: 0 4px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close() if e.button() == Qt.MouseButton.LeftButton else None
        hl.addWidget(close_btn)
        root.addWidget(header)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form = QVBoxLayout(form_widget)
        form.setContentsMargins(16, 12, 16, 12)
        form.setSpacing(10)

        settings = self._preset.get("settings", {})
        env = settings.get("env", {})
        permissions = settings.get("permissions", {})
        plugins = settings.get("enabledPlugins", {})

        def _line(style=""):
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background: {COLORS['separator']}; border: none;{style}")
            return line

        def add_field(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Microsoft YaHei", 9))
            lbl.setStyleSheet(f"color: {COLORS['subtitle']};")
            form.addWidget(lbl)
            form.addWidget(widget)

        def line_edit(text=""):
            edit = QLineEdit()
            edit.setText(text)
            edit.setFont(QFont("Microsoft YaHei", 10))
            edit.setStyleSheet(
                f"background: {COLORS['card_bg']}; color: {COLORS['title']}; "
                f"border: 1px solid {COLORS['card_border']}; border-radius: 4px; padding: 6px;"
            )
            return edit

        # ── 名称 ──
        self.name_input = line_edit(self._preset.get("name", ""))
        add_field("名称:", self.name_input)

        form.addWidget(_line())

        # ── Auth / URL ──
        self.token_input = line_edit(env.get("ANTHROPIC_AUTH_TOKEN", ""))
        add_field("Auth Token:", self.token_input)

        self.base_url_input = line_edit(env.get("ANTHROPIC_BASE_URL", ""))
        add_field("Base URL:", self.base_url_input)

        form.addWidget(_line())

        # ── 模型 ──
        self.model_input = line_edit(env.get("ANTHROPIC_MODEL", ""))
        add_field("模型:", self.model_input)

        self.sonnet_input = line_edit(env.get("ANTHROPIC_DEFAULT_SONNET_MODEL", ""))
        add_field("Sonnet 模型:", self.sonnet_input)

        self.opus_input = line_edit(env.get("ANTHROPIC_DEFAULT_OPUS_MODEL", ""))
        add_field("Opus 模型:", self.opus_input)

        self.haiku_input = line_edit(env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL", ""))
        add_field("Haiku 模型:", self.haiku_input)

        self.reasoning_input = line_edit(env.get("ANTHROPIC_REASONING_MODEL", ""))
        add_field("Reasoning 模型:", self.reasoning_input)

        form.addWidget(_line())

        # ── Timeout / 权限 ──
        self.timeout_input = line_edit(env.get("API_TIMEOUT_MS", "3000000"))
        add_field("API Timeout (ms):", self.timeout_input)

        lbl = QLabel("权限模式:")
        lbl.setFont(QFont("Microsoft YaHei", 9))
        lbl.setStyleSheet(f"color: {COLORS['subtitle']};")
        form.addWidget(lbl)
        self.permission_combo = QComboBox()
        self.permission_combo.addItems(["bypassPermissions", "normal"])
        self.permission_combo.setCurrentText(permissions.get("defaultMode", "bypassPermissions"))
        self.permission_combo.setFont(QFont("Microsoft YaHei", 10))
        self.permission_combo.setStyleSheet(
            f"QComboBox {{ background: {COLORS['card_bg']}; color: {COLORS['title']}; "
            f"border: 1px solid {COLORS['card_border']}; border-radius: 4px; padding: 6px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background: {COLORS['card_bg']}; color: {COLORS['title']}; }}"
        )
        form.addWidget(self.permission_combo)

        form.addWidget(_line())

        # ── 插件 ──
        self.plugins_input = QTextEdit()
        plugin_lines = [name for name, enabled in plugins.items() if enabled]
        self.plugins_input.setPlainText("\n".join(plugin_lines))
        self.plugins_input.setFont(QFont("Consolas", 9))
        self.plugins_input.setStyleSheet(
            f"background: {COLORS['card_bg']}; color: {COLORS['title']}; "
            f"border: 1px solid {COLORS['card_border']}; border-radius: 4px; padding: 6px;"
        )
        self.plugins_input.setFixedHeight(80)
        add_field("插件 (每行一个):", self.plugins_input)

        form.addWidget(_line())

        # ── 其他 JSON ──
        self.extra_input = QTextEdit()
        extra_settings = {k: v for k, v in settings.items() if k not in ("env", "permissions", "enabledPlugins", "statusLine", "skipDangerousModePermissionPrompt")}
        extra_env = {k: v for k, v in env.items() if k not in (
            "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_REASONING_MODEL",
            "API_TIMEOUT_MS", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"
        )}
        if extra_env:
            extra_settings["env"] = extra_env
        self.extra_input.setPlainText(json.dumps(extra_settings, ensure_ascii=False, indent=2))
        self.extra_input.setFont(QFont("Consolas", 9))
        self.extra_input.setStyleSheet(
            f"background: {COLORS['card_bg']}; color: {COLORS['title']}; "
            f"border: 1px solid {COLORS['card_border']}; border-radius: 4px; padding: 6px;"
        )
        self.extra_input.setFixedHeight(80)
        add_field("其他 Settings JSON:", self.extra_input)

        # Save button
        save_btn = QLabel("保存")
        save_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        save_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        save_btn.setFixedHeight(32)
        save_btn.setStyleSheet(
            f"background: {COLORS['header_accent']}; color: white; border-radius: 6px; padding: 4px 16px;"
        )
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        def _on_save_click(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self._do_save()
        save_btn.mousePressEvent = _on_save_click
        form.addWidget(save_btn)

        scroll.setWidget(form_widget)
        root.addWidget(scroll, 1)

    def _do_save(self):
        name = self.name_input.text().strip()
        if not name:
            return

        # 从额外 JSON 开始
        try:
            settings = json.loads(self.extra_input.toPlainText())
            if not isinstance(settings, dict):
                settings = {}
        except json.JSONDecodeError:
            settings = {}

        # env
        env = settings.get("env", {})
        env["ANTHROPIC_AUTH_TOKEN"] = self.token_input.text().strip()
        env["ANTHROPIC_BASE_URL"] = self.base_url_input.text().strip()
        if self.model_input.text().strip():
            env["ANTHROPIC_MODEL"] = self.model_input.text().strip()
        if self.sonnet_input.text().strip():
            env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = self.sonnet_input.text().strip()
        if self.opus_input.text().strip():
            env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = self.opus_input.text().strip()
        if self.haiku_input.text().strip():
            env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = self.haiku_input.text().strip()
        if self.reasoning_input.text().strip():
            env["ANTHROPIC_REASONING_MODEL"] = self.reasoning_input.text().strip()
        env["API_TIMEOUT_MS"] = self.timeout_input.text().strip() or "3000000"
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        settings["env"] = env

        # permissions
        settings["permissions"] = {"defaultMode": self.permission_combo.currentText()}

        # plugins
        plugins = {}
        for line in self.plugins_input.toPlainText().splitlines():
            pname = line.strip()
            if pname:
                plugins[pname] = True
        if plugins:
            settings["enabledPlugins"] = plugins
        elif "enabledPlugins" in settings:
            del settings["enabledPlugins"]

        filepath = os.path.join(os.path.expanduser("~"), ".claude", f"settings.json.{name}")

        # If renaming, delete old file
        old_filepath = self._preset.get("_filepath")
        if old_filepath and old_filepath != filepath and os.path.exists(old_filepath):
            os.remove(old_filepath)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        preset = {
            "name": name,
            "cli_args": ["--allow-dangerously-skip-permissions", "--settings", filepath],
            "settings": settings,
            "_filepath": filepath,
        }
        if self._on_save:
            self._on_save(preset)
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 36:
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


class PresetManagerWindow(QWidget):
    def __init__(self, on_presets_changed=None, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._on_presets_changed = on_presets_changed
        self._drag_pos = None
        self.resize(300, 320)
        self._build_ui()
        self._center_on_parent()

    def _center_on_parent(self):
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.center().x() - self.width() // 2
            y = parent_geo.center().y() - self.height() // 2
            self.move(x, y)

    def _build_ui(self):
        self.setStyleSheet(f"background: {COLORS['window_bg']}; border-radius: 8px;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(36)
        header.setStyleSheet(f"background: {COLORS['header_bg']}; border-bottom: 1px solid #e2e8f0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        title = QLabel("预设管理")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['title']};")
        hl.addWidget(title)
        hl.addStretch()
        close_btn = QLabel("×")
        close_btn.setFont(QFont("Microsoft YaHei", 14))
        close_btn.setStyleSheet("color: #94a3b8; background: transparent; padding: 0 4px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close() if e.button() == Qt.MouseButton.LeftButton else None
        hl.addWidget(close_btn)
        root.addWidget(header)

        # Preset list
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(12, 8, 12, 8)
        self.list_layout.setSpacing(4)
        root.addWidget(self.list_container, 1)

        # Add button
        add_btn = QLabel("+ 添加预设")
        add_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        add_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_btn.setFixedHeight(32)
        add_btn.setStyleSheet(
            f"background: {COLORS['header_accent']}; color: white; border-radius: 6px; padding: 4px 16px;"
        )
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        def _on_add(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self._open_edit()
        add_btn.mousePressEvent = _on_add
        root.addWidget(add_btn)

        self._refresh_list()

    def _refresh_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        presets = load_presets()
        for idx, preset in enumerate(presets):
            row = QFrame()
            row.setStyleSheet(f"background: {COLORS['card_bg']}; border-radius: 6px;")
            row.setFixedHeight(36)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 0, 10, 0)
            rl.setSpacing(6)

            name = QLabel(preset.get("name", "未命名"))
            name.setFont(QFont("Microsoft YaHei", 10))
            name.setStyleSheet(f"color: {COLORS['title']}; background: transparent;")
            rl.addWidget(name, 1)

            edit_btn = QLabel("编辑")
            edit_btn.setFont(QFont("Microsoft YaHei", 9))
            edit_btn.setStyleSheet(f"color: {COLORS['header_accent']}; background: transparent; padding: 0 4px;")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            def _make_edit_handler(i):
                return lambda e: self._open_edit(i) if e.button() == Qt.MouseButton.LeftButton else None
            edit_btn.mousePressEvent = _make_edit_handler(idx)

            del_btn = QLabel("删除")
            del_btn.setFont(QFont("Microsoft YaHei", 9))
            del_btn.setStyleSheet("color: #ef4444; background: transparent; padding: 0 4px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            def _make_del_handler(i):
                return lambda e: self._delete_preset(i) if e.button() == Qt.MouseButton.LeftButton else None
            del_btn.mousePressEvent = _make_del_handler(idx)

            rl.addWidget(edit_btn)
            rl.addWidget(del_btn)
            self.list_layout.addWidget(row)

        self.list_layout.addStretch()

    def _open_edit(self, index=None):
        presets = load_presets()
        preset = presets[index] if index is not None and 0 <= index < len(presets) else {"name": "", "cli_args": [], "settings": {}}
        win = PresetEditWindow(
            preset=preset,
            on_save=lambda p: self._save_preset(p, index),
            parent=self
        )
        win.show()

    def _save_preset(self, preset, index=None):
        self._refresh_list()
        if self._on_presets_changed:
            self._on_presets_changed()

    def _delete_preset(self, index):
        presets = load_presets()
        if 0 <= index < len(presets):
            filepath = presets[index].get("_filepath")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            self._refresh_list()
            if self._on_presets_changed:
                self._on_presets_changed()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 36:
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


class AddWorkspaceWindow(QWidget):
    def __init__(self, on_confirm=None, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._on_confirm = on_confirm
        self._drag_pos = None
        self.resize(360, 180)
        self._build_ui()
        self._center_on_parent()

    def _center_on_parent(self):
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.center().x() - self.width() // 2
            y = parent_geo.center().y() - self.height() // 2
            self.move(x, y)

    def _build_ui(self):
        self.setStyleSheet(f"background: {COLORS['window_bg']}; border-radius: 8px;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(36)
        header.setStyleSheet(f"background: {COLORS['header_bg']}; border-bottom: 1px solid #e2e8f0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        title = QLabel("添加工作区")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['title']};")
        hl.addWidget(title)
        hl.addStretch()
        close_btn = QLabel("×")
        close_btn.setFont(QFont("Microsoft YaHei", 14))
        close_btn.setStyleSheet("color: #94a3b8; background: transparent; padding: 0 4px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self.close() if e.button() == Qt.MouseButton.LeftButton else None
        hl.addWidget(close_btn)
        root.addWidget(header)

        # Form
        form = QVBoxLayout()
        form.setContentsMargins(16, 12, 16, 12)
        form.setSpacing(10)

        # 第一行：工作区
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl1 = QLabel("工作区:")
        lbl1.setFont(QFont("Microsoft YaHei", 9))
        lbl1.setStyleSheet(f"color: {COLORS['subtitle']};")
        row1.addWidget(lbl1)

        self.workspace_combo = QComboBox()
        self.workspace_combo.setEditable(True)
        self.workspace_combo.setFont(QFont("Microsoft YaHei", 10))
        self.workspace_combo.setStyleSheet(
            f"QComboBox {{ background: {COLORS['card_bg']}; color: {COLORS['title']}; "
            f"border: 1px solid {COLORS['card_border']}; border-radius: 4px; padding: 6px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background: {COLORS['card_bg']}; color: {COLORS['title']}; }}"
        )
        for ws in load_history():
            self.workspace_combo.addItem(ws)
        row1.addWidget(self.workspace_combo, 1)

        browse_btn = QLabel("浏览")
        browse_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        browse_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        browse_btn.setFixedHeight(28)
        browse_btn.setFixedWidth(48)
        browse_btn.setStyleSheet(
            f"background: {COLORS['header_accent']}; color: white; border-radius: 4px; padding: 4px 8px;"
        )
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        def _on_browse(event):
            if event.button() == Qt.MouseButton.LeftButton:
                from PySide6.QtWidgets import QFileDialog
                folder = QFileDialog.getExistingDirectory(self, "选择项目文件夹")
                if folder:
                    self.workspace_combo.setCurrentText(folder)
        browse_btn.mousePressEvent = _on_browse
        row1.addWidget(browse_btn)

        form.addLayout(row1)

        # 第二行：预设
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        lbl2 = QLabel("预设:")
        lbl2.setFont(QFont("Microsoft YaHei", 9))
        lbl2.setStyleSheet(f"color: {COLORS['subtitle']};")
        row2.addWidget(lbl2)

        self.preset_combo = QComboBox()
        self.preset_combo.setFont(QFont("Microsoft YaHei", 10))
        self.preset_combo.setStyleSheet(
            f"QComboBox {{ background: {COLORS['card_bg']}; color: {COLORS['title']}; "
            f"border: 1px solid {COLORS['card_border']}; border-radius: 4px; padding: 6px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background: {COLORS['card_bg']}; color: {COLORS['title']}; }}"
        )
        presets = load_presets()
        for p in presets:
            self.preset_combo.addItem(p["name"])
        row2.addWidget(self.preset_combo, 1)

        form.addLayout(row2)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QLabel("取消")
        cancel_btn.setFont(QFont("Microsoft YaHei", 10))
        cancel_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cancel_btn.setFixedHeight(32)
        cancel_btn.setFixedWidth(64)
        cancel_btn.setStyleSheet(
            f"background: {COLORS['card_bg']}; color: {COLORS['title']}; "
            f"border: 1px solid {COLORS['card_border']}; border-radius: 6px; padding: 4px 12px;"
        )
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.mousePressEvent = lambda e: self.close() if e.button() == Qt.MouseButton.LeftButton else None
        btn_row.addWidget(cancel_btn)

        ok_btn = QLabel("确定")
        ok_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        ok_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ok_btn.setFixedHeight(32)
        ok_btn.setFixedWidth(64)
        ok_btn.setStyleSheet(
            f"background: {COLORS['header_accent']}; color: white; border-radius: 6px; padding: 4px 12px;"
        )
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        def _on_ok(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self._do_confirm()
        ok_btn.mousePressEvent = _on_ok
        btn_row.addWidget(ok_btn)

        form.addLayout(btn_row)

        root.addLayout(form)

    def _do_confirm(self):
        folder = self.workspace_combo.currentText().strip()
        if not folder:
            return
        preset_name = self.preset_combo.currentText()
        presets = load_presets()
        preset = next((p for p in presets if p["name"] == preset_name), None)
        if preset is None:
            return

        # Save history
        history = load_history()
        if folder in history:
            history.remove(folder)
        history.insert(0, folder)
        history = history[:20]
        save_history(history)

        if self._on_confirm:
            self._on_confirm(folder, preset)
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 36:
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
        self._new_sessions: set[str] = set()
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

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_click_timeout)
        self._click_session = None

        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._hide_dead_sessions)
        self._hide_dead = False

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

        # 设置按钮
        settings_btn = QLabel("⚙")
        settings_btn.setFont(QFont("Microsoft YaHei", 11))
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"color: {COLORS['status_text']}; background: transparent; border: none; padding: 0 4px;")
        settings_btn.mousePressEvent = lambda e: self._show_preset_manager() if e.button() == Qt.MouseButton.LeftButton else None
        header_layout.addWidget(settings_btn)

        # 添加按钮
        add_btn = QLabel("+")
        add_btn.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"color: {COLORS['header_accent']}; background: transparent; border: none; padding: 0 6px;")
        add_btn.mousePressEvent = lambda e: self._on_add_new() if e.button() == Qt.MouseButton.LeftButton else None
        header_layout.addWidget(add_btn)

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
        self._maybe_schedule_cleanup()
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
                    self._new_sessions.add(s.session_id)
                elif s.status != old.status or s.is_alive != old.is_alive or len(s.tasks) != len(old.tasks):
                    self._changed_sessions.add(s.session_id)

        self._last_sessions = list(sessions)
        self._last_sig = sig

        has_changes = bool(self._changed_sessions or self._new_sessions)

        self.setWindowOpacity(1.0)
        self._opacity_timer.stop()
        self._opacity_timer.start(3000)

        self._rebuild_ui(sessions)

        if (self._changed_sessions or self._new_sessions) and not self._blink_timer.isActive():
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
        self._new_sessions.discard(session_id)
        if not self._changed_sessions and not self._new_sessions:
            self._blink_timer.stop()
        sessions = load_sessions()
        self._rebuild_ui(sessions)

    def _make_row_click_handler(self, session):
        def handler(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self._click_session = session
                self._click_timer.start(250)
                if self._flash_timer.isActive():
                    self._stop_flash()
                event.accept()
        return handler

    def _make_row_double_click_handler(self, session):
        def handler(event):
            self._click_timer.stop()
            self._click_session = None
            if self._flash_timer.isActive():
                self._stop_flash()
            self._show_session_detail(session)
            event.accept()
        return handler

    def _on_click_timeout(self):
        if self._click_session:
            self._acknowledge_change(self._click_session.session_id)
            self._click_session = None

    def _show_session_detail(self, session: Session):
        is_blinking = session.session_id in self._changed_sessions or session.session_id in self._new_sessions
        win = SessionDetailWindow(
            session,
            on_acknowledge=self._acknowledge_change if is_blinking else None,
            parent=self
        )
        win.show()

    def _toggle_view_mode(self):
        new_mode = ViewMode.DETAIL if self._view_mode == ViewMode.COMPACT else ViewMode.COMPACT
        self._set_view_mode(new_mode)

    def _show_preset_manager(self):
        win = PresetManagerWindow(parent=self)
        win.show()

    def _on_add_new(self):
        def _on_confirm(folder, preset):
            args = list(preset["cli_args"])
            import subprocess
            if args:
                quoted = " ".join(f"'{a}'" for a in args)
                cmd = f"Set-Location '{folder}'; claude {quoted}"
            else:
                cmd = f"Set-Location '{folder}'; claude"
            subprocess.Popen(
                ["pwsh.exe", "-NoExit", "-Command", cmd],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

        win = AddWorkspaceWindow(on_confirm=_on_confirm, parent=self)
        win.show()

    def _locate_window(self, pid: int):
        import ctypes
        from ctypes import wintypes

        def _get_hwnds_for_pid(target_pid: int) -> list:
            results = []

            def callback(hwnd, _):
                if not ctypes.windll.user32.IsWindowVisible(hwnd):
                    return True
                proc_id = wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
                if proc_id.value == target_pid:
                    results.append(hwnd)
                return True

            EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            proc = EnumWindowsProc(callback)
            ctypes.windll.user32.EnumWindows(proc, 0)
            return results

        def _bring_to_front(hwnd: int):
            SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)

            fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
            fg_thread = ctypes.windll.user32.GetWindowThreadProcessId(fg_hwnd, None)
            my_thread = ctypes.windll.kernel32.GetCurrentThreadId()

            if fg_thread != my_thread:
                ctypes.windll.user32.AttachThreadInput(fg_thread, my_thread, True)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.AttachThreadInput(fg_thread, my_thread, False)
            else:
                ctypes.windll.user32.SetForegroundWindow(hwnd)

        # Try target pid
        hwnds = _get_hwnds_for_pid(pid)
        if hwnds:
            _bring_to_front(hwnds[0])
            return

        # Try parent / ancestors
        try:
            import psutil
            proc = psutil.Process(pid)
            candidates = []
            parent = proc.parent()
            if parent is not None:
                candidates.append(parent)
            candidates.extend(proc.parents())
            for candidate in candidates:
                hwnds = _get_hwnds_for_pid(candidate.pid)
                if hwnds:
                    _bring_to_front(hwnds[0])
                    return
        except Exception:
            pass

    def _maybe_schedule_cleanup(self):
        sessions = load_sessions()
        has_dead = any(not s.is_alive for s in sessions)
        if has_dead and not self._cleanup_timer.isActive():
            self._cleanup_timer.start(5000)

    def _hide_dead_sessions(self):
        self._hide_dead = True
        self.refresh()

    def _set_view_mode(self, mode: ViewMode):
        if self._view_mode == mode:
            return
        self._view_mode = mode

        # 按钮显示要切换到的目标模式图标
        self.toggle_btn.setText("⊞" if mode == ViewMode.COMPACT else "≡")

        if mode == ViewMode.COMPACT:
            self.setMinimumSize(200, 180)
            self.resize(260, 360)
        else:
            self.setMinimumSize(500, 400)
            self.resize(1100, 700)

        sessions = load_sessions()
        self._rebuild_ui(sessions)

    def _rebuild_ui(self, sessions: list[Session]):
        if self._hide_dead:
            sessions = [s for s in sessions if s.is_alive]
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        # 清除详细模式下残留的列拉伸设置，防止紧凑模式宽度异常
        for col in range(20):
            self.grid_layout.setColumnStretch(col, 0)

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
                is_new = session.session_id in self._new_sessions
                blinking = session.session_id in self._changed_sessions or is_new
                row = _make_compact_row(
                    session, blinking, self._blink_phase, is_new,
                    on_locate=lambda pid=session.pid: self._locate_window(pid)
                )
                row.mousePressEvent = self._make_row_click_handler(session)
                if blinking:
                    row.mouseDoubleClickEvent = self._make_row_double_click_handler(session)
                self.grid_layout.addWidget(row, i, 0)
        else:
            width = self.scroll.viewport().width() - 48
            cols = max(1, width // self.CARD_MIN_WIDTH)
            for i, session in enumerate(sessions):
                row = i // cols
                col = i % cols
                is_new = session.session_id in self._new_sessions
                blinking = session.session_id in self._changed_sessions or is_new
                card = _make_card(
                    session, blinking, self._blink_phase, is_new,
                    on_locate=lambda pid=session.pid: self._locate_window(pid)
                )
                card.mousePressEvent = self._make_row_click_handler(session)
                if blinking:
                    card.mouseDoubleClickEvent = self._make_row_double_click_handler(session)
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
