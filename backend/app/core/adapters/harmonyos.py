"""HarmonyOS device adapter using HDC/Hypium framework."""

import subprocess
import os
import time
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict

from .base import BaseDeviceAdapter, Platform, DisplayInfo, UIElement


class HarmonyOSAdapter(BaseDeviceAdapter):
    """HarmonyOS device adapter."""
    
    def __init__(self, hdc_path: str = "hdc", device_serial: Optional[str] = None):
        self._hdc_path = hdc_path
        self._device_serial = device_serial
        self._display_info: Optional[DisplayInfo] = None
        self._load_display_info()
    
    @property
    def platform(self) -> Platform:
        return Platform.HARMONYOS
    
    @property
    def device_id(self) -> str:
        if self._device_serial:
            return self._device_serial
        result = self._run("list targets")
        for line in result.stdout.splitlines():
            if "device" in line.lower():
                parts = line.split()
                if parts:
                    return parts[0]
        return "unknown"
    
    @property
    def display_info(self) -> DisplayInfo:
        if self._display_info is None:
            self._load_display_info()
        return self._display_info
    
    def _load_display_info(self):
        """Load display information."""
        try:
            result = self._run("shell wm size")
            match = re.search(r"(\d+)x(\d+)", result.stdout)
            width, height = (int(match.group(1)), int(match.group(2))) if match else (1080, 1920)
            
            result = self._run("shell wm density")
            density_match = re.search(r"(\d+)", result.stdout)
            density = int(density_match.group(1)) if density_match else 320
            
            self._display_info = DisplayInfo(
                width=width, height=height, density=density,
                status_bar_height=0, navigation_bar_height=0
            )
        except Exception:
            self._display_info = DisplayInfo(
                width=1080, height=1920, density=320,
                status_bar_height=0, navigation_bar_height=0
            )
    
    def _run(self, args: str) -> subprocess.CompletedProcess:
        cmd = f"{self._hdc_path}"
        if self._device_serial:
            cmd += f" -t {self._device_serial}"
        cmd += f" {args}"
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
    
    def get_screenshot(self, save_path: str) -> bool:
        """Capture screenshot using HDC."""
        cmd = f"{self._hdc_path}"
        if self._device_serial:
            cmd += f" -t {self._device_serial}"
        cmd += f" shell screencap -p > {save_path}"
        
        for _ in range(3):
            subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                return True
            time.sleep(0.1)
        return False
    
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        """Get UI element tree."""
        elements = []
        try:
            xml_path = "/data/local/tmp/uidump.xml"
            self._run(f"shell uiautomator dump {xml_path}")
            local_xml = f"{screenshot_path}.xml"
            self._run(f"file recv {xml_path} {local_xml}")
            
            if os.path.exists(local_xml):
                tree = ET.parse(local_xml)
                root = tree.getroot()
                elements = []
                self._parse_node(root, elements, index=0)
                os.remove(local_xml)
        except Exception:
            pass
        return elements
    
    def _parse_node(self, node, elements: List, index: int) -> int:
        """Parse XML node recursively."""
        bounds = node.attrib.get("bounds", "")
        match = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if not match:
            return index
        
        x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        w, h = x2 - x1, y2 - y1
        
        if w < 10 or h < 10:
            return index
        
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
                enabled=node.attrib.get("enabled", "true") == "true"
            )
            elements.append(element)
            index += 1
        
        for child in node:
            index = self._parse_node(child, elements, index)
        
        return index
    
    def click(self, x: int, y: int) -> bool:
        """Click at pixel coordinates."""
        self._run(f"shell input tap {x} {y}")
        return True
    
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        """Long press at pixel coordinates."""
        self._run(f"shell input swipe {x} {y} {x} {y} {duration}")
        return True
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """Swipe from (x1, y1) to (x2, y2)."""
        self._run(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
        return True
    
    def type_text(self, text: str) -> bool:
        """Type text into active input field."""
        escaped = text.replace('"', '\\"').replace("'", "\\'")
        self._run(f'shell input text "{escaped}"')
        return True
    
    def press_key(self, key: str) -> bool:
        """Press a hardware key."""
        key_map = {"BACK": "4", "HOME": "3", "MENU": "82", "ENTER": "66", "DELETE": "67"}
        key_code = key_map.get(key.upper(), key)
        self._run(f"shell input keyevent {key_code}")
        return True
    
    def launch_app(self, package_name: str) -> bool:
        """Launch an application using the correct ability name."""
        from app.core.config.app_packages import get_harmonyos_ability
        ability = get_harmonyos_ability(package_name)
        self._run(f"shell aa start -a {ability} -p {package_name}")
        return True
    
    def get_current_app(self) -> str:
        """Get current foreground application."""
        result = self._run("shell dumpsys window | grep mCurrentFocus")
        match = re.search(r"([a-zA-Z0-9.]+)/", result.stdout)
        return match.group(1) if match else ""
    
    def is_connected(self) -> bool:
        """Check if device is connected."""
        result = self._run("list targets")
        device_flag = self._device_serial or self.device_id
        return device_flag in result.stdout and "device" in result.stdout
    
    def list_apps(self) -> List[Dict[str, str]]:
        """List installed applications."""
        apps = []
        try:
            result = self._run("shell pm list packages -3")
            for line in result.stdout.splitlines():
                match = re.search(r"package:(.+)", line)
                if match:
                    package_name = match.group(1)
                    apps.append({"package_name": package_name, "name": package_name})
        except Exception:
            pass
        return apps

    def double_tap(self, x: int, y: int) -> bool:
        """Double tap at pixel coordinates with 100ms interval."""
        self._run(f"shell input tap {x} {y}")
        time.sleep(0.1)
        self._run(f"shell input tap {x} {y}")
        return True

    def clear_text(self) -> bool:
        """Clear text in the active input field."""
        # Select all and delete
        self._run("shell input keyevent 123")  # KEYCODE_MOVE_END
        self._run("shell input keyevent 124")  # KEYCODE_FORWARD_DEL
        return True

    def dump_ui_tree(self) -> str:
        """Dump UI hierarchy via HDC and return raw XML string."""
        xml_path = "/data/local/tmp/uidump.xml"
        local_xml = "uidump_local.xml"
        self._run(f"shell uiautomator dump {xml_path}")
        self._run(f"file recv {xml_path} {local_xml}")
        try:
            with open(local_xml, "r", encoding="utf-8", errors="replace") as f_xml:
                content = f_xml.read()
            os.remove(local_xml)
            return content
        except FileNotFoundError:
            return ""

    def list_devices(self) -> List[Dict]:
        """Parse hdc list targets output into list of device dicts."""
        result = self._run("list targets")
        devices = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("["):
                parts = stripped.split()
                if len(parts) >= 1:
                    state = "device" if len(parts) >= 2 else "unknown"
                    devices.append({"id": parts[0], "state": state})
        return devices

    def _resolve_app_name(self, app_name: str) -> str | None:
        """Resolve an app display name to its HarmonyOS bundle name."""
        from app.core.config.app_packages import get_package_name_harmonyos
        return get_package_name_harmonyos(app_name)
