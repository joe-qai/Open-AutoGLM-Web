# Critical Bugfixes Design — Device TCP/IP, Button Logic, Script Execution

**Date:** 2026-05-22
**Priority:** URGENT (issue #3: script execution fails)
**Scope:** 3 targeted fixes across device management, UI buttons, and script/task execution

---

## 1. Fix USB Device TCP/IP Connection

### Problem

`enable_tcpip_mode()` in `device_service.py` runs `adb tcpip {port}` without `-s {device_serial}`, so when multiple USB devices are connected, the command may act on the wrong device.

### Root Cause

The method was intentionally written without `-s` (comment: "adb tcpip command should not use -s parameter, it auto-applies to the current USB device"). This is incorrect for multi-device scenarios.

### Fix

**File:** `backend/app/services/device_service.py`

Change `enable_tcpip_mode()` to accept `device_id` and pass it as `-s` parameter:

```python
def enable_tcpip_mode(self, device_id: str, port: int = 5555) -> bool:
    """Enable TCP/IP mode on a specific USB device."""
    result = subprocess.run(
        f"adb -s {device_id} tcpip {port}",
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        shell=True, timeout=30
    )
    time.sleep(3)  # Wait for ADB service restart on device
    return result.returncode == 0
```

The `enable_wireless_connection()` method already calls `enable_tcpip_mode(device_id, port)` — after this fix, the `-s` parameter will be correctly used.

### Flow (confirmed by user)

1. `adb -s {device_id} tcpip {port}` — enable TCP/IP port on specific USB device
2. Get device IP via `get_device_ip(device_id)` — must be on same network as host
3. `adb connect {ip}:{port}` — establish wireless connection

---

## 2. Button Logic Adjustment — USB/TCP Device Cards

### Problem

- USB devices show a "Disconnect" button — inappropriate because USB is a physical connection, you can't disconnect USB via ADB
- TCP/IP devices should NOT show "Enable Wireless" button (already implemented)
- The "Disconnect" button currently appears for ALL connected devices regardless of connection type

### Current Code

`frontend/src/pages/Device/DevicePage.tsx` lines 188-204:
```tsx
{device.connection_type !== 'tcpip' && (
  <button onClick={() => enableWireless(device.device_id)}>
    开启无线
  </button>
)}
<button onClick={() => disconnectDevice(device.device_id)}>
  断开  // shows for ALL devices, including USB
</button>
```

Backend `device_service.py` `list_devices()` already assigns correct `available_actions`:
- USB: `["wireless", "screenshot", "apps", "launch", "detail"]` — no "disconnect"
- TCP/IP: `["disconnect", "screenshot", "apps", "launch", "detail"]` — no "wireless"

### Fix

**Frontend:** Only show "Disconnect" for tcpip devices, only show "Enable Wireless" for USB devices:

```tsx
// USB device: [开启无线] [详情]
// TCP/IP device: [断开] [详情]
{device.connection_type !== 'tcpip' && (
  <button onClick={() => enableWireless(device.device_id)}>
    开启无线
  </button>
)}
{device.connection_type === 'tcpip' && (
  <button onClick={() => disconnectDevice(device.device_id)}>
    断开
  </button>
)}
<button onClick={() => openDrawer(device)}>
  详情
</button>
```

**Backend:** `disconnect_device()` should only execute `adb disconnect` for tcpip devices, not USB:

```python
def disconnect_device(self, device_id: str):
    device = self.get_device(device_id)
    if device and device.platform == PlatformType.ANDROID:
        if device.connection_type == ConnectionType.TCPIP:
            self._run_adb_command(f"disconnect {device_id}")
    if device_id in self.devices:
        del self.devices[device_id]
```

---

## 3. Fix Script Execution Failure (URGENT)

### Problem

Scripts fail with `TaskStatus.FAILED` but no visible error details. Both the Script page "Execute" button and Task page execution fail.

### Root Causes

1. **Script page "Execute" button doesn't create a task** — it navigates to the Agent page (`navigate('/agent')`), which is an interactive mode, not automated script execution
2. **Task execution subprocess may fail silently** — PYTHONPATH issues, dependency resolution failures, stderr truncated to 500 chars
3. **TaskStatus mapping inconsistency** — backend uses `"executing"`, frontend expects `"running"`, causing display bugs
4. **No error details visible to user** — task becomes `failed` but logs only show truncated error

### Fix Plan

#### 3A. Unify Script Execution Flow

**Script page "Execute" button** should create a task and execute it (not navigate to Agent page):

**File:** `frontend/src/pages/Script/ScriptPage.tsx`

Change `handleExecute` from navigating to Agent page to creating and executing a task:

```tsx
const handleExecute = async (script: Script) => {
  // Instead of navigate('/agent'), create a task and execute it
  setSelectedScriptForExec(script);
  setIsDeviceSelectOpen(true);  // Open device selection modal
};
```

Add a device selection modal for script execution, then:
```tsx
const handleExecuteWithDevice = async () => {
  const taskId = await createTask({
    name: `Execute: ${selectedScriptForExec.name}`,
    description: selectedScriptForExec.description || '',
    script_id: selectedScriptForExec.script_id,
    device_id: selectedDeviceId,
  });
  if (taskId) {
    await executeTask(taskId);
    navigate('/tasks');  // Navigate to task page to monitor progress
  }
};
```

#### 3B. Fix Task Execution Error Logging

**File:** `backend/app/services/task_service.py`

1. **Remove stderr truncation** — log full error details:

```python
# Before (truncated):
error_msg = stderr if stderr else "Unknown error"
await self._log(task_id, "ERROR", f"Task failed: {error_msg[:500]}")

# After (full):
error_msg = stderr if stderr else "Unknown error"
if len(error_msg) > 2000:
    for i in range(0, len(error_msg), 2000):
        await self._log(task_id, "ERROR", f"Error detail (part {i//2000+1}): {error_msg[i:i+2000]}")
else:
    await self._log(task_id, "ERROR", f"Task failed: {error_msg}")
```

2. **Fix PYTHONPATH** — use venv Python, don't override PYTHONPATH:

```python
# Use the venv Python that's already running the backend
python_executable = sys.executable

env_vars = os.environ.copy()
if task.device_id:
    env_vars['PHONE_AGENT_DEVICE_ID'] = task.device_id
env_vars['PHONE_AGENT_BASE_URL'] = settings.model_api_url
env_vars['PHONE_AGENT_MODEL'] = settings.model_name
env_vars['PHONE_AGENT_API_KEY'] = settings.api_key

# Don't override PYTHONPATH — let the venv Python resolve packages naturally
# The script's imports will be resolved via the venv's site-packages
```

3. **Add diagnostic logging** before subprocess launch:

```python
await self._log(task_id, "INFO", f"Python executable: {python_executable}")
await self._log(task_id, "INFO", f"Working directory: {project_root}")
await self._log(task_id, "INFO", f"Device ID: {task.device_id}")
await self._log(task_id, "INFO", f"Script content length: {len(script_content)} chars")
```

#### 3C. Fix TaskStatus Mapping

**File:** `frontend/src/stores/taskStore.ts`

Change `Task.status` type to match backend values:

```ts
export interface Task {
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'stopped';  // Changed 'running' to 'executing'
}
```

**File:** `frontend/src/pages/Task/TaskPage.tsx`

Update status display mapping:

```ts
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '准备中',
    executing: '执行中',   // Changed from 'running'
    completed: '成功',
    failed: '失败',
    stopped: '已停止',
  };
  return statusMap[status] || status;
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'executing':  // Changed from 'running'
      return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
    // ...
  }
};
```

Also update action buttons to use `executing` instead of `running`.

#### 3D. Report Screenshots as Base64

**File:** `backend/app/services/task_service.py`

When executing a task and detecting an error, capture a screenshot and embed it as base64 in the HTML report:

```python
async def _generate_report(self, task_id: str, stdout: str, stderr: str):
    task = await self.get_task(task_id)
    if not task:
        return

    # Capture screenshot on error only
    screenshot_base64 = None
    if task.status in (TaskStatus.FAILED, TaskStatus.STOPPED) and task.device_id:
        from app.services.device_service import DeviceService
        device_service = DeviceService()
        screenshot_base64 = device_service.get_screenshot(task.device_id)

    # Build HTML with optional screenshot section
    screenshot_section = ""
    if screenshot_base64:
        screenshot_section = """
        <h2>Error Screenshot</h2>
        <div style="background:#1e293b;padding:12px;border-radius:8px;border:1px solid #334155;">
          <img src="data:image/png;base64,{screenshot_base64}"
               style="max-width:100%;border-radius:4px;" alt="Error Screenshot" />
        </div>
        """.replace("{screenshot_base64}", screenshot_base64)

    # HTML report stored in database (complete, with embedded base64 images)
```

---

## Summary of Changes

| Component | File | Change |
|-----------|------|--------|
| TCP/IP fix | `backend/app/services/device_service.py` | Add `-s {device_id}` to `adb tcpip` command |
| Button logic | `frontend/src/pages/Device/DevicePage.tsx` | Conditionally show Disconnect only for tcpip, Wireless only for USB |
| Disconnect logic | `backend/app/services/device_service.py` | Only execute `adb disconnect` for tcpip devices |
| Script execute flow | `frontend/src/pages/Script/ScriptPage.tsx` | Create task instead of navigating to Agent page |
| Error logging | `backend/app/services/task_service.py` | Remove truncation, add diagnostic logs, fix PYTHONPATH |
| TaskStatus mapping | `frontend/src/stores/taskStore.ts` + `TaskPage.tsx` | Unify `running` to `executing` |
| Report screenshots | `backend/app/services/task_service.py` | Embed base64 screenshots in HTML report on error |

## Priority Order

1. **Script execution fix** (issue #3) — URGENT, platform unusable without this
2. **TCP/IP fix** (issue #1) — functional bug, affects multi-device scenarios
3. **Button logic** (issue #2) — UX improvement, quick fix

## Not In Scope

- Agent page execution flow (separate concern)
- Report architecture overhaul (current HTML-in-DB approach confirmed by user)
- phone_agent integration with task execution (scripts are standalone Python, confirmed by user)