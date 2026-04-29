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
    except psutil.AccessDenied:
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
