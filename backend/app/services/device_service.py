"""Device service for managing devices."""

import subprocess
import re
import time
from typing import List, Optional, Dict

from app.schemas.device import DeviceInfo, DeviceStatus, PlatformType, ConnectionType


class DeviceService:
    """Service for device management."""
    
    def __init__(self):
        self.devices = {}
    
    def _run_adb_command(self, command: str, device_serial: Optional[str] = None) -> str:
        """Run ADB command and return output."""
        cmd = "adb"
        if device_serial:
            cmd += f" -s {device_serial}"
        cmd += f" {command}"
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True, timeout=30)
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            return ""
    
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

                if ':' in device_id and device_id.split(':')[-1].isdigit():
                    device_info["connection_type"] = "tcpip"
                    device_info["ip"] = device_id.rsplit(':', 1)[0]
                else:
                    device_info["connection_type"] = "usb"
                    device_info["ip"] = None

                devices.append(device_info)
        
        return devices
    
    def _get_device_info(self, device_id: str) -> Dict:
        """Get detailed information about a device."""
        info = {
            "device_id": device_id,
            "name": device_id,
            "platform": "android",
            "status": "connected",
            "connection_type": "usb",
            "ip": None,
            "model": None,
            "manufacturer": None,
            "os_version": None,
            "android_sdk_version": None,
            "device_type": None,
            "screen_width": None,
            "screen_height": None,
            "battery_level": None
        }
        
        # Get model, manufacturer, OS version, SDK version, device type
        info["model"] = self._run_adb_command("shell getprop ro.product.model", device_id).strip()
        info["manufacturer"] = self._run_adb_command("shell getprop ro.product.manufacturer", device_id).strip()
        info["os_version"] = self._run_adb_command("shell getprop ro.build.version.release", device_id).strip()
        info["android_sdk_version"] = self._run_adb_command("shell getprop ro.build.version.sdk", device_id).strip()
        info["device_type"] = self._run_adb_command("shell getprop ro.build.characteristics", device_id).strip()
        
        # Get screen resolution
        output = self._run_adb_command("shell wm size", device_id)
        match = re.search(r'(\d+)x(\d+)', output)
        if match:
            info["screen_width"] = int(match.group(1))
            info["screen_height"] = int(match.group(2))

        # Get battery level
        output = self._run_adb_command("shell dumpsys battery", device_id)
        for line in output.split('\n'):
            if 'level:' in line:
                match = re.search(r'level:\s*(\d+)', line)
                if match:
                    info["battery_level"] = int(match.group(1))
        
        # Set name
        if info["model"]:
            info["name"] = info["model"]
        elif info["manufacturer"]:
            info["name"] = f"{info['manufacturer']} Device"
        
        return info
    
    def get_device_ip(self, device_id: str) -> Optional[str]:
        """Get device IP address via ADB."""
        output = self._run_adb_command("shell ip addr show wlan0", device_id)
        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
        if match:
            return match.group(1)

        output = self._run_adb_command("shell ifconfig wlan0", device_id)
        match = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', output)
        if match:
            return match.group(1)

        output = self._run_adb_command("shell netcfg", device_id)
        for line in output.split('\n'):
            if 'wlan0' in line:
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    return match.group(1)

        return None
    
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
    
    def enable_wireless_connection(self, device_id: str, port: int = 5555) -> Dict[str, any]:
        """Enable wireless connection for a USB device."""
        ip = self.get_device_ip(device_id)
        if not ip:
            return {
                "success": False,
                "message": "无法获取设备IP地址，请确保设备已连接网络"
            }

        if not self.enable_tcpip_mode(device_id, port):
            return {
                "success": False,
                "message": "无法开启TCP/IP模式，请检查USB连接"
            }

        time.sleep(2)
        success = self.connect_tcpip(f"{ip}:{port}")

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
    
    def _discover_hdc_devices(self) -> List[Dict]:
        """Discover connected HarmonyOS devices via HDC."""
        devices = []
        try:
            result = subprocess.run(
                "hdc list targets", 
                capture_output=True, 
                text=True, 
                encoding="utf-8",
                errors="replace",
                shell=True, 
                timeout=30
            )
            output = result.stdout.strip()
            
            for line in output.split('\n'):
                line = line.strip()
                if line and 'device' in line.lower():
                    parts = line.split()
                    device_id = parts[0] if parts else line
                    devices.append({
                        "device_id": device_id,
                        "name": f"HarmonyOS Device",
                        "platform": "harmonyos",
                        "status": "connected",
                        "connection_type": "usb",
                        "ip": None,
                        "model": None,
                        "manufacturer": "Huawei",
                        "os_version": None,
                        "screen_width": None,
                        "screen_height": None
                    })
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return devices
    
    def list_devices(self, platform: PlatformType | None = None) -> List[DeviceInfo]:
        """List all connected devices."""
        device_list = []
        
        # Discover real devices
        adb_devices = self._discover_adb_devices()
        hdc_devices = self._discover_hdc_devices()
        
        # Combine and filter by platform
        all_devices = adb_devices + hdc_devices
        
        # If no real devices found, return empty list
        if not all_devices:
            all_devices = []
        
        for device in all_devices:
            if platform and device["platform"] != platform.value:
                continue
            
            # 根据连接类型确定可用操作
            # USB设备：去掉断开，保留开启无线和详情
            # TCPIP设备：去掉开启无线，保留断开和详情
            conn_type = device["connection_type"]
            if conn_type == "usb":
                available_actions = ["wireless", "screenshot", "apps", "launch", "detail"]
            elif conn_type == "tcpip":
                available_actions = ["disconnect", "screenshot", "apps", "launch", "detail"]
            else:
                available_actions = ["detail"]
            
            device_list.append(DeviceInfo(
                device_id=device["device_id"],
                name=device["name"],
                platform=PlatformType(device["platform"]),
                status=DeviceStatus(device["status"]),
                connection_type=ConnectionType(conn_type),
                ip=device["ip"],
                model=device["model"],
                manufacturer=device["manufacturer"],
                os_version=device["os_version"],
                screen_width=device["screen_width"],
                screen_height=device["screen_height"],
                battery_level=device.get("battery_level"),
                device_type=device.get("device_type"),
                android_sdk_version=device.get("android_sdk_version"),
                available_actions=available_actions
            ))
        
        return device_list
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device by ID."""
        devices = self.list_devices()
        return next((d for d in devices if d.device_id == device_id), None)
    
    def connect_device(self, device_id: str) -> bool:
        """Connect to a device."""
        device = self.get_device(device_id)
        if device:
            if device.platform == PlatformType.ANDROID:
                # Try reconnecting ADB device
                self._run_adb_command(f"connect {device_id}")
                time.sleep(1)
            self.devices[device_id] = {"status": "connected"}
            return True
        return False
    
    def disconnect_device(self, device_id: str):
        """Disconnect from a device. Only disconnects TCP/IP devices; USB is physical."""
        device = self.get_device(device_id)
        if device and device.platform == PlatformType.ANDROID:
            if device.connection_type == ConnectionType.TCPIP:
                self._run_adb_command(f"disconnect {device_id}")
        if device_id in self.devices:
            del self.devices[device_id]
    
    def get_screenshot(self, device_id: str) -> Optional[str]:
        """Get screenshot from device."""
        device = self.get_device(device_id)
        if device:
            import base64
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                save_path = f.name
            
            try:
                if device.platform == PlatformType.ANDROID:
                    cmd = f"adb -s {device_id} exec-out screencap -p > {save_path}"
                    subprocess.run(cmd, shell=True, capture_output=True)
                    
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        with open(save_path, "rb") as f:
                            return base64.b64encode(f.read()).decode()
            finally:
                if os.path.exists(save_path):
                    os.unlink(save_path)
        
        return None
    
    def launch_app(self, device_id: str, app_name: str) -> bool:
        """Launch an app on device."""
        device = self.get_device(device_id)
        if device:
            if device.platform == PlatformType.ANDROID:
                self._run_adb_command(f"shell monkey -p {app_name} -c android.intent.category.LAUNCHER 1", device_id)
                return True
        return False
    
    def get_installed_apps(self, device_id: str) -> List[dict]:
        """Get installed apps."""
        device = self.get_device(device_id)
        if device and device.platform == PlatformType.ANDROID:
            output = self._run_adb_command("shell pm list packages -3", device_id)
            apps = []
            for line in output.split('\n'):
                match = re.search(r"package:(.+)", line)
                if match:
                    package_name = match.group(1)
                    apps.append({"package_name": package_name, "name": package_name})
            return apps
        
        return [
            {"package_name": "com.tencent.mm", "name": "微信"},
            {"package_name": "com.xingin.xhs", "name": "小红书"},
            {"package_name": "com.ss.android.ugc.aweme", "name": "抖音"}
        ]
    
    def connect_tcpip(self, ip_port: str) -> bool:
        """Connect to an Android device via TCP/IP (e.g., 192.168.1.100:5555)."""
        try:
            result = self._run_adb_command(f"connect {ip_port}")
            time.sleep(1)
            return "connected" in result.lower()
        except Exception:
            return False
    
    def disconnect_tcpip(self, ip_port: str):
        """Disconnect from an Android device connected via TCP/IP."""
        self._run_adb_command(f"disconnect {ip_port}")
        if ip_port in self.devices:
            del self.devices[ip_port]
