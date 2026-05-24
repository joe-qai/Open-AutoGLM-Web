# Platform Bug Fixes & Enhancements Design

**Date**: 2026-05-21
**Project**: Open-AutoGLM (LOCKIN Agent Platform)
**Approach**: Fix-by-Fix (Sequential) — Infrastructure first, then bugs, then UI

## Overview

8 issues from `questions.txt`, categorized as bugs, UI adjustments, and feature enhancements. Implemented sequentially in dependency order.

## Implementation Order

| # | Issue | Category | Priority | Depends On |
|---|-------|----------|----------|------------|
| 6 | Audit logging system | Enhancement | P0 | None |
| 1 | Script delete bug | Bug | P1 | #6 (audit log records deletes) |
| 3 | Script execution error | Bug | P1 | #6 (audit log records execution) |
| 5 | Task execute/delete not working | Bug | P1 | #6 (audit log records task ops) |
| 2 | Script edit modal too small | UI | P2 | None |
| 4 | Remove TCP/IP connection button | UI | P2 | None |
| 7 | Dashboard device stats by name | UI | P2 | None |
| 8 | Remove header search/notifications/settings | UI | P2 | None |

---

## Section 1: Audit Logging System (#6)

### Architecture

Add a SQLite-backed audit log that records every operation in the system — user actions, system events, device operations, agent interactions, script/task lifecycle events.

### Components

**New file: `backend/app/services/audit_log_service.py`**

- `AuditLogService` — singleton service that writes log entries to SQLite
- Uses Python's built-in `sqlite3` module (no additional dependency)
- Database file: `backend/audit_log.db`
- Thread-safe writes using a write queue or connection-per-write pattern

**Database schema (`logs` table)**:

```sql
CREATE TABLE logs (
    log_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,        -- 'debug', 'info', 'warning', 'error'
    category TEXT NOT NULL,     -- 'device', 'script', 'task', 'agent', 'system', 'api'
    action TEXT NOT NULL,       -- 'connected', 'disconnected', 'created', 'deleted', 'executed', 'completed', 'failed', etc.
    operator TEXT NOT NULL,     -- 'user', 'system', 'agent'
    target_id TEXT,             -- ID of the affected entity
    target_name TEXT,           -- Human-readable name of the entity
    detail TEXT,                -- JSON blob with extra context
    device_id TEXT,
    script_id TEXT,
    task_id TEXT
);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_category ON logs(category);
CREATE INDEX idx_logs_level ON logs(level);
CREATE INDEX idx_logs_device ON logs(device_id);
CREATE INDEX idx_logs_script ON logs(script_id);
CREATE INDEX idx_logs_task ON logs(task_id);
```

**Integration points**:

1. **FastAPI middleware** — logs all HTTP requests as `category='api'` entries (method, endpoint, status code, duration)
2. **Service decorator** — `@audit_log(category, action)` that service methods use to log operations with their results
3. **WebSocket events** — task start/step/complete/fail events logged as `category='task'`
4. **Device operations** — connect, disconnect, screenshot, tap, swipe logged as `category='device'`
5. **Agent operations** — VLM calls, action parsing, step execution logged as `category='agent'`

### API Changes

The existing `/api/v1/logs` endpoints (`logs.py`) remain but the backend switches from in-memory list to SQLite queries:

- `GET /api/v1/logs` — accepts query params: `level`, `category`, `device_id`, `script_id`, `task_id`, `search`, `skip`, `limit`
- `GET /api/v1/logs/summary` — returns aggregated counts and stats from SQLite
- `DELETE /api/v1/logs` — clears all logs (with confirmation)

### Frontend Changes

`LogsPage.tsx` already has the right structure (search, level filter, type filter, summary cards, expandable entries). Changes:

- Replace `type` filter options from API-focused types (`api_request`, `api_response`) to category-based (`device`, `script`, `task`, `agent`, `system`, `api`)
- Add filter fields for specific `device_id`, `script_id`, `task_id`
- Update `LogEntry` interface: rename `type` field to `category`, add `action` and `operator` fields
- Summary cards remain the same (total, errors, warnings, avg response time)

---

## Section 2: Bug Fixes (#1, #3, #5)

### Bug #1 — Script Delete Shows Success But Doesn't Delete

**Root cause**: To be investigated during implementation. Likely candidates:
- Frontend `scriptApi.deleteScript()` URL path mismatch
- Frontend shows success message before API response confirms deletion
- Backend service singleton state inconsistency

**Fix**:
- Verify `scriptApi.deleteScript()` calls correct `DELETE /api/v1/scripts/{script_id}` endpoint
- Move success message display after confirmed API success response
- Add audit log entry for script deletion
- Add proper error state if deletion fails (show error message, don't remove from list)

### Bug #3 — Script Execution Error

**Root cause** (confirmed): Two issues:
1. Frontend `handleExecute` violates React hooks rules — `useNavigate` is dynamically imported inside an async function
2. Backend `execute_script` uses `subprocess.run` which fails because scripts import `uiautomator2` (not installed) or reference XCTest/Hypium (different runtime)

**Frontend fix**:
- Move `useNavigate` to component top level: `const navigate = useNavigate();`
- Change `handleExecute` to: set current script → navigate to `/agent` page
- The agent page is where execution should happen (through AgentEngine), not via subprocess

**Backend fix**:
- Script execution should route through the task system: create a task with the script → execute via AgentEngine
- The `ScriptService.execute_script()` method should be reworked to create a task and delegate execution to `TaskService`
- Remove the subprocess-based execution methods (`_execute_android_script`, etc.)
- Add audit log entries for script execution attempts and results

### Bug #5 — Task Execute/Delete Buttons Ineffective

**Root cause** (confirmed): Frontend not wired to backend:
- Delete button: `// Delete logic` placeholder — does nothing after confirm dialog
- Execute button: `executeTask()` from store may not properly call `POST /api/v1/tasks/{task_id}/execute`

**Delete fix**:
- Replace `// Delete logic` comment with actual API call
- Call `taskApi.deleteTask(task.task_id)` after confirm
- Refresh task list with `fetchTasks()`
- Add audit log entry for task deletion

**Execute fix**:
- Verify `taskStore.executeTask()` calls `POST /api/v1/tasks/{task_id}/execute`
- Fix the store action if it's not properly wired
- Add audit log entry for task execution start

---

## Section 3: UI Adjustments (#2, #4, #7, #8)

### #2 — Script Edit Modal Enlargement

**Current**: `max-w-3xl` (~768px) modal with simple textarea
**New**: `max-w-5xl` (~1024px) modal with full-height code editor

Changes to `ScriptPage.tsx` edit modal:
- Change container from `max-w-3xl` to `max-w-5xl`
- Ensure `max-h-[90vh]` works properly with the wider layout
- The textarea already uses `flex-1` and `overflow-hidden` — verify height fills available space
- Add monospace font styling with appropriate line height
- Keep existing save/cancel button layout

### #4 — Remove TCP/IP Connection Button

Changes to `DevicePage.tsx`:
- Remove "TCP/IP 连接" button from header (lines 103-109)
- Remove TCP/IP connection modal (lines 237-310)
- Remove state variables: `isModalOpen`, `tcpIpAddress`, `port`
- Remove function: `handleConnectTcpIp`
- Remove imports: `Wifi`, `X`, `Check` (if only used in modal)
- Keep the empty state message but remove TCP/IP button reference
- Keep "刷新" button in header

### #7 — Dashboard Device Stats by Name + Connection Type

Changes to `Dashboard.tsx`:
- Replace `uniqueDevices` dedup logic: group by device name instead of `device_id`
- A device with both USB and WiFi connections counts as **1 unique device** but shows **USB: 1, WiFi: 1** in connection breakdown
- Stats card for "设备数量" shows unique device name count
- Add new stats or expand existing: show USB connections count and WiFi connections count separately
- Update pie chart: group by device name, show per-device connection type breakdown in legend
- Add connection type counts to the chart's side panel

**Implementation detail**:
```typescript
// Deduplicate by device name
const uniqueDeviceNames = [...new Set(devices.map(d => d.name))];
const usbCount = devices.filter(d => d.connection_type === 'usb').length;
const wifiCount = devices.filter(d => d.connection_type === 'tcpip').length;
```

### #8 — Remove Header Search/Notifications/Settings

Changes to `Header.tsx`:
- Remove search input box (lines 17-25)
- Remove notification bell button (lines 28-31)
- Remove settings button (lines 34-37)
- Remove `Search`, `Bell`, `Settings` icon imports from lucide-react
- Remove `searchQuery` state variable
- Keep: page title "LOCKIN Agent Platform" (left) + user profile section (right)
- Simplified header layout: just title and user avatar/name

---

## Testing Strategy

- **Audit log**: Verify SQLite writes, query filtering, middleware logging, decorator logging
- **Script delete**: Delete a script, verify it disappears from list, verify audit log entry
- **Script execution**: Click "执行" on a script card, verify navigation to agent page works
- **Task delete**: Click delete, confirm, verify task removed, verify audit log entry
- **Task execute**: Click execute, verify API call, verify task status changes
- **Edit modal**: Open edit modal, verify wider layout, verify code editing works
- **Device page**: Verify TCP/IP button removed, page still functional
- **Dashboard**: Test with devices having both USB and WiFi connections, verify correct counts
- **Header**: Verify search/notification/settings removed, page title and user info remain

## Out of Scope

- Migrating existing in-memory stores (scripts, tasks) to SQLite — future work
- Adding real authentication/authorization — future work
- Adding pagination to log list — future work (current filter/search is sufficient)