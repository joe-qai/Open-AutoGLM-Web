"""Base device adapter interface."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import base64
import tempfile
import os


class Platform(Enum):
    """Supported platforms."""
    ANDROID = "android"
    IOS = "ios"
    HARMONYOS = "harmonyos"


@dataclass
class DisplayInfo:
    """Device display information."""
    width: int
    height: int
    density: float
    status_bar_height: int
    navigation_bar_height: int
    
    def normalize_coord(self, x: int, y: int) -> tuple[float, float]:
        """Convert pixel coordinates to normalized (0-1000) coordinates."""
        return (x / self.width * 1000, y / self.height * 1000)
    
    def denormalize_coord(self, nx: float, ny: float) -> tuple[int, int]:
        """Convert normalized coordinates to pixel coordinates."""
        return (int(nx / 1000 * self.width), int(ny / 1000 * self.height))


@dataclass
class UIElement:
    """UI element information."""
    index: int
    bbox_normalized: Dict[str, float]
    bbox_pixel: Optional[Dict[str, int]] = None
    resource_id: Optional[str] = None
    text: Optional[str] = None
    content_desc: Optional[str] = None
    class_name: Optional[str] = None
    package_name: Optional[str] = None
    clickable: bool = False
    enabled: bool = True
    
    def center(self) -> tuple[float, float]:
        """Get center coordinates in normalized format."""
        return (
            self.bbox_normalized["x"] + self.bbox_normalized["w"] / 2,
            self.bbox_normalized["y"] + self.bbox_normalized["h"] / 2,
        )


class BaseDeviceAdapter(ABC):
    """Abstract base class for device adapters."""
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Get the platform type."""
        pass
    
    @property
    @abstractmethod
    def device_id(self) -> str:
        """Get the device identifier."""
        pass
    
    @property
    @abstractmethod
    def display_info(self) -> DisplayInfo:
        """Get display information."""
        pass
    
    @abstractmethod
    def get_screenshot(self, save_path: str) -> bool:
        """Capture screenshot and save to path."""
        pass
    
    def get_screenshot_base64(self) -> str:
        """Capture screenshot and return as base64 encoded string."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            save_path = f.name
        try:
            self.get_screenshot(save_path)
            with open(save_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return data
        finally:
            os.unlink(save_path)
    
    @abstractmethod
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        """Get UI element tree from current screen."""
        pass
    
    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        """Click at pixel coordinates."""
        pass
    
    def click_element(self, element: UIElement) -> bool:
        """Click on a UI element."""
        cx, cy = element.center()
        px, py = self.display_info.denormalize_coord(cx, cy)
        return self.click(px, py)
    
    @abstractmethod
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        """Long press at pixel coordinates."""
        pass
    
    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """Swipe from (x1, y1) to (x2, y2)."""
        pass
    
    @abstractmethod
    def type_text(self, text: str) -> bool:
        """Type text into active input field."""
        pass
    
    @abstractmethod
    def press_key(self, key: str) -> bool:
        """Press a hardware key."""
        pass
    
    @abstractmethod
    def launch_app(self, package_name: str) -> bool:
        """Launch an application."""
        pass
    
    @abstractmethod
    def get_current_app(self) -> str:
        """Get current foreground application package name."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if device is connected."""
        pass
    
    @abstractmethod
    def list_apps(self) -> List[Dict[str, str]]:
        """List installed applications."""
        pass
