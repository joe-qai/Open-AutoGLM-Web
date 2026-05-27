"""HDC device implementation for HarmonyOS."""

import subprocess
from typing import Optional

from ..base_device import BaseDevice, DisplayInfo
from .connection import HDCConnection


class HDCDevice(BaseDevice):
    """HarmonyOS device controlled via HDC."""

    def __init__(self, device_id: Optional[str] = None):
        super().__init__(device_id)
        self._connection = HDCConnection(device_id)
        self._display_info: Optional[DisplayInfo] = None

    def get_screenshot(self, timeout: int = 10) -> bytes:
        """Capture screenshot via HDC."""
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "snapshot", "-d"])
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except Exception:
            pass
        return b""

    def get_current_app(self) -> str:
        """Get current foreground app package name."""
        return ""

    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "uitest", "click", str(x), str(y)])
        subprocess.run(cmd, capture_output=True, timeout=10)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
              duration_ms: int | None = None) -> None:
        """Swipe from start to end."""
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "uitest", "swipe", str(start_x), str(start_y), str(end_x), str(end_y)])
        if duration_ms:
            cmd.append(str(duration_ms))
        subprocess.run(cmd, capture_output=True, timeout=10)

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at coordinates."""
        self.swipe(x, y, x, y, duration_ms)

    def type_text(self, text: str) -> None:
        """Type text."""
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "uitest", "input", text])
        subprocess.run(cmd, capture_output=True, timeout=10)

    def press_key(self, key: str) -> None:
        """Press hardware key."""
        pass

    def launch_app(self, app_name: str) -> bool:
        """Launch application."""
        return False

    def back(self) -> None:
        """Press back button."""
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "uitest", "press", "BACK"])
        subprocess.run(cmd, capture_output=True, timeout=10)

    def home(self) -> None:
        """Press home button."""
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["shell", "uitest", "press", "HOME"])
        subprocess.run(cmd, capture_output=True, timeout=10)

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._connection.is_connected()

    def get_display_info(self) -> DisplayInfo:
        """Get display information."""
        if self._display_info is None:
            self._display_info = DisplayInfo(
                width=1080,
                height=1920,
                density=320,
                status_bar_height=48,
                navigation_bar_height=0
            )
        return self._display_info
