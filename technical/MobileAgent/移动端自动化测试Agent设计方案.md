# 移动端自动化测试 Agent 完整设计方案

> 基于 Mobile-Agent 项目技术架构，设计一个跨平台、多设备隔离、元素定位驱动的自动化测试 Agent。

---

## 目录

1. [项目背景与现状分析](#1-项目背景与现状分析)
2. [核心问题与解决思路](#2-核心问题与解决思路)
3. [整体架构设计](#3-整体架构设计)
4. [平台适配层（设备控制层）设计](#4-平台适配层设备控制层设计)
5. [Agent 核心引擎设计](#5-agent-核心引擎设计)
6. [元素定位器设计（解决跨设备脚本失效）](#6-元素定位器设计解决跨设备脚本失效)
7. [多设备隔离执行设计](#7-多设备隔离执行设计)
8. [自然语言用例生成器](#8-自然语言用例生成器)
9. [脚本转换器（测试步骤 → 框架脚本）](#9-脚本转换器测试步骤--框架脚本)
10. [所有 Prompt 模板汇总](#10-所有-prompt-模板汇总)
11. [完整目录结构](#11-完整目录结构)
12. [快速开始示例](#12-快速开始示例)
13. [与 Mobile-Agent 项目的集成关系](#13-与-mobile-agent-项目的集成关系)

---

## 1. 项目背景与现状分析

### 1.1 Mobile-Agent 项目概述

原项目 `Mobile-Agent` 是阿里通义实验室开发的 GUI 自动化 Agent 系列，核心能力：

| 版本 | 特点 | Agent 架构 |
|------|------|-----------|
| Mobile-Agent-v3.5 | 最新版，多平台基础 GUI Agent | 单 Agent ReAct 模式 |
| Mobile-Agent-v3 | 多平台多 Agent 框架 | 多 Agent 协作（Manager/Executor/Reflector/Grounding） |

### 1.2 现有项目的可复用组件

| 组件 | 文件位置 | 参考价值 |
|------|---------|---------|
| ADB 控制 | `mobile_use/utils.py` → `AdbTools` | Android 设备控制的直接复用 |
| Agent 主循环 | `mobile_use/run_gui_owl_1_5_for_mobile.py` | 执行器循环的参考模板 |
| SoM 标注 | `browser_use/browser/playwright/som.py` | 元素标注与 UI 理解 |
| 消息构建 | `mobile_use/utils.py` → `build_messages` | 多轮对话历史管理 |
| Prompt 设计模式 | `mobile_use/utils.py` / `browser_use/prompts.py` | Tool Call 格式定义 |

### 1.3 现有方案核心缺陷

| 缺陷 | 表现 | 根因 |
|------|------|------|
| **坐标依赖** | 脚本绑定特定分辨率，换设备失效 | 使用绝对坐标 (x,y) 而非元素属性定位 |
| **无设备隔离** | 多设备执行共享状态 | 缺少设备上下文抽象 |
| **无脚本导出** | 仅运行时执行，无法生成可复用脚本 | 缺少测试步骤 → 框架脚本的转换层 |
| **仅 Android** | 不支持 iOS/鸿蒙 | 缺少平台抽象层 |

---

## 2. 核心问题与解决思路

### 2.1 问题一：跨设备脚本失效

**现象**：在 A 手机上用坐标定位生成的脚本，B 手机分辨率不同导致坐标偏移。

**解决**：使用**元素属性定位**替代绝对坐标。

```
【不推荐】
{"action": "click", "coordinate": [500, 300]}

【推荐】
{"action": "click", "locator": {"resource_id": "com.taobao:id/btn_login"}}
{"action": "click", "locator": {"text": "登录"}}
{"action": "click", "locator": {"semantic": "页面底部的红色确认按钮"}}
```

### 2.2 问题二：多设备并行冲突

**现象**：DeviceA 和 DeviceB 并行执行脚本，共享状态导致相互干扰。

**解决**：使用 `DeviceContext` 进行设备隔离，每个设备拥有独立上下文。

### 2.3 问题三：不支持 iOS/鸿蒙

**解决**：设计 `BaseDeviceAdapter` 抽象基类，各平台各自实现。

### 2.4 问题四：无脚本导出能力

**解决**：设计 `ScriptConverter` 将测试步骤转换为各框架代码。

---

## 3. 整体架构设计

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  用户交互层                                           │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────────┐              │
│  │ 自然语言测试需求   │  │ 结构化测试步骤     │  │ 自动化测试脚本       │              │
│  │ "测试淘宝登录功能" │→│ [Step1, Step2...] │→│ test_login.py       │              │
│  └───────────────────┘  └───────────────────┘  └──────────────────────┘              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                   核心引擎层                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Multi-Agent 协作                                      │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐  │ │
│  │  │ 用例生成器  │ │ 测试执行器  │ │ 断言验证器  │ │ 元素定位器  │ │ 脚本转换器   │  │ │
│  │  │ Generator  │ │  Executor  │ │  Verifier  │ │  Finder   │ │  Converter   │  │ │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └──────┬───────┘  │ │
│  │        │               │              │              │               │          │ │
│  │  LLM (GUI-Owl / Qwen-VL + 专用小型模型)                                    │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                               平台适配层                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                       BaseDeviceAdapter (抽象基类)                              │ │
│  │  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐           │ │
│  │  │  AndroidAdapter    │ │     iOSAdapter     │ │ HarmonyOSAdapter  │           │ │
│  │  │  (ADB + UIAutomator)│ │  (WDA + XCUITest) │ │  (hdc + hiinspect) │           │ │
│  │  └────────────────────┘ └────────────────────┘ └────────────────────┘           │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                设备管理&隔离层                                        │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  DeviceContext[device_001]              DeviceContext[device_002]              │ │
│  │  ├─ adapter: AndroidAdapter             ├─ adapter: iOSAdapter                 │ │
│  │  ├─ message_history: []                 ├─ message_history: []                 │ │
│  │  ├─ screenshot_dir: ./screenshots/01/   ├─ screenshot_dir: ./screenshots/02/   │ │
│  │  ├─ lock: asyncio.Lock()               ├─ lock: asyncio.Lock()                 │ │
│  │  └─ current_app: ""                    └─ current_app: ""                      │ │
│  │                                                                                 │ │
│  │  DevicePool - 管理设备注册/获取/释放，保证串行执行                              │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 数据流（从自然语言到测试报告）

```
自然语言需求
    │
    ▼
┌──────────────┐   LLM 解析
│ 用例生成器    │───────────────▶ 结构化测试步骤 [Step1, Step2, ...]
└──────────────┘
    │                                 │                        │
    │                                 ▼                        ▼
    │                          ┌──────────────┐       ┌──────────────┐
    │                          │  脚本转换器   │       │  DevicePool  │
    │                          │  选择平台框架  │       │  选择目标设备  │
    │                          │  → .py / .swift  │       │  获取隔离上下文 │
    │                          └──────────────┘       └──────┬───────┘
    │                                                        │
    │                                                        ▼
    │                                                 ┌──────────────┐
    │                                                 │  测试执行器   │
    │                                                 │  ReAct 循环   │
    │                                                 │  (截图→推理→   │
    │                                                 │  元素定位→    │
    │                                                 │  执行→验证)   │
    │                                                 └──────┬───────┘
    │                                                        │
    ▼                                                        ▼
┌──────────────┐                                       ┌──────────────┐
│ 保存脚本文件  │                                       │ 生成测试报告   │
│ test_login.py│                                       │ passed: 5/6  │
└──────────────┘                                       └──────────────┘
```

---

## 4. 平台适配层（设备控制层）设计

### 4.1 抽象基类（所有平台的统一接口）

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Platform(Enum):
    ANDROID = "android"
    IOS = "ios"
    HARMONYOS = "harmonyos"


@dataclass
class DisplayInfo:
    """设备屏幕信息"""
    width: int
    height: int
    density: float
    status_bar_height: int
    navigation_bar_height: int
    
    def normalize_coord(self, x: int, y: int) -> Tuple[float, float]:
        """将绝对坐标归一化到 0-1000"""
        return (x / self.width * 1000, y / self.height * 1000)
    
    def denormalize_coord(self, nx: float, ny: float) -> Tuple[int, int]:
        """将归一化坐标还原为绝对坐标"""
        return (int(nx / 1000 * self.width), int(ny / 1000 * self.height))


@dataclass
class UIElement:
    """UI 元素 - 基于属性定位的核心数据结构"""
    # 元素标识
    index: int                            # 在当前屏幕元素列表中的序号
    
    # 边界框 (归一化 0-1000)
    bbox_normalized: Dict[str, float]     # {"x": nx, "y": ny, "w": nw, "h": nh}
    
    # 边界框 (绝对像素)
    bbox_pixel: Optional[Dict[str, int]]  # {"x": px, "y": py, "w": pw, "h": ph}
    
    # 元素属性（用于定位的关键字段）
    resource_id: Optional[str] = None     # Android: resource-id / iOS: accessibilityIdentifier
    text: Optional[str] = None            # 元素文本
    content_desc: Optional[str] = None    # content-description / accessibilityLabel
    class_name: Optional[str] = None      # android.widget.Button / XCUIElementTypeButton
    package_name: Optional[str] = None    # com.taobao.taobao
    
    # 额外属性
    clickable: bool = False
    enabled: bool = True
    focused: bool = False
    bounds: Optional[str] = None          # 原始 bounds 字符串
    
    # 子元素列表
    children: List['UIElement'] = field(default_factory=list)
    parent: Optional['UIElement'] = None
    
    def center(self) -> Tuple[float, float]:
        """获取元素中心点（归一化坐标）"""
        return (
            self.bbox_normalized["x"] + self.bbox_normalized["w"] / 2,
            self.bbox_normalized["y"] + self.bbox_normalized["h"] / 2,
        )


class BaseDeviceAdapter(ABC):
    """设备适配器抽象基类 - 定义所有平台必须实现的操作"""
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        """返回平台类型"""
        pass
    
    @property
    @abstractmethod
    def device_id(self) -> str:
        """返回设备唯一标识"""
        pass
    
    @property
    @abstractmethod
    def display_info(self) -> DisplayInfo:
        """返回屏幕信息"""
        pass
    
    # ========== 截图 ==========
    
    @abstractmethod
    def get_screenshot(self, save_path: str) -> bool:
        """获取截图并保存到指定路径"""
        pass
    
    @abstractmethod
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        """获取当前界面的 UI 元素树（用于 SoM 标注和元素定位）

        必须返回带 bbox_normalized 的元素列表。
        Android: 解析 uiautomator dump XML
        iOS: 解析 WDA page source XML
        鸿蒙: 解析 hiinspect JSON
        """
        pass
    
    # ========== 用户操作 ==========
    
    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        """在坐标 (x, y) 处点击"""
        pass
    
    @abstractmethod
    def click_element(self, element: UIElement) -> bool:
        """点击指定元素（按中心点）"""
        cx, cy = element.center()
        px, py = self.display_info.denormalize_coord(cx, cy)
        return self.click(px, py)
    
    @abstractmethod
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        """长按"""
        pass
    
    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """滑动"""
        pass
    
    @abstractmethod
    def type_text(self, text: str) -> bool:
        """输入文本"""
        pass
    
    @abstractmethod
    def press_key(self, key: str) -> bool:
        """按键 (BACK, HOME, MENU, POWER, VOLUME_UP, VOLUME_DOWN)"""
        pass
    
    # ========== 应用管理 ==========
    
    @abstractmethod
    def get_installed_packages(self) -> List[str]:
        """获取已安装应用包名列表"""
        pass
    
    @abstractmethod
    def launch_app(self, package_name: str) -> bool:
        """启动应用"""
        pass
    
    @abstractmethod
    def close_app(self, package_name: str) -> bool:
        """关闭应用"""
        pass
    
    @abstractmethod
    def get_current_app(self) -> str:
        """获取当前前台应用包名"""
        pass
    
    # ========== 连接管理 ==========
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查设备是否在线"""
        pass
    
    @abstractmethod
    def reconnect(self) -> bool:
        """重连设备"""
        pass
    
    @abstractmethod
    def release(self):
        """释放设备资源"""
        pass
```

### 4.2 Android 适配器实现

```python
import subprocess
import os
import time
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Tuple
from PIL import Image


class AndroidAdapter(BaseDeviceAdapter):
    """Android 设备适配器 - 使用 ADB + UIAutomator"""
    
    def __init__(self, adb_path: str, device_serial: Optional[str] = None):
        self._adb_path = adb_path
        self._device_serial = device_serial
        self._device_flag = f" -s {device_serial} " if device_serial else " "
        self._display_info = None
        self._load_display_info()
    
    @property
    def platform(self) -> Platform:
        return Platform.ANDROID
    
    @property
    def device_id(self) -> str:
        if self._device_serial:
            return self._device_serial
        result = self._run("devices")
        for line in result.stdout.splitlines():
            if "\tdevice" in line:
                return line.split("\t")[0]
        return "unknown"
    
    @property
    def display_info(self) -> DisplayInfo:
        if self._display_info is None:
            self._load_display_info()
        return self._display_info
    
    def _load_display_info(self):
        """加载屏幕信息"""
        # 获取屏幕尺寸
        result = self._run("shell wm size")
        match = re.search(r"(\d+)x(\d+)", result.stdout)
        if match:
            width, height = int(match.group(1)), int(match.group(2))
        else:
            width, height = 1080, 1920
        
        # 获取密度
        result = self._run("shell wm density")
        density_match = re.search(r"(\d+)", result.stdout)
        density = int(density_match.group(1)) if density_match else 320
        
        # 获取状态栏高度
        result = self._run("shell dumpsys window displays")
        status_bar_match = re.search(r"status=(\d+)", result.stdout)
        status_bar_height = int(status_bar_match.group(1)) if status_bar_match else 0
        
        self._display_info = DisplayInfo(
            width=width,
            height=height,
            density=density,
            status_bar_height=status_bar_height,
            navigation_bar_height=0
        )
    
    def _run(self, args: str) -> subprocess.CompletedProcess:
        """执行 ADB 命令"""
        cmd = f"{self._adb_path}{self._device_flag}{args}"
        return subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    # ========== 截图 ==========
    
    def get_screenshot(self, save_path: str) -> bool:
        cmd = f"{self._adb_path}"
        if self._device_serial:
            cmd += f" -s {self._device_serial}"
        cmd += f" exec-out screencap -p > {save_path}"
        
        for _ in range(3):
            subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                return True
            time.sleep(0.1)
        return False
    
    # ========== 元素获取 ==========
    
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        """通过 UIAutomator dump 获取 UI 元素树"""
        # 1. 拉取 XML
        xml_path = "/data/local/tmp/uidump.xml"
        self._run(f"shell uiautomator dump {xml_path}")
        local_xml = f"{screenshot_path}.xml"
        self._run(f"pull {xml_path} {local_xml}")
        
        if not os.path.exists(local_xml):
            return []
        
        # 2. 解析 XML
        tree = ET.parse(local_xml)
        root = tree.getroot()
        
        # 3. 提取可交互元素
        elements = []
        self._parse_node(root, elements, index=0)
        
        # 4. 清理临时文件
        os.remove(local_xml)
        
        return elements
    
    def _parse_node(self, node, elements: List, index: int) -> int:
        """递归解析 XML 节点"""
        tag = node.tag
        bounds = node.attrib.get("bounds", "")
        
        # 解析 bounds: "[x1,y1][x2,y2]"
        match = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if not match:
            return index
        
        x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        w, h = x2 - x1, y2 - y1
        
        # 过滤太小元素
        if w < 10 or h < 10:
            return index
        
        # 归一化坐标
        sw, sh = self.display_info.width, self.display_info.height
        nx, ny = x1 / sw * 1000, y1 / sh * 1000
        nw, nh = w / sw * 1000, h / sh * 1000
        
        clickable = node.attrib.get("clickable", "false") == "true"
        
        if clickable or len(list(node)) == 0:
            element = UIElement(
                index=index,
                bbox_normalized={"x": nx, "y": ny, "w": nw, "h": nh},
                bbox_pixel={"x": x1, "y": y1, "w": w, "h": h},
                resource_id=node.attrib.get("resource-id", ""),
                text=node.attrib.get("text", ""),
                content_desc=node.attrib.get("content-desc", ""),
                class_name=node.attrib.get("class", ""),
                package_name=node.attrib.get("package", ""),
                clickable=clickable,
                enabled=node.attrib.get("enabled", "true") == "true",
                bounds=bounds
            )
            elements.append(element)
            index += 1
        
        for child in node:
            index = self._parse_node(child, elements, index)
        
        return index
    
    # ========== 用户操作 ==========
    
    def click(self, x: int, y: int) -> bool:
        self._run(f"shell input tap {x} {y}")
        return True
    
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        self._run(f"shell input swipe {x} {y} {x} {y} {duration}")
        return True
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        self._run(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
        return True
    
    def type_text(self, text: str) -> bool:
        escaped = text.replace('"', '\\"').replace("'", "\\'")
        commands = [
            "shell ime enable com.android.adbkeyboard/.AdbIME",
            "shell ime set com.android.adbkeyboard/.AdbIME",
            f'shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped}"',
            "shell ime disable com.android.adbkeyboard/.AdbIME",
        ]
        for cmd in commands:
            self._run(cmd)
            time.sleep(0.05)
        return True
    
    def press_key(self, key: str) -> bool:
        key_map = {
            "BACK": "4", "HOME": "3", "MENU": "82",
            "POWER": "26", "VOLUME_UP": "24", "VOLUME_DOWN": "25",
            "ENTER": "66", "DELETE": "67", "CLEAR": "28",
        }
        key_code = key_map.get(key.upper(), key)
        self._run(f"shell input keyevent {key_code}")
        return True
    
    # ========== 应用管理 ==========
    
    def get_installed_packages(self) -> List[str]:
        result = self._run("shell pm list packages -3")
        pkgs = []
        for line in result.stdout.splitlines():
            s = line.strip().replace("package:", "")
            if s:
                pkgs.append(s)
        return sorted(set(pkgs))
    
    def launch_app(self, package_name: str) -> bool:
        self._run(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        return True
    
    def close_app(self, package_name: str) -> bool:
        self._run(f"shell am force-stop {package_name}")
        return True
    
    def get_current_app(self) -> str:
        result = self._run("shell dumpsys window | grep mCurrentFocus")
        match = re.search(r"([a-zA-Z0-9.]+)/", result.stdout)
        return match.group(1) if match else ""
    
    # ========== 连接管理 ==========
    
    def is_connected(self) -> bool:
        result = self._run("devices")
        device_flag = self._device_serial or self.device_id
        return device_flag in result.stdout and "device" in result.stdout
    
    def reconnect(self) -> bool:
        self._run("kill-server")
        time.sleep(2)
        self._run("start-server")
        time.sleep(2)
        return self.is_connected()
    
    def release(self):
        pass
```

### 4.3 iOS 适配器实现（预留入口）

```python
class iOSAdapter(BaseDeviceAdapter):
    """iOS 设备适配器 - 使用 WebDriverAgent (WDA)
    
    前置条件：
    1. 安装 facebook-wda: pip install facebook-wda
    2. 在设备上运行 WebDriverAgentRunner
    3. WDA 默认监听 http://localhost:8100
    """
    
    def __init__(self, wda_url: str = "http://localhost:8100", device_udid: Optional[str] = None):
        import wda  # facebook-wda
        self._wda_url = wda_url
        self._device_udid = device_udid
        self._client = wda.Client(wda_url)
        self._session = self._client.session()
        self._display_info = None
        self._load_display_info()
    
    @property
    def platform(self) -> Platform:
        return Platform.IOS
    
    @property
    def device_id(self) -> str:
        return self._device_udid or self._session.window_size().__str__()
    
    @property
    def display_info(self) -> DisplayInfo:
        if self._display_info is None:
            self._load_display_info()
        return self._display_info
    
    def _load_display_info(self):
        size = self._session.window_size()
        self._display_info = DisplayInfo(
            width=size.width,
            height=size.height,
            density=3.0,
            status_bar_height=44,
            navigation_bar_height=0
        )
    
    def get_screenshot(self, save_path: str) -> bool:
        screenshot_data = self._client.screenshot().tobytes()
        with open(save_path, 'wb') as f:
            f.write(screenshot_data)
        return os.path.exists(save_path)
    
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        """通过 WDA page source 获取 UI 元素"""
        source = self._client.source()
        elements = []
        self._parse_wda_source(source, elements)
        return elements
    
    def click(self, x: int, y: int) -> bool:
        self._session.tap(x, y)
        return True
    
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        self._session.tap_hold(x, y, duration / 1000)
        return True
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        self._session.swipe(x1, y1, x2, y2, duration / 1000)
        return True
    
    def type_text(self, text: str) -> bool:
        self._session.send_keys(text)
        return True
    
    def press_key(self, key: str) -> bool:
        key_map = {"HOME": "home", "BACK": "", "VOLUME_UP": "", "VOLUME_DOWN": ""}
        mapped = key_map.get(key.upper(), key.lower())
        if hasattr(self._session, mapped):
            getattr(self._session, mapped)()
        return True
    
    def get_installed_packages(self) -> List[str]:
        return self._client.apps()
    
    def launch_app(self, bundle_id: str) -> bool:
        self._session.app_activate(bundle_id)
        return True
    
    def close_app(self, bundle_id: str) -> bool:
        self._session.app_terminate(bundle_id)
        return True
    
    def get_current_app(self) -> str:
        info = self._client.app_current()
        return info.get("bundleId", "") if info else ""
    
    def is_connected(self) -> bool:
        try:
            self._client.status()
            return True
        except Exception:
            return False
    
    def reconnect(self) -> bool:
        self._client = wda.Client(self._wda_url)
        self._session = self._client.session()
        return True
    
    def release(self):
        if self._session:
            self._session.close()
```

### 4.4 鸿蒙适配器实现（预留入口）

```python
class HarmonyOSAdapter(BaseDeviceAdapter):
    """鸿蒙设备适配器 - 使用 hdc + hiinspect
    
    前置条件：
    1. 安装 DevEco Testing / hdc 工具
    2. 连接鸿蒙设备：hdc list targets
    3. hiinspect 用于获取 UI 层次结构
    """
    
    def __init__(self, hdc_path: str = "hdc", device_serial: Optional[str] = None):
        self._hdc_path = hdc_path
        self._device_serial = device_serial
        self._device_flag = f" -t {device_serial} " if device_serial else " "
        self._display_info = None
        self._load_display_info()
    
    def _hdc(self, args: str) -> subprocess.CompletedProcess:
        cmd = f"{self._hdc_path}{self._device_flag}{args}"
        return subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    def _load_display_info(self):
        # 通过 hdc 获取屏幕信息
        result = self._hdc("shell hidumper -s 10 -a display")
        width, height = 1080, 2340  # 默认值
        for line in result.stdout.splitlines():
            if "width" in line.lower():
                match = re.search(r"(\d+)", line.split(":")[-1])
                if match:
                    width = int(match.group(1))
            if "height" in line.lower():
                match = re.search(r"(\d+)", line.split(":")[-1])
                if match:
                    height = int(match.group(1))
        
        self._display_info = DisplayInfo(
            width=width, height=height, density=3.0,
            status_bar_height=48, navigation_bar_height=0
        )
    
    @property
    def platform(self) -> Platform:
        return Platform.HARMONYOS
    
    @property
    def device_id(self) -> str:
        return self._device_serial or "harmonyos_device"
    
    @property
    def display_info(self) -> DisplayInfo:
        if self._display_info is None:
            self._load_display_info()
        return self._display_info
    
    def get_screenshot(self, save_path: str) -> bool:
        self._hdc(f"shell snapshot display {save_path}")
        return os.path.exists(save_path)
    
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        """通过 hiinspect 获取 UI 元素树"""
        # hiinspect dump -o output.json
        json_path = f"{screenshot_path}.json"
        self._hdc(f"shell hiinspect -c -o {json_path}")
        
        if not os.path.exists(json_path):
            return []
        
        elements = []
        with open(json_path, 'r') as f:
            import json
            data = json.load(f)
            self._parse_hiinspect(data, elements)
        
        os.remove(json_path)
        return elements
    
    def _parse_hiinspect(self, node, elements: List, index: int = 0) -> int:
        """递归解析 hiinspect JSON"""
        bounds = node.get("bounds", {})
        if not bounds:
            return index
        
        nx = bounds.get("left", 0) / self.display_info.width * 1000
        ny = bounds.get("top", 0) / self.display_info.height * 1000
        nw = (bounds.get("right", 0) - bounds.get("left", 0)) / self.display_info.width * 1000
        nh = (bounds.get("bottom", 0) - bounds.get("top", 0)) / self.display_info.height * 1000
        
        clickable = node.get("clickable", False)
        if clickable:
            element = UIElement(
                index=index,
                bbox_normalized={"x": nx, "y": ny, "w": nw, "h": nh},
                bbox_pixel={"x": int(bounds.get("left", 0)), "y": int(bounds.get("top", 0)),
                            "w": int(bounds.get("right", 0) - bounds.get("left", 0)),
                            "h": int(bounds.get("bottom", 0) - bounds.get("top", 0))},
                resource_id=node.get("id", ""),
                text=node.get("text", ""),
                content_desc=node.get("description", ""),
                class_name=node.get("type", ""),
                clickable=True,
                enabled=node.get("enabled", True),
            )
            elements.append(element)
            index += 1
        
        for child in node.get("children", []):
            index = self._parse_hiinspect(child, elements, index)
        
        return index
    
    def click(self, x: int, y: int) -> bool:
        self._hdc(f"shell input mouse tap {x} {y}")
        return True
    
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        self._hdc(f"shell input mouse swipe {x} {y} {x} {y} {duration}")
        return True
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        self._hdc(f"shell input mouse swipe {x1} {y1} {x2} {y2}")
        return True
    
    def type_text(self, text: str) -> bool:
        escaped = text.replace(" ", "%s")
        self._hdc(f'shell input text "{escaped}"')
        return True
    
    def press_key(self, key: str) -> bool:
        key_map = {"BACK": "back", "HOME": "home", "MENU": "menu", "ENTER": "enter"}
        mapped = key_map.get(key.upper(), key.lower())
        self._hdc(f"shell input keyevent {mapped}")
        return True
    
    def get_installed_packages(self) -> List[str]:
        result = self._hdc("shell bm list")
        pkgs = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                pkgs.extend(line.split(","))
        return pkgs
    
    def launch_app(self, bundle_name: str) -> bool:
        self._hdc(f"shell aa start -a EntryAbility -b {bundle_name}")
        return True
    
    def close_app(self, bundle_name: str) -> bool:
        self._hdc(f"shell aa force-stop {bundle_name}")
        return True
    
    def get_current_app(self) -> str:
        result = self._hdc("shell hidumper -s WindowManagerService -a -a")
        for line in result.stdout.splitlines():
            if "current" in line.lower() and "mission" in line.lower():
                match = re.search(r"bundleName:(\S+)", line)
                if match:
                    return match.group(1)
        return ""
    
    def is_connected(self) -> bool:
        result = self._hdc("list targets")
        return self._device_serial in result.stdout if self._device_serial else bool(result.stdout.strip())
    
    def reconnect(self) -> bool:
        self._hdc("kill")
        time.sleep(2)
        self._hdc("start")
        time.sleep(2)
        return True
    
    def release(self):
        pass
```

### 4.5 适配器工厂

```python
class DeviceAdapterFactory:
    """设备适配器工厂"""
    
    @staticmethod
    def create(platform: Platform, **kwargs) -> BaseDeviceAdapter:
        adapters = {
            Platform.ANDROID: AndroidAdapter,
            Platform.IOS: iOSAdapter,
            Platform.HARMONYOS: HarmonyOSAdapter,
        }
        if platform not in adapters:
            raise ValueError(f"不支持的平台: {platform}, 可用: {[p.value for p in adapters.keys()]}")
        
        return adapters[platform](**kwargs)
```

---

## 5. Agent 核心引擎设计

### 5.1 Agent 执行循环（ReAct 模式）

```python
import asyncio
import json
import time
import os
import copy
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from PIL import Image

from .adapter import BaseDeviceAdapter, UIElement
from .locator import ElementLocator, ElementFinder
from .prompts import (
    SYSTEM_PROMPT_AGENT,
    INSTRUCTION_PROMPT,
    ASSERTION_PROMPT,
    ACTION_SPACE_PROMPT,
)


@dataclass
class TestStep:
    """测试步骤"""
    step_id: int
    action: str                    # click / type / swipe / assert / open / done
    locator: Optional[ElementLocator] = None
    params: Dict[str, Any] = field(default_factory=dict)
    expected: Optional[str] = None
    timeout: int = 10


@dataclass
class StepResult:
    """单步执行结果"""
    step_id: int
    success: bool
    action: str
    screenshot: Optional[str] = None
    element: Optional[UIElement] = None
    error: Optional[str] = None
    actual_state: Optional[str] = None
    duration: float = 0.0


@dataclass
class TestResult:
    """完整测试执行结果"""
    device_id: str
    steps: List[StepResult]
    passed: int = 0
    total: int = 0
    duration: float = 0.0
    
    def __post_init__(self):
        self.passed = sum(1 for s in self.steps if s.success)
        self.total = len(self.steps)
    
    @property
    def success_rate(self) -> float:
        return self.passed / self.total * 100 if self.total > 0 else 0.0


class TestAgent:
    """自动化测试 Agent 核心执行器"""
    
    def __init__(
        self,
        adapter: BaseDeviceAdapter,
        llm_client,
        model_name: str = "gui-owl-1.5-8b",
        max_steps: int = 50,
        screenshot_dir: str = "./screenshots",
    ):
        self.adapter = adapter
        self.llm = llm_client
        self.model_name = model_name
        self.max_steps = max_steps
        self.screenshot_dir = screenshot_dir
        
        self.message_history: List[Dict] = []
        self.action_history: List[Dict] = []
        self.current_step = 0
        
        os.makedirs(screenshot_dir, exist_ok=True)
    
    async def execute_step(self, step: TestStep) -> StepResult:
        """执行单个测试步骤"""
        start_time = time.time()
        screenshot_path = os.path.join(
            self.screenshot_dir,
            f"step_{self.current_step:03d}.png"
        )
        
        try:
            # 1. 截图
            self.adapter.get_screenshot(screenshot_path)
            
            # 2. 获取元素树
            elements = self.adapter.get_element_tree(screenshot_path)
            
            # 3. 如果是断言步骤，使用 VLM 验证
            if step.action == "assert":
                result = await self._execute_assert(step, screenshot_path)
                result.duration = time.time() - start_time
                return result
            
            # 4. 如果是应用操作步骤
            if step.action == "open_app":
                self.adapter.launch_app(step.params.get("package_name", step.params.get("app_name", "")))
                time.sleep(2)
                result = StepResult(
                    step_id=step.step_id,
                    success=True,
                    action=step.action,
                    screenshot=screenshot_path,
                )
                result.duration = time.time() - start_time
                return result
            
            # 5. 元素定位
            target_element = await self._locate_element(step.locator, elements, screenshot_path)
            
            if target_element is None and step.action not in ["wait", "done", "skip"]:
                return StepResult(
                    step_id=step.step_id,
                    success=False,
                    action=step.action,
                    screenshot=screenshot_path,
                    error=f"找不到目标元素: {step.locator}",
                    duration=time.time() - start_time,
                )
            
            # 6. 执行动作
            success = await self._execute_action(step.action, target_element, step.params)
            
            time.sleep(1)
            
            result = StepResult(
                step_id=step.step_id,
                success=success,
                action=step.action,
                screenshot=screenshot_path,
                element=target_element,
                duration=time.time() - start_time,
            )
            
            self.current_step += 1
            
            # 7. 记录历史
            self._record_history(step, result)
            
            return result
            
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                success=False,
                action=step.action,
                screenshot=screenshot_path,
                error=str(e),
                duration=time.time() - start_time,
            )
    
    async def execute_test_case(self, steps: List[TestStep]) -> TestResult:
        """执行完整测试用例"""
        start_time = time.time()
        results = []
        
        for step in steps:
            result = await self.execute_step(step)
            results.append(result)
            
            # 断言失败时停止
            if not result.success and step.action == "assert":
                break
        
        return TestResult(
            device_id=self.adapter.device_id,
            steps=results,
            duration=time.time() - start_time,
        )
    
    async def _locate_element(
        self,
        locator: ElementLocator,
        elements: List[UIElement],
        screenshot_path: str,
    ) -> Optional[UIElement]:
        """定位元素"""
        if locator is None:
            return None
        
        finder = ElementFinder(self.llm, self.adapter.display_info)
        return await finder.find_element(locator, elements, screenshot_path)
    
    async def _execute_action(
        self,
        action: str,
        element: Optional[UIElement],
        params: Dict[str, Any],
    ) -> bool:
        """执行动作"""
        if element:
            cx, cy = element.center()
            px, py = self.adapter.display_info.denormalize_coord(cx, cy)
        
        if action == "click":
            self.adapter.click_element(element)
            return True
        
        elif action == "long_press":
            duration = params.get("duration", 800)
            self.adapter.long_press(px, py, duration)
            return True
        
        elif action == "swipe":
            direction = params.get("direction", "up")
            w, h = self.adapter.display_info.width, self.adapter.display_info.height
            if direction == "up":
                self.adapter.swipe(w // 2, h // 2, w // 2, h // 4)
            elif direction == "down":
                self.adapter.swipe(w // 2, h // 4, w // 2, h // 2)
            elif direction == "left":
                self.adapter.swipe(w // 2, h // 2, w // 4, h // 2)
            elif direction == "right":
                self.adapter.swipe(w // 4, h // 2, w // 2, h // 2)
            else:
                x1, y1 = params.get("x1", 0), params.get("y1", 0)
                x2, y2 = params.get("x2", 0), params.get("y2", 0)
                self.adapter.swipe(x1, y1, x2, y2)
            return True
        
        elif action == "type":
            text = params.get("text", "")
            if element:
                self.adapter.click_element(element)
                time.sleep(0.5)
            self.adapter.type_text(text)
            return True
        
        elif action == "press_key":
            key = params.get("key", "BACK")
            self.adapter.press_key(key)
            return True
        
        elif action == "wait":
            t = params.get("time", 2)
            time.sleep(t)
            return True
        
        elif action == "done":
            return True
        
        return False
    
    async def _execute_assert(self, step: TestStep, screenshot_path: str) -> StepResult:
        """执行断言 - 使用 VLM 验证"""
        prompt = ASSERTION_PROMPT.format(expected=step.expected)
        
        img_base64 = self._image_to_base64(screenshot_path)
        
        response = self.llm.vision(prompt, [img_base64])
        
        passed = "PASS" in response.upper()
        
        return StepResult(
            step_id=step.step_id,
            success=passed,
            action="assert",
            screenshot=screenshot_path,
            actual_state=response,
            error=None if passed else f"断言失败. 预期: {step.expected}, 模型判断: {response}",
        )
    
    def _record_history(self, step: TestStep, result: StepResult):
        """记录执行历史"""
        self.action_history.append({
            "step": step.step_id,
            "action": step.action,
            "locator": step.locator.to_dict() if step.locator else None,
            "success": result.success,
        })
    
    def _image_to_base64(self, image_path: str) -> str:
        """将图片转为 base64"""
        import base64
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
```

---

## 6. 元素定位器设计（解决跨设备脚本失效）

### 6.1 核心定位器

```python
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class ElementLocator:
    """元素定位器 - 支持多种定位方式
    
    优先级：resource_id > text > text_contains > content_desc > xpath > semantic
    
    使用示例：
        locator = ElementLocator(text="登录")
        locator = ElementLocator(resource_id="com.taobao:id/btn_login")
        locator = ElementLocator(semantic="页面底部的红色确认按钮")
    """
    
    # 基础属性定位（高优先级，精确匹配）
    resource_id: Optional[str] = None       # Android: resource-id, iOS: accessibilityIdentifier
    text: Optional[str] = None              # 文本精确匹配
    text_contains: Optional[str] = None     # 文本包含匹配
    content_desc: Optional[str] = None      # content-description / accessibilityLabel
    class_name: Optional[str] = None        # 控件类型 (Button, EditText, ImageView)
    
    # XPath 定位
    xpath: Optional[str] = None
    
    # 语义定位（低优先级，使用 VLM 理解）
    semantic: Optional[str] = None          # "购物车图标", "红色的确认按钮"
    
    # 相对位置（相对于其他元素）
    relative: Optional[Dict] = None         # {"relation": "below", "target": ElementLocator(...)}
    
    # 超时
    timeout: int = 10
    
    def to_dict(self) -> Dict:
        """转换为可序列化字典"""
        result = {}
        for k, v in self.__dict__.items():
            if v is not None:
                if k == "relative" and isinstance(v, dict) and "target" in v:
                    v = {**v, "target": v["target"].to_dict()}
                result[k] = v
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ElementLocator':
        """从字典还原"""
        if "relative" in data and isinstance(data["relative"], dict) and "target" in data["relative"]:
            data["relative"]["target"] = cls.from_dict(data["relative"]["target"])
        return cls(**data)


class ElementFinder:
    """元素查找器"""
    
    def __init__(self, llm_client, display_info: 'DisplayInfo'):
        self.llm = llm_client
        self.display_info = display_info
    
    async def find_element(
        self,
        locator: ElementLocator,
        elements: List['UIElement'],
        screenshot_path: str,
    ) -> Optional['UIElement']:
        """在元素列表中查找目标元素
        
        查找顺序：
        1. resource_id 精确匹配
        2. text 精确匹配
        3. text_contains 模糊匹配
        4. content_desc 匹配
        5. xpath 匹配
        6. 相对位置匹配
        7. 语义匹配（VLM）
        """
        
        # 1. resource-id 精确匹配
        if locator.resource_id:
            for elem in elements:
                if elem.resource_id == locator.resource_id:
                    return elem
        
        # 2. text 精确匹配
        if locator.text:
            for elem in elements:
                if elem.text == locator.text:
                    return elem
        
        # 3. text 包含匹配
        if locator.text_contains:
            for elem in elements:
                if locator.text_contains in elem.text:
                    return elem
        
        # 4. content-desc 匹配
        if locator.content_desc:
            for elem in elements:
                if elem.content_desc == locator.content_desc:
                    return elem
        
        # 5. 相对位置匹配
        if locator.relative:
            return await self._find_by_relative_position(
                locator.relative, elements, screenshot_path
            )
        
        # 6. 语义匹配（使用 VLM）
        if locator.semantic:
            return await self._semantic_match(
                locator.semantic, elements, screenshot_path
            )
        
        return None
    
    async def _semantic_match(
        self,
        semantic: str,
        elements: List['UIElement'],
        screenshot_path: str,
    ) -> Optional['UIElement']:
        """语义匹配 - VLM 理解自然语言描述找到对应元素"""
        
        # 筛选可交互元素
        candidate_count = len(elements)
        if candidate_count == 0:
            return None
        
        if candidate_count == 1:
            return elements[0]
        
        # 构建候选列表
        candidate_text = ""
        for i, elem in enumerate(elements[:20]):  # 最多 20 个候选
            desc = []
            if elem.text:
                desc.append(f"文本: {elem.text}")
            if elem.content_desc:
                desc.append(f"描述: {elem.content_desc}")
            if elem.resource_id:
                rid = elem.resource_id.split("/")[-1] if "/" in elem.resource_id else elem.resource_id
                desc.append(f"ID: {rid}")
            if elem.class_name:
                desc.append(f"类型: {elem.class_name.split('.')[-1]}")
            
            if desc:
                candidate_text += f"[{i}] {' | '.join(desc)}\n"
        
        prompt = SEMANTIC_MATCH_PROMPT.format(
            description=semantic,
            options=candidate_text,
        )
        
        # 调用 VLM
        response = self.llm.chat(prompt)
        
        # 解析结果
        match = re.search(r'\[?(\d+)\]?', response)
        if match:
            idx = int(match.group(1))
            if 0 <= idx < len(elements):
                return elements[idx]
        
        return None
    
    async def _find_by_relative_position(
        self,
        relative: Dict,
        elements: List['UIElement'],
        screenshot_path: str,
    ) -> Optional['UIElement']:
        """相对位置查找"""
        target_locator = relative.get("target")
        relation = relative.get("relation", "below")
        
        if not target_locator:
            return None
        
        target_elem = await self.find_element(target_locator, elements, screenshot_path)
        if not target_elem:
            return None
        
        tx = target_elem.bbox_normalized["x"]
        ty = target_elem.bbox_normalized["y"]
        tw = target_elem.bbox_normalized["w"]
        th = target_elem.bbox_normalized["h"]
        
        candidates = []
        for elem in elements:
            if elem is target_elem:
                continue
            ex = elem.bbox_normalized["x"]
            ey = elem.bbox_normalized["y"]
            ew = elem.bbox_normalized["w"]
            eh = elem.bbox_normalized["h"]
            
            if relation == "below" and ey >= ty + th:
                candidates.append((ey - (ty + th), elem))
            elif relation == "above" and ey + eh <= ty:
                candidates.append(((ty) - (ey + eh), elem))
            elif relation == "left" and ex + ew <= tx:
                candidates.append(((tx) - (ex + ew), elem))
            elif relation == "right" and ex >= tx + tw:
                candidates.append((ex - (tx + tw), elem))
            elif relation == "inside" and ex >= tx and ey >= ty and ex + ew <= tx + tw and ey + eh <= ty + th:
                candidates.append((0, elem))
        
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        return None
```

### 6.2 SoM（Set-of-Marks）标注器

```python
class SoMAnnotator:
    """SoM 标注器 - 在截图上标注元素序号"""
    
    def __init__(self, display_info: 'DisplayInfo'):
        self.display_info = display_info
        self.label_colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 0, 0), (0, 128, 0), (0, 0, 128),
        ]
    
    def annotate(self, image_path: str, elements: List['UIElement']) -> str:
        """在截图上标注 SoM 标签
        
        Returns:
            标注后的图片保存路径
        """
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        save_path = image_path.replace(".png", "_som.png")
        
        for i, elem in enumerate(elements[:100]):
            bbox = elem.bbox_pixel
            if not bbox:
                continue
            
            color = self.label_colors[i % len(self.label_colors)]
            
            # 画边框
            draw.rectangle(
                [bbox["x"], bbox["y"], bbox["x"] + bbox["w"], bbox["y"] + bbox["h"]],
                outline=color,
                width=2,
            )
            
            # 画标签背景
            label = str(i)
            font_size = max(12, int(bbox["h"] * 0.3))
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            bbox_text = draw.textbbox((0, 0), label, font=font)
            tw = bbox_text[2] - bbox_text[0]
            th = bbox_text[3] - bbox_text[1]
            
            draw.rectangle(
                [bbox["x"], bbox["y"] - th - 2, bbox["x"] + tw + 4, bbox["y"]],
                fill=color,
            )
            draw.text(
                (bbox["x"] + 2, bbox["y"] - th - 1),
                label,
                fill=(255, 255, 255),
                font=font,
            )
        
        img.save(save_path)
        return save_path
```

---

## 7. 多设备隔离执行设计

### 7.1 设备上下文

```python
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import uuid


@dataclass
class DeviceContext:
    """设备上下文 - 完全隔离
    
    每个设备拥有：
    - 独立的 adapter
    - 独立的执行状态
    - 独立的 asyncio.Lock（保证串行）
    - 独立的截图目录
    - 独立的消息历史
    """
    context_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    adapter: Optional['BaseDeviceAdapter'] = None
    
    # 状态
    message_history: List[Dict] = field(default_factory=list)
    action_history: List[Dict] = field(default_factory=list)
    screenshot_dir: str = ""
    current_app: str = ""
    step_count: int = 0
    
    # 设备级锁 - 保证单设备串行
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    @property
    def device_id(self) -> str:
        return self.adapter.device_id if self.adapter else "unknown"
    
    async def acquire(self):
        """获取设备锁"""
        await self._lock.acquire()
    
    def release(self):
        """释放设备锁"""
        if self._lock.locked():
            self._lock.release()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


class DevicePool:
    """设备池 - 统一管理多设备的注册、获取、释放
    
    核心功能：
    1. 注册设备
    2. 获取设备上下文（自动获取锁）
    3. 释放设备上下文
    4. 并行执行（自动隔离）
    """
    
    def __init__(self, max_concurrent: int = 10):
        self._devices: Dict[str, DeviceContext] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    def register(self, config: 'DeviceConfig', adapter: 'BaseDeviceAdapter') -> DeviceContext:
        """注册设备到池中"""
        if config.device_id in self._devices:
            raise ValueError(f"设备 {config.device_id} 已注册")
        
        ctx = DeviceContext(
            adapter=adapter,
            screenshot_dir=f"./output/{config.device_id}/screenshots/",
        )
        ctx.config = config
        self._devices[config.device_id] = ctx
        return ctx
    
    def unregister(self, device_id: str):
        """注销设备"""
        if device_id in self._devices:
            self._devices[device_id].adapter.release()
            del self._devices[device_id]
    
    def get_context(self, device_id: str) -> Optional[DeviceContext]:
        """获取设备上下文"""
        return self._devices.get(device_id)
    
    def list_devices(self) -> List[str]:
        """列出所有已注册设备"""
        return list(self._devices.keys())
    
    async def execute_on_device(
        self,
        device_id: str,
        fn,
        *args,
        **kwargs,
    ):
        """在指定设备上执行函数（自动获取锁）
        
        Executes fn(device_context, *args, **kwargs)
        
        使用示例：
            result = await pool.execute_on_device("device_001", my_func, arg1, arg2)
        """
        if device_id not in self._devices:
            raise ValueError(f"设备 {device_id} 未注册")
        
        ctx = self._devices[device_id]
        
        async with ctx:
            async with self._semaphore:
                return await fn(ctx, *args, **kwargs)
    
    async def execute_parallel(
        self,
        tasks: List[Dict],
    ) -> Dict[str, any]:
        """并行在多设备上执行
        
        tasks 格式:
        [
            {"device_id": "device_001", "fn": my_func, "args": (), "kwargs": {}},
            {"device_id": "device_002", "fn": my_func, "args": (), "kwargs": {}},
        ]
        
        Returns:
            {device_id: result, ...}
        """
        coroutines = []
        for task in tasks:
            device_id = task["device_id"]
            fn = task["fn"]
            args = task.get("args", ())
            kwargs = task.get("kwargs", {})
            coroutines.append(self.execute_on_device(device_id, fn, *args, **kwargs))
        
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        return {
            tasks[i]["device_id"]: results[i]
            for i in range(len(tasks))
        }
```

### 7.2 多设备并行执行示例

```python
async def parallel_test_execution_example():
    """多设备并行测试执行示例"""
    
    # 1. 初始化设备池
    pool = DevicePool(max_concurrent=5)
    
    # 2. 注册设备
    android_config = DeviceConfig(
        device_id="pixel_6",
        platform=Platform.ANDROID,
        display=DisplayInfo(width=1080, height=2400, density=420, status_bar_height=0, navigation_bar_height=0),
    )
    android_adapter = AndroidAdapter(adb_path="adb", device_serial="emulator-5554")
    pool.register(android_config, android_adapter)
    
    ios_config = DeviceConfig(
        device_id="iphone_15",
        platform=Platform.IOS,
        display=DisplayInfo(width=1179, height=2556, density=460, status_bar_height=0, navigation_bar_height=0),
    )
    ios_adapter = iOSAdapter(wda_url="http://localhost:8100")
    pool.register(ios_config, ios_adapter)
    
    # 3. 定义测试用例（使用元素定位，坐标无关）
    test_steps = [
        TestStep(step_id=1, action="open_app", params={"app_name": "com.taobao.taobao"}),
        TestStep(step_id=2, action="click", locator=ElementLocator(text="我的淘宝")),
        TestStep(step_id=3, action="click", locator=ElementLocator(semantic="登录/注册按钮")),
        TestStep(step_id=4, action="type", locator=ElementLocator(text_contains="请输入手机号"),
                 params={"text": "13800138000"}),
        TestStep(step_id=5, action="click", locator=ElementLocator(text="获取验证码")),
        TestStep(step_id=6, action="wait", params={"time": 2}),
        TestStep(step_id=7, action="assert", expected="验证码已发送，页面应显示倒计时"),
    ]
    
    # 4. 在多个设备上并行执行（自动隔离）
    async def execute_on_device(ctx: DeviceContext):
        agent = TestAgent(
            adapter=ctx.adapter,
            llm_client=llm_client,
            screenshot_dir=ctx.screenshot_dir,
        )
        return await agent.execute_test_case(test_steps)
    
    results = await pool.execute_parallel([
        {"device_id": "pixel_6", "fn": execute_on_device},
        {"device_id": "iphone_15", "fn": execute_on_device},
    ])
    
    # 5. 输出报告
    for device_id, result in results.items():
        if isinstance(result, Exception):
            print(f"[{device_id}] 执行失败: {result}")
        else:
            print(f"[{device_id}] 通过率: {result.success_rate:.1f}% ({result.passed}/{result.total})")
    
    # 6. 清理设备
    pool.unregister("pixel_6")
    pool.unregister("iphone_15")
```

### 7.3 设备配置管理

```python
import json
from typing import Dict, Optional


class DeviceConfigManager:
    """设备配置管理器 - 支持从文件加载设备配置"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.devices: Dict[str, 'DeviceConfig'] = {}
        
        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)
    
    def load_from_file(self, path: str):
        """从 JSON 文件加载设备配置"""
        with open(path, "r") as f:
            data = json.load(f)
        
        for device_data in data:
            config = DeviceConfig(
                device_id=device_data["device_id"],
                platform=Platform(device_data["platform"]),
                display=DisplayInfo(**device_data["display"]),
                capabilities=device_data.get("capabilities", {}),
            )
            self.devices[config.device_id] = config
    
    def save_to_file(self, path: str):
        """保存设备配置到文件"""
        data = []
        for device_id, config in self.devices.items():
            data.append({
                "device_id": config.device_id,
                "platform": config.platform.value,
                "display": {
                    "width": config.display.width,
                    "height": config.display.height,
                    "density": config.display.density,
                },
                "capabilities": config.capabilities,
            })
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def register_device(self, config: 'DeviceConfig', adapter_params: Dict) -> 'DeviceContext':
        """注册设备并自动创建适配器"""
        adapter = DeviceAdapterFactory.create(config.platform, **adapter_params)
        ctx = DeviceContext(adapter=adapter)
        ctx.config = config
        self.devices[config.device_id] = config
        return ctx
```

**设备配置文件示例** `devices.json`：

```json
[
  {
    "device_id": "pixel_6_emulator",
    "platform": "android",
    "display": {"width": 1080, "height": 2400, "density": 420},
    "capabilities": {"adb_serial": "emulator-5554", "adb_path": "/usr/local/bin/adb"}
  },
  {
    "device_id": "xiaomi_14",
    "platform": "android",
    "display": {"width": 1220, "height": 2670, "density": 440},
    "capabilities": {"adb_serial": "192.168.1.100:5555", "adb_path": "adb"}
  },
  {
    "device_id": "iphone_15_pro",
    "platform": "ios",
    "display": {"width": 1179, "height": 2556, "density": 460},
    "capabilities": {"wda_url": "http://localhost:8100", "udid": "00008110-xxxxxxxx"}
  },
  {
    "device_id": "mate_60_pro",
    "platform": "harmonyos",
    "display": {"width": 1260, "height": 2720, "density": 450},
    "capabilities": {"hdc_path": "hdc", "serial": "xxxxxxxx"}
  }
]
```

---

## 8. 自然语言用例生成器

```python
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class ActionType(Enum):
    """测试动作类型"""
    OPEN_APP = "open_app"
    CLICK = "click"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    TYPE = "type"
    PRESS_KEY = "press_key"
    WAIT = "wait"
    ASSERT = "assert"
    DONE = "done"
    SKIP = "skip"


@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str
    steps: List[TestStep]
    tags: List[str] = field(default_factory=list)
    priority: str = "P0"
    
    def to_json(self) -> str:
        return json.dumps({
            "name": self.name,
            "description": self.description,
            "steps": [s.__dict__ for s in self.steps],
            "tags": self.tags,
            "priority": self.priority,
        }, indent=2, ensure_ascii=False)


class TestCaseGenerator:
    """测试用例生成器 - 将自然语言需求转换为结构化测试步骤"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def generate(self, requirement: str) -> TestCase:
        prompt = TEST_CASE_GENERATION_PROMPT.format(requirement=requirement)
        response = self.llm.chat(prompt)
        test_steps = self._parse_response(response, requirement)
        return TestCase(
            name=self._extract_name(requirement),
            description=requirement,
            steps=test_steps,
            tags=["auto_generated"],
        )
    
    def generate_from_screenshot(self, requirement: str, screenshot_path: str) -> TestCase:
        import base64
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        prompt = TEST_CASE_FROM_SCREENSHOT_PROMPT.format(requirement=requirement)
        response = self.llm.vision(prompt, [img_b64])
        test_steps = self._parse_response(response, requirement)
        return TestCase(
            name=self._extract_name(requirement),
            description=requirement,
            steps=test_steps,
        )
    
    def _parse_response(self, response: str, requirement: str) -> List[TestStep]:
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            data = json.loads(json_str)
            steps = []
            for item in data:
                locator = None
                if "locator" in item and item["locator"]:
                    locator = ElementLocator(
                        resource_id=item["locator"].get("resource_id"),
                        text=item["locator"].get("text"),
                        text_contains=item["locator"].get("text_contains"),
                        content_desc=item["locator"].get("content_desc"),
                        semantic=item["locator"].get("semantic"),
                        xpath=item["locator"].get("xpath"),
                    )
                params = item.get("params", {})
                step = TestStep(
                    step_id=item.get("step_id", len(steps) + 1),
                    action=item.get("action", "click"),
                    locator=locator,
                    params=params,
                    expected=item.get("expected"),
                )
                steps.append(step)
            return steps
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"[WARN] \u89e3\u6790\u6d4b\u8bd5\u6b65\u9aa4\u5931\u8d25: {e}, \u4f7f\u7528\u9ed8\u8ba4\u6b65\u9aa4")
            return [
                TestStep(step_id=1, action="open_app", params={"app_name": requirement}),
                TestStep(step_id=2, action="done"),
            ]
    
    def _extract_name(self, requirement: str) -> str:
        name = requirement.strip()
        if len(name) > 20:
            name = name[:20] + "..."
        return name
```
`````

### 8.1 Prompt 模板（用例生成）

`````text
TEST_CASE_GENERATION_PROMPT = '''# 任务
你是一个移动端自动化测试专家。请将用户的测试需求拆解为可执行的测试步骤。

## 测试需求
{requirement}

## 支持的原子动作
| 动作 | 参数 | 说明 |
|------|------|------|
| open_app | {"app_name": "应用名或包名"} | 打开应用 |
| click | {"locator": {...}} | 点击元素 |
| long_press | {"locator": {...}, "duration": 800} | 长按元素 |
| swipe | {"direction": "up|down|left|right"} | 滑动屏幕 |
| type | {"locator": {...}, "text": "输入文本"} | 输入文本到指定元素 |
| press_key | {"key": "BACK|HOME|MENU"} | 按键 |
| wait | {"time": 2} | 等待 |
| assert | {"expected": "预期结果描述"} | 验证当前界面是否符合预期 |
| done | {} | 测试完成 |

## 输出格式
```json
[
  {{
    "step_id": 1,
    "action": "open_app",
    "params": {{"app_name": "\\u6dd8\\u5b9d"}},
    "expected": "\\u5e94\\u7528\\u542f\\u52a8\\u6210\\u529f\\uff0c\\u663e\\u793a\\u9996\\u9875"
  }},
  {{
    "step_id": 2,
    "action": "click",
    "locator": {{"text": "\\u641c\\u7d22\\u6846"}},
    "params": {{}},
    "expected": "\\u8fdb\\u5165\\u641c\\u7d22\\u9875\\u9762"
  }},
]
```

## 规则
1. 每个步骤必须包含 step_id, action, params, expected
2. 优先使用 locator 定位元素（text/resource_id/semantic）
3. 每个测试用例必须包含断言步骤（assert）
4. 用 done 标记测试完成
'''
`````

### 8.2 Prompt 模板（截图辅助用例生成）

`````text
TEST_CASE_FROM_SCREENSHOT_PROMPT = '''# 任务
根据截图和测试需求，生成可执行的测试步骤。

## 测试需求
{requirement}

## 元素定位规则
- 使用元素的文本来定位（text）
- 使用 resource-id 来定位
- 使用语义描述来定位（如"页面底部的确认按钮"）
- **绝对不要使用坐标 (x, y) 定位**

## 输出格式
```json
[
  {{
    "step_id": 1,
    "action": "click",
    "locator": {{"text": "\\u767b\\u5f55"}},
    "params": {{}},
    "expected": "\\u8df3\\u8f6c\\u5230\\u767b\\u5f55\\u9875\\u9762"
  }}
]
```

## 规则
1. 必须包含断言步骤
2. 每个步骤的 expected 要具体可验证
3. 元素定位信息要准确
'''
`````
`````

---

## 9. 脚本转换器（测试步骤 → 框架脚本）

```python
from typing import Dict, List
from dataclasses import dataclass


class ScriptConverter:
    """脚本转换器 - 将测试步骤转换为各框架的自动化脚本
    
    支持的目标框架：
    - uiautomator2: Android 原生 (pytest)
    - appium: 跨平台 Appium
    - xctest: iOS XCUITest (Swift)
    - harmonyos_uitest: 鸿蒙 UI Test (Java)
    - adb_shell: ADB Shell 命令
    """
    
    def __init__(self):
        self.templates: Dict[str, callable] = {
            "uiautomator2": self._to_uiautomator2,
            "appium": self._to_appium,
            "xctest": self._to_xctest,
            "harmonyos_uitest": self._to_harmonyos,
        }
    
    def convert(self, steps: List[TestStep], target: str = "uiautomator2") -> str:
        """转换为目标框架脚本"""
        if target not in self.templates:
            raise ValueError(f"不支持的目标框架: {target}, 可用: {list(self.templates.keys())}")
        return self.templates[target](steps)
    
    def list_supported_frameworks(self) -> List[str]:
        """列出支持的框架"""
        return list(self.templates.keys())
    
    # ==================== uiautomator2 (pytest) ====================
    
    def _to_uiautomator2(self, steps: List[TestStep]) -> str:
        """转换为 pytest + uiautomator2 脚本"""
        lines = [
            '"""',
            'Auto-generated test script - uiautomator2',
            f'Generated by Mobile Test Agent',
            '"""',
            'import pytest',
            'import uiautomator2 as u2',
            'import time',
            '',
            '',
            'class TestMobile:',
            '',
            '    @pytest.fixture(scope="class")',
            '    def d(self):',
            '        device = u2.connect()  # 连接设备',
            '        yield device',
            '        device.app_stop_all()',
            '',
        ]
        
        for i, step in enumerate(steps):
            lines.append(f'    def test_step_{step.step_id}(self, d):')
            
            code_line = self._step_to_uiautomator2(step)
            lines.append(f'        {code_line}')
            
            if step.expected:
                lines.append(f'        # 预期: {step.expected}')
            
            lines.append(f'        time.sleep(1)')
            lines.append('')
        
        return "\n".join(lines)
    
    def _step_to_uiautomator2(self, step: TestStep) -> str:
        """单步转 uiautomator2 代码"""
        loc = step.locator
        
        if step.action == "open_app":
            app_name = step.params.get("app_name", "")
            return f'd.app_start("{app_name}")'
        
        elif step.action == "click":
            if loc:
                if loc.resource_id:
                    return f'd(resourceId="{loc.resource_id}").click()'
                elif loc.text:
                    return f'd(text="{loc.text}").click()'
                elif loc.text_contains:
                    return f'd(textContains="{loc.text_contains}").click()'
                elif loc.content_desc:
                    return f'd(description="{loc.content_desc}").click()'
                elif loc.xpath:
                    return f'd.xpath("{loc.xpath}").click()'
            return f'# 需要手动定位元素: click'
        
        elif step.action == "type":
            text = step.params.get("text", "")
            if loc:
                if loc.resource_id:
                    return f'd(resourceId="{loc.resource_id}").set_text("{text}")'
                elif loc.text:
                    return f'd(text="{loc.text}").set_text("{text}")'
            return f'd(text="输入框").set_text("{text}")'
        
        elif step.action == "swipe":
            direction = step.params.get("direction", "up")
            return f'd.swipe("{direction}")'
        
        elif step.action == "press_key":
            key = step.params.get("key", "BACK")
            return f'd.press("{key.lower()}")'
        
        elif step.action == "wait":
            t = step.params.get("time", 2)
            return f'time.sleep({t})'
        
        elif step.action == "assert":
            return f'# TODO: 需要 uiautomator2 断言逻辑'
        
        elif step.action == "done":
            return f'print("测试完成")'
        
        return f'# 未实现的动作: {step.action}'
    
    # ==================== Appium (Python) ====================
    
    def _to_appium(self, steps: List[TestStep]) -> str:
        """转换为 Appium Python 脚本"""
        lines = [
            '"""',
            'Auto-generated test script - Appium',
            '"""',
            'from appium import webdriver',
            'from appium.webdriver.common.appiumby import AppiumBy',
            'import time',
            '',
            '',
            'desired_caps = {',
            '    "platformName": "Android",',
            '    "deviceName": "device",',
            '    "appPackage": "com.taobao.taobao",',
            '    "appActivity": ".main.MainActivity",',
            '    "noReset": True,',
            '    "automationName": "UiAutomator2",',
            '}',
            '',
            'driver = webdriver.Remote("http://localhost:4723", desired_caps)',
            '',
        ]
        
        for step in steps:
            code = self._step_to_appium(step)
            lines.append(code)
        
        lines.append('driver.quit()')
        return "\n".join(lines)
    
    def _step_to_appium(self, step: TestStep) -> str:
        """单步转 Appium 代码"""
        loc = step.locator
        
        if step.action == "click":
            if loc:
                if loc.resource_id:
                    return f'driver.find_element(AppiumBy.ID, "{loc.resource_id}").click()'
                elif loc.text:
                    return f'driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, \'new UiSelector().text("{loc.text}")\').click()'
                elif loc.xpath:
                    return f'driver.find_element(AppiumBy.XPATH, "{loc.xpath}").click()'
            return f'driver.find_element(AppiumBy.XPATH, "//android.widget.Button").click()'
        
        elif step.action == "type":
            text = step.params.get("text", "")
            if loc and loc.resource_id:
                return f'el = driver.find_element(AppiumBy.ID, "{loc.resource_id}")\nel.clear()\nel.send_keys("{text}")'
            return f'driver.find_element(AppiumBy.CLASS_NAME, "android.widget.EditText").send_keys("{text}")'
        
        elif step.action == "swipe":
            direction = step.params.get("direction", "up")
            return f'driver.swipe(500, 1500, 500, 500)  # {direction}'
        
        elif step.action == "back":
            return f'driver.back()'
        
        elif step.action == "wait":
            t = step.params.get("time", 2)
            return f'time.sleep({t})'
        
        elif step.action == "assert":
            return f'# 需要在 Appium 中添加断言逻辑'
        
        elif step.action == "done":
            return f'print("测试完成")'
        
        return f'# 未实现: {step.action}'
    
    # ==================== XCUITest (Swift) ====================
    
    def _to_xctest(self, steps: List[TestStep]) -> str:
        """转换为 iOS XCUITest Swift 脚本"""
        lines = [
            'import XCTest',
            '',
            'class MobileTest: XCTestCase {',
            '',
            '    override func setUp() {',
            '        continueAfterFailure = false',
            f'        let app = XCUIApplication()',
            '        app.launch()',
            '    }',
            '',
        ]
        
        for step in steps:
            lines.append(f'    func test_step_{step.step_id}() {{')
            lines.append(f'        let app = XCUIApplication()')
            
            code = self._step_to_xctest(step)
            lines.append(f'        {code}')
            
            lines.append(f'        sleep(1)')
            lines.append(f'    }}')
            lines.append('')
        
        lines.append('}')
        return "\n".join(lines)
    
    def _step_to_xctest(self, step: TestStep) -> str:
        """单步转 XCUITest"""
        loc = step.locator
        
        if step.action == "click":
            if loc and loc.text:
                return f'app.buttons["{loc.text}"].tap()'
            elif loc and loc.content_desc:
                return f'app.buttons["{loc.content_desc}"].tap()'
            return f'app.buttons.element(boundBy: 0).tap()'
        
        elif step.action == "type":
            text = step.params.get("text", "")
            return f'app.textFields.element.tap()\n        app.textFields.element.typeText("{text}")'
        
        elif step.action == "swipe":
            return f'app.swipeUp()'
        
        elif step.action == "wait":
            t = step.params.get("time", 2)
            return f'sleep({t})'
        
        elif step.action == "assert":
            return f'XCTAssert(app.staticTexts["success"].exists)'
        
        return f'// 未实现: {step.action}'
    
    # ==================== 鸿蒙 UI Test (Java) ====================
    
    def _to_harmonyos(self, steps: List[TestStep]) -> str:
        """转换为鸿蒙 UI Test Java 脚本
        
        使用 DevEco Testing 框架:
        https://developer.harmonyos.com/cn/docs/documentation/doc-guides/test-overview-0000001064111714
        """
        lines = [
            'import ohos.aafwk.ability.delegation.AbilityDelegator;',
            'import ohos.aafwk.ability.delegation.AbilityDelegatorRegistry;',
            'import org.junit.Test;',
            '',
            'public class MobileTest {',
            '    private AbilityDelegator delegator;',
            '',
            '    public MobileTest() {',
            '        delegator = AbilityDelegatorRegistry.getAbilityDelegator();',
            '    }',
            '',
        ]
        
        for step in steps:
            lines.append(f'    @Test')
            lines.append(f'    public void testStep{step.step_id}() {{')
            
            code = self._step_to_harmonyos(step)
            lines.append(f'        {code}')
            
            lines.append(f'        try {{ Thread.sleep(1000); }} catch (Exception e) {{}}')
            lines.append(f'    }}')
            lines.append('')
        
        lines.append('}')
        return "\n".join(lines)
    
    def _step_to_harmonyos(self, step: TestStep) -> str:
        """单步转鸿蒙 UI Test"""
        loc = step.locator
        
        if step.action == "click":
            if loc and loc.text:
                return f'delegator.executeShellCommand("uitest click -t {loc.text}");'
            elif loc and loc.resource_id:
                rid = loc.resource_id.replace("/", ".")
                return f'delegator.executeShellCommand("uitest click -i {rid}");'
            return f'// 需要手动定位: click'
        
        elif step.action == "type":
            text = step.params.get("text", "")
            return f'delegator.executeShellCommand("uitest input -t {text}");'
        
        elif step.action == "swipe":
            return f'delegator.executeShellCommand("uitest swipe 500 1000 500 500");'
        
        elif step.action == "press_key":
            key = step.params.get("key", "BACK")
            return f'delegator.executeShellCommand("uitest keyEvent {key}");'
        
        elif step.action == "assert":
            return f'// 断言逻辑'
        
        return f'// 未实现: {step.action}'
    
    # ==================== ADB Shell 命令 ====================
    
    def _to_adb_shell(self, steps: List[TestStep]) -> str:
        """转换为 ADB Shell 命令脚本"""
        lines = ['#!/bin/bash', '# Auto-generated ADB test script', '']
        
        for step in steps:
            code = self._step_to_adb(step)
            lines.append(code)
            if step.expected:
                lines.append(f'# 预期: {step.expected}')
            lines.append('sleep 1')
            lines.append('')
        
        return "\n".join(lines)
    
    def _step_to_adb(self, step: TestStep) -> str:
        """单步转 ADB 命令"""
        loc = step.locator
        
        if step.action == "open_app":
            pkg = step.params.get("app_name", "")
            return f'adb shell monkey -p {pkg} -c android.intent.category.LAUNCHER 1'
        
        elif step.action == "click":
            if loc and loc.text:
                return f'# adb shell uiautomator click text="{loc.text}"'
            return f'# 需要坐标: adb shell input tap x y'
        
        elif step.action == "type":
            text = step.params.get("text", "")
            return f'adb shell input text "{text}"'
        
        elif step.action == "swipe":
            return f'adb shell input swipe 500 1000 500 500'
        
        elif step.action == "press_key":
            key = step.params.get("key", "BACK")
            key_map = {"BACK": "4", "HOME": "3", "MENU": "82"}
            code = key_map.get(key.upper(), key)
            return f'adb shell input keyevent {code}'
        
        elif step.action == "wait":
            t = step.params.get("time", 2)
            return f'sleep {t}'
        
        elif step.action == "done":
            return f'echo "测试完成"'
        
        return f'# 未实现: {step.action}'
```

---

## 10. 所有 Prompt 模板汇总

### 10.1 Agent 执行提示词

````python
# =====================================
# 1. Agent 系统提示词（主提示词）
# =====================================

SYSTEM_PROMPT_AGENT = '''# 角色
你是一个移动端自动化测试专家。你能够操作移动设备执行测试用例。

# 工具
你可以通过调用预定义工具来操作移动设备。

# 可用动作
1. `click` - 点击屏幕上的元素
2. `long_press` - 长按元素
3. `swipe` - 滑动屏幕
4. `type` - 输入文本
5. `press_key` - 按键 (BACK/HOME/MENU/ENTER)
6. `wait` - 等待
7. `open_app` - 打开应用
8. `assert` - 验证当前界面是否符合预期
9. `screenshot` - 截图
10. `done` - 标记测试完成

# 响应格式
Action: <描述>
<tool_call>{"name": "click", "arguments": {"locator": {"text": "登录"}}}</tool_call>

# 重要规则
1. 每个步骤只能执行一个操作
2. 使用元素属性定位，不要使用坐标
3. 断言失败时报告具体原因'''

# =====================================
# 2. 断言提示词
# =====================================

ASSERTION_PROMPT = '''# 任务
判断当前屏幕状态是否满足预期条件。
## 预期条件: {expected}
## 判断标准
- 如果屏幕显示的内容符合预期，输出 PASS
- 如果不符合，输出 FAIL 并说明原因
## 输出格式: PASS 或 FAIL + 原因'''

# =====================================
# 3. 语义匹配提示词
# =====================================

SEMANTIC_MATCH_PROMPT = '''# 任务
从以下元素列表中找到符合自然语言描述的目标元素。
## 目标描述: {description}
## 可用元素列表: {options}
## 输出格式: 只输出元素编号，例如: [3]'''

# =====================================
# 4. 测试用例生成提示词
# =====================================

TEST_CASE_GENERATION_PROMPT = '''
## 测试需求
{requirement}

## 支持的原子动作
| 动作 | 参数 | 说明 |
|------|------|------|
| open_app | {"app_name": "..."} | 打开应用 |
| click | {"locator": {...}} | 点击元素 |
| type | {"locator": {...}, "text": "..."} | 输入文本 |
| swipe | {"direction": "up|down|left|right"} | 滑动 |
| assert | {"expected": "..."} | 验证 |

## 输出格式
```json
[{"step_id": 1, "action": "open_app", "params": {}, "expected": ""}]
```
'''

# =====================================
# 5. 截图辅助用例生成提示词
# =====================================

TEST_CASE_FROM_SCREENSHOT_PROMPT = '''
## 测试需求
{requirement}

## 元素定位规则
- 使用元素的 text / resource-id / 语义描述 来定位
- **绝对不要使用坐标 (x, y) 定位**

## 输出格式
```json
[{"step_id": 1, "action": "click", "locator": {"text": ""}, "params": {}, "expected": ""}]
```
'''

# =====================================
# 6. VLM 截图分析提示词
# =====================================

SCREENSHOT_ANALYSIS_PROMPT = '''# 任务
分析当前手机截图，列出所有可交互的UI元素。
## 输出格式
- 序号
- 文本内容
- 控件类型
- 功能描述'''

# =====================================
# 7. 脚本转换提示词
# =====================================

SCRIPT_GEN_PROMPT = '''# 任务
将以下测试步骤转换为 {framework} 框架的脚本。
## 测试步骤: {test_steps}
## 规则: 保持逻辑不变，使用 {framework} API 规范，添加导入语句和注释。'''

# =====================================
# 8. 错误恢复提示词
# =====================================

ERROR_RECOVERY_PROMPT = '''# 任务
自动化测试在以下步骤遇到了错误，请分析错误原因并提供恢复方案。
## 步骤: {step_info}
## 错误: {error}
## 输出: 错误原因 + 恢复建议 + 替代方案'''
````

---

## 11. 完整目录结构

```
mobile-test-agent/
│
├── README.md                           # 项目说明
├── requirements.txt                    # Python 依赖
├── setup.py                            # 安装脚本
├── devices.json                        # 设备配置文件
│
├── core/
│   ├── __init__.py
│   │
│   ├── adapter/                        # 平台适配层
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseDeviceAdapter 抽象基类
│   │   ├── android.py                  # AndroidAdapter (ADB + UIAutomator)
│   │   ├── ios.py                      # iOSAdapter (WebDriverAgent)
│   │   ├── harmonyos.py                # HarmonyOSAdapter (hdc + hiinspect)
│   │   └── factory.py                  # DeviceAdapterFactory
│   │
│   ├── agent/                          # Agent 核心
│   │   ├── __init__.py
│   │   ├── executor.py                 # TestAgent 执行器 (ReAct 循环)
│   │   ├── planner.py                  # Planner 规划器（多 Agent 协作）
│   │   └── verifier.py                 # Verifier 断言验证器
│   │
│   ├── generator/                      # 用例/脚本生成
│   │   ├── __init__.py
│   │   ├── test_case_generator.py      # TestCaseGenerator 自然语言→测试步骤
│   │   └── script_converter.py         # ScriptConverter 测试步骤→框架脚本
│   │
│   ├── locator/                        # 元素定位（跨设备核心）
│   │   ├── __init__.py
│   │   ├── element_locator.py          # ElementLocator / ElementFinder
│   │   ├── som.py                      # SoMAnnotator 标注器
│   │   └── matchers.py                 # 匹配算法（文本/属性/语义）
│   │
│   ├── device/                         # 设备管理
│   │   ├── __init__.py
│   │   ├── pool.py                     # DevicePool 设备池
│   │   ├── context.py                  # DeviceContext 设备上下文
│   │   └── config.py                   # DeviceConfig / DeviceConfigManager
│   │
│   └── prompts/                        # Prompt 模板
│       ├── __init__.py
│       ├── agent.py                    # Agent 执行 prompt
│       ├── assertion.py                # 断言 prompt
│       ├── generation.py               # 用例生成 prompt
│       ├── matching.py                 # 语义匹配 prompt
│       ├── recovery.py                 # 错误恢复 prompt
│       └── analysis.py                 # 截图分析 prompt
│
├── scripts/                            # 导出脚本模版
│   ├── __init__.py
│   ├── templates.py                    # 各框架代码模板
│   └── examples/                       # 生成示例
│       ├── test_taobao_uiautomator2.py
│       ├── test_taobao_appium.py
│       ├── test_taobao_xctest.swift
│       └── test_taobao_harmonyos.java
│
├── output/                             # 输出目录
│   ├── device_001/                     # 设备 001 的独立输出
│   │   ├── screenshots/                # 截图
│   │   ├── report.json                 # 测试报告
│   │   └── report.html                 # HTML 报告
│   └── device_002/                     # 设备 002 的独立输出
│       ├── screenshots/
│       ├── report.json
│       └── report.html
│
├── examples/                           # 使用示例
│   ├── simple_test.py                  # 简单测试示例
│   ├── multi_device.py                 # 多设备并行示例
│   └── export_script.py                # 脚本导出示例
│
└── tests/                              # 单元测试
    ├── test_adapter.py
    ├── test_locator.py
    ├── test_executor.py
    └── test_converter.py
```

---

## 12. 快速开始示例

### 12.1 最小示例：单个设备执行测试

```python
import asyncio
from core.adapter.factory import DeviceAdapterFactory
from core.adapter.base import Platform
from core.agent.executor import TestAgent, TestStep
from core.locator.element_locator import ElementLocator
from core.device.context import DeviceContext

async def main():
    # 1. 初始化 Android 适配器
    adapter = DeviceAdapterFactory.create(
        Platform.ANDROID,
        adb_path="adb",
        device_serial="emulator-5554",
    )
    
    # 2. 定义测试步骤（元素定位）
    steps = [
        TestStep(
            step_id=1,
            action="open_app",
            params={"app_name": "com.taobao.taobao"},
            expected="淘宝APP启动成功",
        ),
        TestStep(
            step_id=2,
            action="click",
            locator=ElementLocator(text="我的淘宝"),
            expected="进入我的淘宝页面",
        ),
        TestStep(
            step_id=3,
            action="click",
            locator=ElementLocator(text="登录/注册"),
            expected="进入登录页面",
        ),
        TestStep(
            step_id=4,
            action="assert",
            expected="页面显示手机号输入框和登录按钮",
        ),
    ]
    
    # 3. 创建测试 Agent
    agent = TestAgent(
        adapter=adapter,
        llm_client=llm_client,
        screenshot_dir="./output/test_device/screenshots/",
    )
    
    # 4. 执行测试
    result = await agent.execute_test_case(steps)
    
    # 5. 输出结果
    print(f"通过率: {result.success_rate:.1f}% ({result.passed}/{result.total})")
    for step_result in result.steps:
        status = "✅" if step_result.success else "❌"
        print(f"{status} Step {step_result.step_id}: {step_result.action}")
        if step_result.error:
            print(f"   Error: {step_result.error}")
    
    # 6. 释放资源
    adapter.release()


if __name__ == "__main__":
    asyncio.run(main())
```

### 12.2 多设备并行执行示例

```python
async def multi_device_test():
    # 1. 初始化设备池
    from core.device.pool import DevicePool
    from core.device.config import DeviceConfig, DeviceConfigManager
    from core.adapter.factory import DeviceAdapterFactory
    from core.agent.executor import TestAgent, TestStep
    
    pool = DevicePool(max_concurrent=3)
    
    # 2. 从配置文件加载设备
    config_mgr = DeviceConfigManager("devices.json")
    for device_id, config in config_mgr.devices.items():
        adapter_params = config.capabilities
        adapter = DeviceAdapterFactory.create(config.platform, **adapter_params)
        pool.register(config, adapter)
    
    # 3. 定义测试步骤（同一份用例，在不同设备上独立执行）
    test_steps = [
        TestStep(step_id=1, action="open_app", params={"app_name": "com.taobao.taobao"}),
        TestStep(step_id=2, action="click", locator=ElementLocator(text="搜索")),
        TestStep(step_id=3, action="type", locator=ElementLocator(text="搜索"), params={"text": "手机"}),
        TestStep(step_id=4, action="assert", expected="显示搜索结果列表"),
    ]
    
    # 4. 定义在设备上执行的函数
    async def run_on_device(ctx):
        agent = TestAgent(
            adapter=ctx.adapter,
            llm_client=llm_client,
            screenshot_dir=ctx.screenshot_dir,
        )
        return await agent.execute_test_case(test_steps)
    
    # 5. 并行执行
    tasks = [
        {"device_id": "pixel_6_emulator", "fn": run_on_device},
        {"device_id": "xiaomi_14", "fn": run_on_device},
        {"device_id": "iphone_15_pro", "fn": run_on_device},
    ]
    
    results = await pool.execute_parallel(tasks)
    
    # 6. 汇总报告
    print(f"{'设备':<20} {'通过率':<10} {'结果':<10}")
    print("=" * 40)
    for device_id, result in results.items():
        if isinstance(result, Exception):
            print(f"{device_id:<20} {'ERROR':<10} {str(result):<10}")
        else:
            print(f"{device_id:<20} {result.success_rate:.0f}%{'':<7} {'PASS' if result.passed == result.total else 'FAIL'}")
    
    # 7. 清理
    for device_id in pool.list_devices():
        pool.unregister(device_id)
```

### 12.3 自然语言生成测试 + 导出脚本

```python
async def generate_and_export():
    # 1. 自然语言测试需求
    requirement = "测试淘宝APP搜索功能，输入'手机'应该显示搜索结果"
    
    # 2. 生成测试步骤
    from core.generator.test_case_generator import TestCaseGenerator
    
    generator = TestCaseGenerator(llm_client)
    test_case = generator.generate(requirement)
    
    print(f"用例名称: {test_case.name}")
    print(f"测试步骤数: {len(test_case.steps)}")
    
    # 3. 导出为各框架脚本
    from core.generator.script_converter import ScriptConverter
    
    converter = ScriptConverter()
    
    for framework in converter.list_supported_frameworks():
        script = converter.convert(test_case.steps, target=framework)
        
        # 保存文件
        filename = f"./output/scripts/test_search_{framework}.py"
        if framework == "xctest":
            filename = f"./output/scripts/test_search.swift"
        elif framework == "harmonyos_uitest":
            filename = f"./output/scripts/TestSearch.java"
        
        with open(filename, "w") as f:
            f.write(script)
        
        print(f"已导出: {filename}")
```

---

## 13. 与 Mobile-Agent 项目的集成关系

### 13.1 直接复用的组件

| 原始文件 | 组件 | 是否修改 | 说明 |
|---------|------|---------|------|
| `Mobile-Agent-v3.5/mobile_use/utils.py` | `AdbTools` | 是 | 拆分为 `AndroidAdapter`，增加元素获取 |
| `Mobile-Agent-v3.5/mobile_use/utils.py` | `GUIOwlWrapper` | 是 | 复用 LLM 调用封装 |
| `Mobile-Agent-v3.5/mobile_use/run_gui_owl_1_5_for_mobile.py` | 主循环逻辑 | 是 | 改为 `TestAgent.execute_step` |
| `Mobile-Agent-v3.5/mobile_use/utils.py` | `SYSTEM_PROMPT` | 是 | 扩展测试动作，增加 assert |
| `Mobile-Agent-v3.5/browser_use/prompts.py` | Tool Call 格式 | 否 | 直接复用 `<tool_call>` + JSON 格式 |
| `Mobile-Agent-v3.5/browser_use/browser/playwright/som.py` | SoM 标注逻辑 | 是 | 改为移动端版本 |

### 13.2 新增的组件（Mobile-Agent 没有的）

| 组件 | 文件位置 | 说明 |
|------|---------|------|
| 抽象适配器层 | `core/adapter/base.py` | `BaseDeviceAdapter` 接口定义 |
| iOS 适配器 | `core/adapter/ios.py` | WebDriverAgent 封装 |
| 鸿蒙适配器 | `core/adapter/harmonyos.py` | hdc + hiinspect 封装 |
| 元素定位器 | `core/locator/element_locator.py` | 多策略定位，坐标无关 |
| 设备池 | `core/device/pool.py` | 多设备隔离管理 |
| 脚本转换器 | `core/generator/script_converter.py` | 测试步骤 → 框架脚本 |
| TestCase 对象 | `core/agent/executor.py` | `TestStep/TestResult` 数据模型 |
| 断言验证器 | `core/agent/verifier.py` | VLM 驱动的视觉断言 |

### 13.3 不采用的组件（明确不使用的）

| 组件 | 原因 |
|------|------|
| Appium | 用户明确要求不使用 |
| `browser_use/` Playwright 代码 | 浏览器控制，与移动测试无关 |
| `computer_use/` PyAutoGUI 代码 | 桌面端控制，与移动测试无关 |

---

## 附录

### 0. 来源与出处

本方案基于以下开源项目设计：

- **Mobile-Agent-v3.5**：https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5
- 方案中的架构参考、组件命名、ReAct 执行循环、VLM 调用方式均源自该项目
- 所有"与 Mobile-Agent 的集成关系"章节均以此仓库代码为基准分析

### A. 依赖清单

```
# requirements.txt

# 核心
python>=3.9

# LLM API
openai>=1.0.0
dashscope>=1.0.0

# 图片处理
Pillow>=10.0.0
numpy>=1.24.0

# Android 控制（项目自带 ADB，无需额外依赖）
# ADB binary from: https://developer.android.com/tools/releases/platform-tools

# iOS 控制（可选）
# facebook-wda>=0.8.0

# 鸿蒙控制（可选）
# hdc 工具来自 DevEco Studio

# 日志
rich>=13.0.0

# 测试
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

### B. 设计决策记录

| 决策 | 选择 | 替代方案 | 理由 |
|------|------|---------|------|
| 元素定位 | 属性优先，语义兜底 | 纯坐标 | 坐标跨设备失效 |
| 平台抽象 | 接口继承 (`BaseDeviceAdapter`) | 条件分支 | 便于扩展新平台 |
| 设备隔离 | `DeviceContext` + `asyncio.Lock` | 进程隔离 | 轻量，一个程序管理多设备 |
| 脚本转换 | 模板方法 | 运行时解析 | 生成独立的可运行文件 |
| 断言方式 | VLM 视觉断言 | DOM 属性断言 | 更接近人类判断，兼容任意 UI |
| LLM 调用 | OpenAI 兼容接口 | 专有 SDK | 兼容多种模型服务 |
| 坐标系统 | 归一化 0-1000 | 绝对像素 | 便于 VLM 理解，兼容不同分辨率 |
