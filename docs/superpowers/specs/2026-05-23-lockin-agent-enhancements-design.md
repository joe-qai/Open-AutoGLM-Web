# LOCKIN Agent Platform Enhancements

## Overview

Three targeted enhancements to the LOCKIN Agent Platform: fixing the script executor for uploaded local scripts, adding batch delete support for tasks (and fixing reports batch delete UX), and restructuring the sidebar navigation menu.

---

## Task 1: Fix Script Executor for Uploaded Local Scripts

### Problem

When a user uploads a `.py` script via the Script Management page, then creates a task using that script and executes it, the task immediately shows "failed" status with no visible error message. The script content is stored correctly in the database, but the subprocess execution fails silently from the user's perspective.

### Root Causes Identified

1. **TaskPage doesn't fetch scripts on mount** — `TaskPage.tsx` reads `scripts` from `useAgentStore()` but never calls `fetchScripts()`. It relies on scripts being cached from a prior visit to `ScriptPage` or `AgentPage`. If a user navigates directly to TaskPage, the script dropdown is empty.

2. **Execution error details hidden from user** — `task_service.execute_task()` captures `stdout`/`stderr` and logs them to `task_logs`, but the frontend only shows a red "failed" badge. No error detail, log preview, or tooltip is available to help the user understand why the script failed.

3. **Brittle subprocess error handling** — The `subprocess.Popen` call wraps errors in a generic `except Exception as e: ... "Subprocess error: {str(e)}"` message. The actual `stderr` from the failed Python subprocess is logged but not formatted for clarity.

### Changes

**Frontend — TaskPage.tsx:**

- Add `fetchScripts()`, `fetchDevices()`, `fetchApks()` to the existing `useEffect` so all selectable items are loaded on mount
- Add an inline error display: when a task has `status === 'failed'`, show a subtle red badge with "查看详情" that opens a small drawer showing the latest task log entries
- Add polling: for tasks with `status === 'executing'`, poll the task list every 5 seconds to reflect real-time progress

**Backend — task_service.py:**

- In `execute_task()`, after subprocess completes with non-zero return code, format the `stderr` message with clear section headers so it's readable when later displayed
- Add `sys.executable` version info to the debug log before launching subprocess
- Normalize the temp file path on Windows to avoid path-related subprocess issues

---

## Task 2: Batch Delete (Reports + Tasks)

### Reports Batch Delete — Current State

| Layer | Status |
|-------|--------|
| Backend API | ✅ `DELETE /api/v1/reports/batch` exists |
| Backend Schema | ✅ `BatchDeleteRequest`, `BatchDeleteResponse` exist |
| Backend Service | ✅ `batch_delete()` in `ReportService` exists |
| Frontend API | ✅ `reportApi.batchDeleteReports` exists |
| Frontend Store | ✅ `batchDeleteReports` in `useReportStore` exists |
| Frontend UI | ✅ Checkbox column + batch delete button exist |
| Confirmation | ❌ Uses native `confirm()` — needs custom dark modal |

### Tasks Batch Delete — Current State

| Layer | Status |
|-------|--------|
| Backend API | ❌ Missing |
| Backend Schema | ❌ Missing |
| Backend Service | ❌ Missing |
| Frontend API | ❌ Missing |
| Frontend Store | ❌ Missing |
| Frontend UI | ❌ Missing |

### Architecture

All batch delete operations follow the same pattern established by APK batch delete:

```
User clicks checkbox(es) → batch mode activates → selects items → clicks "批量删除"
  → Custom ConfirmDialog opens → confirms → DELETE /api/v1/{resource}/batch
  → Backend loops through IDs, deletes each → returns {deleted_count, failed_ids}
  → Frontend refetches list → deselects all
```

### New: Reusable ConfirmDialog Component

A dark-themed modal component in `frontend/src/components/ConfirmDialog.tsx`:

```
Props:
  open: boolean
  title: string
  message: string
  confirmLabel?: string (default: "确定")
  cancelLabel?: string (default: "取消")
  variant?: 'danger' | 'default' (default: 'danger')
  onConfirm: () => void
  onCancel: () => void
```

Used for:
- Report batch delete confirmation
- Task batch delete confirmation
- Individual task delete confirmation (optional, replaces `confirm()` there too)

### Changes

**Backend — schemas/task.py:**

```python
class BatchDeleteTasksRequest(BaseModel):
    task_ids: List[str]

class BatchDeleteTasksResponse(BaseModel):
    deleted_count: int
    failed_ids: List[str] = []
```

**Backend — services/task_service.py:**

```python
async def batch_delete(self, task_ids: List[str]) -> tuple[int, List[str]]:
    conn = await db.get_connection()
    deleted, failed = 0, []
    for task_id in task_ids:
        process = self.task_processes.get(task_id)
        if process: process.kill(); del self.task_processes[task_id]
        await conn.execute("DELETE FROM task_logs WHERE task_id = ?", (task_id,))
        await conn.execute("DELETE FROM task_devices WHERE task_id = ?", (task_id,))
        await conn.execute("DELETE FROM reports WHERE task_id = ?", (task_id,))
        cursor = await conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        if cursor.rowcount > 0: deleted += 1
        else: failed.append(task_id)
    await conn.commit()
    return deleted, failed
```

**Backend — api/v1/tasks.py:** Add `DELETE /batch` endpoint.

**Frontend — api.ts:** Add `taskApi.batchDeleteTasks()`.

**Frontend — stores/taskStore.ts:** Add `batchDeleteTasks()` method.

**Frontend — pages/Task/TaskPage.tsx:** Add batch mode UI following the ApkPage pattern:
- Checkbox column in table header + rows
- "批量删除" toggle button (activates batch mode)
- Selection count bar with "批量删除" and "取消选择" buttons
- Custom `ConfirmDialog` for delete confirmation

**Frontend — pages/Report/ReportPage.tsx:** Replace `confirm()` with `<ConfirmDialog />`.

---

## Task 3: Menu Restructuring

### Target Navigation Structure

```
┌─ 仪表盘         /              (single item)
┌─ 资源管理                      (collapsible group)
│  ├ 项目管理     /projects
│  ├ APK管理      /apk
│  └ 设备管理     /devices
├─ Agent脚本      /agent          (single item)
├─ 脚本管理       /scripts        (single item)
┌─ 执行中心                      (collapsible group)
│  ├ 任务管理     /tasks
│  └ 报告管理     /reports
├─ 日志中心       /logs           (renamed from "日志管理")
└─ 设置           /settings       (single item)
```

### Changes

**Sidebar.tsx — Data Model:**

Refactor `NavItem` to support both single items and groups:

```typescript
interface NavGroup {
  label: string;
  icon: React.ReactNode;
  children: { path: string; label: string; icon: React.ReactNode }[];
}

interface NavSingle {
  path: string;
  label: string;
  icon: React.ReactNode;
}

type NavEntry = NavSingle | NavGroup;
```

**Sidebar.tsx — Rendering:**

- Single items render as today (`<NavLink>` with active state)
- Groups render as a collapsible section:
  - Clicking the group header toggles expand/collapse
  - Expanded state tracked per group with `useState`
  - Group header styled differently (slightly dimmer, no active highlight)
  - Sub-items indented with left padding
  - Active route highlighting works on sub-items
  - Chevron icon rotates on expand

**No route changes needed** — all paths stay the same.

**Header alignment fix:** The `Layout.tsx` main content area has `ml-60` hardcoded. This already changes when the sidebar collapses (via state in Sidebar). The Header component also has `left-60` hardcoded. To fully support the collapsed sidebar, Header's `left-60` should be dynamically driven by the same collapsed state. However, this is a pre-existing cosmetic issue and is **out of scope** for this task — the sidebar collapse behavior is unchanged.

---

## Implementation Order

1. **Task 3: Menu Restructuring** — most straightforward, no dependencies
2. **Task 2: Batch Delete** — ConfirmDialog component first, then tasks, then reports
3. **Task 1: Script Executor Fix** — needs the most debugging awareness

## Files Changed

| # | File | Type | Task |
|---|------|------|------|
| 1 | `frontend/src/components/layout/Sidebar.tsx` | Edit | 3 |
| 2 | `frontend/src/components/ConfirmDialog.tsx` | **New** | 2 |
| 3 | `backend/app/schemas/task.py` | Edit | 2 |
| 4 | `backend/app/services/task_service.py` | Edit | 1, 2 |
| 5 | `backend/app/api/v1/tasks.py` | Edit | 2 |
| 6 | `frontend/src/services/api.ts` | Edit | 2 |
| 7 | `frontend/src/stores/taskStore.ts` | Edit | 2 |
| 8 | `frontend/src/pages/Task/TaskPage.tsx` | Edit | 1, 2 |
| 9 | `frontend/src/pages/Report/ReportPage.tsx` | Edit | 2 |

No database schema changes, no route path changes, no backend config changes.
