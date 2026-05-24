# Task Execution & Error Reporting Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复任务状态映射问题，统一任务执行流程，并增强错误报告功能

**Architecture:** FastAPI + React，前端 Zustand stores，后端 asyncio subprocess

**Tech Stack:** Python 3.10+, FastAPI, aiosqlite, React 18, TypeScript

---

### Task 1: TaskStatus Mapping Unification

**Files:**
- Modify: `frontend/src/stores/taskStore.ts`
- Modify: `backend/app/services/task_service.py`

- [ ] **Step 1: Add status mapping in taskStore**

Edit `frontend/src/stores/taskStore.ts`:

```typescript
// 任务状态映射 - 统一后端 'running' 为前端 'executing'
const TASK_STATUS_DISPLAY: Record<string, string> = {
  pending: '待执行',
  running: '执行中',  // 后端 running 映射为执行中
  executing: '执行中',  // 前端 executing 保持一致
  completed: '已完成',
  failed: '已失败',
  stopped: '已停止'
};

const mapBackendStatus = (backendStatus: string): string => {
  if (backendStatus === 'running') {
    return 'executing';
  }
  return backendStatus;
};

// 在 useTaskStore 中使用
const displayStatus = (task: Task): string => {
  const status = mapBackendStatus(task.status);
  return TASK_STATUS_DISPLAY[status] || '未知';
};
```

- [ ] **Step 2: Verify backend sends 'running' status**

Edit `backend/app/services/task_service.py`:

```python
# 确保后端状态值保持 'running'
TASK_STATUS_VALUES = ['pending', 'running', 'completed', 'failed', 'stopped']

def get_task_status_display(status: str) -> str:
    """Get display text for task status."""
    mapping = {
        'pending': '待执行',
        'running': '执行中',
        'completed': '已完成',
        'failed': '已失败',
        'stopped': '已停止'
    }
    return mapping.get(status, '未知')
```

---

### Task 2: Script Execution Flow Fix

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/pages/Script/ScriptPage.tsx`
- Modify: `backend/app/services/task_service.py`

- [ ] **Step 1: Add createTask API method**

Edit `frontend/src/services/api.ts`:

```typescript
createTask: async (data: {
  name: string;
  script_id: string;
  device_id?: string;
  task_type?: 'functional' | 'performance';
}): Promise<{ task_id: string; status: string }> => {
  const response = await apiRequest('/tasks', {
    method: 'POST',
    body: JSON.stringify(data)
  });
  return response;
}
```

- [ ] **Step 2: Update script execution button handler**

Edit `frontend/src/pages/Script/ScriptPage.tsx`:

```typescript
const handleExecuteScript = async (script: Script) => {
  try {
    // 创建任务
    const result = await api.createTask({
      name: `${script.name} - ${new Date().toLocaleString()}`,
      script_id: script.id,
      task_type: 'functional'
    });

    // 跳转到任务页面并高亮新任务
    navigate(`/tasks?highlight=${result.task_id}`);

    toast.success('任务已创建并开始执行');
  } catch (error) {
    console.error('Failed to execute script:', error);
    toast.error('执行失败');
  }
};
```

- [ ] **Step 3: Backend task auto-execution on create**

Edit `backend/app/services/task_service.py`:

```python
async def create_task(self, task_data: TaskCreate) -> Task:
    """Create a new task and trigger execution."""
    task = Task(
        task_id=str(uuid.uuid4()),
        name=task_data.name,
        script_id=task_data.script_id,
        device_id=task_data.device_id,
        status='running',  # 直接设为 running，自动执行
        created_at=datetime.now().isoformat()
    )

    await self.db.execute(
        """INSERT INTO tasks (task_id, name, script_id, device_id, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (task.task_id, task.name, task.script_id, task.device_id, task.status, task.created_at)
    )
    await self.db.commit()

    # 触发后台执行
    asyncio.create_task(self._execute_task_async(task.task_id))

    return task

async def _execute_task_async(self, task_id: str):
    """Execute task in background."""
    # 任务执行逻辑
    pass
```

---

### Task 3: Error Report with Device Screenshot

**Files:**
- Modify: `backend/app/services/device_service.py`
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/schemas/report.py`

- [ ] **Step 1: Add get_screenshot_base64 method to device_service**

Edit `backend/app/services/device_service.py`:

```python
async def get_screenshot_base64(self, device_id: str) -> str | None:
    """Capture device screenshot and return base64 encoded image."""
    try:
        result = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'screencap', '-p',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()

        if result.returncode == 0:
            import base64
            return base64.b64encode(stdout).decode('utf-8')
    except Exception as e:
        logging.error(f"Failed to capture screenshot: {e}")

    return None
```

- [ ] **Step 2: Add screenshot to report on task failure**

Edit `backend/app/services/task_service.py`:

```python
async def complete_task(self, task_id: str, status: str, error: str = None):
    """Mark task as completed with status."""
    # 如果失败，捕获截图
    screenshot_base64 = None
    if status == 'failed' and self.device_service:
        task = await self.get_task(task_id)
        if task and task.device_id:
            screenshot_base64 = await self.device_service.get_screenshot_base64(task.device_id)

    # 更新任务状态
    await self.update_task(task_id, {
        'status': status,
        'completed_at': datetime.now().isoformat()
    })

    # 生成报告
    await self.report_service.create_report(
        task_id=task_id,
        status=status,
        error=error,
        screenshot_base64=screenshot_base64
    )
```

- [ ] **Step 3: Update report schema**

Edit `backend/app/schemas/report.py`:

```python
class ReportBase(BaseModel):
    """Base report schema."""
    name: str
    task_id: str
    status: ReportStatus
    screenshot_base64: str | None = None
    summary: str | None = None
    created_at: datetime

class ReportCreate(BaseModel):
    """Report creation schema."""
    name: str
    task_id: str
    status: ReportStatus
    screenshot_base64: str | None = None
    summary: str | None = None

class ReportResponse(ReportBase):
    """Report response schema."""
    id: str
```

---

### Task 4: Device Service Unit Tests

**Files:**
- Create: `backend/tests/test_device_service.py`

- [ ] **Step 1: Create unit test file**

Create `backend/tests/test_device_service.py`:

```python
"""Unit tests for device_service.py."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# 导入被测试的模块
import sys
sys.path.insert(0, 'backend')

from app.services.device_service import DeviceService


class TestDeviceService(unittest.TestCase):
    """Test cases for DeviceService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DeviceService()

    @patch('subprocess.run')
    def test_enable_tcpip_with_valid_device(self, mock_run):
        """Test enabling TCP/IP mode with valid device serial."""
        mock_run.return_value = MagicMock(returncode=0)

        result = asyncio.run(self.service.enable_tcpip('device_serial'))

        # 验证调用了正确的 adb 命令
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        self.assertIn('adb', call_args)
        self.assertIn('-s', call_args)
        self.assertIn('device_serial', call_args)
        self.assertIn('tcpip', call_args)
        self.assertIn('5555', call_args)

    @patch('subprocess.run')
    def test_enable_tcpip_usb_device_no_change(self, mock_run):
        """Test that USB devices are not affected by TCP/IP command."""
        mock_run.return_value = MagicMock(returncode=0)

        # USB 设备调用了 enable_tcpip 应该被 guard 保护
        with patch.object(self.service, '_is_tcpip_device', return_value=False):
            result = asyncio.run(self.service.enable_tcpip('usb_device'))

        # USB 设备不应该调用 tcpip 命令
        for call in mock_run.call_args_list:
            if 'tcpip' in call[0]:
                self.fail("USB device should not call tcpip command")

    @patch('subprocess.run')
    def test_disconnect_tcpip_device(self, mock_run):
        """Test disconnecting a TCP/IP device."""
        mock_run.return_value = MagicMock(returncode=0)

        result = asyncio.run(self.service.disconnect_device('tcpip_device'))

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        self.assertIn('adb', call_args)
        self.assertIn('disconnect', call_args)
        self.assertIn('tcpip_device', call_args)

    @patch('subprocess.run')
    def test_disconnect_usb_device_ignored(self, mock_run):
        """Test that USB device disconnect is ignored."""
        with patch.object(self.service, '_is_tcpip_device', return_value=False):
            result = asyncio.run(self.service.disconnect_device('usb_device'))

        # USB 设备不应该调用 disconnect 命令
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_filter_online_devices(self, mock_run):
        """Test filtering to return only online devices."""
        # 模拟设备列表
        mock_devices = [
            {'device_id': 'device1', 'status': 'device', 'online': True},
            {'device_id': 'device2', 'status': 'offline', 'online': False},
            {'device_id': 'device3', 'status': 'device', 'online': True},
        ]

        with patch.object(self.service, 'list_devices', return_value=mock_devices):
            online_devices = asyncio.run(self.service.get_online_devices())

        self.assertEqual(len(online_devices), 2)
        self.assertTrue(all(d['online'] for d in online_devices))

    @patch('subprocess.run')
    def test_get_screenshot_base64(self, mock_run):
        """Test capturing screenshot as base64."""
        # 模拟 screencap 输出
        mock_image_data = b'\x89PNG\r\n\x1a\n...'  # PNG header

        async def mock_subprocess():
            result = MagicMock()
            result.returncode = 0
            result.communicate = AsyncMock(return_value=(mock_image_data, b''))
            return result

        with patch('asyncio.create_subprocess_exec', side_effect=mock_subprocess):
            result = asyncio.run(self.service.get_screenshot_base64('device1'))

        self.assertIsNotNone(result)
        # 验证返回的是 base64 编码
        import base64
        decoded = base64.b64decode(result)
        self.assertEqual(decoded, mock_image_data)


class TestDeviceConnection(unittest.TestCase):
    """Test cases for device connection logic."""

    @patch('subprocess.run')
    def test_tcpip_command_uses_device_serial_flag(self, mock_run):
        """Test that TCP/IP command uses -s flag with device serial."""
        mock_run.return_value = MagicMock(returncode=0)

        service = DeviceService()
        asyncio.run(service.enable_tcpip('test_device_123'))

        call_args = mock_run.call_args[0]
        # 验证 -s flag 在 device_serial 之前
        s_index = call_args.index('-s')
        device_index = call_args.index('test_device_123')
        self.assertEqual(s_index + 1, device_index)


if __name__ == '__main__':
    unittest.main()
```

---

### Verification

- [ ] Verify task status displays "执行中" for 'running' backend status
- [ ] Verify script execution creates task and navigates to task page
- [ ] Verify failed task reports include base64 screenshot
- [ ] Verify device_service unit tests pass
- [ ] Verify TCP/IP enable/disable commands are correct
