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
