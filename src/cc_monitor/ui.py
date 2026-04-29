"""Claude Code Monitor GUI."""

import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from cc_monitor.data import load_sessions, Session, Task

TASK_STYLES = {
    "completed":   {"icon": "✓", "color": SUCCESS},
    "in_progress": {"icon": "◎", "color": WARNING},
    "pending":     {"icon": "○", "color": SECONDARY},
}

SESSION_STYLES = {
    "busy": {"text": "工作中", "icon": "⚡", "color": WARNING},
    "idle": {"text": "就绪",   "icon": "●",  "color": INFO},
}


def _session_signature(session: Session) -> str:
    """Compact string representing session state for change detection."""
    tasks_str = "|".join(f"{t.id}:{t.status}:{t.subject}" for t in session.tasks)
    return f"{session.session_id}:{session.status}:{session.is_alive}:{tasks_str}"


class MonitorApp:
    REFRESH_INTERVAL_MS = 2000
    CARD_MIN_WIDTH = 220

    def __init__(self, root: ttkb.Window):
        self.root = root
        self.root.title("Claude Code Monitor")
        self.root.geometry("1200x700")
        self.root.minsize(500, 400)
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)

        self._sessions: list[Session] = []
        self._last_signature: str = ""
        self._last_cols: int = 0
        self._build_ui()
        self.refresh()

    def _calc_columns(self, canvas_width: int) -> int:
        return max(1, canvas_width // self.CARD_MIN_WIDTH)

    def _build_ui(self):
        self.main_frame = ttk.Frame(self.root, padding=(15, 10))
        self.main_frame.pack(fill=BOTH, expand=True)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky=EW, pady=(0, 12))

        ttk.Label(
            header_frame,
            text="Claude Code Monitor",
            font=("Helvetica", 16, "bold"),
        ).pack(side=LEFT)

        self.status_bar = ttk.Label(
            header_frame,
            text="",
            font=("Helvetica", 9),
            foreground="gray",
        )
        self.status_bar.pack(side=RIGHT)

        # Canvas + Scrollbar
        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.main_frame, orient=VERTICAL, command=self.canvas.yview
        )
        self.grid_frame = ttk.Frame(self.canvas)

        self._grid_window_id = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor=NW
        )

        def _on_canvas_configure(event):
            self.canvas.itemconfig(self._grid_window_id, width=event.width)
            new_cols = self._calc_columns(event.width)
            if new_cols != self._last_cols:
                self._last_cols = new_cols
                self._full_relayout()

        self.canvas.bind("<Configure>", _on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=1, column=0, sticky=NSEW)
        self.scrollbar.grid(row=1, column=1, sticky=NS)

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _clear_grid(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

    def _full_relayout(self):
        """Destroy and rebuild all cards."""
        cols = self._last_cols or 1
        self._clear_grid()

        for col in range(cols):
            self.grid_frame.columnconfigure(col, weight=1, uniform="session")

        if not self._sessions:
            ttk.Label(
                self.grid_frame,
                text="未检测到活跃 Session",
                font=("Helvetica", 12),
                foreground="gray",
            ).grid(row=0, column=0, columnspan=max(cols, 1), pady=60)
        else:
            for i, session in enumerate(self._sessions):
                self._render_session(session, i // cols, i % cols)

        self.grid_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_session(self, session: Session, row: int, col: int):
        project_name = session.name or os.path.basename(session.cwd) or "Unknown"

        card = ttk.LabelFrame(
            self.grid_frame,
            text=f"  {project_name}  ",
            padding=10,
        )
        card.grid(row=row, column=col, padx=6, pady=6, sticky=NSEW)
        card.columnconfigure(0, weight=1)

        # Session status badge
        if session.is_alive:
            style = SESSION_STYLES.get(session.status, SESSION_STYLES["idle"])
            badge = ttk.Label(
                card,
                text=f" {style['icon']}  {style['text']} ",
                font=("Helvetica", 10, "bold"),
                bootstyle=style["color"],
            )
            badge.grid(row=0, column=0, sticky=W, pady=(0, 6))

        # Separator
        ttk.Separator(card).grid(row=1, column=0, sticky=EW, pady=(0, 6))

        # Tasks
        if session.tasks:
            for idx, task in enumerate(session.tasks):
                self._render_task(card, task, row=idx + 2)
        else:
            ttk.Label(
                card,
                text="暂无任务",
                font=("Helvetica", 9),
                foreground="gray",
            ).grid(row=2, column=0, sticky=W, pady=4)

    def _render_task(self, parent: ttk.Frame, task: Task, row: int):
        ts = TASK_STYLES.get(task.status, TASK_STYLES["pending"])

        task_frame = ttk.Frame(parent)
        task_frame.grid(row=row, column=0, sticky=EW, pady=2)

        ttk.Label(
            task_frame,
            text=ts["icon"],
            font=("Segoe UI", 11, "bold"),
            bootstyle=ts["color"],
        ).pack(side=LEFT, padx=(0, 4))

        ttk.Label(
            task_frame,
            text=task.subject,
            font=("Helvetica", 9),
        ).pack(side=LEFT, fill=X)

    def refresh(self):
        self._sessions = load_sessions()

        # Build signature to detect changes
        sig = "|".join(_session_signature(s) for s in self._sessions)

        # Only rebuild if data or layout changed
        if sig != self._last_signature:
            self._last_signature = sig
            self._full_relayout()

        # Always update status bar time
        now = datetime.now().strftime("%H:%M:%S")
        count = len(self._sessions)
        self.status_bar.config(text=f"最后刷新: {now} | 共 {count} sessions")

        self.root.after(self.REFRESH_INTERVAL_MS, self.refresh)
