# Claude Code 任务监控器设计文档

## 概述

一个轻量级 GUI 小工具，用于实时监控本地 Claude Code CLI 的活跃 Session 及其任务状态。

- **固定在最顶层**，随时可见
- **纯展示，无交互**
- **颜色区分状态**，一目了然

## 功能范围

### 包含

- 扫描并展示当前活跃的 Claude Code Session 列表
- 每个 Session 下展示其任务列表及状态
- 用颜色区分不同状态
- 每 2 秒自动刷新
- 窗口固定最顶层

### 不包含

- 系统托盘最小化
- 点击交互/操作
- 历史记录持久化
- 通知/弹窗提醒

## 数据模型

### Session

| 字段 | 来源 | 说明 |
|------|------|------|
| pid | `sessions/<pid>.json` | 进程 ID |
| session_id | `sessions/<pid>.json` | UUID |
| cwd | `sessions/<pid>.json` | 项目路径 |
| name | `sessions/<pid>.json` | Session 名称（可能为空） |
| status | `sessions/<pid>.json` | `idle` / `busy` |
| is_alive | 进程检测 | 进程是否存活 |
| tasks | `tasks/<sid>/*.json` | 任务列表 |

### Task

| 字段 | 来源 | 说明 |
|------|------|------|
| id | `tasks/<sid>/<id>.json` | 任务 ID |
| subject | `tasks/<sid>/<id>.json` | 任务标题 |
| status | `tasks/<sid>/<id>.json` | `pending` / `in_progress` / `completed` |

### 状态映射

| 层级 | 状态 | 颜色 | 说明 |
|------|------|------|------|
| Session | idle（进程存活） | 🔴 红色标签 | 等待用户回到终端回答问题 |
| Session | busy（进程存活） | 无特殊标记 | 任务正在执行 |
| Session | 进程死亡 | ⚫ 灰色/隐藏 | Session 已结束，不展示 |
| Task | completed | 🟢 绿色 | 已完成 |
| Task | in_progress | 🟡 黄色 | 进行中 |
| Task | pending | ⚪ 灰色 | 待处理 |

## 架构

```
cc_monitor/
├── pyproject.toml
├── uv.lock
├── README.md
└── src/
    └── cc_monitor/
        ├── __init__.py
        ├── data.py         # 数据层
        ├── ui.py           # UI 层
        └── main.py         # 入口
```

### data.py — 数据层

职责：读取 Claude Code 内部数据，检测进程状态。

```python
@dataclass
class Task:
    id: str
    subject: str
    status: str  # pending | in_progress | completed

@dataclass
class Session:
    pid: int
    session_id: str
    cwd: str
    name: str | None
    status: str  # idle | busy
    is_alive: bool
    tasks: list[Task]

def load_sessions() -> list[Session]: ...
def load_tasks(session_id: str) -> list[Task]: ...
def is_process_alive(pid: int) -> bool: ...
```

数据来源：
- Sessions: `~/.claude/sessions/*.json`
- Tasks: `~/.claude/tasks/<session_id>/*.json`（排除 `.lock` 和 `.highwatermark`）
- 进程检测: Windows `tasklist` / `psutil`

### ui.py — UI 层

职责：ttkbootstrap 界面渲染和定时刷新。

```python
class MonitorApp:
    def __init__(self, root: ttkb.Window): ...
    def refresh(self) -> None: ...      # 重新加载数据并更新 UI
    def _build_ui(self) -> None: ...    # 构建界面
    def _update_display(self, sessions: list[Session]) -> None: ...
```

界面元素：
- 主窗口：400×600，置顶
- Session 列表：项目名称 + 状态标签
- Task 列表：缩进 + 状态圆点 + 标题
- 底部状态栏：最后刷新时间 + Session 计数

### main.py — 入口

```python
def main():
    app = ttkb.Window("Claude Code Monitor", themename="darkly")
    monitor = MonitorApp(app)
    app.mainloop()
```

## 数据流

```
定时器(2s)
  │
  ▼
load_sessions() ──→ 读取 sessions/*.json
  │                    ├── 解析 JSON
  │                    ├── is_process_alive(pid)
  │                    └── load_tasks(session_id)
  │                         └── 读取 tasks/<sid>/*.json
  ▼
_update_display(sessions) ──→ 清空 Treeview
                                └── 插入 Session 行 + Task 行
```

## 错误处理

| 场景 | 策略 |
|------|------|
| Sessions 目录为空 | 显示 "未检测到活跃 Session" |
| JSON 解析失败 | 跳过该文件，记录到状态栏 |
| 进程检测失败 | 保守认为存活，避免误过滤 |
| 权限不足 | 静默跳过，状态栏提示 |

## 依赖

```toml
[project]
name = "cc-monitor"
version = "0.1.0"
dependencies = [
    "ttkbootstrap>=1.10",
    "psutil>=5.9",  # Windows 进程检测
]

[project.scripts]
cc-monitor = "cc_monitor.main:main"
```

## 运行方式

```bash
cd D:\my\projects\cc_monitor
uv run cc-monitor
```
