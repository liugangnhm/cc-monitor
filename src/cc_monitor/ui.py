"""Claude Code Monitor GUI."""

import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from cc_monitor.data import load_sessions, Session, Task


class MonitorApp:
    REFRESH_INTERVAL_MS = 2000  # 2 seconds
    CARD_MIN_WIDTH = 280  # minimum card width in pixels

    def __init__(self, root: ttkb.Window):
        self.root = root
        self.root.title("Claude Code Monitor")
        self.root.geometry("1200x700")
        self.root.minsize(400, 300)
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)

        self._sessions: list[Session] = []
        self._build_ui()
        self.refresh()

    def _calc_columns(self, canvas_width: int) -> int:
        cols = max(1, canvas_width // self.CARD_MIN_WIDTH)
        return cols

    def _build_ui(self):
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=BOTH, expand=True)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        # Title
        self.title_label = ttk.Label(
            self.main_frame,
            text="Claude Code Monitor",
            font=("Helvetica", 16, "bold"),
        )
        self.title_label.grid(row=0, column=0, sticky=W, pady=(0, 10))

        # Scrollable grid container
        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.main_frame, orient=VERTICAL, command=self.canvas.yview
        )
        self.grid_frame = ttk.Frame(self.canvas)

        self._grid_window_id = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor=NW
        )

        def _on_canvas_configure(event):
            width = event.width
            self.canvas.itemconfig(self._grid_window_id, width=width)
            self._relayout()

        self.canvas.bind("<Configure>", _on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=1, column=0, sticky=NSEW)
        self.scrollbar.grid(row=1, column=1, sticky=NS)

        # Status bar
        self.status_bar = ttk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 9),
            foreground="gray",
        )
        self.status_bar.grid(row=2, column=0, sticky=W, pady=(10, 0))

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _status_color(self, status: str) -> str:
        mapping = {
            "completed": SUCCESS,
            "in_progress": WARNING,
            "pending": SECONDARY,
        }
        return mapping.get(status, SECONDARY)

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
            empty_label = ttk.Label(
                self.grid_frame,
                text="未检测到活跃 Session",
                font=("Helvetica", 12),
                foreground="gray",
            )
            empty_label.grid(row=0, column=0, columnspan=max(cols, 1), pady=40)
        else:
            for i, session in enumerate(self._sessions):
                row = i // cols
                col = i % cols
                self._render_session(session, row, col)

        self.grid_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_session(self, session: Session, row: int, col: int):
        project_name = session.name or os.path.basename(session.cwd) or "Unknown"

        card = ttk.LabelFrame(
            self.grid_frame,
            text=project_name,
            padding=10,
        )
        card.grid(row=row, column=col, padx=10, pady=10, sticky=NSEW)
        card.columnconfigure(0, weight=1)

        # Session status indicator
        if session.is_alive and session.status == "busy":
            busy_badge = ttk.Label(
                card,
                text=" 工作中 ",
                font=("Helvetica", 9),
                bootstyle=WARNING,
            )
            busy_badge.grid(row=0, column=0, sticky=W, pady=(0, 8))
        elif session.is_alive and session.status == "idle":
            ready_badge = ttk.Label(
                card,
                text=" 就绪 ",
                font=("Helvetica", 9),
                bootstyle=INFO,
            )
            ready_badge.grid(row=0, column=0, sticky=W, pady=(0, 8))

        # Tasks
        if session.tasks:
            for idx, task in enumerate(session.tasks):
                self._render_task(card, task, row=idx + 1)
        else:
            no_tasks = ttk.Label(
                card,
                text="无任务",
                font=("Helvetica", 9),
                foreground="gray",
            )
            no_tasks.grid(row=1, column=0, sticky=W)

    def _render_task(self, parent: ttk.Frame, task: Task, row: int):
        color = self._status_color(task.status)
        dot = "●"

        task_frame = ttk.Frame(parent)
        task_frame.grid(row=row, column=0, sticky=EW, pady=(2, 0))

        dot_label = ttk.Label(
            task_frame,
            text=dot,
            font=("Helvetica", 10),
            bootstyle=color,
        )
        dot_label.pack(side=LEFT)

        text = f" {task.subject}"
        task_label = ttk.Label(
            task_frame,
            text=text,
            font=("Helvetica", 9),
        )
        task_label.pack(side=LEFT)

    def refresh(self):
        self._sessions = load_sessions()
        self._relayout()

        # Update status bar
        now = datetime.now().strftime("%H:%M:%S")
        count = len(self._sessions)
        self.status_bar.config(text=f"最后刷新: {now} | 共 {count} sessions")

        # Schedule next refresh
        self.root.after(self.REFRESH_INTERVAL_MS, self.refresh)
