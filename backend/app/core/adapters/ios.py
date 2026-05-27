"""iOS device adapter using WebDriverAgent/XCUITest."""

import requests
import json
import os
import time
from typing import List, Optional, Dict

from .base import BaseDeviceAdapter, Platform, DisplayInfo, UIElement


class IOSAdapter(BaseDeviceAdapter):
    """iOS device adapter."""
    
    def __init__(self, wda_url: str = "http://localhost:8100"):
        self._wda_url = wda_url
        self._session_id = None
        self._display_info: Optional[DisplayInfo] = None
        self._connect()
    
    @property
    def platform(self) -> Platform:
        return Platform.IOS
    
    @property
    def device_id(self) -> str:
        return self._get_device_info().get("udid", "unknown")
    
    @property
    def display_info(self) -> DisplayInfo:
        if self._display_info is None:
            self._load_display_info()
        return self._display_info
    
    def _connect(self):
        """Connect to WebDriverAgent."""
        try:
            response = requests.post(f"{self._wda_url}/session", json={
                "desiredCapabilities": {}
            })
            if response.status_code == 200:
                self._session_id = response.json().get("sessionId")
        except Exception:
            pass
    
    def _load_display_info(self):
        """Load display information from device."""
        try:
            response = requests.get(f"{self._wda_url}/window/size")
            if response.status_code == 200:
                size = response.json().get("value", {})
                width = size.get("width", 375)
                height = size.get("height", 812)
                self._display_info = DisplayInfo(
                    width=width, height=height, density=2.0,
                    status_bar_height=44, navigation_bar_height=0
                )
        except Exception:
            self._display_info = DisplayInfo(
                width=375, height=812, density=2.0,
                status_bar_height=44, navigation_bar_height=0
            )
    
    def _get_device_info(self) -> Dict:
        """Get device information."""
        try:
            response = requests.get(f"{self._wda_url}/status")
            if response.status_code == 200:
                return response.json().get("value", {}).get("device", {})
        except Exception:
            pass
        return {}
    
    def get_screenshot(self, save_path: str) -> bool:
        """Capture screenshot using WebDriverAgent."""
        try:
            response = requests.get(f"{self._wda_url}/screenshot")
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                return True
        except Exception:
            pass
        return False
    
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        """Get UI element tree."""
        elements = []
        try:
            response = requests.get(f"{self._wda_url}/source")
            if response.status_code == 200:
                source = response.json()
                elements = self._parse_source(source, screenshot_path)
        except Exception:
            pass
        return elements
    
    def _parse_source(self, source: Dict, screenshot_path: str) -> List[UIElement]:
        """Parse XML source to UI elements."""
        elements = []
        return elements
    
    def click(self, x: int, y: int) -> bool:
        """Click at pixel coordinates."""
        try:
            requests.post(f"{self._wda_url}/element/click", json={
                "x": x,
                "y": y
            })
            return True
        except Exception:
            return False
    
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        """Long press at pixel coordinates."""
        try:
            requests.post(f"{self._wda_url}/touch/longclick", json={
                "x": x,
                "y": y,
                "duration": duration / 1000
            })
            return True
        except Exception:
            return False
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """Swipe from (x1, y1) to (x2, y2)."""
        try:
            requests.post(f"{self._wda_url}/touch/swipe", json={
                "startX": x1,
                "startY": y1,
                "endX": x2,
                "endY": y2,
                "duration": duration / 1000
            })
            return True
        except Exception:
            return False
    
    def type_text(self, text: str) -> bool:
        """Type text into active input field."""
        try:
            requests.post(f"{self._wda_url}/keys", json={
                "value": list(text)
            })
            return True
        except Exception:
            return False
    
    def press_key(self, key: str) -> bool:
        """Press a hardware key."""
        key_map = {"BACK": "back", "HOME": "home", "ENTER": "enter", "DELETE": "delete"}
        ios_key = key_map.get(key.upper())
        if ios_key:
            try:
                requests.post(f"{self._wda_url}/appium/device/press_button", json={
                    "name": ios_key
                })
                return True
            except Exception:
                pass
        return False
    
    def launch_app(self, package_name: str) -> bool:
        """Launch an application."""
        try:
            requests.post(f"{self._wda_url}/appium/app/launch", json={
                "bundleId": package_name
            })
            return True
        except Exception:
            return False
    
    def get_current_app(self) -> str:
        """Get current foreground application."""
        try:
            response = requests.get(f"{self._wda_url}/appium/app/state")
            if response.status_code == 200:
                return response.json().get("value", "")
        except Exception:
            pass
        return ""
    
    def is_connected(self) -> bool:
        """Check if device is connected."""
        try:
            response = requests.get(f"{self._wda_url}/status", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_apps(self) -> List[Dict[str, str]]:
        """List installed applications."""
        apps = []
        try:
            response = requests.get(f"{self._wda_url}/appium/device/installed_apps")
            if response.status_code == 200:
                for bundle_id in response.json().get("value", []):
                    apps.append({"package_name": bundle_id, "name": bundle_id})
        except Exception:
            pass
        return apps

    def double_tap(self, x: int, y: int) -> bool:
        """Double tap at pixel coordinates via WDA."""
        try:
            requests.post(f"{self._wda_url}/touch/doubleclick", json={
                "x": x, "y": y
            })
            return True
        except Exception:
            return False

    def clear_text(self) -> bool:
        """Clear text in the active input field via WDA."""
        try:
            requests.post(f"{self._wda_url}/wda/element/clear", json={})
            return True
        except Exception:
            return False

    def hide_keyboard(self) -> bool:
        """Dismiss the on-screen keyboard via WDA."""
        try:
            requests.post(f"{self._wda_url}/wda/keyboard/dismiss", json={})
            return True
        except Exception:
            return False

    def dump_ui_tree(self) -> str:
        """Get UI hierarchy from WDA /source endpoint, return raw XML."""
        try:
            response = requests.get(f"{self._wda_url}/source")
            if response.status_code == 200:
                data = response.json()
                return data.get("value", "")
            return ""
        except Exception:
            return ""

    def list_devices(self) -> List[Dict]:
        """Get device list from WDA status endpoint."""
        try:
            response = requests.get(f"{self._wda_url}/status")
            if response.status_code == 200:
                data = response.json().get("value", {})
                device_info = data.get("device", {})
                return [{"id": device_info.get("udid", "unknown"), "state": "device"}]
            return []
        except Exception:
            return []

    def _resolve_app_name(self, app_name: str) -> str | None:
        """Resolve an app display name to its iOS bundle ID."""
        from backend.app.core.config.app_packages import get_package_name_ios
        return get_package_name_ios(app_name)
