# PhoneAgent 平台化迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 将 phone_agent 的全部核心能力迁移到 backend，实现平台化的 Agent 服务，最终删除 phone_agent 目录

**架构：** 分层迁移架构，将 phone_agent 的 adb/hdc/xctest/actions/model/config 模块逐步迁移到 backend/app/core/ 对应目录，通过统一的 Adapter 模式整合

**技术栈：** Python 3.10+, FastAPI, SQLAlchemy, aiosqlite, openai SDK

---

## 文件结构概览

```
backend/app/core/
├── devices/                    # 设备抽象层
│   ├── __init__.py
│   ├── base_device.py         # 设备基类
│   ├── factory.py              # 设备工厂
│   ├── adb/                    # Android ADB
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── device.py
│   │   ├── input.py
│   │   └── screenshot.py
│   ├── hdc/                    # HarmonyOS HDC
│   │   └── ...
│   └── xctest/                # iOS XCTest
│       └── ...
├── actions/                   # 动作处理引擎
│   ├── __init__.py
│   ├── handler.py
│   └── action_types.py
├── model/                     # AI 模型客户端
│   ├── __init__.py
│   ├── client.py
│   └── config.py
├── config/                    # 配置管理
│   ├── __init__.py
│   ├── prompts.py
│   ├── apps.py
│   └── timing.py
└── agent/                     # Agent 核心循环
    ├── __init__.py
    ├── base_agent.py
    ├── android_agent.py
    └── task_manager.py

backend/app/api/v1/
└── agent/                     # Agent API 端点
    ├── __init__.py
    ├── tasks.py
    └── execution.py

backend/app/schemas/
└── agent.py                   # Agent 数据模型

backend/app/services/
└── agent_service.py           # Agent 业务服务
```

---

## 实施阶段

### Phase 1: 设备层迁移 (adb/hdc/xctest)

#### Task 1: 创建设备抽象层基础结构

**Files:**
- Create: `backend/app/core/devices/__init__.py`
- Create: `backend/app/core/devices/base_device.py`
- Create: `backend/app/core/devices/factory.py`
- Modify: `backend/app/core/adapters/__init__.py:1-20`

- [ ] **Step 1: 创建设备抽象基类 base_device.py**

```python
# backend/app/core/devices/base_device.py
"""Base device abstraction for multi-platform support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class DisplayInfo:
    """Display information for a device."""
    width: int
    height: int
    density: int
    status_bar_height: int = 0
    navigation_bar_height: int = 0


@runtime_checkable
class DeviceProtocol(Protocol):
    """Protocol defining device operations."""

    def get_screenshot(self, device_id: str | None = None, timeout: int = 10) -> bytes:
        ...

    def get_current_app(self, device_id: str | None = None) -> str:
        ...

    def tap(self, x: int, y: int, device_id: str | None = None) -> None:
        ...

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
              duration_ms: int | None = None, device_id: str | None = None) -> None:
        ...

    def launch_app(self, app_name: str, device_id: str | None = None) -> bool:
        ...

    def type_text(self, text: str, device_id: str | None = None) -> None:
        ...

    def back(self, device_id: str | None = None) -> None:
        ...

    def home(self, device_id: str | None = None) -> None:
        ...


class BaseDevice(ABC):
    """Abstract base class for device implementations."""

    def __init__(self, device_id: str | None = None):
        self.device_id = device_id

    @abstractmethod
    def get_screenshot(self, timeout: int = 10) -> bytes:
        """Capture screenshot from device."""
        pass

    @abstractmethod
    def get_current_app(self) -> str:
        """Get current foreground app."""
        pass

    @abstractmethod
    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        pass

    @abstractmethod
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
              duration_ms: int | None = None) -> None:
        """Swipe from start to end."""
        pass

    @abstractmethod
    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at coordinates."""
        pass

    @abstractmethod
    def type_text(self, text: str) -> None:
        """Type text."""
        pass

    @abstractmethod
    def press_key(self, key: str) -> None:
        """Press hardware key."""
        pass

    @abstractmethod
    def launch_app(self, app_name: str) -> bool:
        """Launch application."""
        pass

    @abstractmethod
    def back(self) -> None:
        """Press back button."""
        pass

    @abstractmethod
    def home(self) -> None:
        """Press home button."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if device is connected."""
        pass

    def get_display_info(self) -> DisplayInfo:
        """Get display information. Override in subclass."""
        return DisplayInfo(width=1080, height=1920, density=320)
```

- [ ] **Step 2: 创建设备工厂 factory.py**

```python
# backend/app/core/devices/factory.py
"""Device factory for creating platform-specific device instances."""

from enum import Enum
from typing import Type

from .base_device import BaseDevice, DisplayInfo
from .adb import ADBDevice
from .hdc import HDCDevice
from .xctest import XCTestDevice


class Platform(Enum):
    """Supported platforms."""
    ANDROID = "android"
    HARMONYOS = "harmonyos"
    IOS = "ios"


class DeviceFactory:
    """Factory for creating platform-specific device instances."""

    _device_classes: dict[Platform, Type[BaseDevice]] = {
        Platform.ANDROID: ADBDevice,
        Platform.HARMONYOS: HDCDevice,
        Platform.IOS: XCTestDevice,
    }

    @classmethod
    def create_device(cls, platform: Platform, device_id: str | None = None) -> BaseDevice:
        """Create a device instance for the specified platform."""
        device_class = cls._device_classes.get(platform)
        if not device_class:
            raise ValueError(f"Unsupported platform: {platform}")
        return device_class(device_id=device_id)

    @classmethod
    def create_by_name(cls, platform_name: str, device_id: str | None = None) -> BaseDevice:
        """Create a device by platform name string."""
        platform_map = {
            "android": Platform.ANDROID,
            "adb": Platform.ANDROID,
            "harmonyos": Platform.HARMONYOS,
            "hdc": Platform.HARMONYOS,
            "ios": Platform.IOS,
            "xctest": Platform.IOS,
        }
        platform = platform_map.get(platform_name.lower())
        if not platform:
            raise ValueError(f"Unknown platform: {platform_name}")
        return cls.create_device(platform, device_id)
```

- [ ] **Step 3: 创建 devices/__init__.py**

```python
# backend/app/core/devices/__init__.py
"""Device abstraction layer for multi-platform support."""

from .base_device import BaseDevice, DeviceProtocol, DisplayInfo
from .factory import DeviceFactory, Platform

__all__ = [
    "BaseDevice",
    "DeviceProtocol",
    "DisplayInfo",
    "DeviceFactory",
    "Platform",
]
```

- [ ] **Step 4: 提交 Phase 1 第一部分**

```bash
git add backend/app/core/devices/
git commit -m "feat(core): add device abstraction layer base structure"
```

---

#### Task 2: 迁移 ADB 设备实现

**Files:**
- Create: `backend/app/core/devices/adb/__init__.py`
- Create: `backend/app/core/devices/adb/connection.py`
- Create: `backend/app/core/devices/adb/device.py`
- Create: `backend/app/core/devices/adb/input.py`
- Create: `backend/app/core/devices/adb/screenshot.py`

- [ ] **Step 1: 创建 ADB 模块的 __init__.py**

```python
# backend/app/core/devices/adb/__init__.py
"""Android device implementation via ADB."""

from .device import ADBDevice
from .connection import ADBConnection
from .screenshot import get_screenshot
from .input import tap, swipe, long_press, type_text, back, home, press_key

__all__ = [
    "ADBDevice",
    "ADBConnection",
    "get_screenshot",
    "tap",
    "swipe",
    "long_press",
    "type_text",
    "back",
    "home",
    "press_key",
]
```

- [ ] **Step 2: 创建 ADB connection.py**

```python
# backend/app/core/devices/adb/connection.py
"""ADB connection management."""

import subprocess
import re
from typing import Optional


class ADBConnection:
    """Manages ADB connection to Android devices."""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id

    def _build_command(self, *args) -> list[str]:
        """Build ADB command with device targeting."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    def execute(self, *args, timeout: int = 30) -> tuple[int, str, str]:
        """Execute ADB command and return (returncode, stdout, stderr)."""
        cmd = self._build_command(*args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", "ADB not found"

    def get_state(self) -> str:
        """Get device state."""
        _, stdout, _ = self.execute("get-state")
        return stdout

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.get_state() == "device"

    def list_devices(self) -> list[str]:
        """List all connected devices."""
        _, stdout, _ = self.execute("devices")
        devices = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def get_property(self, property_name: str) -> str:
        """Get device property via getprop."""
        _, stdout, _ = self.execute("shell", "getprop", property_name)
        return stdout

    def get_model(self) -> str:
        """Get device model name."""
        return self.get_property("ro.product.model")

    def get_screen_size(self) -> tuple[int, int]:
        """Get screen size as (width, height)."""
        _, stdout, _ = self.execute("shell", "wm", "size")
        match = re.search(r"(\d+)x(\d+)", stdout)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 1080, 1920

    def get_screen_density(self) -> int:
        """Get screen density."""
        _, stdout, _ = self.execute("shell", "wm", "density")
        match = re.search(r"(\d+)", stdout)
        if match:
            return int(match.group(1))
        return 320
```

- [ ] **Step 3: 创建 ADB device.py**

```python
# backend/app/core/devices/adb/device.py
"""ADB device implementation."""

from typing import Optional

from ..base_device import BaseDevice, DisplayInfo
from .connection import ADBConnection
from .screenshot import get_screenshot as adb_get_screenshot
from .input import (
    tap as adb_tap,
    swipe as adb_swipe,
    long_press as adb_long_press,
    type_text as adb_type_text,
    back as adb_back,
    home as adb_home,
    press_key as adb_press_key,
)


class ADBDevice(BaseDevice):
    """Android device controlled via ADB."""

    def __init__(self, device_id: Optional[str] = None):
        super().__init__(device_id)
        self._connection = ADBConnection(device_id)
        self._display_info: Optional[DisplayInfo] = None

    @property
    def connection(self) -> ADBConnection:
        """Get ADB connection."""
        return self._connection

    def get_screenshot(self, timeout: int = 10) -> bytes:
        """Capture screenshot via ADB."""
        return adb_get_screenshot(self.device_id, timeout)

    def get_current_app(self) -> str:
        """Get current foreground app package name."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend([
            "shell", "dumpsys", "window", "|",
            "grep", "-E", "mCurrentFocus"
        ])
        import subprocess
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stdout.strip()
            match = re.search(r"(\w+\.\w+)", output)
            if match:
                return match.group(1)
        except Exception:
            pass
        return ""

    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        adb_tap(x, y, self.device_id)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
              duration_ms: Optional[int] = None) -> None:
        """Swipe from start to end."""
        adb_swipe(start_x, start_y, end_x, end_y, duration_ms, self.device_id)

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at coordinates."""
        adb_long_press(x, y, duration_ms, self.device_id)

    def type_text(self, text: str) -> None:
        """Type text."""
        adb_type_text(text, self.device_id)

    def press_key(self, key: str) -> None:
        """Press hardware key."""
        adb_press_key(key, self.device_id)

    def launch_app(self, app_name: str) -> bool:
        """Launch application by package name."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "monkey", "-p", app_name, "-c",
                    "android.intent.category.LAUNCHER", "1"])
        import subprocess
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def back(self) -> None:
        """Press back button."""
        adb_back(self.device_id)

    def home(self) -> None:
        """Press home button."""
        adb_home(self.device_id)

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._connection.is_connected()

    def get_display_info(self) -> DisplayInfo:
        """Get display information."""
        if self._display_info is None:
            width, height = self._connection.get_screen_size()
            density = self._connection.get_screen_density()
            self._display_info = DisplayInfo(
                width=width,
                height=height,
                density=density,
                status_bar_height=48,
                navigation_bar_height=0
            )
        return self._display_info


import re
```

- [ ] **Step 4: 创建 ADB screenshot.py**

```python
# backend/app/core/devices/adb/screenshot.py
"""Screenshot capture via ADB."""

import subprocess
from typing import Optional


def get_screenshot(device_id: Optional[str] = None, timeout: int = 10) -> bytes:
    """
    Capture screenshot from Android device via ADB.

    Returns:
        PNG image data as bytes.
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["exec-out", "screenshot"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        raise RuntimeError(f"Screenshot failed: returncode={result.returncode}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Screenshot timed out")
    except FileNotFoundError:
        raise RuntimeError("ADB not found")
```

- [ ] **Step 5: 创建 ADB input.py**

```python
# backend/app/core/devices/adb/input.py
"""Input operations via ADB."""

import subprocess
from typing import Optional


def tap(x: int, y: int, device_id: Optional[str] = None) -> None:
    """Tap at coordinates."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "tap", str(x), str(y)])
    subprocess.run(cmd, capture_output=True, timeout=10)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: Optional[int] = None,
    device_id: Optional[str] = None
) -> None:
    """Swipe from start to end."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "swipe",
                str(start_x), str(start_y), str(end_x), str(end_y)])
    if duration_ms:
        cmd.append(str(duration_ms))
    subprocess.run(cmd, capture_output=True, timeout=10)


def long_press(x: int, y: int, duration_ms: int = 1000,
               device_id: Optional[str] = None) -> None:
    """Long press at coordinates using swipe to same location."""
    swipe(x, y, x, y, duration_ms, device_id)


def type_text(text: str, device_id: Optional[str] = None) -> None:
    """Type text."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    escaped_text = text.replace(" ", "%s").replace("'", "\\'")
    cmd.extend(["shell", "input", "text", escaped_text])
    subprocess.run(cmd, capture_output=True, timeout=10)


def back(device_id: Optional[str] = None) -> None:
    """Press back button."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "keyevent", "KEYCODE_BACK"])
    subprocess.run(cmd, capture_output=True, timeout=10)


def home(device_id: Optional[str] = None) -> None:
    """Press home button."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "keyevent", "KEYCODE_HOME"])
    subprocess.run(cmd, capture_output=True, timeout=10)


def press_key(key: str, device_id: Optional[str] = None) -> None:
    """Press hardware key by name."""
    key_map = {
        "back": "KEYCODE_BACK",
        "home": "KEYCODE_HOME",
        "power": "KEYCODE_POWER",
        "volume_up": "KEYCODE_VOLUME_UP",
        "volume_down": "KEYCODE_VOLUME_DOWN",
        "menu": "KEYCODE_MENU",
        "search": "KEYCODE_SEARCH",
    }
    keycode = key_map.get(key.lower(), key.upper())
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "keyevent", keycode])
    subprocess.run(cmd, capture_output=True, timeout=10)
```

- [ ] **Step 6: 提交 ADB 迁移**

```bash
git add backend/app/core/devices/adb/
git commit -m "feat(core): migrate ADB device implementation from phone_agent"
```

---

#### Task 3: 迁移 HDC 设备实现

**Files:**
- Create: `backend/app/core/devices/hdc/__init__.py`
- Create: `backend/app/core/devices/hdc/connection.py`
- Create: `backend/app/core/devices/hdc/device.py`
- Create: `backend/app/core/devices/hdc/input.py`
- Create: `backend/app/core/devices/hdc/screenshot.py`

> HDC 实现与 ADB 结构类似，请参考 phone_agent/hdc/ 的实现进行迁移

- [ ] **Step 1: 创建 HDC 模块结构**

参考 ADB 实现创建 HDC 模块，主要差异：
- 使用 `hdc` 命令替代 `adb`
- HarmonyOS 特定的应用启动方式

```python
# backend/app/core/devices/hdc/__init__.py
"""HarmonyOS device implementation via HDC."""

from .device import HDCDevice
from .connection import HDCConnection

__all__ = ["HDCDevice", "HDCConnection"]
```

- [ ] **Step 2: 创建 HDC connection.py**

```python
# backend/app/core/devices/hdc/connection.py
"""HDC connection management for HarmonyOS."""

import subprocess
from typing import Optional


class HDCConnection:
    """Manages HDC connection to HarmonyOS devices."""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id

    def _build_command(self, *args) -> list[str]:
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    def execute(self, *args, timeout: int = 30) -> tuple[int, str, str]:
        cmd = self._build_command(*args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", "HDC not found"

    def is_connected(self) -> bool:
        _, stdout, _ = self.execute("list targets")
        return "device" in stdout.lower()

    # ... 其他方法参考 ADBConnection
```

- [ ] **Step 3: 创建 HDC device.py**

参考 ADBDevice 实现，注意 HarmonyOS 特有的 API

- [ ] **Step 4: 提交 HDC 迁移**

```bash
git add backend/app/core/devices/hdc/
git commit -m "feat(core): migrate HDC device implementation from phone_agent"
```

---

#### Task 4: 迁移 XCTest (iOS) 设备实现

**Files:**
- Create: `backend/app/core/devices/xctest/__init__.py`
- Create: `backend/app/core/devices/xctest/connection.py`
- Create: `backend/app/core/devices/xctest/device.py`
- Create: `backend/app/core/devices/xctest/input.py`
- Create: `backend/app/core/devices/xctest/screenshot.py`

> iOS 实现使用 WebDriverAgent (WDA)，需要通过 HTTP 请求与 WDA 交互

- [ ] **Step 1: 创建 XCTest 模块结构**

```python
# backend/app/core/devices/xctest/__init__.py
"""iOS device implementation via XCTest/WebDriverAgent."""

from .device import XCTestDevice
from .connection import XCTestConnection

__all__ = ["XCTestDevice", "XCTestConnection"]
```

- [ ] **Step 2: 创建 XCTest connection.py**

```python
# backend/app/core/devices/xctest/connection.py
"""XCTest connection via WebDriverAgent."""

import json
import requests
from typing import Optional, Any


class XCTestConnection:
    """Manages XCTest connection via WebDriverAgent."""

    def __init__(self, device_id: Optional[str] = None, wda_url: str = "http://localhost:8100"):
        self.device_id = device_id
        self.wda_url = wda_url.rstrip("/")
        self.session_id: Optional[str] = None

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to WDA."""
        url = f"{self.wda_url}{path}"
        try:
            response = requests.request(method, url, timeout=30, **kwargs)
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def create_session(self, capabilities: Optional[dict] = None) -> str:
        """Create WDA session."""
        data = capabilities or {"capabilities": {"alwaysMatch": {}, "firstMatch": [{}]}}
        result = self._request("POST", "/session", json=data)
        self.session_id = result.get("sessionId")
        return self.session_id or ""

    def delete_session(self) -> None:
        """Delete WDA session."""
        if self.session_id:
            self._request("DELETE", f"/session/{self.session_id}")
            self.session_id = None

    def screenshot(self) -> bytes:
        """Get screenshot."""
        if not self.session_id:
            self.create_session()
        result = self._request("GET", f"/session/{self.session_id}/screenshot")
        if "value" in result and "data" in result["value"]:
            import base64
            return base64.b64decode(result["value"]["data"])
        return b""

    def tap(self, x: float, y: float) -> bool:
        """Tap at coordinates."""
        if not self.session_id:
            return False
        result = self._request(
            "POST",
            f"/session/{self.session_id}/execute/script",
            json={"script": "mobile: tap", "args": [{"x": x, "y": y}]}
        )
        return "error" not in result

    # ... 其他方法
```

- [ ] **Step 3: 提交 iOS 迁移**

```bash
git add backend/app/core/devices/xctest/
git commit -m "feat(core): migrate XCTest device implementation from phone_agent"
```

---

### Phase 2: 核心层实现

#### Task 5: 创建 Action 处理引擎

**Files:**
- Create: `backend/app/core/actions/__init__.py`
- Create: `backend/app/core/actions/action_types.py`
- Create: `backend/app/core/actions/handler.py`
- Create: `backend/app/core/actions/action_result.py`

- [ ] **Step 1: 创建 action_types.py**

```python
# backend/app/core/actions/action_types.py
"""Action type definitions."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TapAction:
    """Tap action."""
    element: List[int]  # [x, y]


@dataclass
class SwipeAction:
    """Swipe action."""
    element: List[int]  # [x1, y1, x2, y2]
    duration: Optional[int] = None


@dataclass
class LongPressAction:
    """Long press action."""
    element: List[int]  # [x, y]
    duration: int = 1000


@dataclass
class TypeAction:
    """Type text action."""
    text: str


@dataclass
class LaunchAction:
    """Launch app action."""
    app_name: str


@dataclass
class BackAction:
    """Back button action."""
    pass


@dataclass
class HomeAction:
    """Home button action."""
    pass


@dataclass
class WaitAction:
    """Wait action."""
    duration: int = 1000


@dataclass
class FinishAction:
    """Finish task action."""
    message: Optional[str] = None


ActionType = TapAction | SwipeAction | LongPressAction | TypeAction | LaunchAction | BackAction | HomeAction | WaitAction | FinishAction
```

- [ ] **Step 2: 创建 handler.py**

```python
# backend/app/core/actions/handler.py
"""Action handler for executing parsed actions."""

import ast
import json
import re
from typing import Any, Callable, Optional

from .action_types import (
    ActionType, TapAction, SwipeAction, LongPressAction,
    TypeAction, LaunchAction, BackAction, HomeAction,
    WaitAction, FinishAction
)
from .action_result import ActionResult


class ActionHandler:
    """Handles execution of actions from AI model output."""

    def __init__(
        self,
        device,
        confirmation_callback: Optional[Callable[[str], bool]] = None,
    ):
        self.device = device
        self.confirmation_callback = confirmation_callback or self._default_confirmation

    def _default_confirmation(self, action: str) -> bool:
        return True

    def execute(self, action: ActionType, screen_width: int = 1080, screen_height: int = 1920) -> ActionResult:
        """Execute an action and return result."""
        try:
            if isinstance(action, TapAction):
                x, y = action.element
                self._convert_and_tap(x, y, screen_width, screen_height)
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, SwipeAction):
                x1, y1, x2, y2 = action.element
                self._convert_and_swipe(x1, y1, x2, y2, action.duration, screen_width, screen_height)
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, LongPressAction):
                x, y = action.element
                self._convert_and_long_press(x, y, action.duration, screen_width, screen_height)
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, TypeAction):
                self.device.type_text(action.text)
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, LaunchAction):
                self.device.launch_app(action.app_name)
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, BackAction):
                self.device.back()
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, HomeAction):
                self.device.home()
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, WaitAction):
                import time
                time.sleep(action.duration / 1000)
                return ActionResult(success=True, should_finish=False)

            elif isinstance(action, FinishAction):
                return ActionResult(
                    success=True,
                    should_finish=True,
                    message=action.message
                )

            return ActionResult(success=False, should_finish=True, message=f"Unknown action type: {type(action)}")

        except Exception as e:
            return ActionResult(success=False, should_finish=True, message=str(e))

    def _convert_and_tap(self, rel_x: float, rel_y: float, screen_width: int, screen_height: int) -> None:
        """Convert relative coordinates to absolute and tap."""
        x = int(rel_x / 999 * screen_width)
        y = int(rel_y / 999 * screen_height)
        self.device.tap(x, y)

    def _convert_and_swipe(self, rel_x1: float, rel_y1: float, rel_x2: float, rel_y2: float,
                          duration: Optional[int], screen_width: int, screen_height: int) -> None:
        """Convert relative coordinates to absolute and swipe."""
        x1 = int(rel_x1 / 999 * screen_width)
        y1 = int(rel_y1 / 999 * screen_height)
        x2 = int(rel_x2 / 999 * screen_width)
        y2 = int(rel_y2 / 999 * screen_height)
        self.device.swipe(x1, y1, x2, y2, duration)

    def _convert_and_long_press(self, rel_x: float, rel_y: float, duration: int,
                                screen_width: int, screen_height: int) -> None:
        """Convert relative coordinates to absolute and long press."""
        x = int(rel_x / 999 * screen_width)
        y = int(rel_y / 999 * screen_height)
        self.device.long_press(x, y, duration)


def parse_action(action_str: str) -> ActionType:
    """Parse action string into ActionType object."""
    action_str = action_str.strip()

    # JSON format: {"action": "Tap", "element": [x, y]}
    if action_str.startswith("{"):
        try:
            data = json.loads(action_str)
            action_name = data.get("action", "").lower()
            element = data.get("element", [])

            if action_name == "tap":
                return TapAction(element=element)
            elif action_name == "swipe":
                return SwipeAction(element=element, duration=data.get("duration"))
            elif action_name == "long_press":
                return LongPressAction(element=element, duration=data.get("duration", 1000))
            elif action_name in ("type", "type_text"):
                return TypeAction(text=data.get("text", ""))
            elif action_name == "launch":
                return LaunchAction(app_name=data.get("app_name", ""))
            elif action_name == "back":
                return BackAction()
            elif action_name == "home":
                return HomeAction()
            elif action_name == "wait":
                return WaitAction(duration=data.get("duration", 1000))
            elif action_name == "finish":
                return FinishAction(message=data.get("message"))
        except json.JSONDecodeError:
            pass

    # Pseudo-code format: do(action="Tap", element=[x, y])
    if action_str.startswith("do(") or action_str.startswith("finish("):
        try:
            if action_str.startswith("finish("):
                match = re.search(r'message\s*=\s*"([^"]*)"', action_str)
                return FinishAction(message=match.group(1) if match else None)

            action_match = re.search(r'action\s*=\s*"(\w+)"', action_str)
            element_match = re.search(r'element\s*=\s*\[([^\]]+)\]', action_str)

            if action_match:
                action_name = action_match.group(1).lower()
                element = []
                if element_match:
                    element = [int(x.strip()) for x in element_match.group(1).split(",")]

                if action_name == "tap":
                    return TapAction(element=element)
                elif action_name == "swipe":
                    return SwipeAction(element=element)
                elif action_name == "long_press":
                    return LongPressAction(element=element)
                elif action_name in ("type", "type_name"):
                    text_match = re.search(r'text\s*=\s*"([^"]*)"', action_str)
                    return TypeAction(text=text_match.group(1) if text_match else "")
                elif action_name == "launch":
                    app_match = re.search(r'app_name\s*=\s*"([^"]*)"', action_str)
                    return LaunchAction(app_name=app_match.group(1) if app_match else "")
                elif action_name == "back":
                    return BackAction()
                elif action_name == "home":
                    return HomeAction()
                elif action_name == "wait":
                    return WaitAction()
        except Exception:
            pass

    raise ValueError(f"Cannot parse action: {action_str}")
```

- [ ] **Step 3: 创建 action_result.py**

```python
# backend/app/core/actions/action_result.py
"""Action result definition."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    should_finish: bool
    message: Optional[str] = None
    requires_confirmation: bool = False
```

- [ ] **Step 4: 提交 Action 引擎**

```bash
git add backend/app/core/actions/
git commit -m "feat(core): implement action handling engine"
```

---

#### Task 6: 创建 Model 客户端

**Files:**
- Create: `backend/app/core/model/__init__.py`
- Create: `backend/app/core/model/client.py`
- Create: `backend/app/core/model/config.py`

- [ ] **Step 1: 创建 model/config.py**

```python
# backend/app/core/model/config.py
"""Model configuration."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelConfig:
    """Configuration for AI model."""
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "AutoPhone-phone-9b"
    provider: str = "openai"  # 'openai' or 'anthropic'
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    extra_body: dict[str, Any] = field(default_factory=dict)
    lang: str = "cn"
```

- [ ] **Step 2: 创建 model/client.py**

```python
# backend/app/core/model/client.py
"""AI model client for vision-language model inference."""

import json
import re
import time
from dataclasses import dataclass

import openai
import anthropic

from .config import ModelConfig


JSON_ANSWER_OPEN = "<json_answer>"
JSON_ANSWER_CLOSE = "</json_answer>"
JSON_THINK_OPEN = "<json_think>"
JSON_THINK_CLOSE = "</json_think>"


@dataclass
class ModelResponse:
    """Response from AI model."""
    thinking: str
    action: str
    raw_content: str
    time_to_first_token: float | None = None
    time_to_thinking_end: float | None = None
    total_time: float | None = None


class ModelClient:
    """Client for interacting with vision-language models."""

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        if self.config.provider == "anthropic":
            self.client = anthropic.Anthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url if self.config.base_url else None
            )
        else:
            self.client = openai.OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key
            )

    def request(self, messages: list[dict]) -> ModelResponse:
        """Send request to model and get response."""
        start_time = time.time()

        try:
            if self.config.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.config.model_name,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=messages
                )
                content = response.content[0].text
                first_token_time = None
            else:
                stream = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    frequency_penalty=self.config.frequency_penalty,
                    stream=True,
                    **self.config.extra_body
                )

                content_parts = []
                thinking_parts = []
                in_thinking = False
                first_token_time = None

                for chunk in stream:
                    if first_token_time is None:
                        first_token_time = time.time() - start_time

                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        # Check for thinking tags
                        if JSON_THINK_OPEN in delta:
                            in_thinking = True
                            delta = delta.replace(JSON_THINK_OPEN, "")
                        if JSON_THINK_CLOSE in delta:
                            in_thinking = False
                            delta = delta.replace(JSON_THINK_CLOSE, "")

                        if in_thinking:
                            thinking_parts.append(delta)
                        else:
                            content_parts.append(delta)

                content = "".join(content_parts)
                thinking = "".join(thinking_parts)

        except Exception as e:
            raise RuntimeError(f"Model request failed: {e}")

        total_time = time.time() - start_time
        thinking_end = first_token_time  # Approximation

        return ModelResponse(
            thinking=thinking,
            action=content,
            raw_content=content,
            time_to_first_token=first_token_time,
            time_to_thinking_end=thinking_end,
            total_time=total_time
        )
```

- [ ] **Step 3: 提交 Model 客户端**

```bash
git add backend/app/core/model/
git commit -m "feat(core): implement AI model client"
```

---

#### Task 7: 创建 Agent 核心循环

**Files:**
- Create: `backend/app/core/agent/__init__.py`
- Create: `backend/app/core/agent/base_agent.py`
- Create: `backend/app/core/agent/android_agent.py`
- Create: `backend/app/core/agent/task_manager.py`

- [ ] **Step 1: 创建 base_agent.py**

```python
# backend/app/core/agent/base_agent.py
"""Base Agent class for task execution."""

import asyncio
import base64
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..devices import DeviceFactory, Platform
from ..model import ModelClient, ModelConfig
from ..actions import ActionHandler, parse_action


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TaskStep:
    """Single step in task execution."""
    step_number: int
    screenshot: str  # base64
    thinking: str
    action: str
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentTask:
    """Agent task definition."""
    id: str
    description: str
    device_id: str
    platform: str
    status: TaskStatus = TaskStatus.PENDING
    max_steps: int = 100
    model_config: Optional[ModelConfig] = None
    steps: list[TaskStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_message: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for Agent implementations."""

    def __init__(
        self,
        device_id: str,
        platform: str,
        model_config: Optional[ModelConfig] = None,
        max_steps: int = 100,
        status_callback: Optional[Callable[[TaskStatus, TaskStep | None], None]] = None,
    ):
        self.device_id = device_id
        self.platform = platform
        self.max_steps = max_steps
        self.status_callback = status_callback

        # Initialize device
        self.device = DeviceFactory.create_by_name(platform, device_id)

        # Initialize model client
        self.model_client = ModelClient(model_config)

        # Initialize action handler
        self.action_handler = ActionHandler(self.device)

        # Task state
        self.current_task: Optional[AgentTask] = None
        self._stop_requested = False

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for the agent."""
        pass

    async def execute_task(self, task: AgentTask) -> AgentTask:
        """Execute a task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.current_task = task
        self._stop_requested = False

        try:
            display_info = self.device.get_display_info()
            screen_width = display_info.width
            screen_height = display_info.height

            for step_num in range(1, self.max_steps + 1):
                if self._stop_requested:
                    task.status = TaskStatus.STOPPED
                    task.result_message = "Task stopped by user"
                    break

                # Capture screenshot
                screenshot_bytes = self.device.get_screenshot()
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

                # Build messages
                messages = self._build_messages(task.description, screenshot_bytes, task.steps)

                # Call model
                response = self.model_client.request(messages)

                # Parse action
                try:
                    action = parse_action(response.action)
                except ValueError as e:
                    task.steps.append(TaskStep(
                        step_number=step_num,
                        screenshot=screenshot_b64,
                        thinking=response.thinking,
                        action=response.action,
                        success=False
                    ))
                    continue

                # Execute action
                result = self.action_handler.execute(action, screen_width, screen_height)

                task.steps.append(TaskStep(
                    step_number=step_num,
                    screenshot=screenshot_b64,
                    thinking=response.thinking,
                    action=str(action),
                    success=result.success
                ))

                # Notify status
                if self.status_callback:
                    self.status_callback(task.status, task.steps[-1])

                if result.should_finish:
                    task.status = TaskStatus.FINISHED
                    task.result_message = result.message
                    break

                # Small delay between steps
                await asyncio.sleep(0.5)

            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FINISHED
                task.result_message = "Max steps reached"

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result_message = str(e)

        finally:
            task.finished_at = datetime.now()
            self.current_task = None

        return task

    def stop(self) -> None:
        """Request stop of current task."""
        self._stop_requested = True

    @abstractmethod
    def _build_messages(self, description: str, screenshot: bytes, history: list[TaskStep]) -> list[dict]:
        """Build messages for model request."""
        pass
```

- [ ] **Step 2: 创建 android_agent.py**

```python
# backend/app/core/agent/android_agent.py
"""Android-specific Agent implementation."""

from typing import Any

from .base_agent import BaseAgent


SYSTEM_PROMPT_ANDROID = """You are an AI assistant that controls Android devices.
Given a screenshot and a task description, decide what action to take.

Actions:
- Tap: do(action="Tap", element=[x, y])
- Swipe: do(action="Swipe", element=[x1, y1, x2, y2])
- LongPress: do(action="LongPress", element=[x, y])
- Type: do(action="Type", text="content")
- Launch: do(action="Launch", app_name="package.name")
- Back: do(action="Back")
- Home: do(action="Home")
- Wait: do(action="Wait")
- Finish: finish(message="result")

Use coordinates 0-999 (relative to screen size).
"""


class AndroidAgent(BaseAgent):
    """Agent for Android devices."""

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT_ANDROID

    def _build_messages(self, description: str, screenshot: bytes, history: list) -> list[dict]:
        """Build messages for Android agent."""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": [
                {"type": "text", "text": f"Task: {description}"},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{self._bytes_to_base64(screenshot)}"
                }}
            ]}
        ]

        # Add history
        for step in history[-5:]:
            messages.append({
                "role": "assistant",
                "content": f"Thought: {step.thinking}\nAction: {step.action}"
            })

        return messages

    def _bytes_to_base64(self, data: bytes) -> str:
        import base64
        return base64.b64encode(data).decode()
```

- [ ] **Step 3: 提交 Agent 核心**

```bash
git add backend/app/core/agent/
git commit -m "feat(core): implement Agent core loop"
```

---

### Phase 3: API 层实现

#### Task 8: 创建 Agent 数据模型

**Files:**
- Create: `backend/app/schemas/agent.py`

- [ ] **Step 1: 创建 schemas/agent.py**

```python
# backend/app/schemas/agent.py
"""Agent-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class PlatformType(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    HARMONYOS = "harmonyos"


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    STOPPED = "stopped"


class TaskStepSchema(BaseModel):
    """Single step in task execution."""
    step_number: int
    screenshot: str
    thinking: str
    action: str
    success: bool
    timestamp: datetime


class AgentTaskCreate(BaseModel):
    """Request to create an agent task."""
    description: str
    device_id: str
    platform: PlatformType
    max_steps: Optional[int] = 100
    model_config_id: Optional[str] = None


class AgentTaskResponse(BaseModel):
    """Agent task response."""
    id: str
    description: str
    device_id: str
    platform: PlatformType
    status: TaskStatusEnum
    max_steps: int
    steps: list[TaskStepSchema] = []
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_message: Optional[str] = None


class AgentTaskListResponse(BaseModel):
    """List of agent tasks."""
    tasks: list[AgentTaskResponse]
    total: int
```

---

#### Task 9: 创建 Agent API 端点

**Files:**
- Create: `backend/app/api/v1/agent/__init__.py`
- Create: `backend/app/api/v1/agent/tasks.py`
- Create: `backend/app/api/v1/agent/execution.py`
- Create: `backend/app/services/agent_service.py`

- [ ] **Step 1: 创建 agent_service.py**

```python
# backend/app/services/agent_service.py
"""Agent service for task management."""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from app.core.agent import AndroidAgent, AgentTask, TaskStatus
from app.core.agent.android_agent import AndroidAgent
from app.core.devices import DeviceFactory, Platform
from app.core.model import ModelConfig


class AgentService:
    """Service for managing agent tasks."""

    def __init__(self):
        self._running_agents: dict[str, AndroidAgent] = {}
        self._tasks: dict[str, AgentTask] = {}

    def create_task(
        self,
        description: str,
        device_id: str,
        platform: str,
        max_steps: int = 100,
        model_config: Optional[ModelConfig] = None
    ) -> AgentTask:
        """Create a new agent task."""
        task = AgentTask(
            id=str(uuid.uuid4()),
            description=description,
            device_id=device_id,
            platform=platform,
            max_steps=max_steps,
            model_config=model_config,
        )
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[AgentTask]:
        """List all tasks."""
        return list(self._tasks.values())

    async def execute_task(self, task_id: str) -> AgentTask:
        """Execute a task."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Create agent based on platform
        if task.platform.lower() in ("android", "adb"):
            agent = AndroidAgent(
                device_id=task.device_id,
                platform="android",
                model_config=task.model_config,
                max_steps=task.max_steps,
            )
        else:
            raise ValueError(f"Unsupported platform: {task.platform}")

        self._running_agents[task_id] = agent

        try:
            result = await agent.execute_task(task)
            self._tasks[task_id] = result
            return result
        finally:
            self._running_agents.pop(task_id, None)

    def stop_task(self, task_id: str) -> bool:
        """Stop a running task."""
        agent = self._running_agents.get(task_id)
        if agent:
            agent.stop()
            return True
        return False
```

- [ ] **Step 2: 创建 tasks.py**

```python
# backend/app/api/v1/agent/tasks.py
"""Agent task management API."""

from fastapi import APIRouter, HTTPException

from app.schemas.agent import (
    AgentTaskCreate,
    AgentTaskResponse,
    AgentTaskListResponse,
    TaskStepSchema,
    PlatformType,
    TaskStatusEnum,
)
from app.services.agent_service import AgentService

router = APIRouter()
agent_service = AgentService()


def _task_to_response(task) -> AgentTaskResponse:
    """Convert AgentTask to response model."""
    return AgentTaskResponse(
        id=task.id,
        description=task.description,
        device_id=task.device_id,
        platform=task.platform,
        status=task.status.value,
        max_steps=task.max_steps,
        steps=[
            TaskStepSchema(
                step_number=s.step_number,
                screenshot=s.screenshot,
                thinking=s.thinking,
                action=s.action,
                success=s.success,
                timestamp=s.timestamp,
            )
            for s in task.steps
        ],
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
        result_message=task.result_message,
    )


@router.post("/", response_model=AgentTaskResponse)
async def create_task(request: AgentTaskCreate):
    """Create a new agent task."""
    task = agent_service.create_task(
        description=request.description,
        device_id=request.device_id,
        platform=request.platform,
        max_steps=request.max_steps or 100,
    )
    return _task_to_response(task)


@router.get("/", response_model=AgentTaskListResponse)
async def list_tasks():
    """List all tasks."""
    tasks = agent_service.list_tasks()
    return AgentTaskListResponse(
        tasks=[_task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/{task_id}", response_model=AgentTaskResponse)
async def get_task(task_id: str):
    """Get task by ID."""
    task = agent_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.post("/{task_id}/execute")
async def execute_task(task_id: str):
    """Execute a task."""
    import asyncio
    task = agent_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    asyncio.create_task(agent_service.execute_task(task_id))
    return {"task_id": task_id, "status": "executing"}


@router.post("/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a running task."""
    if not agent_service.stop_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found or not running")
    return {"task_id": task_id, "status": "stopped"}
```

- [ ] **Step 3: 创建 execution.py**

```python
# backend/app/api/v1/agent/execution.py
"""Agent execution WebSocket handling."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for agent execution."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)

    async def send_update(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(data)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(task_id: str, websocket: WebSocket):
    """WebSocket endpoint for agent execution updates."""
    await manager.connect(task_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (e.g., stop command)
            if data == "stop":
                # Send stop signal
                await manager.send_update(task_id, {"type": "stop"})
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
```

- [ ] **Step 4: 提交 API 层**

```bash
git add backend/app/api/v1/agent/ backend/app/schemas/agent.py backend/app/services/agent_service.py
git commit -m "feat(api): implement Agent API endpoints"
```

---

### Phase 4: 集成与验证

#### Task 10: 更新 backend 主路由

**Files:**
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 更新 API v1 路由**

```python
# backend/app/api/v1/__init__.py
"""API v1 router configuration."""

from fastapi import APIRouter

from . import agent, control, devices, tasks

router = APIRouter()

router.include_router(agent.tasks.router, prefix="/agent/tasks", tags=["agent"])
router.include_router(agent.execution.router, prefix="/agent/ws", tags=["agent"])
router.include_router(control.router, prefix="/control", tags=["control"])
router.include_router(devices.router, prefix="/devices", tags=["devices"])
```

- [ ] **Step 2: 提交路由更新**

```bash
git add backend/app/api/v1/__init__.py
git commit -m "feat(api): integrate Agent routes into API v1"
```

---

#### Task 11: 删除 phone_agent 目录（最终验证）

- [ ] **Step 1: 确认所有 phone_agent 引用已迁移**

检查以下文件确保无 phone_agent 引用：
- `backend/app/core/adapters/phone_agent_adapter.py` - 确认已被新实现替代
- `backend/app/core/devices/` - 确认新实现完整

- [ ] **Step 2: 删除 phone_agent 目录**

```bash
# 确认没有其他文件引用 phone_agent
grep -r "from phone_agent" backend/
grep -r "import phone_agent" backend/

# 删除 phone_agent 目录
rm -rf phone_agent/

# 提交删除
git add -A
git commit -m "chore: remove phone_agent directory after full migration"
```

---

## 实施检查清单

### Phase 1 设备层
- [ ] Task 1: 设备抽象层基础结构
- [ ] Task 2: ADB 设备实现
- [ ] Task 3: HDC 设备实现
- [ ] Task 4: XCTest 设备实现

### Phase 2 核心层
- [ ] Task 5: Action 处理引擎
- [ ] Task 6: Model 客户端
- [ ] Task 7: Agent 核心循环

### Phase 3 API 层
- [ ] Task 8: Agent 数据模型
- [ ] Task 9: Agent API 端点

### Phase 4 集成验证
- [ ] Task 10: 更新 backend 主路由
- [ ] Task 11: 删除 phone_agent 目录

---

## 技术验证

### 测试验证点

| 验证项 | 测试方法 |
|--------|----------|
| ADB 设备连接 | `adb devices` 确认设备在线 |
| 截图获取 | 调用 `/api/v1/devices/{id}/screenshot` |
| 点击操作 | 调用 `/api/v1/agent/devices/{id}/tap` |
| Agent 任务创建 | POST `/api/v1/agent/tasks` |
| Agent 任务执行 | POST `/api/v1/agent/tasks/{id}/execute` |
| WebSocket 推送 | 连接 `/api/v1/agent/ws/{task_id}` 验证消息推送 |

---

**Plan complete.**