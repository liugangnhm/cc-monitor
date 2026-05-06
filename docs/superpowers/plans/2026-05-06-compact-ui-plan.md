# 紧凑 UI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Claude Code Monitor 添加紧凑列表视图、无边框可拖动窗口、透明度控制，支持视图切换。

**Architecture:** 在现有 `ui.py` 的 `MonitorWindow` 上扩展，添加 `ViewMode` 枚举区分紧凑/详细模式。紧凑模式使用垂直列表替换网格布局，无边框通过 `FramelessWindowHint` 实现，透明度通过 `QTimer` 自动恢复。

**Tech Stack:** PySide6, Python 3.11+

---

## 文件映射

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/cc_monitor/ui.py` | 大幅修改 | 主窗口类、卡片/列表行组件、透明度、拖动逻辑 |
| `tests/test_ui.py` | 新建 | 视图切换、透明度、无边框窗口的单元测试 |

---

### Task 1: 无边框窗口 + 标题栏 + 可拖动

**Files:**
- Modify: `src/cc_monitor/ui.py:190-210` (MonitorWindow.__init__)
- Modify: `src/cc_monitor/ui.py:339-344` (resizeEvent)

- [ ] **Step 1: 修改窗口为无边框，添加鼠标拖动**

在 `MonitorWindow.__init__` 中：
- 添加 `Qt.FramelessWindowHint` 到窗口 flags
- 设置默认尺寸 `300 × 400`
- 添加 `_drag_pos` 实例变量

在 `MonitorWindow` 中添加：

```python
def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
        self._drag_pos = event.globalPosition().toPoint()

def mouseMoveEvent(self, event):
    if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
        delta = event.globalPosition().toPoint() - self._drag_pos
        self.move(self.pos() + delta)
        self._drag_pos = event.globalPosition().toPoint()

def mouseReleaseEvent(self, event):
    self._drag_pos = None
```

- [ ] **Step 2: 自绘标题栏**

在 `_build_ui` 中，把现有的 header_bar 改成自绘标题栏：
- 高度保持 40px（原来是 52px）
- 标题文字左侧对齐
- 右侧添加视图切换按钮（两个按钮：`≡` 列表、`⊞` 网格）和关闭按钮 `×`
- 关闭按钮点击调用 `self.close()`

关闭按钮样式：
```python
close_btn = QLabel("×")
close_btn.setFont(QFont("Microsoft YaHei", 14))
close_btn.setStyleSheet("color: #94a3b8; background: transparent; border: none; padding: 0 8px;")
close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
close_btn.mousePressEvent = lambda e: self.close() if e.button() == Qt.MouseButton.LeftButton else None
```

- [ ] **Step 3: 验证窗口可拖动**

运行应用，按住标题栏区域拖动窗口。

- [ ] **Step 4: Commit**

```bash
git add src/cc_monitor/ui.py
git commit -m "feat: borderless window with custom title bar and drag support"
```

---

### Task 2: 透明度控制

**Files:**
- Modify: `src/cc_monitor/ui.py` (MonitorWindow 类)

- [ ] **Step 1: 添加透明度相关状态和方法**

在 `MonitorWindow.__init__` 末尾添加：

```python
self._opacity_timer = QTimer(self)
self._opacity_timer.setSingleShot(True)
self._opacity_timer.timeout.connect(lambda: self.setWindowOpacity(0.3))
self.setWindowOpacity(0.3)
```

- [ ] **Step 2: 重写 enter/leave 事件**

```python
def enterEvent(self, event):
    self.setWindowOpacity(1.0)
    self._opacity_timer.stop()
    super().enterEvent(event)

def leaveEvent(self, event):
    self._opacity_timer.start(500)  # 离开 500ms 后恢复半透明
    super().leaveEvent(event)
```

- [ ] **Step 3: 状态变化时触发不透明**

修改 `refresh()` 方法，在 `sig != self._last_sig` 时：

```python
if sig != self._last_sig:
    self.setWindowOpacity(1.0)
    self._opacity_timer.stop()
    self._opacity_timer.start(3000)  # 3 秒后恢复
    self._last_sig = sig
    self._rebuild_cards(sessions)
```

- [ ] **Step 4: 验证透明度行为**

运行应用：
- 窗口默认半透明
- 鼠标移入变不透明
- 鼠标移出 0.5 秒后恢复半透明
- 状态变化时变不透明，3 秒后恢复

- [ ] **Step 5: Commit**

```bash
git add src/cc_monitor/ui.py
git commit -m "feat: auto-transparency - 0.3 default, opaque on hover and state change"
```

---

### Task 3: 紧凑列表视图

**Files:**
- Modify: `src/cc_monitor/ui.py` (添加 _make_compact_row 和 ViewMode)

- [ ] **Step 1: 添加 ViewMode 枚举**

在文件顶部（COLORS 之后）添加：

```python
from enum import Enum

class ViewMode(Enum):
    COMPACT = "compact"
    DETAIL = "detail"
```

- [ ] **Step 2: 创建紧凑列表行组件**

添加 `_make_compact_row(session: Session) -> QFrame` 函数：

```python
def _make_compact_row(session: Session) -> QFrame:
    row = QFrame()
    row.setFixedHeight(36)
    row.setStyleSheet("QFrame { background: transparent; border: none; }")

    # 状态颜色
    if session.is_alive and session.status == "busy":
        accent = COLORS["accent_busy"]
    elif session.is_alive:
        accent = COLORS["accent_idle"]
    else:
        accent = COLORS["accent_dead"]

    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # 左侧竖条
    strip = QFrame()
    strip.setFixedWidth(4)
    strip.setStyleSheet(f"QFrame {{ background: {accent}; border: none; border-radius: 2px; }}")
    layout.addWidget(strip)
    layout.addSpacing(10)

    # 项目名称
    project_name = session.name or ""
    if not project_name and session.cwd:
        import os
        project_name = os.path.basename(session.cwd) or "Unknown"

    name = QLabel(project_name)
    name.setFont(QFont("Microsoft YaHei", 10))
    name.setStyleSheet(f"color: {COLORS['title']}; background: transparent; border: none;")
    layout.addWidget(name, 1)

    # 状态 + 任务数
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
```

- [ ] **Step 3: 修改 _rebuild_cards 支持两种模式**

将 `_rebuild_cards` 改名为 `_rebuild_ui`，根据 `self._view_mode` 决定布局：

```python
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
        empty.setStyleSheet(f"color: {COLORS['empty_text']}; background: transparent; border: none;")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(empty, 0, 0)
        return

    if self._view_mode == ViewMode.COMPACT:
        for i, session in enumerate(sessions):
            row = _make_compact_row(session)
            self.grid_layout.addWidget(row, i, 0)
    else:
        width = self.scroll.viewport().width() - 48
        cols = max(1, width // self.CARD_MIN_WIDTH)
        for i, session in enumerate(sessions):
            row = i // cols
            col = i % cols
            card = _make_card(session)
            self.grid_layout.addWidget(card, row, col)
        for col in range(cols):
            self.grid_layout.setColumnStretch(col, 1)
```

注意：`refresh()` 中调用的 `_rebuild_cards` 需要改为 `_rebuild_ui`。

- [ ] **Step 4: 设置默认紧凑模式**

在 `__init__` 中添加 `self._view_mode = ViewMode.COMPACT`。

- [ ] **Step 5: 验证紧凑列表显示**

运行应用，确认：
- 默认显示紧凑列表
- 每行 36px 高，显示项目名称 + 状态 + 任务数
- 状态颜色条正确显示

- [ ] **Step 6: Commit**

```bash
git add src/cc_monitor/ui.py
git commit -m "feat: compact list view with status strip and task count"
```

---

### Task 4: 视图切换 + 窗口大小自适应

**Files:**
- Modify: `src/cc_monitor/ui.py` (标题栏按钮、切换方法)

- [ ] **Step 1: 添加视图切换按钮到标题栏**

在 `_build_ui` 的 header_layout 中，在 close_btn 之前添加：

```python
self.compact_btn = QLabel("≡")
self.compact_btn.setFont(QFont("Microsoft YaHei", 12))
self.compact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
self.compact_btn.mousePressEvent = lambda e: self._set_view_mode(ViewMode.COMPACT) if e.button() == Qt.MouseButton.LeftButton else None

self.detail_btn = QLabel("⊞")
self.detail_btn.setFont(QFont("Microsoft YaHei", 12))
self.detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
self.detail_btn.mousePressEvent = lambda e: self._set_view_mode(ViewMode.DETAIL) if e.button() == Qt.MouseButton.LeftButton else None

header_layout.addWidget(self.compact_btn)
header_layout.addWidget(self.detail_btn)
```

- [ ] **Step 2: 添加 _set_view_mode 方法**

```python
def _set_view_mode(self, mode: ViewMode):
    if self._view_mode == mode:
        return
    self._view_mode = mode

    # 更新按钮样式
    active_color = COLORS["header_accent"]
    inactive_color = COLORS["subtitle"]
    self.compact_btn.setStyleSheet(f"color: {active_color if mode == ViewMode.COMPACT else inactive_color}; background: transparent; border: none; padding: 0 6px;")
    self.detail_btn.setStyleSheet(f"color: {active_color if mode == ViewMode.DETAIL else inactive_color}; background: transparent; border: none; padding: 0 6px;")

    # 调整窗口大小
    if mode == ViewMode.COMPACT:
        self.resize(300, 400)
        self.setMinimumSize(240, 200)
    else:
        self.resize(1100, 700)
        self.setMinimumSize(500, 400)

    # 重绘
    sessions = load_sessions()
    self._rebuild_ui(sessions)
```

- [ ] **Step 3: 初始化按钮样式**

在 `_build_ui` 末尾或 `__init__` 中调用 `_set_view_mode(ViewMode.COMPACT)` 设置初始样式。

- [ ] **Step 4: 修改 resizeEvent**

```python
def resizeEvent(self, event):
    super().resizeEvent(event)
    if hasattr(self, "_last_sig") and self._last_sig and self._view_mode == ViewMode.DETAIL:
        sessions = load_sessions()
        self._rebuild_ui(sessions)
```

只在详细模式下响应 resize 重新计算列数。

- [ ] **Step 5: 验证视图切换**

运行应用：
- 点击 `⊞` 切换到详细模式，窗口变大，显示卡片网格
- 点击 `≡` 切换回紧凑模式，窗口变小，显示列表
- 按钮高亮状态正确

- [ ] **Step 6: Commit**

```bash
git add src/cc_monitor/ui.py
git commit -m "feat: view mode toggle between compact list and detail grid"
```

---

### Task 5: 端到端验证

**Files:**
- 无需修改代码

- [ ] **Step 1: 运行应用并验证所有功能**

```bash
cd D:/my/projects/cc_monitor
python -m cc_monitor.main
```

验证清单：
- [ ] 窗口默认 300×400，无边框
- [ ] 按住标题栏可拖动
- [ ] 默认透明度 0.3
- [ ] 鼠标移入变不透明，移出 0.5 秒后恢复
- [ ] 紧凑列表显示正确（项目名称、状态、任务数）
- [ ] 点击 `⊞` 切换到详细模式，窗口变大
- [ ] 详细模式显示卡片网格
- [ ] 点击 `≡` 切换回紧凑模式，窗口变小
- [ ] session 状态变化时窗口变不透明，3 秒后恢复
- [ ] 关闭按钮正常工作

- [ ] **Step 2: Commit（如有调整）**

```bash
git add -A
git commit -m "fix: polish compact UI interactions"
```

---

## 自检

### Spec 覆盖度

| Spec 需求 | 对应 Task |
|-----------|-----------|
| 窗口默认 300×400 | Task 1 |
| 无边框 + 可拖动 | Task 1 |
| 默认透明度 0.3 | Task 2 |
| 悬浮变不透明 | Task 2 |
| 状态变化 3 秒提示 | Task 2 |
| 紧凑列表视图 | Task 3 |
| 详细卡片视图保留 | Task 3, 4 |
| 视图切换 | Task 4 |
| 窗口大小自适应 | Task 4 |

### Placeholder 扫描
- 无 TBD/TODO
- 无 "add appropriate error handling" 等模糊描述
- 所有代码块包含完整代码

### 类型一致性
- `ViewMode.COMPACT` 和 `ViewMode.DETAIL` 在整个计划中一致
- `_rebuild_ui` 替代 `_rebuild_cards`，调用处同步更新
