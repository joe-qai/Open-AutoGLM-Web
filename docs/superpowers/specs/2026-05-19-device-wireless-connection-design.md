# 设备智能发现与TCP/IP连接设计方案

## 1. 概述

本设计方案旨在增强LOCKIN Agent Platform的设备管理功能，实现智能设备发现和一键TCP/IP连接，让用户可以轻松地将USB连接的Android设备转换为无线连接。

## 2. 目标

- 自动发现所有通过ADB连接的设备（USB和TCP/IP）
- 提供一键开启设备无线连接的功能
- 自动获取设备IP地址
- 提供流畅的用户体验

## 3. 现有功能

- ✅ `adb devices` 自动发现已实现
- ✅ TCP/IP连接功能已实现
- ✅ 设备信息获取已实现（型号、系统版本、分辨率等）

## 4. 新增功能设计

### 4.1 智能设备发现

**功能描述：**
- 页面加载时自动调用 `adb devices` 获取设备列表
- 实时显示设备连接状态（USB/TCP/IP）
- 支持按平台筛选设备

**技术实现：**
```python
def _discover_adb_devices(self) -> List[Dict]:
    """Discover connected ADB devices (USB and TCPIP)."""
    output = self._run_adb_command("devices")

    for line in output.split('\n'):
        parts = line.split('\t')
        if len(parts) >= 2 and parts[1] == 'device':
            device_id = parts[0]
            # 判断设备类型：如果是IP:Port格式则为TCP/IP连接
            is_tcpip = ':' in device_id and device_id.split(':')[-1].isdigit()
```

### 4.2 一键开启无线连接

**功能描述：**
用户点击"开启无线连接"按钮后，平台自动：
1. 获取设备的IP地址
2. 执行 `adb tcpip 5555` 开启TCP/IP模式
3. 执行 `adb connect <IP>:5555` 连接设备
4. 刷新设备列表，显示新的TCP/IP连接设备

**技术实现：**

#### 后端 - 获取设备IP
```python
def get_device_ip(self, device_id: str) -> Optional[str]:
    """Get device IP address."""
    output = self._run_adb_command("shell ip addr show wlan0", device_id)
    # 解析IP地址，格式如：inet 192.168.1.100/24
    match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
    if match:
        return match.group(1)

    # 备选方案：尝试其他网络接口
    output = self._run_adb_command("shell ifconfig wlan0", device_id)
    match = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', output)
    if match:
        return match.group(1)

    return None
```

#### 后端 - 开启TCP/IP模式
```python
def enable_tcpip_mode(self, device_id: str) -> bool:
    """Enable TCP/IP mode on device."""
    result = self._run_adb_command("tcpip 5555", device_id)
    time.sleep(2)  # 等待设备重启ADB服务
    return result is not None

def connect_tcpip(self, ip: str, port: int = 5555) -> bool:
    """Connect to device via TCP/IP."""
    result = self._run_adb_command(f"connect {ip}:{port}")
    return "connected" in result.lower()
```

#### 后端 - 组合操作
```python
def enable_wireless_connection(self, device_id: str) -> Dict[str, Any]:
    """Enable wireless connection for a USB device."""
    # 1. 获取IP
    ip = self.get_device_ip(device_id)
    if not ip:
        return {"success": False, "message": "无法获取设备IP地址"}

    # 2. 开启TCP/IP模式
    if not self.enable_tcpip_mode(device_id):
        return {"success": False, "message": "无法开启TCP/IP模式"}

    # 3. 连接TCP/IP设备
    success = self.connect_tcpip(ip)

    return {
        "success": success,
        "message": f"成功开启无线连接: {ip}:5555",
        "ip": ip,
        "port": 5555
    }
```

### 4.3 前端UI增强

**设备卡片显示：**
- 显示连接类型标签（USB / TCP/IP）
- USB设备显示"开启无线连接"按钮
- TCP/IP设备显示IP地址

**交互流程：**
1. 用户点击"开启无线连接"按钮
2. 显示加载状态："正在获取设备信息..."
3. 成功后显示："无线连接已开启: 192.168.1.100:5555"
4. 自动刷新设备列表

## 5. API设计

### 5.1 新增端点

#### POST `/api/v1/devices/{device_id}/wireless`
开启设备的无线连接功能

**请求体：**
```json
{
  "port": 5555  // 可选，默认5555
}
```

**响应：**
```json
{
  "success": true,
  "message": "无线连接已开启",
  "device_id": "192.168.1.100:5555",
  "ip": "192.168.1.100",
  "port": 5555
}
```

#### GET `/api/v1/devices/{device_id}/ip`
获取设备的IP地址

**响应：**
```json
{
  "ip": "192.168.1.100",
  "interface": "wlan0"
}
```

### 5.2 现有端点增强

#### GET `/api/v1/devices`
增强返回数据，包含连接类型

```json
{
  "devices": [
    {
      "device_id": "192.168.1.100:5555",
      "name": "Xiaomi 13",
      "platform": "android",
      "status": "connected",
      "connection_type": "tcpip",
      "ip": "192.168.1.100",
      "model": "Xiaomi 13"
    },
    {
      "device_id": "4a3f2c1d",
      "name": "USB Device",
      "platform": "android",
      "status": "connected",
      "connection_type": "usb"
    }
  ]
}
```

## 6. 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 无法获取设备IP | 提示用户检查设备网络连接 |
| TCP/IP模式开启失败 | 提示用户重新连接USB |
| TCP/IP连接失败 | 自动重试一次，仍失败则提示用户手动操作 |
| 设备离线 | 自动刷新列表并提示用户检查连接 |

## 7. 用户体验优化

### 7.1 引导提示
- 首次使用时显示使用说明
- USB设备检测到时提示："是否开启无线连接？"

### 7.2 状态反馈
- 每个操作都有明确的加载状态
- 成功后显示绿色提示
- 失败时显示红色错误和解决方案

### 7.3 设备列表
- 按连接类型分组显示（USB设备 / 无线设备）
- 显示设备的连接质量（信号强度等）

## 8. 安全性考虑

- TCP/IP连接仅在局域网内可用
- 不支持通过互联网远程连接
- 连接信息不持久化存储

## 9. 测试计划

### 9.1 功能测试
- [ ] USB设备自动发现
- [ ] TCP/IP设备自动发现
- [ ] 获取设备IP成功
- [ ] 开启无线连接成功
- [ ] 切换连接类型成功

### 9.2 异常测试
- [ ] 设备断开连接处理
- [ ] 网络异常处理
- [ ] 权限异常处理

## 10. 实施步骤

1. **后端增强**
   - 添加设备IP获取功能
   - 添加开启TCP/IP模式功能
   - 组合操作API实现
   - 增强设备列表返回数据

2. **前端增强**
   - 更新设备Store添加无线连接方法
   - 增强设备卡片UI显示连接类型
   - 添加一键开启无线连接按钮
   - 实现完整的用户交互流程

3. **测试验证**
   - 单元测试
   - 集成测试
   - 用户验收测试

## 11. 预计工作量

- 后端开发：2-3小时
- 前端开发：2-3小时
- 测试验证：1-2小时
- **总计：5-8小时**
