# Task Execution & Error Reporting Enhancements Design

**Date:** 2026-05-23
**Status:** Approved
**Approach:** 任务执行与错误报告增强

---

## Overview

修复任务状态映射问题，统一任务执行流程，并增强错误报告功能（嵌入设备截图）。

## Change Summary

| # | Module | Issue | Fix |
|---|--------|-------|-----|
| 1 | 任务状态 | 后端 'running' 前端显示不一致 | 统一映射为 'executing' |
| 2 | 脚本执行 | 点击执行跳转 Agent 页面 | 改为创建 Task 并自动执行 |
| 3 | 错误报告 | 错误日志无设备上下文 | 错误时嵌入 base64 设备截图 |
| 4 | 单元测试 | device_service 缺乏测试 | 添加 TCP/IP 和断开连接的单元测试 |

---

## 1. Task Status Unification

### 1.1 Current Issue

后端 Task 状态使用 `running`，前端 TaskStatus 枚举使用 `executing`，导致状态显示不正确。

### 1.2 Mapping Table

| Backend Value | Frontend Value | Display Text |
|--------------|-----------------|--------------|
| pending | pending | 待执行 |
| running | executing | 执行中 |
| completed | completed | 已完成 |
| failed | failed | 已失败 |
| stopped | stopped | 已停止 |

### 1.3 Files

| File | Change |
|------|--------|
| `backend/app/services/task_service.py` | 保持 `running` 发送给前端 |
| `frontend/src/stores/taskStore.ts` | 添加 `running` → `executing` 映射 |

### 1.4 Implementation

**File:** `frontend/src/stores/taskStore.ts`

```typescript
const STATUS_MAP: Record<string, TaskStatus> = {
  'pending': 'pending',
  'running': 'executing',  // 统一映射
  'completed': 'completed',
  'failed': 'failed',
  'stopped': 'stopped'
};

const mapBackendStatus = (backendStatus: string): TaskStatus => {
  return STATUS_MAP[backendStatus] || 'pending';
};
```

---

## 2. Script Execution Flow Fix

### 2.1 Current Issue

点击脚本执行按钮后，跳转到 Agent 页面，但任务没有正确创建。

### 2.2 New Flow

```
用户点击"执行" → 创建 Task记录 → 跳转到 Task 页面高亮显示 → 后台自动执行
```

### 2.3 Files

| File | Change |
|------|--------|
| `frontend/src/pages/Script/ScriptPage.tsx` | 执行按钮调用 Task 创建 API |
| `frontend/src/services/api.ts` | 添加 createTask API |
| `backend/app/services/task_service.py` | Task 创建后自动触发执行 |

### 2.4 API Changes

**Request:**
```typescript
interface CreateTaskRequest {
  name: string;
  script_id: string;
  device_id?: string;
  task_type: 'functional' | 'performance';
}
```

**Response:**
```typescript
interface CreateTaskResponse {
  task_id: string;
  status: 'pending';
  created_at: string;
}
```

---

## 3. Error Report with Device Screenshot

### 3.1 Current Issue

任务失败时，日志缺乏设备屏幕上下文，难以调试。

### 3.2 Enhancement

任务失败时，自动捕获设备截图并嵌入错误报告中。

### 3.3 Files

| File | Change |
|------|--------|
| `backend/app/services/task_service.py` | 失败时调用截图 API |
| `backend/app/services/device_service.py` | 添加 get_screenshot_base64 方法 |
| `backend/app/schemas/report.py` | Report 添加 screenshot_base64 字段 |

### 3.4 Schema Changes

**File:** `backend/app/schemas/report.py`

```python
class ReportBase(BaseModel):
    """Base report schema."""
    name: str
    task_id: str
    status: ReportStatus
    screenshot_base64: str | None = None  # 错误时设备截图
    summary: str | None = None
    created_at: datetime

class ReportResponse(ReportBase):
    """Report response schema."""
    id: str
```

---

## 4. Device Service Unit Tests

### 4.1 Test Coverage

为 `device_service.py` 添加 TCP/IP 连接和断开连接的单元测试。

### 4.2 Files

| File | Change |
|------|--------|
| `backend/tests/test_device_service.py` | 创建测试文件 |

### 4.3 Test Cases

| Test Case | Description |
|-----------|-------------|
| test_enable_tcpip_with_valid_device | 测试使用 -s 参数启用 TCP/IP |
| test_enable_tcpip_usb_device_no_change | USB 设备不执行 TCP/IP |
| test_disconnect_tcpip_device | 断开 TCP/IP 设备 |
| test_disconnect_usb_device_ignored | USB 设备断开被忽略 |
| test_filter_online_devices | 只返回在线设备 |

### 4.4 Mock Strategy

使用 `unittest.mock` 模拟 ADB 命令：

```python
from unittest.mock import patch, MagicMock

@patch('subprocess.run')
def test_enable_tcpip_with_valid_device(self, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    # 调用 device_service.enable_tcpip('device_serial')
    # 验证 subprocess.run 调用了 'adb -s device_serial tcpip 5555'
```

---

## 5. Summary of Changes

| Priority | File | Change |
|----------|------|--------|
| P1 | `frontend/src/stores/taskStore.ts` | TaskStatus 映射统一 |
| P1 | `frontend/src/pages/Script/ScriptPage.tsx` | 执行流程改为创建 Task |
| P1 | `backend/app/services/task_service.py` | 失败时捕获截图 |
| P1 | `backend/app/services/device_service.py` | 添加 get_screenshot_base64 |
| P2 | `backend/app/schemas/report.py` | 添加 screenshot_base64 字段 |
| P2 | `backend/tests/test_device_service.py` | 添加单元测试 |
