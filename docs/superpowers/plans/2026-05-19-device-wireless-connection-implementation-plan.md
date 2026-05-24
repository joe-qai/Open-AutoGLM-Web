# 设备智能发现与TCP/IP连接实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现智能设备发现和一键TCP/IP无线连接功能，让用户可以轻松将USB设备转换为无线连接

**Architecture:** 后端通过ADB命令实现设备发现、IP获取和TCP/IP模式切换，前端提供友好的UI交互和实时状态反馈

**Tech Stack:** Python/FastAPI (后端), React/TypeScript/Zustand (前端), ADB (设备通信)

---

## 文件结构

### 后端文件
- **修改:** `backend/app/schemas/device.py` - 添加连接类型字段
- **修改:** `backend/app/services/device_service.py` - 添加IP获取、TCP/IP模式切换功能
- **修改:** `backend/app/api/v1/devices.py` - 添加新的API端点

### 前端文件
- **修改:** `frontend/src/stores/deviceStore.ts` - 添加无线连接相关方法
- **修改:** `frontend/src/pages/Device/DevicePage.tsx` - 增强UI显示和交互

---

## 任务清单

### Task 1: 后端 - 增强设备数据模型

**Files:**
- Modify: `backend/app/schemas/device.py`

- [ ] **Step 1: 添加连接类型枚举和增强的设备信息模型**

```python
class ConnectionType(str, Enum):
    """Device connection type."""
    USB = "usb"
    TCPIP = "tcpip"

class DeviceInfo(BaseModel):
    """Device information model."""
    device_id: str
    name: str
    platform: PlatformType
    status: DeviceStatus
    connection_type: ConnectionType = ConnectionType.USB  # 新增字段
    ip: Optional[str] = None  # 新增字段：TCP/IP设备的IP地址
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    os_version: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    battery_level: Optional[int] = None
    last_seen: Optional[str] = None
    
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 添加无线连接请求模型**

```python
class WirelessConnectRequest(BaseModel):
    """Request model for enabling wireless connection."""
    device_id: str
    port: int = 5555
```

- [ ] **Step 3: 添加设备IP响应模型**

```python
class DeviceIpResponse(BaseModel):
    """Response model for device IP address."""
    ip: Optional[str]
    interface: Optional[str] = None
```

---

### Task 2: 后端 - 实现设备IP获取功能

**Files:**
- Modify: `backend/app/services/device_service.py`

- [ ] **Step 1: 在DeviceService类中添加设备IP获取方法**

```python
def get_device_ip(self, device_id: str) -> Optional[str]:
    """Get device IP address via ADB."""
    # 尝试获取wlan0接口的IP地址
    output = self._run_adb_command("shell ip addr show wlan0", device_id)
    match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
    if match:
        return match.group(1)

    # 备选方案1：使用ifconfig
    output = self._run_adb_command("shell ifconfig wlan0", device_id)
    match = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', output)
    if match:
        return match.group(1)

    # 备选方案2：使用netcfg
    output = self._run_adb_command("shell netcfg", device_id)
    for line in output.split('\n'):
        if 'wlan0' in line:
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                return match.group(1)

    return None
```

- [ ] **Step 2: 添加TCP/IP模式开启方法**

```python
def enable_tcpip_mode(self, device_id: str, port: int = 5555) -> bool:
    """Enable TCP/IP mode on device."""
    result = self._run_adb_command(f"tcpip {port}", device_id)
    time.sleep(2)  # 等待设备重启ADB服务
    return result is not None
```

- [ ] **Step 3: 修改_discover_adb_devices方法，添加连接类型判断**

```python
def _discover_adb_devices(self) -> List[Dict]:
    """Discover connected ADB devices (USB and TCPIP)."""
    devices = []
    output = self._run_adb_command("devices")

    for line in output.split('\n'):
        line = line.strip()
        if not line or line.startswith('List of devices'):
            continue

        parts = line.split('\t')
        if len(parts) >= 2 and parts[1] == 'device':
            device_id = parts[0]
            device_info = self._get_device_info(device_id)

            # 判断连接类型
            if ':' in device_id and device_id.split(':')[-1].isdigit():
                device_info["connection_type"] = "tcpip"
                device_info["ip"] = device_id.rsplit(':', 1)[0]
            else:
                device_info["connection_type"] = "usb"
                device_info["ip"] = None

            devices.append(device_info)

    return devices
```

- [ ] **Step 4: 修改_get_device_info方法，添加connection_type和ip字段**

```python
def _get_device_info(self, device_id: str) -> Dict:
    """Get detailed information about a device."""
    info = {
        "device_id": device_id,
        "name": device_id,
        "platform": "android",
        "status": "connected",
        "connection_type": "usb",  # 默认USB
        "ip": None,  # 默认无IP
        "model": None,
        "manufacturer": None,
        "os_version": None,
        "screen_width": None,
        "screen_height": None
    }
    # ... 其余代码保持不变 ...
    return info
```

- [ ] **Step 5: 修改list_devices方法，传递connection_type**

```python
def list_devices(self, platform: PlatformType | None = None) -> List[DeviceInfo]:
    """List all connected devices."""
    # ... 前面的代码保持不变 ...

    for device in all_devices:
        if platform and device["platform"] != platform.value:
            continue

        device_list.append(DeviceInfo(
            device_id=device["device_id"],
            name=device["name"],
            platform=PlatformType(device["platform"]),
            status=DeviceStatus(device["status"]),
            connection_type=ConnectionType(device["connection_type"]),  # 新增
            ip=device["ip"],  # 新增
            model=device["model"],
            manufacturer=device["manufacturer"],
            os_version=device["os_version"],
            screen_width=device["screen_width"],
            screen_height=device["screen_height"]
        ))

    return device_list
```

- [ ] **Step 6: 添加一键开启无线连接方法**

```python
def enable_wireless_connection(self, device_id: str, port: int = 5555) -> Dict[str, Any]:
    """Enable wireless connection for a USB device."""
    # 1. 获取IP
    ip = self.get_device_ip(device_id)
    if not ip:
        return {
            "success": False,
            "message": "无法获取设备IP地址，请确保设备已连接网络"
        }

    # 2. 开启TCP/IP模式
    if not self.enable_tcpip_mode(device_id, port):
        return {
            "success": False,
            "message": "无法开启TCP/IP模式，请检查USB连接"
        }

    # 3. 连接TCP/IP设备
    time.sleep(2)  # 等待ADB服务重启
    success = self.connect_tcpip(ip, port)

    if success:
        return {
            "success": True,
            "message": f"无线连接已开启: {ip}:{port}",
            "device_id": f"{ip}:{port}",
            "ip": ip,
            "port": port
        }
    else:
        return {
            "success": False,
            "message": "TCP/IP连接失败，请手动执行连接命令"
        }
```

---

### Task 3: 后端 - 添加新的API端点

**Files:**
- Modify: `backend/app/api/v1/devices.py`

- [ ] **Step 1: 添加导入**

```python
from app.schemas.device import DeviceInfo, DeviceStatus, PlatformType, TcpIpConnectRequest, WirelessConnectRequest, DeviceIpResponse, ConnectionType
```

- [ ] **Step 2: 添加获取设备IP的端点**

```python
@router.get("/{device_id}/ip")
async def get_device_ip(device_id: str):
    """Get device IP address."""
    ip = device_service.get_device_ip(device_id)
    if not ip:
        raise HTTPException(status_code=404, detail="无法获取设备IP地址")
    return {"ip": ip, "interface": "wlan0"}
```

- [ ] **Step 3: 添加一键开启无线连接的端点**

```python
@router.post("/{device_id}/wireless")
async def enable_wireless(device_id: str, port: int = 5555):
    """Enable wireless connection for a USB device."""
    result = device_service.enable_wireless_connection(device_id, port)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result
```

- [ ] **Step 4: 更新TCP/IP连接端点（可选优化）**

增强现有的TCP/IP连接端点，添加端口参数支持。

---

### Task 4: 前端 - 更新设备Store

**Files:**
- Modify: `frontend/src/stores/deviceStore.ts`

- [ ] **Step 1: 更新Device接口，添加连接类型字段**

```typescript
export interface Device {
  device_id: string;
  name: string;
  platform: 'android' | 'ios' | 'harmonyos';
  status: 'connected' | 'disconnected' | 'busy';
  connection_type: 'usb' | 'tcpip';  // 新增
  ip?: string;  // 新增
  model?: string;
  manufacturer?: string;
  os_version?: string;
  screen_width?: number;
  screen_height?: number;
  battery_level?: number;
  last_seen?: string;
}
```

- [ ] **Step 2: 更新DeviceState接口**

```typescript
interface DeviceState {
  devices: Device[];
  selectedDevice: Device | null;
  loading: boolean;
  connectingTcpIp: boolean;
  enablingWireless: boolean;  // 新增
  error: string | null;
  success: string | null;

  // Actions
  fetchDevices: () => Promise<void>;
  selectDevice: (device: Device | null) => void;
  connectDevice: (deviceId: string) => Promise<void>;
  disconnectDevice: (deviceId: string) => Promise<void>;
  connectTcpIp: (ipPort: string) => Promise<void>;
  enableWireless: (deviceId: string, port?: number) => Promise<void>;  // 新增
  getDeviceIp: (deviceId: string) => Promise<string | null>;  // 新增
  clearMessages: () => void;
}
```

- [ ] **Step 3: 添加enableWireless方法实现**

```typescript
enableWireless: async (deviceId: string, port: number = 5555) => {
  set({ enablingWireless: true, error: null, success: null });
  try {
    const response = await deviceApi.enableWireless(deviceId, port) as unknown as {
      success: boolean;
      message: string;
      device_id?: string;
    };
    
    if (response.success) {
      await get().fetchDevices();
      set({ enablingWireless: false, success: response.message });
    } else {
      set({ enablingWireless: false, error: response.message });
    }
  } catch (error: any) {
    set({ 
      enablingWireless: false, 
      error: error.response?.data?.detail || 'Failed to enable wireless connection' 
    });
  }
},
```

- [ ] **Step 4: 添加getDeviceIp方法实现**

```typescript
getDeviceIp: async (deviceId: string) => {
  try {
    const response = await deviceApi.getDeviceIp(deviceId) as unknown as { ip: string };
    return response.ip;
  } catch (error) {
    console.error('Failed to get device IP:', error);
    return null;
  }
},
```

- [ ] **Step 5: 在api.ts中添加新的API方法**

```typescript
// 在deviceApi中添加
enableWireless: (deviceId: string, port: number = 5555) =>
  api.post(`/api/v1/devices/${deviceId}/wireless`, { port }),
getDeviceIp: (deviceId: string) => api.get(`/api/v1/devices/${deviceId}/ip`),
```

---

### Task 5: 前端 - 增强设备页面UI

**Files:**
- Modify: `frontend/src/pages/Device/DevicePage.tsx`

- [ ] **Step 1: 添加连接类型显示组件**

```typescript
const getConnectionBadge = (connectionType: string, ip?: string) => {
  switch (connectionType) {
    case 'usb':
      return (
        <div className="flex items-center gap-1">
          <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full">
            USB
          </span>
        </div>
      );
    case 'tcpip':
      return (
        <div className="flex items-center gap-1">
          <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
            无线
          </span>
          {ip && (
            <span className="text-[#64748b] text-xs">{ip}</span>
          )}
        </div>
      );
    default:
      return null;
  }
};
```

- [ ] **Step 2: 在设备卡片中添加连接类型显示**

在状态徽章旁边添加连接类型显示：
```typescript
<div className="flex items-center gap-2 mt-1">
  {getPlatformIcon(device.platform)}
  <span className="text-[#94a3b8] text-sm capitalize">{device.platform}</span>
  {getConnectionBadge(device.connection_type, device.ip)}
</div>
```

- [ ] **Step 3: 为USB设备添加"开启无线连接"按钮**

在设备卡片的操作按钮区域：
```typescript
<div className="flex gap-2">
  {device.status === 'disconnected' ? (
    <button
      onClick={() => connectDevice(device.device_id)}
      className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
    >
      <Power className="w-4 h-4" />
      连接
    </button>
  ) : (
    <>
      {device.connection_type === 'usb' && (
        <button
          onClick={() => enableWireless(device.device_id)}
          disabled={enablingWireless}
          className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
        >
          <Wifi className="w-4 h-4" />
          {enablingWireless ? '开启中...' : '开启无线'}
        </button>
      )}
      <button
        onClick={() => disconnectDevice(device.device_id)}
        className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
      >
        <Power className="w-4 h-4" />
        断开
      </button>
    </>
  )}
  <button className="flex-1 py-2 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors">
    <Monitor className="w-4 h-4" />
    详情
  </button>
</div>
```

- [ ] **Step 4: 更新错误和成功消息提示**

添加enablingWireless状态的加载提示：
```typescript
{enablingWireless && (
  <div className="mb-4 p-3 bg-blue-900/30 border border-blue-500/30 rounded-lg flex items-center gap-2 text-blue-300">
    <Loader2 className="w-4 h-4 animate-spin" />
    正在开启无线连接...
  </div>
)}
```

---

### Task 6: 测试验证

**Files:**
- 测试手动功能（无需自动化测试）

- [ ] **Step 1: 启动后端服务**

```bash
cd backend
python run.py
```

验证：`http://localhost:8000/docs` 打开API文档

- [ ] **Step 2: 测试设备发现API**

```bash
curl http://localhost:8000/api/v1/devices
```

预期：返回设备列表，包含connection_type字段

- [ ] **Step 3: 测试获取设备IP API**

```bash
curl http://localhost:8000/api/v1/devices/<device_id>/ip
```

预期：返回设备IP地址

- [ ] **Step 4: 启动前端服务**

```bash
cd frontend
npm run dev
```

- [ ] **Step 5: 测试完整流程**

1. 连接USB设备
2. 访问设备管理页面
3. 点击"开启无线连接"按钮
4. 验证设备成功转换TCP/IP连接
5. 拔掉USB线，确认TCP/IP连接仍然有效

---

## 实施检查清单

- [ ] Task 1: 设备数据模型增强
- [ ] Task 2: 设备IP获取和TCP/IP模式切换
- [ ] Task 3: 后端API端点
- [ ] Task 4: 前端Store更新
- [ ] Task 5: 前端UI增强
- [ ] Task 6: 测试验证

---

## 预计时间

- Task 1: 10分钟
- Task 2: 30分钟
- Task 3: 15分钟
- Task 4: 20分钟
- Task 5: 25分钟
- Task 6: 15分钟
- **总计: 约115分钟（2小时）**

---

## 关键注意事项

1. **USB断开问题**: 执行 `adb tcpip 5555` 后，USB连接会短暂断开，这是正常现象
2. **IP获取失败**: 部分设备可能需要root权限或特定网络配置才能获取IP
3. **防火墙设置**: 确保电脑防火墙允许ADB端口（5555）通信
4. **网络要求**: USB设备和电脑必须在同一网络才能建立TCP/IP连接

---

**文档版本:** 1.0
**创建日期:** 2026-05-19
**状态:** 待实施
