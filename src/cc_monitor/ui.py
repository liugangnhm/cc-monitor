"""Claude Code Monitor GUI."""

import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from cc_monitor.data import load_sessions, Session, Task

# Task status visual config
TASK_STYLES = {
    "completed":  {"icon": "✓", "color": SUCCESS,  "fg": "#2e7d32"},
    "in_progress": {"icon": "◎", "color": WARNING,  "fg": "#e65100"},
    "pending":    {"icon": "○", "color": SECONDARY, "fg": "#757575"},
}

SESSION_STYLES = {
    "busy": {"text": "工作中", "icon": "⚡", "color": WARNING},
    "idle": {"text": "就绪",   "icon": "●",  "color": INFO},
}


class MonitorApp:
    REFRESH_INTERVAL_MS = 2000
    CARD_MIN_WIDTH = 300

    def __init__(self, root: ttkb.Window):
        self.root = root
        self.root.title("Claude Code Monitor")
        self.root.geometry("1200x700")
        self.root.minsize(500, 400)
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)

        self._sessions: list[Session] = []
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
            text="⬡",
            font=("Segoe UI Emoji", 18),
        ).pack(side=LEFT, padx=(0, 6))

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
            self._relayout()

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

    def _relayout(self):
        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 1:
            return

        cols = self._calc_columns(canvas_width)
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

        card = ttk.Frame(self.grid_frame, padding=12)
        card.grid(row=row, column=col, padx=8, pady=8, sticky=NSEW)
        card.columnconfigure(0, weight=1)

        # Apply card border via themed LabelFrame wrapper
        card_border = ttk.LabelFrame(
            self.grid_frame,
            text=f"  {project_name}  ",
            padding=12,
        )
        card_border.grid(row=row, column=col, padx=8, pady=8, sticky=NSEW)
        card_border.columnconfigure(0, weight=1)

        # Reassign card to the LabelFrame
        card = card_border

        # Session status badge
        if session.is_alive:
            style = SESSION_STYLES.get(session.status, SESSION_STYLES["idle"])
            badge_frame = ttk.Frame(card)
            badge_frame.grid(row=0, column=0, sticky=W, pady=(0, 8))

            badge = ttk.Label(
                badge_frame,
                text=f" {style['icon']}  {style['text']} ",
                font=("Helvetica", 10, "bold"),
                bootstyle=style["color"],
            )
            badge.pack(side=LEFT)

        # Separator
        ttk.Separator(card).grid(row=1, column=0, sticky=EW, pady=(0, 8))

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
        task_frame.grid(row=row, column=0, sticky=EW, pady=3)

        icon_label = ttk.Label(
            task_frame,
            text=ts["icon"],
            font=("Segoe UI", 12, "bold"),
            bootstyle=ts["color"],
        )
        icon_label.pack(side=LEFT, padx=(0, 6))

        ttk.Label(
            task_frame,
            text=task.subject,
            font=("Helvetica", 9),
            wraplength=220,
        ).pack(side=LEFT, fill=X)

    def refresh(self):
        self._sessions = load_sessions()
        self._relayout()

        now = datetime.now().strftime("%H:%M:%S")
        count = len(self._sessions)
        self.status_bar.config(text=f"最后刷新: {now} | 共 {count} sessions")

        self.root.after(self.REFRESH_INTERVAL_MS, self.refresh)
