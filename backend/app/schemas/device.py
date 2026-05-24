"""Device schemas."""

from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import Optional


class PlatformType(str, Enum):
    """Supported platforms."""
    ANDROID = "android"
    IOS = "ios"
    HARMONYOS = "harmonyos"


class DeviceStatus(str, Enum):
    """Device connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ONLINE = "online"
    OFFLINE = "offline"


class ConnectionType(str, Enum):
    """Device connection type."""
    USB = "usb"
    TCPIP = "tcpip"


class DeviceInfo(BaseModel):
    """Device information model."""
    device_id: str
    name: str
    platform: PlatformType
    status: DeviceStatus
    connection_type: ConnectionType = ConnectionType.USB
    ip: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    os_version: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    battery_level: Optional[int] = None
    device_type: Optional[str] = None
    android_sdk_version: Optional[str] = None
    last_seen: Optional[str] = None
    available_actions: Optional[list] = None
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class DeviceConnectRequest(BaseModel):
    """Request model for connecting a device."""
    device_id: str
    platform: PlatformType


class DeviceActionResponse(BaseModel):
    """Response model for device actions."""
    success: bool
    message: str
    device_id: str


class TcpIpConnectRequest(BaseModel):
    """Request model for TCP/IP connection."""
    ip_port: str


class WirelessConnectRequest(BaseModel):
    """Request model for enabling wireless connection."""
    device_id: str
    port: int = 5555


class DeviceIpResponse(BaseModel):
    """Response model for device IP address."""
    ip: Optional[str] = None
    interface: Optional[str] = None
