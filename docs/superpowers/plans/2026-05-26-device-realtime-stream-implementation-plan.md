# 设备实时画面同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现设备实时画面同步到 Web 平台，基于 AutoGLM-GUI 成熟方案

**Architecture:** 采用 Socket.IO 实现前端与后端的实时通信，后端 ScrcpyStreamer 管理视频流，前端 ScrcpyPlayer 使用 WebCodecs 解码渲染

**Tech Stack:** FastAPI + Socket.IO + @yume-chan/scrcpy-decoder-webcodecs + WebCodecs API

---

## 任务概览

| 任务 | 文件 | 操作 |
|------|------|------|
| Task 1 | `backend/app/services/socketio_server.py` | 修改事件名称为短横线风格 |
| Task 2 | `frontend/package.json` | 添加解码库依赖 |
| Task 3 | `frontend/src/components/ScrcpyPlayer/ScrcpyPlayer.tsx` | 替换为 AutoGLM-GUI 实现 |
| Task 4 | `frontend/src/components/ScrcpyPlayer/index.ts` | 新增组件导出文件 |

---

## Task 1: 修改后端 Socket.IO 事件名称

**Files:**
- Modify: `backend/app/services/socketio_server.py`

**Event 名称对照:**

| 当前名称 | 新名称 |
|---------|--------|
| `connect_device_event` | `connect-device` |
| `disconnect_device_event` | `disconnect-device` |

- [ ] **Step 1: 修改事件注册**

```python
@sio.event
async def connect_device(sid, data):
    """Handle device connection request with concurrency control."""
    device_id = data.get("device_id")
    max_size = int(data.get("maxSize") or 1280)
    bit_rate = int(data.get("bitRate") or 4_000_000)

    logger.info(f"Received connect-device for device {device_id} from {sid}")

    if not device_id:
        await sio.emit("error", {"message": "请提供设备ID", "type": "missing_device_id"}, to=sid)
        return

    # ... 后续逻辑保持不变 ...

@sio.event
async def disconnect_device(sid):
    """Handle client disconnection."""
    logger.info(f"Client disconnecting: {sid}")
    await _stop_stream_for_sid(sid, sio)
```

- [ ] **Step 2: 验证修改**

Run: `grep -n "connect_device\|disconnect_device" backend/app/services/socketio_server.py`
Expected: 无匹配结果（已全部替换为短横线风格）

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/socketio_server.py
git commit -m "feat(stream): rename Socket.IO events to kebab-case style"
```

---

## Task 2: 添加前端解码库依赖

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 添加依赖**

在 `package.json` 的 `dependencies` 中添加:

```json
"@yume-chan/scrcpy-decoder-webcodecs": "^1.0.0"
```

完整示例:

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.28.0",
    "@yume-chan/scrcpy-decoder-webcodecs": "^1.0.0",
    "axios": "^1.6.8",
    "react": "^18.2.0",
    ...
  }
}
```

- [ ] **Step 2: 安装依赖**

Run: `cd frontend && npm install`
Expected: 安装成功，无 error

- [ ] **Step 3: 提交**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): add @yume-chan/scrcpy-decoder-webcodecs for video decoding"
```

---

## Task 3: 替换前端 ScrcpyPlayer 组件

**Files:**
- Replace: `frontend/src/components/ScrcpyPlayer/ScrcpyPlayer.tsx`

**实现要点:**
- 使用 `@yume-chan/scrcpy-decoder-webcodecs` 的 `WebCodecsVideoDecoder`、`WebGLVideoFrameRenderer`、`BitmapVideoFrameRenderer`
- Socket.IO 事件使用短横线风格 (`connect-device`, `disconnect-device`)
- 内置 controlApi 调用处理触摸/滑动
- 支持 `isVisible` 可见性感知
- 支持 `enableControl` 控制开关

- [ ] **Step 1: 编写 ScrcpyPlayer.tsx**

参考 AutoGLM-GUI 的 [ScrcpyPlayer.tsx](file:///C:/pythonworkspace/AutoGLM-GUI/frontend/src/components/ScrcpyPlayer.tsx) 实现:

```typescript
import { useCallback, useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import {
  BitmapVideoFrameRenderer,
  WebCodecsVideoDecoder,
  WebGLVideoFrameRenderer,
} from '@yume-chan/scrcpy-decoder-webcodecs';
import { ScrcpyVideoCodecId } from '@yume-chan/scrcpy';
import {
  touchDown,
  touchMove,
  touchUp,
  swipe,
} from '../../services/controlApi';

interface ScrcpyPlayerProps {
  deviceId: string;
  onStreamReady?: (stream: { close: () => void } | null) => void;
  onFallback?: (reason?: string) => void;
  isVisible?: boolean;
  enableControl?: boolean;
  className?: string;
}

export function ScrcpyPlayer({
  deviceId,
  onStreamReady,
  onFallback,
  isVisible = true,
  enableControl = false,
  className,
}: ScrcpyPlayerProps) {
  // ... 实现 Socket.IO 连接、视频解码、控制等功能
}

export default ScrcpyPlayer;
```

**核心功能实现:**

1. **Socket.IO 连接:**
```typescript
const socket = io(socketUrl, {
  path: '/socket.io',
  transports: ['websocket'],
  timeout: 10000,
});

socket.on('connect', () => {
  socket.emit('connect-device', {
    device_id: deviceId,
    maxSize: 1280,
    bitRate: 4_000_000,
  });
});
```

2. **视频解码:**
```typescript
const createDecoder = async (codecId: ScrcpyVideoCodecId) => {
  const renderer = WebGLVideoFrameRenderer.isSupported
    ? new WebGLVideoFrameRenderer()
    : new BitmapVideoFrameRenderer();

  return new WebCodecsVideoDecoder({
    codec: codecId,
    renderer,
  });
};
```

3. **触摸控制:**
```typescript
const handleMouseDown = async (e: MouseEvent) => {
  if (!enableControl) return;
  const coords = mapToDeviceCoordinates(e.clientX, e.clientY);
  await touchDown(deviceId, coords.x, coords.y);
};
```

- [ ] **Step 2: 创建 index.ts 导出文件**

新建 `frontend/src/components/ScrcpyPlayer/index.ts`:

```typescript
export { ScrcpyPlayer, default } from './ScrcpyPlayer';
```

- [ ] **Step 3: 验证组件编译**

Run: `cd frontend && npm run build`
Expected: 编译成功，无 error

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/ScrcpyPlayer/
git commit -m "feat(frontend): replace ScrcpyPlayer with AutoGLM-GUI implementation"
```

---

## Task 4: 验证集成

**Files:**
- Test: 手动测试 Device 页面视频流功能

- [ ] **Step 1: 启动后端服务**

Run: `cd backend && python run.py`
Expected: 服务启动成功，无 error

- [ ] **Step 2: 启动前端服务**

Run: `cd frontend && npm run dev`
Expected: 前端启动成功，访问 http://localhost:3000

- [ ] **Step 3: 测试视频流**

1. 连接 Android 设备
2. 进入 Device 页面
3. 点击设备查看详情
4. 验证视频流显示正常

Expected: 视频流正常显示，触摸控制正常工作

---

## 实施检查清单

| 任务 | 状态 |
|------|------|
| Task 1: Socket.IO 事件名称修改 | ⬜ |
| Task 2: 添加解码库依赖 | ⬜ |
| Task 3: ScrcpyPlayer 组件替换 | ⬜ |
| Task 4: 集成验证 | ⬜ |
