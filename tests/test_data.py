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
    @patch("cc_monitor.data.os.path.exists", return_value=True)
    @patch("builtins.open")
    @patch("cc_monitor.data.is_process_alive")
    def test_load_sessions_success(self, mock_alive, mock_open, mock_exists, mock_expanduser, mock_listdir):
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

        mocked_tasks = [Task(id="t1", subject="task1", status="pending")]
        with patch("cc_monitor.data.load_tasks", return_value=mocked_tasks) as mock_load_tasks:
            sessions = load_sessions()

        assert len(sessions) == 1
        assert sessions[0].pid == 1234
        assert sessions[0].session_id == "uuid-1"
        assert sessions[0].cwd == "D:\\project"
        assert sessions[0].name == "test-session"
        assert sessions[0].status == "idle"
        assert sessions[0].is_alive is True
        assert sessions[0].tasks is mocked_tasks
        mock_load_tasks.assert_called_once_with("uuid-1")

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("cc_monitor.data.os.path.exists", return_value=True)
    def test_load_sessions_empty(self, mock_exists, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = []

        sessions = load_sessions()
        assert sessions == []

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("cc_monitor.data.os.path.exists", return_value=True)
    def test_load_sessions_ignores_non_json(self, mock_exists, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = [".highwatermark", "not-json.txt"]

        sessions = load_sessions()
        assert sessions == []

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("cc_monitor.data.os.path.exists", return_value=True)
    @patch("builtins.open")
    @patch("cc_monitor.data.is_process_alive")
    def test_load_sessions_skips_invalid_json(self, mock_alive, mock_open, mock_exists, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = ["1234.json", "5678.json"]

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.side_effect = ["not json", json.dumps({"pid": 5678, "sessionId": "uuid-2"})]
        mock_open.return_value = mock_file

        mock_alive.return_value = True

        with patch("cc_monitor.data.load_tasks", return_value=[]) as mock_load_tasks:
            sessions = load_sessions()

        assert len(sessions) == 1
        assert sessions[0].pid == 5678
        assert sessions[0].session_id == "uuid-2"


class TestLoadTasks:
    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("cc_monitor.data.os.path.exists", return_value=True)
    @patch("builtins.open")
    def test_load_tasks_success(self, mock_open, mock_exists, mock_expanduser, mock_listdir):
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
        assert tasks[0].subject == "任务1"
        assert tasks[0].status == "completed"
        assert tasks[1].subject == "任务2"
        assert tasks[1].status == "in_progress"

        subjects = [t.subject for t in tasks]
        assert ".lock" not in subjects
        assert ".highwatermark" not in subjects

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("cc_monitor.data.os.path.exists", return_value=True)
    def test_load_tasks_empty(self, mock_exists, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = []

        tasks = load_tasks("test-session-id")
        assert tasks == []

    @patch("cc_monitor.data.os.listdir")
    @patch("cc_monitor.data.os.path.expanduser")
    @patch("cc_monitor.data.os.path.exists", return_value=True)
    @patch("builtins.open")
    def test_load_tasks_skips_invalid_json(self, mock_open, mock_exists, mock_expanduser, mock_listdir):
        mock_expanduser.return_value = "C:\\Users\\test\\.claude"
        mock_listdir.return_value = ["1.json", "2.json"]

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.side_effect = ["not json", json.dumps({"id": "2", "subject": "任务2", "status": "pending"})]
        mock_open.return_value = mock_file

        tasks = load_tasks("test-session-id")

        assert len(tasks) == 1
        assert tasks[0].id == "2"
        assert tasks[0].subject == "任务2"


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

    @patch("cc_monitor.data.psutil.Process")
    def test_is_process_alive_access_denied(self, mock_process_class):
        import psutil
        mock_process_class.side_effect = psutil.AccessDenied(1234)

        assert is_process_alive(1234) is False
