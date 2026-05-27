🔍 Open-AutoGLM Web端设备实时画面同步方案

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    浏览器 (Chrome/Edge)                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  ScrcpyPlayer.tsx                                           │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │ Socket.IO → ReadableStream → TransformStream        │    │    │
│  │  │           → WebCodecsVideoDecoder → Canvas          │    │    │
│  │  └────────────────────┬────────────────────────────────┘    │    │
│  │                       │ WebGL/Bitmap渲染                      │    │
│  │                       ▼                                     │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │  Canvas (画面显示 + 鼠标交互)                        │    │    │
│  │  └────────────────────┬────────────────────────────────┘    │    │
│  └───────────────────────┼─────────────────────────────────────┘    │
│                          │                                         │
│              HTTP API (tap/swipe/touch/down/move/up)               │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│              FastAPI + Socket.IO 后端 (Python)                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Socket.IO Server                                          │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │ 事件处理: connect-device, video-data, disconnect     │    │    │
│  │  │ 并发控制: asyncio.Lock / 设备级互斥                 │    │    │
│  │  └────────────────────┬────────────────────────────────┘    │    │
│  └───────────────────────┼─────────────────────────────────────┘    │
│                          │                                          │
│  ┌───────────────────────▼─────────────────────────────────────┐    │
│  │               ScrcpyStreamer (核心视频流引擎)                  │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │ start() → _cleanup → _push_server → _setup_forward  │    │    │
│  │  │ → _start_server → _connect_socket                  │    │    │
│  │  │ → read_video_metadata → iter_packets               │    │    │
│  │  └────────────────────┬────────────────────────────────┘    │    │
│  └───────────────────────┼─────────────────────────────────────┘    │
│                          │                                          │
│  ┌───────────────────────▼─────────────────────────────────────┐    │
│  │                      ADB 设备层                               │    │
│  │  adb_device.py | control API | screenshot API              │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │     Android 真机           │
              │   (USB / WiFi ADB)        │
              └───────────────────────────┘
```

---

## 二、核心组件说明

### 2.1 后端组件

#### ScrcpyStreamer (`backend/app/services/scrcpy_streamer.py`)

**职责**：管理scrcpy服务器生命周期和视频流解析

**关键配置参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `device_id` | None | ADB设备序列号（None表示默认设备） |
| `max_size` | 1280 | 最大视频分辨率（保持宽高比） |
| `bit_rate` | 4,000,000 | 视频码率（bps） |
| `port` | 27183 | TCP端口 |
| `idr_interval_s` | 1 | IDR帧间隔（关键帧频率） |

**生命周期流程**：

```
start() 
  │
  ├─→ _check_device_available()      # 验证设备在线状态
  │
  ├─→ _cleanup_existing_server()     # 清理残留进程和端口
  │     ├─→ pkill -9 -f app_process.*scrcpy
  │     ├─→ adb forward --remove tcp:27183
  │     └─→ wait_for_port_release()  # 轮询等待端口释放
  │
  ├─→ _push_server()                 # 推送scrcpy-server到设备
  │
  ├─→ _setup_port_forward()          # 设置端口转发
  │     └─→ adb forward tcp:27183 localabstract:scrcpy
  │
  ├─→ _start_server()                # 启动scrcpy服务器（3次重试）
  │
  ├─→ _connect_socket()              # TCP连接（10次指数退避重试）
  │
  └─→ read_video_metadata()          # 读取设备名称、分辨率、编码信息
```

**协议解析（scrcpy v3.3.3）**：

```
1. 读1字节 dummy byte（send_dummy_byte=true）
2. 读64字节设备名（send_device_meta=true）
3. 读编解码器元数据（send_codec_meta=true）
   └─→ 4字节 codec_id + 4字节 width + 4字节 height
4. 循环读取帧数据：
   ├─→ 8字节 PTS（presentation timestamp）
   │     ├─→ PTS == 1<<63 → configuration packet（SPS/PPS）
   │     └─→ PTS & 1<<62 → keyframe标记
   ├─→ 4字节 data_length
   └─→ data_length字节 payload（H.264 NAL单元）
```

**资源清理（stop()）**：

```
1. 设置 _should_stop 事件标志
2. 关闭 TCP socket
3. 终止 scrcpy 进程（2s超时后强制kill）
4. 移除 ADB 端口转发
```

#### ScrcpyProtocol (`backend/app/services/scrcpy_protocol.py`)

**职责**：定义scrcpy协议数据结构和常量

**关键常量**：

| 常量 | 值 | 说明 |
|------|----|------|
| `PTS_CONFIG` | 1 << 63 | 配置包标记 |
| `PTS_KEYFRAME` | 1 << 62 | 关键帧标记 |
| `DEFAULT_PORT` | 27183 | 默认端口 |

**数据结构**：
- `ScrcpyVideoStreamOptions` - 视频流选项配置
- `ScrcpyVideoStreamMetadata` - 视频流元数据（设备名、分辨率、编码）
- `ScrcpyMediaStreamPacket` - 媒体数据包（配置包/数据包）

---

### 2.2 前端组件

#### ScrcpyPlayer (`frontend/src/components/ScrcpyPlayer/ScrcpyPlayer.tsx`)

**职责**：Web端视频流接收、解码、渲染和交互控制

**Props配置**：

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `deviceId` | string | - | 设备ID（必填） |
| `enableControl` | boolean | false | 是否启用触摸控制 |
| `fallbackTimeout` | number | 20000 | 降级超时时间(ms) |
| `isVisible` | boolean | true | 组件可见性（控制连接状态） |

**解码流程**：

```
Socket.IO连接 → video-metadata → 创建WebCodecsVideoDecoder
                                      │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
            WebGLVideoFrameRenderer              BitmapVideoFrameRenderer
            (GPU加速，优先)                        (CPU软渲染，回退)
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
                                  Canvas渲染
```

**TransformStream排序机制**：

```
收到video-data → 判断包类型
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
  configuration包         data包
         │                     │
    立即传递给           等待configuration
    decoder               包后再传递
```

**WebCodecs不可用降级链**：

```
检测WebCodecs支持
    │
    ├─→ browser_unsupported    → 浏览器不支持（非Chrome/Edge）
    │
    ├─→ insecure_context       → 非HTTPS/localhost环境
    │
    └─→ decoder_unsupported    → 编解码器不支持
            │
            ▼
    降级到截图轮询模式
```

---

## 三、通信协议

### 3.1 Socket.IO 事件流

**连接建立**：

| 方向 | 事件名 | 数据结构 | 说明 |
|------|--------|----------|------|
| Client → Server | `connect-device` | `{ device_id, maxSize, bitRate }` | 请求建立视频流 |
| Server → Client | `video-metadata` | `{ deviceName, width, height, codec }` | 发送视频元数据 |
| Server → Client | `video-data` | `{ isConfig, isKeyframe, pts, data }` | 发送视频帧数据 |
| Server → Client | `error` | `{ message, type }` | 发送错误信息 |

**错误类型**：

| 类型 | 说明 |
|------|------|
| `port_conflict` | 端口冲突 |
| `device_offline` | 设备离线 |
| `timeout` | 连接超时 |
| `connection_failed` | 连接失败 |

### 3.2 HTTP控制API

| 操作 | API端点 | ADB命令 |
|------|---------|---------|
| 点击 | `POST /api/control/tap` | `input tap x y` |
| 滑动 | `POST /api/control/swipe` | `input swipe x1 y1 x2 y2` |
| 按下 | `POST /api/control/touch/down` | `input motionevent DOWN x y` |
| 移动 | `POST /api/control/touch/move` | `input motionevent MOVE x y` |
| 抬起 | `POST /api/control/touch/up` | `input motionevent UP x y` |

---

## 四、坐标映射机制

**从鼠标位置到设备坐标的转换**：

```
1. 获取容器的 getBoundingClientRect()
2. 计算鼠标相对容器的偏移 (relativeX, relativeY)
3. 考虑视频宽高比和容器宽高比，计算缩放和偏移
4. 映射到视频流坐标：streamX, streamY
5. 映射到设备真实分辨率：
   deviceX = streamX * (deviceResolution.width / streamDimensions.width)
   deviceY = streamY * (deviceResolution.height / streamDimensions.height)
```

**触摸节流优化**：

| 事件类型 | 节流/防抖时间 | 说明 |
|----------|---------------|------|
| touch move | 50ms | MOTION_THROTTLE_MS |
| pending move | 补发机制 | 上次未发送的移动在下次触发时补发 |
| wheel | 300ms | WHEEL_DELAY_MS，累积deltaY后一次性发送 |

---

## 五、生命周期管理

### 5.1 智能重连策略

```
Socket断连 → 3秒后自动重连
组件隐藏(isVisible=false) → 断开连接，抑制重连
组件重新可见 → 延迟100ms后重连
主动断开 → suppressReconnect=true，不自动重连
```

### 5.2 并发控制

- **设备级互斥**：每个设备一个 `asyncio.Lock`，防止同一设备多个客户端同时连接
- **连接踢除**：新连接自动踢掉同设备的旧连接
- **Session隔离**：每个Socket.IO session独立管理streamer和stream task

### 5.3 资源清理

**前端清理流程**：

```
disconnectDevice(suppressReconnect)
  │
  ├─→ dispose decoder           # 释放解码器
  ├─→ disconnect socket         # 断开Socket连接
  ├─→ clear timers              # 清除所有定时器
  └─→ setStatus('disconnected') # 更新状态
```

---

## 六、延迟分析

| 环节 | 延迟范围 | 说明 |
|------|----------|------|
| scrcpy采集+编码 | ~10-20ms | 设备端H.264编码 |
| ADB端口转发 | ~5ms | 本地TCP转发 |
| TCP读取+解析 | ~5ms | 后端协议解析 |
| Socket.IO推送 | ~5-10ms | WebSocket传输 |
| WebCodecs解码 | ~10-20ms | 浏览器硬件解码 |
| Canvas渲染 | ~5ms | GPU渲染 |
| **总计** | **~40-65ms** | 本地USB连接 |

> **截图轮询模式延迟**：750-1200ms（远程设备或WebCodecs不可用时）

---

## 七、关键设计决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 视频采集 | scrcpy内嵌服务器 | 延迟最低(~50ms)，CPU占用低，成熟稳定 |
| 传输协议 | Socket.IO | 双向通信，自动重连，比原生WebSocket更可靠 |
| 浏览器解码 | WebCodecs API | 零依赖，硬件加速，延迟最低 |
| 渲染方式 | WebGL优先 | GPU加速，Bitmap回退兼容旧浏览器 |
| 控制通道 | HTTP API独立 | 与视频流解耦，各自优化，更灵活 |
| 触摸实现 | ADB motionevent | 比input tap更细粒度，支持DOWN/MOVE/UP |
| 降级方案 | 截图轮询 | 兼容所有设备（含远程），保证可用性 |
| 并发控制 | asyncio.Lock/设备 | 防止多客户端抢占同一设备 |

---

## 八、部署注意事项

### 8.1 依赖要求

- **scrcpy-server**：需将 `scrcpy-server-v3.3.3` 放置在以下任一位置：
  - `resources/scrcpy-server-v3.3.3`
  - `backend/app/services/scrcpy-server-v3.3.3`
  - 环境变量 `SCRCPY_SERVER_PATH` 指定路径

### 8.2 浏览器支持

| 浏览器 | WebCodecs支持 | 备注 |
|--------|--------------|------|
| Chrome | ✅ | 推荐 |
| Edge | ✅ | 推荐 |
| Firefox | ❌ | 降级到截图轮询 |
| Safari | ❌ | 降级到截图轮询 |

### 8.3 安全要求

- WebCodecs API需要**HTTPS环境**或**localhost**
- 非安全上下文将自动降级到截图轮询模式

---

## 九、代码位置速查

| 组件 | 文件路径 |
|------|----------|
| ScrcpyStreamer | `backend/app/services/scrcpy_streamer.py` |
| ScrcpyProtocol | `backend/app/services/scrcpy_protocol.py` |
| Socket.IO Server | `backend/app/api/socketio.py` |
| ScrcpyPlayer | `frontend/src/components/ScrcpyPlayer/ScrcpyPlayer.tsx` |
| Control API | `frontend/src/services/controlApi.ts` |

---

> 🦞 **方案优势**：scrcpy+WebCodecs是目前Web端实时显示Android设备画面的最优解，延迟低、性能好、兼容性强，非常适合Agent可视化平台使用。
