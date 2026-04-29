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

    def __init__(self, root: ttkb.Window):
        self.root = root
        self.root.title("Claude Code Monitor")
        self.root.geometry("400x600")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, True)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Main container
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=BOTH, expand=True)

        # Title
        self.title_label = ttk.Label(
            self.main_frame,
            text="Claude Code Monitor",
            font=("Helvetica", 14, "bold"),
        )
        self.title_label.pack(anchor=W, pady=(0, 10))

        # Sessions container
        self.sessions_frame = ttk.Frame(self.main_frame)
        self.sessions_frame.pack(fill=BOTH, expand=True)

        # Status bar
        self.status_bar = ttk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 9),
            foreground="gray",
        )
        self.status_bar.pack(anchor=W, pady=(10, 0))

    def _status_color(self, status: str) -> str:
        mapping = {
            "completed": SUCCESS,
            "in_progress": WARNING,
            "pending": SECONDARY,
        }
        return mapping.get(status, SECONDARY)

    def _clear_sessions(self):
        for widget in self.sessions_frame.winfo_children():
            widget.destroy()

    def _render_session(self, session: Session):
        # Session row
        session_frame = ttk.Frame(self.sessions_frame)
        session_frame.pack(fill=X, pady=(5, 0))

        # Project name from cwd
        project_name = session.name or os.path.basename(session.cwd) or "Unknown"
        session_text = f"{project_name}"

        session_label = ttk.Label(
            session_frame,
            text=session_text,
            font=("Helvetica", 11, "bold"),
        )
        session_label.pack(side=LEFT)

        # Idle indicator
        if session.is_alive and session.status == "idle":
            idle_badge = ttk.Label(
                session_frame,
                text=" 等待回答 ",
                font=("Helvetica", 8),
                bootstyle=DANGER,
            )
            idle_badge.pack(side=LEFT, padx=(8, 0))

        # Tasks
        if session.tasks:
            tasks_frame = ttk.Frame(self.sessions_frame)
            tasks_frame.pack(fill=X, padx=(15, 0))

            for task in session.tasks:
                self._render_task(tasks_frame, task)
        else:
            no_tasks = ttk.Label(
                self.sessions_frame,
                text="  无任务",
                font=("Helvetica", 9),
                foreground="gray",
            )
            no_tasks.pack(anchor=W, padx=(15, 0))

    def _render_task(self, parent: ttk.Frame, task: Task):
        task_frame = ttk.Frame(parent)
        task_frame.pack(fill=X, pady=(2, 0))

        color = self._status_color(task.status)
        dot = "●"

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
        sessions = load_sessions()

        self._clear_sessions()

        if not sessions:
            empty_label = ttk.Label(
                self.sessions_frame,
                text="未检测到活跃 Session",
                font=("Helvetica", 10),
                foreground="gray",
            )
            empty_label.pack(pady=20)
        else:
            for session in sessions:
                self._render_session(session)

        # Update status bar
        now = datetime.now().strftime("%H:%M:%S")
        count = len(sessions)
        self.status_bar.config(text=f"最后刷新: {now} | 共 {count} sessions")

        # Schedule next refresh
        self.root.after(self.REFRESH_INTERVAL_MS, self.refresh)
