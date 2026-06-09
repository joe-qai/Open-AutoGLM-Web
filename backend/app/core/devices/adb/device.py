"""ADB device implementation."""

import re
import subprocess
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

    def force_stop_app(self, package_name: str) -> bool:
        """Force stop an application by package name."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "am", "force-stop", package_name])
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

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
