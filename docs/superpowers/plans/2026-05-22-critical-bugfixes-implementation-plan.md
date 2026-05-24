# Critical Bugfixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 critical bugs: USB tcpip connection targeting, device button logic by connection type, and script execution failure with proper error logging.

**Architecture:** Targeted surgical fixes to existing backend services and frontend components. No new files or modules — just fixing existing code paths. Backend: device_service.py and task_service.py. Frontend: DevicePage.tsx, ScriptPage.tsx, taskStore.ts, TaskPage.tsx.

**Tech Stack:** Python 3.10+ / FastAPI (backend), React + TypeScript + Zustand + Vite (frontend), SQLite (aiosqlite), ADB (Android Debug Bridge)

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `backend/app/services/device_service.py` | Fix `enable_tcpip_mode` to use `-s {device_id}`; fix `disconnect_device` to only disconnect tcpip | Modify |
| `backend/app/services/task_service.py` | Fix stderr truncation, PYTHONPATH, diagnostic logging; add base64 screenshot in `_generate_report` | Modify |
| `frontend/src/pages/Device/DevicePage.tsx` | Show Disconnect only for tcpip, Wireless only for USB | Modify |
| `frontend/src/pages/Script/ScriptPage.tsx` | Replace `navigate('/agent')` with task creation + device selection modal | Modify |
| `frontend/src/stores/taskStore.ts` | Change `Task.status` type: `'running'` to `'executing'` | Modify |
| `frontend/src/pages/Task/TaskPage.tsx` | Update status maps and button checks from `'running'` to `'executing'` | Modify |
| `backend/tests/test_task_service.py` | Add test for full stderr logging (no truncation) | Modify |

---

## Task 1: Fix TCP/IP Mode — Use `-s` Device Serial

**Files:**
- Modify: `backend/app/services/device_service.py:144-158`

The `enable_tcpip_mode` method at line 144 runs `adb tcpip {port}` without targeting a specific device. When multiple USB devices are connected, this command may act on the wrong one. The fix adds `-s {device_id}` to target the specific device.

- [ ] **Step 1: Edit `enable_tcpip_mode` to use `-s` parameter**

In `backend/app/services/device_service.py`, replace the `enable_tcpip_mode` method (lines 144-158) with:

```python
    def enable_tcpip_mode(self, device_id: str, port: int = 5555) -> bool:
        """Enable TCP/IP mode on a specific USB device."""
        result = subprocess.run(
            f"adb -s {device_id} tcpip {port}",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
            timeout=30
        )
        time.sleep(3)  # Wait for ADB service restart on device
        return result.returncode == 0
```

This changes `f"adb tcpip {port}"` to `f"adb -s {device_id} tcpip {port}"`, increases sleep from 2 to 3 seconds, and simplifies the return check to just `result.returncode == 0` (since `adb tcpip` returns 0 on success).

- [ ] **Step 2: Verify the call chain still works**

The `enable_wireless_connection` method at line 160 already calls `self.enable_tcpip_mode(device_id, port)` — so it already passes `device_id`. No change needed there. Verify by reading the method:

```python
def enable_wireless_connection(self, device_id: str, port: int = 5555) -> Dict[str, any]:
    # ...
    if not self.enable_tcpip_mode(device_id, port):  # already passes device_id
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/device_service.py
git commit -m "fix: use -s device_serial in adb tcpip command for multi-device targeting"
```

---

## Task 2: Fix Disconnect — Only for TCP/IP Devices

**Files:**
- Modify: `backend/app/services/device_service.py:297-303`

The `disconnect_device` method at line 297 runs `adb disconnect` for ALL Android devices, including USB. USB devices cannot be disconnected via ADB (they're physically connected). The fix adds a condition to only disconnect TCP/IP devices.

- [ ] **Step 1: Edit `disconnect_device` to check connection type**

In `backend/app/services/device_service.py`, replace the `disconnect_device` method (lines 297-303) with:

```python
    def disconnect_device(self, device_id: str):
        """Disconnect from a device. Only disconnects TCP/IP devices; USB is physical."""
        device = self.get_device(device_id)
        if device and device.platform == PlatformType.ANDROID:
            if device.connection_type == ConnectionType.TCPIP:
                self._run_adb_command(f"disconnect {device_id}")
        if device_id in self.devices:
            del self.devices[device_id]
```

The key change: `adb disconnect` only runs when `device.connection_type == ConnectionType.TCPIP`. USB devices are physically connected and cannot be disconnected via ADB.

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/device_service.py
git commit -m "fix: only adb disconnect for tcpip devices, not USB"
```

---

## Task 3: Fix Device Page Button Logic

**Files:**
- Modify: `frontend/src/pages/Device/DevicePage.tsx:177-214`

The "Disconnect" button currently appears for ALL connected devices (line 198-204). It should only appear for TCP/IP devices. The "Enable Wireless" button already correctly only shows for non-tcpip devices (line 188-197). The fix wraps "Disconnect" in a `connection_type === 'tcpip'` condition.

- [ ] **Step 1: Edit button rendering in DevicePage.tsx**

In `frontend/src/pages/Device/DevicePage.tsx`, replace the connected-device buttons block (lines 187-205) with:

```tsx
                <>
                  {device.connection_type !== 'tcpip' && (
                    <button
                      onClick={() => enableWireless(device.device_id)}
                      disabled={enablingWirelessDeviceId === device.device_id}
                      className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Wifi className="w-4 h-4" />
                      {enablingWirelessDeviceId === device.device_id ? '开启中...' : '开启无线'}
                    </button>
                  )}
                  {device.connection_type === 'tcpip' && (
                    <button
                      onClick={() => disconnectDevice(device.device_id)}
                      className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Power className="w-4 h-4" />
                      断开
                    </button>
                  )}
                </>
```

The change: the unconditional `<button onClick={() => disconnectDevice(...)>断开</button>` becomes `{device.connection_type === 'tcpip' && (<button>断开</button>)}`. Result:
- USB devices show: [开启无线] [详情]
- TCP/IP devices show: [断开] [详情]

- [ ] **Step 2: Verify visually — run frontend dev server**

Run: `cd frontend && npm run dev`
Expected: Device page loads. USB device cards show only [开启无线] [详情]. TCP/IP device cards show only [断开] [详情]. No device card shows both Disconnect and Wireless simultaneously.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Device/DevicePage.tsx
git commit -m "fix: show Disconnect only for tcpip devices, Wireless only for USB"
```

---

## Task 4: Fix Task Execution Error Logging and PYTHONPATH

**Files:**
- Modify: `backend/app/services/task_service.py:129-228`

This is the most critical fix. The `execute_task` method has three bugs:
1. stderr truncated to 500 chars — user sees no real error
2. PYTHONPATH overridden to `backend/` root, breaking script imports that need venv packages
3. Python executable uses `python.exe` path hack instead of `sys.executable`

- [ ] **Step 1: Fix stderr truncation and stdout truncation**

In `backend/app/services/task_service.py`, replace the error logging section (lines 205-213) with:

```python
            if process.returncode == 0:
                await self._update_task_status(task_id, TaskStatus.COMPLETED, progress=100)
                await self._log(task_id, "INFO", "Task completed successfully")
                if stdout:
                    # Log stdout in chunks to avoid single huge entry
                    for i in range(0, len(stdout), 2000):
                        chunk = stdout[i:i+2000]
                        await self._log(task_id, "INFO", f"Output: {chunk}")
            else:
                await self._update_task_status(task_id, TaskStatus.FAILED, progress=100)
                error_msg = stderr if stderr else "Unknown error"
                # Log full error — split into chunks if very long
                if len(error_msg) > 2000:
                    for i in range(0, len(error_msg), 2000):
                        chunk = error_msg[i:i+2000]
                        await self._log(task_id, "ERROR", f"Error detail (part {i//2000+1}): {chunk}")
                else:
                    await self._log(task_id, "ERROR", f"Task failed: {error_msg}")
```

Key changes:
- `stdout[:500]` becomes full stdout logged in 2000-char chunks
- `error_msg[:500]` becomes full stderr logged in 2000-char chunks
- No truncation — user sees the complete error

- [ ] **Step 2: Fix PYTHONPATH and Python executable**

In `backend/app/services/task_service.py`, replace the env vars and python executable section (lines 164-183) with:

```python
            # 构建环境变量
            env_vars = os.environ.copy()
            if task.device_id:
                env_vars['PHONE_AGENT_DEVICE_ID'] = task.device_id
            env_vars['PHONE_AGENT_BASE_URL'] = settings.model_api_url
            env_vars['PHONE_AGENT_MODEL'] = settings.model_name
            env_vars['PHONE_AGENT_API_KEY'] = settings.api_key

            # Don't override PYTHONPATH — let the venv Python resolve packages naturally
            # The script's imports are resolved via the venv's site-packages

            # Add diagnostic logging before subprocess launch
            await self._log(task_id, "INFO", f"Python executable: {sys.executable}")
            await self._log(task_id, "INFO", f"Device ID: {task.device_id}")
            await self._log(task_id, "INFO", f"Script content length: {len(script_content)} chars")
            await self._log(task_id, "INFO", f"Script first 3 lines: {chr(10).join(script_content.split(chr(10))[:3])}")

            # Use the venv Python that's already running the backend
            python_executable = sys.executable
```

Key changes:
- Removed the `PYTHONPATH = project_root + ...` override — scripts import from venv site-packages naturally
- Removed the `python.exe` path hack — use `sys.executable` directly (this is already the correct venv Python)
- Added diagnostic logging: Python path, device ID, script size, first 3 lines

- [ ] **Step 3: Remove PYTHONPATH override line and old Python path log**

In the same method, remove these specific lines that are now redundant:

```python
# REMOVE this line (was at ~line 175):
            env_vars['PYTHONPATH'] = project_root + os.pathsep + env_vars.get('PYTHONPATH', '')

# REMOVE this line (was at ~line 177):
            await self._log(task_id, "INFO", f"Python path: {project_root}")
```

Keep the `project_root` variable and `cwd=project_root` in the subprocess call — the working directory is still needed. Just remove the PYTHONPATH override and old log line.

- [ ] **Step 4: Add test for full error logging**

In `backend/tests/test_task_service.py`, add a new test at the end of the file:

```python
@pytest.mark.asyncio
async def test_execute_task_logs_full_error_on_failure(task_service, script_service):
    """Verify that full stderr is logged without truncation."""
    # Create a script that produces a long error message
    long_error_script = """
import sys
for i in range(100):
    print(f"Error line {i}: This is a simulated error message that should not be truncated", file=sys.stderr)
sys.exit(1)
"""
    script_id = await script_service.create_script(
        name="long_error", content=long_error_script, script_type="manual", platform="android"
    )
    task_id = await task_service.create_task(
        name="Error logging test", script_id=script_id, platform="android"
    )
    await task_service.execute_task(task_id)
    task = await task_service.get_task(task_id)
    assert task.status == TaskStatus.FAILED

    logs = await task_service.get_task_logs(task_id)
    error_logs = [l for l in logs if l['level'] == 'ERROR']
    # Verify error logs contain the full message (not truncated to 500 chars)
    assert len(error_logs) > 0
    # Total error content should be longer than 500 chars (was truncated before)
    total_error_text = "".join(l['message'] for l in error_logs)
    assert len(total_error_text) > 500
```

- [ ] **Step 5: Run tests to verify**

Run: `cd backend && python -m pytest tests/test_task_service.py -v`
Expected: All tests pass, including the new `test_execute_task_logs_full_error_on_failure`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/task_service.py backend/tests/test_task_service.py
git commit -m "fix: remove stderr truncation, fix PYTHONPATH, use sys.executable, add diagnostic logging"
```

---

## Task 5: Fix TaskStatus Mapping — `running` to `executing`

**Files:**
- Modify: `frontend/src/stores/taskStore.ts:8`
- Modify: `frontend/src/pages/Task/TaskPage.tsx:72,88,100,221`

Backend uses `TaskStatus.EXECUTING = "executing"` but frontend maps this to `"running"`. The status display, icon, and action button checks all use `'running'`. Change them all to `'executing'`.

- [ ] **Step 1: Fix Task interface type in taskStore.ts**

In `frontend/src/stores/taskStore.ts`, change line 8:

```ts
// Before:
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';

// After:
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'stopped';
```

- [ ] **Step 2: Fix status display in TaskPage.tsx**

In `frontend/src/pages/Task/TaskPage.tsx`, make 4 changes:

1. `getStatusIcon` — change `case 'running':` to `case 'executing':` at line 72:
```tsx
      case 'executing':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
```

2. `getStatusText` — change `running: '执行中'` to `executing: '执行中'` at line 88:
```tsx
      executing: '执行中',
```

3. `getStatusClass` — change `case 'running':` to `case 'executing':` at line 100:
```tsx
      case 'executing':
        return 'text-blue-400';
```

4. Action buttons — change `task.status === 'running'` to `task.status === 'executing'` at line 221:
```tsx
                          {task.status === 'executing' ? (
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/taskStore.ts frontend/src/pages/Task/TaskPage.tsx
git commit -m "fix: unify TaskStatus mapping from 'running' to 'executing' matching backend"
```

---

## Task 6: Fix Script Page "Execute" — Create Task Instead of Navigate

**Files:**
- Modify: `frontend/src/pages/Script/ScriptPage.tsx`

Currently `handleExecute` navigates to `/agent` page (interactive mode). The fix changes it to create a task and execute it via the task execution flow, with a device selection dialog.

- [ ] **Step 1: Add new state variables and stores**

At the top of `ScriptPage.tsx`, add `useTaskStore` and `useDeviceStore` imports and new state variables. Find the existing state declarations (around line 8-19) and add:

```tsx
import { useTaskStore } from '../../stores/taskStore';
import { useDeviceStore } from '../../stores/deviceStore';

// Inside the component function, add new state:
  const { createTask, executeTask } = useTaskStore();
  const { devices, fetchDevices } = useDeviceStore();

  const [selectedScriptForExec, setSelectedScriptForExec] = useState<Script | null>(null);
  const [isDeviceSelectOpen, setIsDeviceSelectOpen] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
```

Also add a `useEffect` to fetch devices when the component mounts (alongside the existing `fetchScripts`):

```tsx
  useEffect(() => {
    fetchScripts();
    fetchDevices();
  }, [fetchScripts, fetchDevices]);
```

- [ ] **Step 2: Replace `handleExecute` function**

Replace the `handleExecute` function (around line 76-79) with:

```tsx
  const handleExecute = (script: Script) => {
    setSelectedScriptForExec(script);
    setSelectedDeviceId('');
    setIsDeviceSelectOpen(true);
  };

  const handleExecuteWithDevice = async () => {
    if (!selectedScriptForExec || !selectedDeviceId) return;

    const taskId = await createTask({
      name: `Execute: ${selectedScriptForExec.name}`,
      description: selectedScriptForExec.description || '',
      script_id: selectedScriptForExec.script_id,
      device_id: selectedDeviceId,
    });

    if (taskId) {
      await executeTask(taskId);
      navigate('/tasks');
    }

    setIsDeviceSelectOpen(false);
    setSelectedScriptForExec(null);
    setSelectedDeviceId('');
  };
```

- [ ] **Step 3: Add device selection modal**

Add a new modal at the bottom of the component JSX (after the existing Edit Modal, before the closing `</div>`). This modal appears when `isDeviceSelectOpen` is true:

```tsx
      {/* Device Select Modal for Script Execution */}
      {isDeviceSelectOpen && selectedScriptForExec && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">执行脚本: {selectedScriptForExec.name}</h2>
              <button
                onClick={() => { setIsDeviceSelectOpen(false); setSelectedScriptForExec(null); }}
                className="p-2 hover:bg-[#334155] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#94a3b8]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">选择设备 *</label>
                <div className="space-y-2">
                  {devices.filter(d => d.status === 'connected').map((device) => (
                    <label key={device.device_id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="device-select"
                        checked={selectedDeviceId === device.device_id}
                        onChange={() => setSelectedDeviceId(device.device_id)}
                        className="w-4 h-4 border-[#334155] bg-[#0f172a] text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-[#94a3b8]">{device.name || device.device_id} ({device.platform})</span>
                      {device.connection_type === 'tcpip' ? (
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">WiFi</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">USB</span>
                      )}
                    </label>
                  ))}
                  {devices.filter(d => d.status === 'connected').length === 0 && (
                    <p className="text-[#64748b] text-sm">暂无在线设备，请先在设备管理页连接设备</p>
                  )}
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => { setIsDeviceSelectOpen(false); setSelectedScriptForExec(null); }}
                  className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleExecuteWithDevice}
                  disabled={!selectedDeviceId}
                  className="flex-1 px-4 py-2.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                >
                  创建任务并执行
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
```

- [ ] **Step 4: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds. ScriptPage no longer imports `useNavigate` for the `/agent` route in `handleExecute` (though it still uses `navigate('/tasks')` so `useNavigate` stays).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Script/ScriptPage.tsx
git commit -m "fix: script execute creates task instead of navigating to agent page"
```

---

## Task 7: Add Base64 Screenshot to Error Reports

**Files:**
- Modify: `backend/app/services/task_service.py:230-297`

When a task fails, capture a device screenshot and embed it as base64 in the HTML report. Only capture screenshots on errors (not on success), matching user requirement.

- [ ] **Step 1: Modify `_generate_report` to capture and embed screenshot**

In `backend/app/services/task_service.py`, replace the `_generate_report` method (lines 230-297) with:

```python
    async def _generate_report(self, task_id: str, stdout: str, stderr: str):
        task = await self.get_task(task_id)
        if not task:
            return

        if task.status == TaskStatus.COMPLETED:
            status_text = "passed"
        elif task.status == TaskStatus.STOPPED:
            status_text = "stopped"
        else:
            status_text = "failed"

        # Capture screenshot on error only (not on success)
        screenshot_base64 = None
        if task.status in (TaskStatus.FAILED, TaskStatus.STOPPED) and task.device_id:
            from app.services.device_service import DeviceService
            device_service = DeviceService()
            try:
                screenshot_base64 = device_service.get_screenshot(task.device_id)
            except Exception:
                screenshot_base64 = None

        started = task.started_at or task.created_at
        completed = task.completed_at or time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            start_dt = datetime.datetime.fromisoformat(started)
            end_dt = datetime.datetime.fromisoformat(completed)
            duration = int((end_dt - start_dt).total_seconds())
        except Exception:
            duration = 0

        logs = await self.get_task_logs(task_id)
        step_rows = ""
        for i, log in enumerate(logs[:50]):
            step_rows += f"<tr><td>{i+1}</td><td>{log['timestamp']}</td><td>{log['level']}</td><td>{log['message']}</td></tr>\n"

        # Build screenshot section if available
        screenshot_section = ""
        if screenshot_base64:
            screenshot_section = f"""
        <h2>Error Screenshot</h2>
        <div style="background:#1e293b;padding:12px;border-radius:8px;border:1px solid #334155;margin:16px 0;">
          <img src="data:image/png;base64,{screenshot_base64}"
               style="max-width:100%;border-radius:4px;" alt="Error Screenshot" />
        </div>
        """

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>Test Report - {task.name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
h1 {{ color: #fff; border-bottom: 1px solid #334155; padding-bottom: 10px; }}
h2 {{ color: #e2e8f0; margin-top: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #334155; }}
th {{ background: #1e293b; color: #94a3b8; }}
.status-passed {{ color: #3ddc84; }}
.status-failed {{ color: #ef4444; }}
.status-stopped {{ color: #f59e0b; }}
.summary {{ display: flex; gap: 16px; margin: 16px 0; }}
.summary-item {{ background: #1e293b; padding: 12px 20px; border-radius: 8px; border: 1px solid #334155; }}
</style></head>
<body>
<h1>Test Report: {task.name}</h1>
<div class="summary">
  <div class="summary-item"><strong>Status:</strong> <span class="status-{status_text}">{status_text}</span></div>
  <div class="summary-item"><strong>Duration:</strong> {duration}s</div>
  <div class="summary-item"><strong>Started:</strong> {started}</div>
  <div class="summary-item"><strong>Completed:</strong> {completed}</div>
</div>
{screenshot_section}
<h2>Execution Log</h2>
<table><thead><tr><th>#</th><th>Time</th><th>Level</th><th>Message</th></tr></thead><tbody>
{step_rows}
</tbody></table>
</body></html>"""

        conn = await db.get_connection()
        await conn.execute(
            """INSERT OR REPLACE INTO reports (task_id, name, device_name, script_name, script_type, status, started_at, completed_at, duration_seconds, html_content, summary, total_steps, passed_steps, failed_steps, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, task.name, task.device_id, task.script_id, "", status_text,
             started, completed, duration, html_content,
             f"Total steps: {len(logs)}", len(logs),
             len([l for l in logs if l['level'] == 'INFO']),
             len([l for l in logs if l['level'] == 'ERROR']),
             time.strftime("%Y-%m-%dT%H:%M:%S"))
        )
        await conn.commit()
```

Key changes:
- Added `screenshot_base64` capture: only when `TaskStatus.FAILED` or `STOPPED`, and only when `task.device_id` is set
- `DeviceService().get_screenshot()` returns base64 string — directly embeddable as `<img src="data:image/png;base64,...">`
- Added `<h2>` style and `screenshot_section` between summary and log table
- Wrapped screenshot capture in try/except to avoid crashing report generation if screenshot fails
- Removed unused `has_error` variable from old code

- [ ] **Step 2: Verify existing report tests still pass**

Run: `cd backend && python -m pytest tests/test_task_service.py::test_execute_task_creates_report tests/test_task_service.py::test_generate_report_creates_html -v`
Expected: Both tests pass. The HTML content should still contain "Test Report".

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/task_service.py
git commit -m "feat: embed base64 device screenshot in error reports"
```

---

## Task 8: Smoke Test — Full Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 3: Manual verification checklist**

Start the backend and frontend, then verify:

1. **Device page**: Connect a USB Android device — card shows [开启无线] [详情] (no 断开)
2. **TCP/IP flow**: Click 开启无线 — device switches to tcpip — card shows [断开] [详情] (no 开启无线)
3. **Script page**: Click 执行 on a script — device selection modal appears — select device — creates task — navigates to task page
4. **Task page**: Task status shows "执行中" (not "running") while executing, "失败" when failed
5. **Error logs**: Failed task shows full error details in logs (not truncated)
6. **Report**: Failed task report shows device screenshot (if device connected)

- [ ] **Step 4: Final commit if any fixes needed**

If any adjustments were needed during smoke testing, commit them:
```bash
git add -A
git commit -m "fix: smoke test adjustments for critical bugfixes"
```

---

## Self-Review

**1. Spec coverage check:**

| Spec section | Task |
|-------------|------|
| 1. Fix USB TCP/IP (add `-s`) | Task 1 |
| 2. Button logic (Disconnect only tcpip) | Tasks 2, 3 |
| 2. Backend disconnect (only tcpip) | Task 2 |
| 3A. Unify script execution flow | Task 6 |
| 3B. Fix error logging (no truncation, PYTHONPATH) | Task 4 |
| 3C. Fix TaskStatus mapping | Task 5 |
| 3D. Base64 screenshot in report | Task 7 |
| Smoke test | Task 8 |

All spec sections covered.

**2. Placeholder scan:** No TBD, TODO, "implement later", "similar to Task N", or vague instructions. All steps have exact code.

**3. Type consistency:**
- `TaskStatus.EXECUTING` used consistently in backend (Task 4)
- `'executing'` used consistently in frontend (Task 5: taskStore, TaskPage)
- `ConnectionType.TCPIP` used in backend (Task 2)
- `device.connection_type === 'tcpip'` used in frontend (Tasks 3, 6)
- `DeviceService().get_screenshot()` returns `Optional[str]` (base64) — used in Task 7
- `handleExecuteWithDevice` function name consistent between definition (Task 6 Step 2) and modal button onClick (Task 6 Step 3)

No type/name mismatches found.