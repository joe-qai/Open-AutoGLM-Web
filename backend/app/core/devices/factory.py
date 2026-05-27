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
    def register_device(cls, platform: Platform, device_class: Type[BaseDevice]) -> None:
        """Register a device class for a platform."""
        cls._device_classes[platform] = device_class

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
