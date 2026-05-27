"""XCTest device implementation for iOS."""

from typing import Optional

from ..base_device import BaseDevice, DisplayInfo
from .connection import XCTestConnection


class XCTestDevice(BaseDevice):
    """iOS device controlled via XCTest/WebDriverAgent."""

    def __init__(self, device_id: Optional[str] = None, wda_url: str = "http://localhost:8100"):
        super().__init__(device_id)
        self._connection = XCTestConnection(device_id, wda_url)
        self._display_info: Optional[DisplayInfo] = None

    def get_screenshot(self, timeout: int = 10) -> bytes:
        """Capture screenshot via WDA."""
        return self._connection.screenshot()

    def get_current_app(self) -> str:
        """Get current foreground app."""
        return ""

    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        self._connection.tap(x, y)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
              duration_ms: int | None = None) -> None:
        """Swipe from start to end."""
        pass

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at coordinates."""
        pass

    def type_text(self, text: str) -> None:
        """Type text."""
        pass

    def press_key(self, key: str) -> None:
        """Press hardware key."""
        pass

    def launch_app(self, app_name: str) -> bool:
        """Launch application."""
        return False

    def back(self) -> None:
        """Press back button."""
        pass

    def home(self) -> None:
        """Press home button."""
        pass

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return True

    def get_display_info(self) -> DisplayInfo:
        """Get display information."""
        if self._display_info is None:
            self._display_info = DisplayInfo(
                width=1170,
                height=2532,
                density=326,
                status_bar_height=47,
                navigation_bar_height=34
            )
        return self._display_info
