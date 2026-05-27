# AutoGLM-GUI 实时设备交互方案

## 一、整体架构

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端 (React)                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  DeviceMonitor (设备监视器)                                     │   │
│  │  ┌──────────────────┐    ┌──────────────────┐                 │   │
│  │  │ ScrcpyPlayer     │    │ ScreenshotPoller │                 │   │
│  │  │ (视频流模式)      │    │ (截图轮询模式)    │                 │   │
│  │  └────────┬─────────┘    └────────┬─────────┘                 │   │
│  │           │                       │                           │   │
│  │           ▼                       ▼                           │   │
│  │  ┌──────────────────────────────────────────────┐             │   │
│  │  │         用户交互层 (Touch/Swipe)             │             │   │
│  │  └────────────────────┬───────────────────────┘             │   │
│  └───────────────────────┼──────────────────────────────────────┘   │
│                          │                                         │
│                          ▼                                         │
├─────────────────────────────────────────────────────────────────────┤
│                         后端 (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Socket.IO Server (视频流)       REST API (控制指令)          │   │
│  │  ┌────────────────────────┐   ┌──────────────────────────┐   │   │
│  │  │ connect-device         │   │ /api/control/tap        │   │   │
│  │  │ video-metadata         │   │ /api/control/swipe      │   │   │
│  │  │ video-data             │   │ /api/control/touch/*    │   │   │
│  │  └──────────┬─────────────┘   └──────────┬─────────────┘   │   │
│  │             │                           │                   │   │
│  │             ▼                           ▼                   │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │              ScrcpyStreamer                          │   │   │
│  │  │  - 推送 scrcpy-server 到设备                        │   │   │
│  │  │  - ADB 端口转发 (tcp:27183)                         │   │   │
│  │  │  - 解析 H.264 视频流                               │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                   │
│                               ▼                                   │
├─────────────────────────────────────────────────────────────────────┤
│                         设备层 (ADB)                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Android 设备                                               │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │  scrcpy-server.jar                                    │ │   │
│  │  │  - MediaCodec H.264 编码                              │ │   │
│  │  │  - LocalSocket 数据传输                               │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、设备连接机制

### 2.1 ADB 设备管理

**核心组件**：`DeviceManager`（单例模式）

```python
# 设备发现流程
class DeviceManager:
    def _poll_devices(self):
        # 1. 获取 ADB 设备列表
        adb_devices = self._adb_conn.list_devices()
        
        # 2. 并行获取设备序列号
        with ThreadPoolExecutor(max_workers=8) as pool:
            serials = list(pool.map(get_device_serial, adb_devices))
        
        # 3. 按序列号分组，支持多连接方式
        grouped_by_serial: dict[str, list[DeviceInfo]] = defaultdict(list)
```

**支持的连接类型**：

| 连接类型 | 方式 | 优先级 |
|---------|------|--------|
| USB | `adb devices` 直接识别 | 最高 |
| WiFi | `adb tcpip 5555` + `adb connect IP:5555` | 中等 |
| mDNS | ADB 30.0.0+ 自动发现 | 自动降级 |
| Remote | HTTP 代理连接 | 最低 |

### 2.2 连接状态管理

```python
class ManagedDevice:
    serial: DeviceSerial          # 设备唯一标识
    connections: list[DeviceConnection]  # 多种连接方式
    primary_connection_idx: int  # 当前活跃连接索引
    
    @property
    def primary_device_id(self):
        return self.connections[self.primary_connection_idx].device_id
```

---

## 三、实时画面同步方案

### 3.1 方案一：Scrcpy 视频流（实时预览）

**适用场景**：GUI 实时预览，低延迟要求

#### 3.1.1 后端流程

```python
# socketio_server.py - 视频流启动流程
async def connect_device(sid, data):
    # 1. 获取设备 ID 和配置参数
    device_id = data.get("device_id")
    max_size = int(data.get("maxSize") or 1280)
    bit_rate = int(data.get("bitRate") or 4_000_000)
    
    # 2. 创建 ScrcpyStreamer 实例
    streamer = ScrcpyStreamer(
        device_id=device_id,
        max_size=max_size,
        bit_rate=bit_rate,
    )
    
    # 3. 启动流（内部包含多个步骤）
    await streamer.start()
    
    # 4. 读取元数据并发送
    metadata = await streamer.read_video_metadata()
    await sio.emit("video-metadata", {
        "deviceName": metadata.device_name,
        "width": metadata.width,
        "height": metadata.height,
        "codec": metadata.codec,
    }, to=sid)
    
    # 5. 开始流式传输
    _stream_tasks[sid] = asyncio.create_task(_stream_packets(sid, streamer))
```

#### 3.1.2 ScrcpyStreamer 启动流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 清理现有进程 | 杀死设备上残留的 scrcpy-server |
| 2 | 推送服务器 | `adb push scrcpy-server /data/local/tmp/` |
| 3 | 端口转发 | `adb forward tcp:27183 localabstract:scrcpy` |
| 4 | 启动服务 | `CLASSPATH=... app_process ... com.genymobile.scrcpy.Server` |
| 5 | TCP 连接 | 连接 localhost:27183 |
| 6 | 读取元数据 | 设备名、分辨率、编码信息 |

#### 3.1.3 前端解码流程

```typescript
// ScrcpyPlayer.tsx - 视频流解码
socket.on('video-metadata', async (metadata) => {
    // 1. 创建 WebCodecs 解码器
    const codecId = metadata.codec || ScrcpyVideoCodecId.H264;
    decoderRef.current = new WebCodecsVideoDecoder({
        codec: codecId,
        renderer: new WebGLVideoFrameRenderer(),
    });
    
    // 2. 设置视频流管道
    const videoStream = new ReadableStream<VideoPacket>({
        start(controller) {
            socket.on('video-data', (data) => {
                controller.enqueue(data);
            });
        }
    });
    
    // 3. 管道到解码器
    videoStream.pipeTo(decoderRef.current.writable);
});
```

#### 3.1.4 技术参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 最大分辨率 | 1280px | 自适应缩放 |
| 码率 | 4 Mbps | 保证流畅度 |
| 帧率 | 20 FPS | 实时性与性能平衡 |
| 编码格式 | H.264 | 硬件加速支持广泛 |
| 端口 | 27183 | scrcpy 默认端口 |

### 3.2 方案二：截图轮询（Agent 决策）

**适用场景**：AI Agent 决策输入，高分辨率要求

#### 3.2.1 后端实现

```python
# adb_plus/screenshot.py
def capture_screenshot(device_id=None, timeout=10):
    cmd = [adb_path, "-s", device_id, "exec-out", "screencap", "-p"]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    
    # 验证 PNG 格式
    if not _is_valid_png(result.stdout):
        return _fallback_screenshot()
    
    # 转换为 Base64
    base64_data = base64.b64encode(result.stdout).decode("utf-8")
    return Screenshot(base64_data=base64_data, width=width, height=height)
```

#### 3.2.2 前端轮询

```typescript
// hooks/useScreenshotPolling.ts
export function useScreenshotPolling({ deviceId, enabled, pollDelayMs }) {
    const [screenshot, setScreenshot] = useState(null);
    
    useEffect(() => {
        if (!enabled) return;
        
        const poll = async () => {
            const data = await getScreenshot(deviceId);
            if (data.success) {
                setScreenshot(data);
            }
            setTimeout(poll, pollDelayMs);
        };
        
        poll();
    }, [deviceId, enabled, pollDelayMs]);
    
    return { screenshot };
}
```

#### 3.2.3 轮询策略

| 模式 | 轮询间隔 | 适用场景 |
|------|---------|---------|
| 视频模式 | - | 实时预览（无轮询） |
| 截图模式 | 750ms | 快速更新 |
| 自动模式（降级） | 1200ms | 视频失败后降级 |

---

## 四、用户交互控制

### 4.1 触摸事件处理

#### 4.1.1 坐标映射

```typescript
// ScrcpyPlayer.tsx
const mapToDeviceCoordinates = (clientX: number, clientY: number) => {
    const rect = canvas.getBoundingClientRect();
    const relativeX = clientX - rect.left;
    const relativeY = clientY - rect.top;
    
    // 计算流式视频中的坐标
    const streamX = (relativeX / rect.width) * streamDimensions.width;
    const streamY = (relativeY / rect.height) * streamDimensions.height;
    
    // 考虑设备实际分辨率缩放
    const scaleX = deviceResolution.width / streamDimensions.width;
    const scaleY = deviceResolution.height / streamDimensions.height;
    
    return {
        x: Math.round(streamX * scaleX),
        y: Math.round(streamY * scaleY),
    };
};
```

#### 4.1.2 触摸事件序列

```typescript
// 触摸按下
const handleMouseDown = async (event) => {
    const coords = mapToDeviceCoordinates(event.clientX, event.clientY);
    await sendTouchDown(coords.x, coords.y, deviceId);
};

// 触摸移动（节流处理）
const handleMouseMove = (event) => {
    const now = Date.now();
    if (now - lastMoveTimeRef.current < MOTION_THROTTLE_MS) {
        // 节流：缓存坐标，批量发送
        pendingMoveRef.current = coords;
        return;
    }
    sendTouchMove(coords.x, coords.y, deviceId);
};

// 触摸抬起
const handleMouseUp = async (event) => {
    const coords = mapToDeviceCoordinates(event.clientX, event.clientY);
    await sendTouchUp(coords.x, coords.y, deviceId);
};
```

### 4.2 REST API 接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/control/tap` | POST | 点击操作 |
| `/api/control/swipe` | POST | 滑动操作 |
| `/api/control/touch/down` | POST | 触摸按下 |
| `/api/control/touch/move` | POST | 触摸移动 |
| `/api/control/touch/up` | POST | 触摸抬起 |

#### 4.2.1 点击接口

```python
# api/control.py
@router.post("/api/control/tap", response_model=TapResponse)
async def control_tap(request: TapRequest) -> TapResponse:
    device = ADBDevice(request.device_id)
    await asyncio.to_thread(device.tap, x=request.x, y=request.y)
    return TapResponse(success=True)
```

```typescript
// api.ts
export async function sendTap(x: number, y: number, deviceId?: string) {
    const res = await axios.post('/api/control/tap', {
        x, y, device_id: deviceId
    });
    return res.data;
}
```

#### 4.2.2 滑动接口

```python
@router.post("/api/control/swipe", response_model=SwipeResponse)
async def control_swipe(request: SwipeRequest) -> SwipeResponse:
    device = ADBDevice(request.device_id)
    await asyncio.to_thread(
        device.swipe,
        start_x=request.start_x,
        start_y=request.start_y,
        end_x=request.end_x,
        end_y=request.end_y,
        duration_ms=request.duration_ms,
    )
    return SwipeResponse(success=True)
```

---

## 五、模式切换与故障降级

### 5.1 DisplayMode 切换

```typescript
// DeviceMonitor.tsx
type DisplayMode = 'auto' | 'video' | 'screenshot';

const [displayMode, setDisplayMode] = useState<DisplayMode>('auto');
const [videoStreamFailed, setVideoStreamFailed] = useState(false);

// 自动模式逻辑
const shouldUseVideo = displayMode === 'video' || 
    (displayMode === 'auto' && useVideoStream && !videoStreamFailed);
```

### 5.2 故障降级流程

```
视频流启动失败
        │
        ▼
┌───────────────────┐
│ 检查失败原因      │
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
浏览器不支持   其他错误
WebCodecs       │
    │           ▼
    ▼    自动降级到截图模式
显示警告
    │
    ▼
建议下载桌面应用
```

### 5.3 WebCodecs 兼容性检查

```typescript
// lib/webcodecs-utils.ts
export function detectWebCodecsUnavailabilityReason(): string | null {
    // 1. 检查安全上下文
    if (!window.isSecureContext) {
        return 'insecure_context';
    }
    
    // 2. 检查浏览器支持
    if (!('VideoDecoder' in window)) {
        return 'browser_unsupported';
    }
    
    return null;
}
```

---

## 六、关键技术特性

### 6.1 断线重连机制

```typescript
// ScrcpyPlayer.tsx
socket.on('disconnect', () => {
    // 检查组件可见性
    if (!isVisibleRef.current) {
        console.log('组件不可见，跳过重连');
        return;
    }
    
    // 3秒后自动重连
    reconnectTimerRef.current = setTimeout(() => {
        connectDevice();
    }, 3000);
});
```

### 6.2 设备级并发控制

```python
# socketio_server.py
_device_locks: dict[str, asyncio.Lock] = {}

async def connect_device(sid, data):
    device_lock = _device_locks.setdefault(device_id, asyncio.Lock())
    
    async with device_lock:
        # 停止同一设备的其他连接
        sids_to_stop = [s for s, streamer in _socket_streamers.items()
                        if s != sid and streamer.device_id == device_id]
        for s in sids_to_stop:
            await _stop_stream_for_sid(s)
        
        # 启动新流
        streamer = ScrcpyStreamer(device_id=device_id)
        await streamer.start()
```

### 6.3 性能优化策略

| 优化项 | 实现方式 |
|--------|---------|
| 触摸节流 | 50ms 节流窗口 |
| 图片懒加载 | ResizeObserver 触发重绘 |
| 不可见时暂停 | PageVisibility API |
| 端口复用 | 自动清理释放 |

---

## 七、数据流汇总

### 7.1 视频流数据流

```
Android设备
    │
    ▼ (MediaCodec H.264)
scrcpy-server
    │
    ▼ (LocalSocket)
ADB端口转发 (tcp:27183)
    │
    ▼ (TCP Socket)
ScrcpyStreamer
    │
    ▼ (Socket.IO)
Socket.IO Server
    │
    ▼ (video-data 事件)
ScrcpyPlayer
    │
    ▼ (WebCodecs)
WebGLVideoFrameRenderer
    │
    ▼
Canvas 渲染
```

### 7.2 用户交互数据流

```
用户鼠标事件
    │
    ▼ (坐标映射)
Canvas 坐标 → 设备坐标
    │
    ▼ (HTTP POST)
/api/control/*
    │
    ▼ (ADB Shell)
adb shell input tap/swipe
    │
    ▼
Android 设备执行
```

---

## 八、总结

| 特性 | 实现方式 | 优势 |
|------|---------|------|
| **实时预览** | Scrcpy + WebCodecs | 低延迟（50-150ms） |
| **高分辨率截图** | `adb exec-out screencap` | 无临时文件，避免损坏 |
| **用户交互** | REST API + 触摸事件序列 | 精确控制 |
| **故障降级** | 自动切换截图模式 | 高可用性 |
| **并发控制** | 设备级 Lock | 防止资源冲突 |
