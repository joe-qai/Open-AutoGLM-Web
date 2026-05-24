# Platform Architecture Overhaul Design

**Date:** 2026-05-22
**Status:** Approved
**Approach:** 方案B — 统一架构重写

---

## Overview

7 bug fixes / UX enhancements with unified SQLite persistence, subprocess executor, and custom HTML report generation. Replaces all in-memory dict storage with SQLite, adds proper process lifecycle management for task execution, and creates an inline report system with base64 screenshots on error only.

## Change Summary

| # | Module | Issue | Fix |
|---|--------|-------|-----|
| 1 | 设备管理 | 连接方式显示"无线"→改为"TCP/IP" | Frontend badge text change, connection_type display optimization |
| 2 | 设备详情 | 字段过多/顺序不固定 | Remove SDK版本/设备类型/last_seen; fix order to: 型号→制造商→系统版本→分辨率→连接方式→IP→电量→设备ID |
| 3 | 仪表盘 | 设备状态文字/圆点与背景撞色 | Text color brighter, dot larger with glow, connection type white+bold |
| 4 | APK管理 | 无批量删除;列表未降序 | Add batch delete with multi-select mode; sort by upload_time DESC |
| 5 | 项目管理 | 新项目未按时间降序 | SQLite query ORDER BY created_at DESC |
| 6 | 脚本管理 | 上传脚本数据不持久 | SQLite persistence; content stored in DB directly, no local file |
| 7 | 脚本执行 | 执行按钮跳转Agent;异步执行 | Navigate to Agent page with script_id param; task execution via subprocess |
| 8 | 任务管理 | 创建后不自动执行;无取消;无报告 | Auto-execute on create; cancel all non-completed states; custom HTML report with error screenshots (base64 in DB) |

---

## 1. Data Persistence Layer — SQLite

All services transition from in-memory dicts to SQLite. Single database file managed via `aiosqlite`.

### Database Schema

**File**: `backend/app/db/database.py`

```sql
-- 脚本表
CREATE TABLE scripts (
  script_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  content TEXT NOT NULL,
  script_type TEXT NOT NULL,    -- 'ai_generated' | 'external'
  platform TEXT NOT NULL,       -- 'android' | 'ios' | 'harmonyos'
  project_id TEXT,
  description TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  version INTEGER DEFAULT 1
);

-- 任务表
CREATE TABLE tasks (
  task_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  task_type TEXT DEFAULT 'functional',
  platform TEXT DEFAULT 'android',
  status TEXT DEFAULT 'pending',   -- pending/running/completed/failed/stopped
  script_id TEXT REFERENCES scripts(script_id),
  device_id TEXT,
  apk_id TEXT,
  description TEXT,
  progress INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  started_at TEXT,
  completed_at TEXT
);

-- 任务设备关联表
CREATE TABLE task_devices (
  task_id TEXT REFERENCES tasks(task_id),
  device_id TEXT,
  PRIMARY KEY (task_id, device_id)
);

-- 任务日志表
CREATE TABLE task_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT REFERENCES tasks(task_id),
  timestamp TEXT,
  level TEXT,
  message TEXT
);

-- 项目表
CREATE TABLE projects (
  project_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  platform TEXT DEFAULT 'android',
  created_at TEXT NOT NULL,
  updated_at TEXT
);

-- APK表
CREATE TABLE apks (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  original_filename TEXT,
  package_name TEXT,
  version TEXT,
  file_size INTEGER,
  file_path TEXT,                 -- APK文件本身仍需本地存储
  upload_time TEXT NOT NULL,
  status TEXT DEFAULT 'uploaded'
);

-- 报告表
CREATE TABLE reports (
  task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
  name TEXT,
  device_name TEXT,
  script_name TEXT,
  script_type TEXT,
  status TEXT,                    -- 通过/失败/已停止
  started_at TEXT,
  completed_at TEXT,
  duration_seconds INTEGER,
  html_content TEXT,              -- 完整HTML报告（含base64图片内嵌），图片仅在错误时存在，量小
  summary TEXT,
  total_steps INTEGER,
  passed_steps INTEGER,
  failed_steps INTEGER,
  created_at TEXT NOT NULL
);
```

**Note on report storage**: Screenshots are only captured on errors (typically 1-3 per task). Since the volume is small, the entire HTML report including base64-encoded error screenshots is stored in a single `html_content` field. No separate assets table needed.

### Database Module

`backend/app/db/database.py`:
- `Database` class with `aiosqlite` connection pool
- `init_db()` — create tables if not exist
- `get_connection()` — return async connection
- Called from `backend/app/main.py` startup event

### Service Layer Changes

All service classes (`ScriptService`, `TaskService`, `ProjectService`, `ApkService`) replace internal dicts with SQLite reads/writes via the `Database` class. Key changes:

- **ScriptService**: `create_script` → INSERT into scripts table; `list_scripts` → SELECT with filters; `get_script` → SELECT by script_id; `delete_script` → DELETE. No file_path — content is stored directly in DB.
- **TaskService**: Same pattern. `execute_task` → UPDATE status + spawn subprocess. `stop_task` → UPDATE status + kill subprocess process.
- **ProjectService**: `list_projects` → SELECT ORDER BY created_at DESC.
- **ApkService**: `list_apks` → SELECT ORDER BY upload_time DESC. `delete_apk_batch` → DELETE WHERE id IN (...).
- **ReportService**: `generate_report` → INSERT into reports table. `get_report` → SELECT html_content.

---

## 2. 设备管理 — 连接方式 + 详情抽屉

### 2.1 连接方式显示优化

**Frontend `DevicePage.tsx` — `getConnectionBadge` function:**
- `tcpip` case: Change badge text from "无线" to "TCP/IP", color stays green (`bg-green-500/20 text-green-400`)
- `usb` case: No change, stays "USB"

**Frontend `DeviceDetailDrawer.tsx` — connection_type display:**
- Same change: `connection_type === 'tcpip' ? 'TCP/IP' : 'USB'` instead of current `'USB' : '无线'`

### 2.2 设备详情抽屉 — 精简字段 + 固定顺序

**Remove**: `device_type`, `android_sdk_version`, `last_seen` displays (delete the conditional rendering blocks)

**Fixed order** (always show all fields, conditional on data availability):
1. 型号 (model)
2. 制造商 (manufacturer)
3. 系统版本 (os_version)
4. 分辨率 (screen_width x screen_height)
5. 连接方式 (connection_type: usb→"USB", tcpip→"TCP/IP")
6. IP地址 (ip — only shown for tcpip devices)
7. 电量 (battery_level — format: "100%")
8. 设备ID (device_id — full ID, not truncated)

**Frontend changes**: Reorder the conditional blocks in DeviceDetailDrawer.tsx to match this exact sequence. Remove `device_type`, `android_sdk_version`, `last_seen` blocks entirely.

---

## 3. 仪表盘 — 设备状态高亮

**Frontend `Dashboard.tsx` — Device status list section:**

Current:
- Device name: `text-[#94a3b8]` (grey)
- Status dot: `w-3 h-3 rounded-full` (3x3, small)
- Connection count: `text-white font-medium text-xs`

Changes:
- Device name: `text-[#e2e8f0]` (brighter light grey)
- Status dot: `w-4 h-4 rounded-full shadow-md` (4x4 with glow effect)
- Connection count: `text-white font-medium text-xs` (no change, already bright)
- Platform color dots (Android green, iOS white, HarmonyOS blue): `shadow-md` added to each

No background color changes — the highlight comes from brighter text and larger glowing dots, not from adding colored backgrounds that would clash.

---

## 4. APK管理 — 批量删除 + 降序排序

### 4.1 Batch Delete

**Frontend `ApkPage.tsx`:**
- Add state: `isBatchMode: boolean`, `selectedApkIds: Set<string>`
- Header area: Add "批量删除" button (next to existing "上传APK" button)
  - Default state: grey/disabled, no items selected
  - Click to enter batch mode → checkboxes appear on each row + header
  - When items selected: button turns red, shows count "删除 (N)"
  - "取消选择" button appears to exit batch mode
- Row changes in batch mode: Add checkbox column at left, checkbox click toggles selection
- Header row: Add "全选" checkbox in batch mode
- Confirmation dialog before batch delete: "确定要删除 {N} 个APK文件吗？"
- Exit batch mode after successful delete

**Frontend `apkStore.ts`:**
- Add `deleteApkBatch(apkIds: string[])` action
- Calls new API endpoint `DELETE /api/v1/apks/batch`

**Backend `apks.py`:**
- New endpoint: `DELETE /api/v1/apks/batch`
- Request body: `{ "apk_ids": ["id1", "id2", ...] }`
- Deletes each APK from database and removes file from disk

**Backend `apk_service.py`:**
- New method: `delete_apk_batch(apk_ids: List[str])` → DELETE FROM apks WHERE id IN (...), also delete files from uploads directory

### 4.2 Upload Time DESC Sort

**Backend `apk_service.py`:**
- `list_apks()` query: `SELECT * FROM apks ORDER BY upload_time DESC`

No frontend changes needed — backend guarantees order.

---

## 5. 项目管理 — 创建时间降序

**Backend `project_service.py`:**
- `list_projects()` query: `SELECT * FROM projects ORDER BY created_at DESC`

No frontend changes needed.

---

## 6. 脚本管理 — 持久化 + 执行跳转

### 6.1 Script Persistence

Scripts stored entirely in SQLite — no local file storage.

- Upload: `.py` file content read and INSERTed into `scripts` table with `script_type='external'`
- AI generated: Content INSERTed with `script_type='ai_generated'`
- Execution: Read `content` from DB, write to temp file `/tmp/task_{task_id}.py`, execute via subprocess, delete temp file after completion
- No `file_path` column in scripts table

### 6.2 Execute Button → Navigate to Agent

**Frontend `ScriptPage.tsx` — `handleExecute` function:**
- Current: `navigate('/agent')`
- Changed: `navigate('/agent?script_id=${script.script_id}')`

**Frontend `AgentPage.tsx`:**
- On mount, check URL query param `script_id`
- If `script_id` present: fetch script from store, load content into input area
- User can edit/confirm, then start VLM agent loop execution
- This path does NOT create a task or generate a report (per user requirement)

---

## 7. 任务管理 — 自动执行 + 取消 + 报告

### 7.1 Auto-Execute on Create

**Frontend `TaskPage.tsx` — `handleCreateTask` function:**
- After `createTask` returns task_id, immediately call `executeTask(task_id)`
- No manual "执行" button needed for newly created tasks
- Existing tasks with status `pending` can still be manually executed if needed

**Backend `tasks.py`:**
- `POST /` creates task with status `pending`
- Frontend calls `POST /{task_id}/execute` right after creation

### 7.2 Executor — Subprocess with Process Lifecycle

**Backend `task_service.py` — `execute_task` method:**

```python
import subprocess
import tempfile
import os

class TaskService:
    def __init__(self):
        self.task_processes: Dict[str, subprocess.Popen] = {}

    def execute_task(self, task_id: str):
        # Read script content from SQLite
        script = self._get_script(task.script_id)
        if not script:
            # mark failed, return
            return

        # Write script to temp file
        temp_script = tempfile.NamedTemporaryFile(
            suffix='.py', delete=False, prefix=f'task_{task_id}_'
        )
        temp_script.write(script.content.encode('utf-8'))
        temp_script.close()

        # Execute via subprocess
        env_vars = os.environ.copy()
        env_vars['PHONE_AGENT_DEVICE_ID'] = task.device_id
        env_vars['PHONE_AGENT_BASE_URL'] = settings.base_url
        env_vars['PHONE_AGENT_MODEL'] = settings.model
        process = subprocess.Popen(
            ['python', temp_script.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env_vars
        )
        self.task_processes[task_id] = process

        # Update task status to running
        self._update_task_status(task_id, 'running')

        # Wait for completion (runs in background via FastAPI BackgroundTasks)
        stdout, stderr = process.communicate()

        # Determine result
        if process.returncode == 0:
            self._update_task_status(task_id, 'completed')
        else:
            self._update_task_status(task_id, 'failed')

        # Generate report
        self._generate_report(task_id, stdout, stderr)

        # Cleanup
        os.unlink(temp_script.name)
        del self.task_processes[task_id]
```

### 7.3 Cancel Execution — All Non-Completed States

**Frontend `TaskPage.tsx`:**
- Show "取消执行" button for `pending` and `running` status (not just `running`)
- `pending`: cancel without subprocess kill (just change status)
- `running`: cancel with subprocess kill + status change
- `completed`, `failed`, `stopped`: no cancel button

**Backend `task_service.py` — `stop_task` method:**
- If `task_id` in `task_processes`: call `process.terminate()`, wait 5s, if still alive call `process.kill()`
- Always update status to `stopped` in SQLite

### 7.4 HTML Report Generation

**Report content**:
- Task name, description, device info
- Script name and type
- Execution time (start, end, duration)
- Overall result (pass/fail/stopped)
- Step-by-step log (text descriptions only, no screenshots per step)
- Error screenshots: captured by the task execution wrapper when subprocess returns non-zero exit code or stderr contains error markers. The wrapper calls `adb shell screencap` via `device_service.get_screenshot(device_id)` at the point of failure, converts to base64, and stores the screenshot data alongside the error log entry. Embedded as base64 `<img>` inline in HTML

**Report template**: `backend/app/templates/report_template.html` — Jinja2 template with:
- Header: task metadata table
- Body: step log table (numbered rows with timestamp, action, result)
- Error section: if errors exist, show error screenshots inline
- Footer: summary statistics

**Storage**: Complete HTML (including base64 error screenshots) stored in `reports.html_content` column. Since screenshots only exist on errors (1-3 per task typically), total report size stays manageable (~1-3 MB max).

**Preview API**: `GET /api/v1/reports/{task_id}/preview` → returns `html_content` directly as `Content-Type: text/html`. Frontend renders via iframe or new tab.

---

## Files Modified / Created

| File | Type | Changes |
|------|------|---------|
| `backend/app/db/database.py` | NEW | SQLite database module with aiosqlite, table creation, connection management |
| `backend/app/db/__init__.py` | MODIFY | Export Database class |
| `backend/app/main.py` | MODIFY | Add startup event to init_db() |
| `backend/app/services/script_service.py` | MODIFY | Replace dict with SQLite; remove file_path; read content from DB |
| `backend/app/services/task_service.py` | MODIFY | Replace dict with SQLite; add subprocess executor; add process tracking dict; add report generation |
| `backend/app/services/project_service.py` | MODIFY | Replace dict with SQLite; ORDER BY created_at DESC |
| `backend/app/services/apk_service.py` | MODIFY | Replace dict with SQLite; ORDER BY upload_time DESC; add batch delete |
| `backend/app/services/report_service.py` | MODIFY/NEW | Report generation from template + task data; store in reports table |
| `backend/app/api/v1/apks.py` | MODIFY | Add batch delete endpoint |
| `backend/app/api/v1/reports.py` | MODIFY | Add preview endpoint returning html_content |
| `backend/app/templates/report_template.html` | NEW | Jinja2 HTML report template |
| `backend/app/schemas/apk.py` | MODIFY | Add batch delete request schema |
| `frontend/src/stores/deviceStore.ts` | MODIFY | Remove deviceApps/loadingApps fields; no other changes needed |
| `frontend/src/stores/apkStore.ts` | MODIFY | Add isBatchMode/selectedApkIds state; add deleteApkBatch action |
| `frontend/src/stores/taskStore.ts` | MODIFY | createTask auto-calls executeTask; add cancelTask for pending status |
| `frontend/src/pages/Device/DevicePage.tsx` | MODIFY | Change "无线"→"TCP/IP" in getConnectionBadge |
| `frontend/src/components/DeviceDetailDrawer.tsx` | MODIFY | Remove device_type/android_sdk_version/last_seen; reorder fields to fixed sequence; change connection display to TCP/IP/USB |
| `frontend/src/pages/Dashboard/Dashboard.tsx` | MODIFY | Brighter device name text, larger glowing dots |
| `frontend/src/pages/Apk/ApkPage.tsx` | MODIFY | Add batch mode UI (checkboxes, batch delete button, cancel button) |
| `frontend/src/pages/Script/ScriptPage.tsx` | MODIFY | handleExecute navigates with script_id query param |
| `frontend/src/pages/Task/TaskPage.tsx` | MODIFY | Auto-execute after create; show cancel for pending+running; add report preview link/button |

---

## Out of Scope

- Agent页面 VLM loop 执行流程改动（保持现有逻辑不变）
- Device backend API changes (no new endpoints)
- iOS/HarmonyOS executor implementation (only Android subprocess for now)
- Report lazy loading / pagination (report sizes are small due to error-only screenshots)