"""Device adapter factory."""

from typing import Optional
from .base import BaseDeviceAdapter, Platform
from .android import AndroidAdapter
from .ios import IOSAdapter
from .harmonyos import HarmonyOSAdapter


class DeviceAdapterFactory:
    """Factory class for creating device adapters."""
    
    @staticmethod
    def create_adapter(
        platform: Platform,
        device_serial: Optional[str] = None,
        **kwargs
    ) -> BaseDeviceAdapter:
        """Create a device adapter based on platform."""
        
        if platform == Platform.ANDROID:
            return AndroidAdapter(
                adb_path=kwargs.get("adb_path", "adb"),
                device_serial=device_serial
            )
        
        elif platform == Platform.IOS:
            return IOSAdapter(
                wda_url=kwargs.get("wda_url", "http://localhost:8100")
            )
        
        elif platform == Platform.HARMONYOS:
            return HarmonyOSAdapter(
                hdc_path=kwargs.get("hdc_path", "hdc"),
                device_serial=device_serial
            )
        
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    @staticmethod
    def create_adapter_by_name(
        platform_name: str,
        device_serial: Optional[str] = None,
        **kwargs
    ) -> BaseDeviceAdapter:
        """Create a device adapter by platform name string."""
        
        platform_map = {
            "android": Platform.ANDROID,
            "ios": Platform.IOS,
            "harmonyos": Platform.HARMONYOS,
            "harmony": Platform.HARMONYOS,
        }
        
        platform = platform_map.get(platform_name.lower())
        if not platform:
            raise ValueError(f"Unsupported platform: {platform_name}")
        
        return DeviceAdapterFactory.create_adapter(platform, device_serial, **kwargs)
    
    @staticmethod
    def list_supported_platforms() -> list[str]:
        """List all supported platforms."""
        return [p.value for p in Platform]
