# Platform UX Improvements Design

**Date**: 2026-05-21
**Status**: Draft
**Scope**: 5 user-reported issues from questions.txt — APK filename, device scan, report batch delete, log search, device detail button
**Precedes**: `2026-05-21-platform-bugfixes-and-enhancements-design.md` (different scope — that covers audit logging, script bugs, UI adjustments)

---

## Overview

Five UX/functional issues reported by the user, spanning APK management, device management, report management, and log management. All fixes are incremental improvements to existing features — no new subsystems.

---

## Issue 1: APK管理 — 上传文件名显示

### Problem

When an APK is uploaded, the original filename (e.g., `微信_8.0.apk`) is not preserved for display. The `list_apks` method sets `name=filename` using the saved UUID-based filename (`abc12345.apk`). The upload method stores the original filename temporarily but it's lost on subsequent list calls since there's no persistent metadata store.

### Solution

**SQLite metadata storage** for APK info persistence:

- Create a new `apk_metadata.db` SQLite database (same pattern as `audit_log.db`)
- Store `apk_id`, `original_filename`, `package_name`, `version`, `upload_time`, `file_size`, `status` in a table
- On upload: write metadata row with `original_filename = filename`
- On list: query metadata table for each APK, populate `ApkInfo.original_filename`
- On delete: delete both the APK file and the metadata row

### Backend Changes

1. **Schema** (`schemas/apk.py`):
   - Add `original_filename: Optional[str] = None` to `ApkInfo`

2. **Service** (`services/apk_service.py`):
   - Create `ApkMetadataService` (SQLite-backed, same singleton pattern as `AuditLogService`)
   - Database file: `backend/apk_metadata.db`
   - Table structure:
     ```sql
     CREATE TABLE apk_metadata (
         apk_id TEXT PRIMARY KEY,
         original_filename TEXT NOT NULL,
         package_name TEXT,
         version TEXT,
         file_size INTEGER,
         upload_time TEXT NOT NULL,
         status TEXT NOT NULL DEFAULT 'uploaded'
     );
     ```
   - `upload_apk`: save metadata row with `original_filename=filename`
   - `list_apks`: query metadata table → populate `original_filename` in ApkInfo; fall back to file-based info if metadata row missing
   - `delete_apk`: delete metadata row alongside the file

### Frontend Changes

1. **ApkPage.tsx**:
   - Add "原始文件名" column to the table (after "APK信息" column)
   - Display `apk.original_filename` in the new column
   - Fallback: if `original_filename` is null, show `apk.name`

### Data Flow

```
Upload: filename → ApkMetadataService.save(apk_id, original_filename=filename)
List:   ApkMetadataService.query() → ApkInfo(original_filename=...)
Delete: ApkMetadataService.delete(apk_id) + os.remove(file_path)
```

---

## Issue 2: 设备管理 — 自动扫描

### Problem

Device discovery works on backend but requires manual "刷新" clicks. Users want automatic discovery of USB and WiFi-connected devices.

### Solution

**30-second polling + dedicated scan button**:

- Auto-scan every 30 seconds while the Device page is open
- Rename "刷新" to "扫描设备" with scan icon
- Show subtle "自动扫描已开启" indicator

### Frontend Changes

1. **DevicePage.tsx**:
   - Add `useEffect` with `setInterval` calling `fetchDevices()` every 30 seconds
   - Clear interval on component unmount (`return () => clearInterval(...)`)
   - Change button text from "刷新" to "扫描设备", icon from `RefreshCw` to `Search`
   - Add a small green dot + "自动扫描已开启" text next to the page subtitle
   - Keep manual "扫描设备" button for immediate refresh (clears interval, re-fetches, restarts interval)

2. **No backend changes needed** — `list_devices` already discovers devices on each call

---

## Issue 3: 报告管理 — 批量删除

### Problem

Report list only supports single delete via `DELETE /reports/{report_id}`. No batch delete UI or endpoint.

### Solution

**Checkbox selection + batch endpoint + floating action bar**:

### Backend Changes

1. **Schema** (`schemas/report.py`):
   ```python
   class BatchDeleteRequest(BaseModel):
       report_ids: List[str]

   class BatchDeleteResponse(BaseModel):
       deleted_count: int
       failed_ids: List[str] = []
   ```

2. **API** (`api/v1/reports.py`):
   ```python
   @router.delete("/batch", response_model=BatchDeleteResponse)
   async def batch_delete_reports(request: BatchDeleteRequest):
       deleted, failed = report_service.batch_delete(request.report_ids)
       return BatchDeleteResponse(deleted_count=deleted, failed_ids=failed)
   ```

3. **Service** (`services/report_service.py`):
   - Add `batch_delete(report_ids: List[str]) -> tuple[int, List[str]]`
   - Iterate over IDs, delete each, track successes and failures
   - Return count of deleted and list of IDs that failed (not found)

### Frontend Changes

1. **ReportPage.tsx**:
   - Add checkbox column (leftmost) to table rows
   - "Select All" checkbox in table header
   - State: `selectedIds: Set<string>` tracking checked report IDs
   - When `selectedIds.size > 0`, show floating action bar above table:
     - Text: "已选择 {N} 项"
     - "批量删除" button (red, Trash2 icon) with confirmation dialog
     - "取消选择" button (clears all checkboxes)
   - After successful batch delete → clear selection → refresh list

2. **reportStore.ts**:
   - Add `batchDeleteReports(ids: string[])` action
   - Calls `DELETE /reports/batch` with `{"report_ids": ids}`

3. **api.ts**:
   - Add `batchDeleteReports(ids)` method to `reportApi`

---

## Issue 4: 日志管理 — 预览和搜索

### Problem

Logs have data but the frontend only searches client-side on the `action` field (limited to loaded 100 entries). The `detail` field content is not shown in expanded entries. Backend already supports `search`, `start_time`, `end_time`, `skip`, `limit` parameters that the frontend ignores.

### Solution

**Server-side search + detail display + pagination + time range filters**:

### Frontend Changes

1. **LogsPage.tsx** — major refactor of filter/search logic:
   - Remove client-side `filteredLogs` array (lines 82-87 currently filter locally)
   - Replace with server-side API calls: whenever filters change, call `logApi.getLogs()` with params:
     ```
     GET /logs/?search=...&level=...&category=...&start_time=...&end_time=...&skip=0&limit=50
     ```
   - Add pagination controls at bottom of log list:
     - "上一页" / "下一页" buttons
     - Page number display ("第 X 页")
     - `skip` and `limit` managed in state (`currentPage: number`, `pageSize: 50`)
   - Add date picker inputs for `start_time` and `end_time` in the filter section
   - In expanded log entry, display additional fields:
     - `detail` JSON — pretty-printed in a `<pre>` code block with syntax highlighting
     - `target_name` if present
     - `target_id` if present
   - Debounce search input (300ms) to avoid excessive API calls

2. **api.ts** — update logApi.getLogs():
   - Accept and forward: `search`, `start_time`, `end_time`, `skip`, `limit`, `level`, `category`

### No Backend Changes Needed

The backend `/logs/` endpoint already supports all required query parameters. The `search` param searches `target_name LIKE ?`, `error LIKE ?`, `detail LIKE ?` in SQLite.

---

## Issue 5: 设备管理 — 详情按钮无效

### Problem

The "详情" button on each device card (line 192-195 of DevicePage.tsx) has no `onClick` handler — it's a dead button.

### Solution

**Side drawer panel** showing full device info, live screenshot, and installed apps.

### Frontend Changes

1. **DeviceDetailDrawer.tsx** (new component):
   - Slide-over panel from right edge, width ~400px
   - Overlay backdrop (click outside to close)
   - Header: device name + platform icon + status badge
   - Device info section (key-value pairs):
     - 型号 (model)
     - 制造商 (manufacturer)
     - 系统版本 (os_version)
     - 分辨率 (screen_width × screen_height)
     - 连接类型 (connection_type)
     - IP地址 (ip)
     - 电池电量 (battery_level)
     - 最后在线 (last_seen)
   - Screenshot section:
     - On drawer open, call `GET /devices/{device_id}/screenshot`
     - Display base64 image with refresh button
     - Show "截图获取失败" placeholder on API failure
   - Installed apps section:
     - On drawer open, call `GET /devices/{device_id}/apps`
     - Display list with package_name and name
   - Action buttons at drawer bottom:
     - 连接 / 断开 (depending on device status)
     - 开启无线 (if USB device)
   - Close: X button in top-right, click outside backdrop, or ESC key

2. **DevicePage.tsx**:
   - Add state: `drawerOpen: boolean` (default false)
   - "详情" button onClick: `selectDevice(device)` → `setDrawerOpen(true)`
   - Render `<DeviceDetailDrawer device={selectedDevice} open={drawerOpen} onClose={() => setDrawerOpen(false)} />`

3. **deviceStore.ts**:
   - Already has `selectedDevice` and `selectDevice` — use existing state
   - Add `fetchDeviceScreenshot(deviceId: string)` action → calls screenshot API
   - Add `fetchDeviceApps(deviceId: string)` action → calls apps API

### No Backend Changes Needed

The backend already has:
- `GET /devices/{device_id}` — device details
- `GET /devices/{device_id}/screenshot` — screenshot
- `GET /devices/{device_id}/apps` — installed apps

---

## Implementation Priority

1. **Issue 5** (设备详情按钮) — simplest, highest-impact fix (dead button → functional drawer)
2. **Issue 2** (自动扫描) — small frontend-only change, high UX improvement
3. **Issue 1** (APK文件名) — SQLite metadata service + schema change
4. **Issue 4** (日志搜索) — frontend filter/pagination rewrite
5. **Issue 3** (批量删除) — new endpoint + checkbox UI pattern

All 5 are independent and can be implemented in parallel.

---

## Error Handling

- **APK metadata**: if SQLite query fails or metadata row missing for an APK → fall back to current file-based info (original_filename shows as null)
- **Device detail drawer**: screenshot API failure → show "截图获取失败" placeholder with retry button. Apps API failure → show "暂无数据"
- **Batch delete**: partial failures → backend returns `failed_ids` list. Frontend shows warning: "N项删除失败: {failed IDs}"
- **Log search**: API error → show error toast message, keep last successfully loaded data visible. Network timeout → show "搜索超时，请重试"

---

## Testing Checklist

- **APK**: Upload APK with Chinese filename → verify `original_filename` stored in SQLite → displayed in table → persists after page refresh
- **Device scan**: Verify 30-second polling triggers (check network tab) → devices update without manual click → "自动扫描已开启" indicator visible
- **Device detail**: Click "详情" → drawer slides in → screenshot loads → apps list shows → connect/disconnect buttons work → close works (X, click-outside, ESC)
- **Report batch delete**: Select 3 reports → action bar appears → click "批量删除" → confirm → all 3 removed → action bar disappears → verify audit log entries
- **Logs**: Type search term → API call includes `search` param → results filter server-side → expand entry → `detail` JSON visible → pagination works → time range filters work