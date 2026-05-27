# 设备实时画面同步 Web 平台方案

**日期**: 2026-05-26
**类型**: 设计文档
**状态**: 已确认

---

## 1. 概述

本设计旨在实现设备实时画面同步到 Web 平台，参考 AutoGLM-GUI 的成熟方案，实现低延迟、高性能的 Android 设备屏幕投射功能。

### 1.1 核心目标

- 实时视频流：设备屏幕实时投射到 Web 前端
- 低延迟：scrcpy-server 模式实现 < 100ms 延迟
- 高兼容性：支持 scrcpy-server 优先，screenrecord 降级
- 完整控制：支持触摸、滑动等远程控制功能

### 1.2 技术选型

| 组件 | 技术方案 | 说明 |
|------|---------|------|
| 视频传输 | scrcpy-server + Socket.IO | 成熟方案，低延迟 |
| 视频解码 | @yume-chan/scrcpy-decoder-webcodecs | 专业 H.264 解码库 |
| 视频渲染 | WebGL / Canvas 2D | 硬件加速渲染 |
| 设备控制 | REST API (controlApi) | 触摸、滑动等操作 |

---

## 2. 架构设计

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (React)                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   ScrcpyPlayer.tsx                        │   │
│  │  - Socket.IO 连接 (connect-device 事件)                   │   │
│  │  - @yume-chan/scrcpy-decoder-webcodecs 解码              │   │
│  │  - WebGL/Canvas 渲染                                     │   │
│  │  - 内置 controlApi 调用 (REST) 处理触摸/滑动             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Socket.IO
                              │ video-data / video-metadata / error
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        后端 (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 socketio_server.py                         │   │
│  │  - connect-device: 启动 ScrcpyStreamer                   │   │
│  │  - video-metadata: 推送设备分辨率/编码信息               │   │
│  │  - video-data: 推送 H.264 视频包                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 scrcpy_streamer.py                         │   │
│  │  - scrcpy-server 优先模式                                 │   │
│  │  - screenrecord 降级模式                                  │   │
│  │  - H.264 视频流解析                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ ADB
                              ▼
                    ┌─────────────────────┐
                    │   Android Device     │
                    │  scrcpy-server.jar   │
                    └─────────────────────┘
```

### 2.2 视频流优先级

```
请求连接设备
    │
    ▼
┌─────────────────────────────────────┐
│    1. 尝试 scrcpy-server 模式       │
│    - 推送 JAR 到 /data/local/tmp/   │
│    - ADB port forward               │
│    - 启动 Server 3.3.4              │
└──────────────┬──────────────────────┘
               │ 失败
               ▼
┌─────────────────────────────────────┐
│    2. 降级到 screenrecord 模式       │
│    - adb exec-out screenrecord      │
│    - 轮询 H.264 帧                  │
└─────────────────────────────────────┘
```

---

## 3. Socket.IO 事件契约

### 3.1 事件列表

| 事件名 | 方向 | 说明 |
|--------|------|------|
| `connect-device` | 前端→后端 | 请求连接设备 |
| `disconnect-device` | 前端→后端 | 请求断开连接 |
| `video-metadata` | 后端→前端 | 设备元数据 |
| `video-data` | 后端→前端 | 视频数据包 |
| `error` | 后端→前端 | 错误信息 |

### 3.2 事件详情

#### connect-device (前端 → 后端)

```json
{
  "device_id": "string",
  "maxSize": 1280,
  "bitRate": 4000000
}
```

#### video-metadata (后端 → 前端)

```json
{
  "deviceName": "string",
  "width": 1080,
  "height": 1920,
  "codec": "h264"
}
```

#### video-data (后端 → 前端)

```json
{
  "type": "configuration" | "data",
  "data": "ArrayBuffer",
  "timestamp": 1234567890,
  "keyframe": true,
  "pts": 12345
}
```

#### error (后端 → 前端)

```json
{
  "message": "错误描述",
  "type": "connection_failed | device_offline | timeout | ..."
}
```

---

## 4. 前端设计

### 4.1 ScrcpyPlayer 组件

**文件**: `frontend/src/components/ScrcpyPlayer/ScrcpyPlayer.tsx`

**功能**:
- Socket.IO 连接管理
- 视频流解码渲染
- 用户交互处理（触摸、滑动）
- 自动重连机制

**Props**:
```typescript
interface ScrcpyPlayerProps {
  deviceId: string;
  onStreamReady?: (stream: { close: () => void } | null) => void;
  onFallback?: (reason?: string) => void;
  isVisible?: boolean;
  enableControl?: boolean;
  className?: string;
}
```

### 4.2 解码流程

```
video-data 收到 → TransformStream(配置包优先) → ReadableStream →
WebCodecsVideoDecoder → WebGLVideoFrameRenderer → Canvas 渲染
```

### 4.3 坐标映射

```
Canvas点击 → 流分辨率坐标 → 设备实际分辨率坐标 → REST API → ADB
```

### 4.4 前端依赖

```json
{
  "@yume-chan/scrcpy-decoder-webcodecs": "^1.0.0"
}
```

---

## 5. 后端设计

### 5.1 ScrcpyStreamer 类

**文件**: `backend/app/services/scrcpy_streamer.py`

**功能**:
- scrcpy-server 生命周期管理
- 视频流读取和解析
- 设备元数据提取
- 降级模式支持

**核心方法**:
- `start()`: 启动视频流
- `read_packet()`: 读取视频包
- `stop()`: 停止视频流

### 5.2 Socket.IO Server

**文件**: `backend/app/services/socketio_server.py`

**功能**:
- 客户端连接管理
- 设备级并发控制
- 视频包推送

### 5.3 scrcpy-server 路径

**位置**: `resources/scrcpy-server-v3.3.3`

**查找优先级**:
1. `resources/scrcpy-server`
2. `resources/scrcpy-server-v3.3.3`
3. 系统安装路径

---

## 6. 关键设计点

### 6.1 并发控制

- 设备级 Lock：同一设备同时只有一个视频流
- Socket 级别：同一客户端只能连接一个设备

### 6.2 资源管理

- disconnect 时停止 streamer
- 清理端口转发
- 取消 streaming task

### 6.3 断线重连

- Socket.IO 自动重连
- 前端可见性感知（isVisible）
- 重连间隔 3 秒

### 6.4 错误处理

| 错误类型 | 用户提示 |
|---------|---------|
| device_offline | 设备无响应，请检查USB/WiFi连接 |
| connection_failed | 连接失败，请重试 |
| timeout | 连接超时，请检查设备连接 |
| not_implemented | 该操作在Windows平台暂不支持 |

---

## 7. 改动清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/socketio_server.py` | 修改 | 事件名称改为短横线风格 |
| `frontend/package.json` | 添加 | `@yume-chan/scrcpy-decoder-webcodecs` 依赖 |
| `frontend/src/components/ScrcpyPlayer/ScrcpyPlayer.tsx` | 替换 | 使用 AutoGLM-GUI 完整实现 |
| `frontend/src/components/ScrcpyPlayer/index.ts` | 新增 | 组件导出 |

---

## 8. 参考实现

- AutoGLM-GUI: `C:\pythonworkspace\AutoGLM-GUI`
  - `AutoGLM_GUI/scrcpy_stream.py`
  - `AutoGLM_GUI/socketio_server.py`
  - `frontend/src/components/ScrcpyPlayer.tsx`
