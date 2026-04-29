# Claude Code Monitor 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个置顶 GUI 小工具，实时监控 Claude Code 的 Session 和 Task 状态。

**Architecture:** 分层架构，`data.py` 负责读取 Claude Code 内部 JSON 和进程检测，`ui.py` 负责 ttkbootstrap 界面渲染和定时刷新，`main.py` 作为入口。TDD 驱动开发，先写测试再实现。

**Tech Stack:** Python 3.12+, ttkbootstrap, psutil, pytest, uv

---

## 文件结构

```
cc_monitor/
├── pyproject.toml
├── uv.lock
├── README.md
├── src/
│   └── cc_monitor/
│       ├── __init__.py
│       ├── data.py         # Session/Task 模型 + 数据读取 + 进程检测
│       ├── ui.py           # MonitorApp GUI 类
│       └── main.py         # 入口
└── tests/
    ├── test_data.py        # data.py 单元测试
    └── test_ui.py          # ui.py 单元测试
```

---

### Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `src/cc_monitor/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: 初始化 uv 项目并安装依赖**

Run:
```bash
cd D:\my\projects\cc_monitor
uv init --package cc-monitor
uv add ttkbootstrap psutil
uv add --dev pytest
```

Expected: `pyproject.toml` 创建，`uv.lock` 生成，`src/cc_monitor/` 目录存在。

- [ ] **Step 2: 验证目录结构**

Run: `ls -R src/`
Expected:
```
src/
cc_monitor/
    __init__.py
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "init: uv project with ttkbootstrap, psutil, pytest"
```

---

### Task 2: data.py 测试

**Files:**
- Create: `tests/test_data.py`

- [ ] **Step 1: 编写 Session/Task 模型及 load_sessions 测试**

```python
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from cc_monitor.data import Task, Session, load_sessions, load_tasks, is_process_alive


class TestTask:
    def test_task_creation(self):
        task = Task(id="1", subject="测试任务", status="pending")
        assert task.id == "1"
        assert task.subject == "测试任务"
        assert task.status == "pending"


class TestSession:
    def test_session_creation(self):
        session = Session(
            pid=1234,
            session_id="test-uuid",
            cwd="D:\\project",
            name="test-session",
            status="idle",
            is_alive=True,
            tasks=[],
        )
        assert session.pid == 1234
        assert session.is_alive is True


class TestLoadSessions:
    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("builtins.open")
    @patch("cc_monitor.data.is_process_alive")
    def test_load_sessions_success(self, mock_alive, mock_open, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = ["1234.json"]

        session_data = {
            "pid": 1234,
            "sessionId": "uuid-1",
            "cwd": "D:\\project",
            "name": "test-session",
            "status": "idle",
            "startedAt": 1234567890,
        }
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = json.dumps(session_data)
        mock_open.return_value = mock_file

        mock_alive.return_value = True

        with patch("cc_monitor.data.load_tasks", return_value=[]) as mock_load_tasks:
            sessions = load_sessions()

        assert len(sessions) == 1
        assert sessions[0].pid == 1234
        assert sessions[0].session_id == "uuid-1"
        assert sessions[0].is_alive is True
        mock_load_tasks.assert_called_once_with("uuid-1")

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    def test_load_sessions_empty(self, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = []

        sessions = load_sessions()
        assert sessions == []

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    def test_load_sessions_ignores_non_json(self, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = [".highwatermark", "not-json.txt"]

        sessions = load_sessions()
        assert sessions == []


class TestLoadTasks:
    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("builtins.open")
    def test_load_tasks_success(self, mock_open, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = ["1.json", "2.json", ".lock", ".highwatermark"]

        task1_data = {"id": "1", "subject": "任务1", "status": "completed"}
        task2_data = {"id": "2", "subject": "任务2", "status": "in_progress"}

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.side_effect = [json.dumps(task1_data), json.dumps(task2_data)]
        mock_open.return_value = mock_file

        tasks = load_tasks("test-session-id")

        assert len(tasks) == 2
        assert tasks[0].status == "completed"
        assert tasks[1].status == "in_progress"

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    def test_load_tasks_empty(self, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = []

        tasks = load_tasks("test-session-id")
        assert tasks == []


class TestIsProcessAlive:
    @patch("cc_monitor.data.psutil.Process")
    def test_process_alive(self, mock_process_class):
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process

        assert is_process_alive(1234) is True

    @patch("cc_monitor.data.psutil.Process")
    def test_process_dead(self, mock_process_class):
        mock_process = MagicMock()
        mock_process.is_running.return_value = False
        mock_process_class.return_value = mock_process

        assert is_process_alive(1234) is False

    @patch("cc_monitor.data.psutil.Process")
    def test_process_not_found(self, mock_process_class):
        import psutil
        mock_process_class.side_effect = psutil.NoSuchProcess(1234)

        assert is_process_alive(1234) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_data.py -v`
Expected: ImportError / ModuleNotFoundError — `cc_monitor.data` 不存在

- [ ] **Step 3: Commit**

```bash
git add tests/test_data.py
git commit -m "test: add data.py unit tests"
```

---

### Task 3: data.py 实现

**Files:**
- Create: `src/cc_monitor/data.py`

- [ ] **Step 1: 实现数据层**

```python
"""Claude Code 数据读取层."""

import json
import os
from dataclasses import dataclass
from typing import List

import psutil


@dataclass
class Task:
    id: str
    subject: str
    status: str


@dataclass
class Session:
    pid: int
    session_id: str
    cwd: str
    name: str | None
    status: str
    is_alive: bool
    tasks: list[Task]


def _claude_dir() -> str:
    return os.path.expanduser("~/.claude")


def is_process_alive(pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
        return proc.is_running()
    except psutil.NoSuchProcess:
        return False


def load_tasks(session_id: str) -> list[Task]:
    tasks_dir = os.path.join(_claude_dir(), "tasks", session_id)
    if not os.path.exists(tasks_dir):
        return []

    tasks: list[Task] = []
    for filename in os.listdir(tasks_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(tasks_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            tasks.append(
                Task(
                    id=str(data.get("id", "")),
                    subject=data.get("subject", "未知任务"),
                    status=data.get("status", "pending"),
                )
            )
        except (json.JSONDecodeError, OSError):
            continue

    return tasks


def load_sessions() -> list[Session]:
    sessions_dir = os.path.join(_claude_dir(), "sessions")
    if not os.path.exists(sessions_dir):
        return []

    sessions: list[Session] = []
    for filename in os.listdir(sessions_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(sessions_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        pid = data.get("pid", 0)
        is_alive = is_process_alive(pid) if pid else False

        session_id = data.get("sessionId", "")
        tasks = load_tasks(session_id) if session_id else []

        sessions.append(
            Session(
                pid=pid,
                session_id=session_id,
                cwd=data.get("cwd", ""),
                name=data.get("name"),
                status=data.get("status", "idle"),
                is_alive=is_alive,
                tasks=tasks,
            )
        )

    return sessions
```

- [ ] **Step 2: 运行测试确认通过**

Run: `uv run pytest tests/test_data.py -v`
Expected: 8 tests passed

- [ ] **Step 3: Commit**

```bash
git add src/cc_monitor/data.py
git commit -m "feat: implement data layer for session/task loading"
```

---

### Task 4: ui.py 实现

**Files:**
- Create: `src/cc_monitor/ui.py`

- [ ] **Step 1: 实现 GUI**

```python
"""Claude Code Monitor GUI."""

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
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        count = len(sessions)
        self.status_bar.config(text=f"最后刷新: {now} | 共 {count} sessions")

        # Schedule next refresh
        self.root.after(self.REFRESH_INTERVAL_MS, self.refresh)
```

- [ ] **Step 2: Commit**

```bash
git add src/cc_monitor/ui.py
git commit -m "feat: implement MonitorApp GUI with ttkbootstrap"
```

---

### Task 5: main.py 入口

**Files:**
- Create: `src/cc_monitor/main.py`

- [ ] **Step 1: 实现入口**

```python
"""Claude Code Monitor entry point."""

import ttkbootstrap as ttkb

from cc_monitor.ui import MonitorApp


def main():
    app = ttkb.Window(themename="darkly")
    MonitorApp(app)
    app.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/cc_monitor/main.py
git commit -m "feat: add main entry point"
```

---

### Task 6: 运行验证

- [ ] **Step 1: 运行程序**

Run: `uv run cc-monitor`

Expected:
- 窗口弹出，标题 "Claude Code Monitor"
- 窗口固定在最顶层
- 显示当前活跃的 Claude Code Session 列表
- 每个 Session 下显示任务及状态颜色
- 底部状态栏显示刷新时间和 Session 计数
- 每 2 秒自动刷新

- [ ] **Step 2: 验证状态颜色**

确认：
- 🟢 completed 任务显示绿色圆点
- 🟡 in_progress 任务显示黄色圆点
- ⚪ pending 任务显示灰色圆点
- 🔴 idle Session 显示 "等待回答" 红色标签
- busy Session 无特殊标记

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat: complete cc monitor with verification"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 扫描并展示 Session 列表 → Task 3 (data.py) + Task 4 (ui.py)
- ✅ 每个 Session 下展示任务 → Task 3 + Task 4
- ✅ 颜色区分状态 → Task 4 (`_status_color`, idle badge)
- ✅ 每 2 秒自动刷新 → Task 4 (`REFRESH_INTERVAL_MS`, `after`)
- ✅ 窗口固定最顶层 → Task 4 (`-topmost`)
- ✅ 纯展示无交互 → 无按钮/事件绑定

**2. Placeholder scan:**
- ✅ 无 TBD/TODO
- ✅ 无 "add appropriate error handling" 等模糊描述
- ✅ 每个步骤都有完整代码
- ✅ 无 "similar to Task N"

**3. Type consistency:**
- ✅ `Session` / `Task` dataclass 在 Task 2 测试和 Task 3 实现中一致
- ✅ `load_sessions()` / `load_tasks()` 签名一致
- ✅ `is_process_alive(pid: int)` 签名一致
