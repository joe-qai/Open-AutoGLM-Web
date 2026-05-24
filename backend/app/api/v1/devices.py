"""Device management API."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.device import DeviceInfo, DeviceStatus, PlatformType, TcpIpConnectRequest, WirelessConnectRequest, DeviceIpResponse, ConnectionType
from app.services.device_service import DeviceService

router = APIRouter()
device_service = DeviceService()


@router.get("/")
async def list_devices(platform: PlatformType | None = None):
    """List all connected devices."""
    devices = device_service.list_devices(platform)
    return {"devices": devices}


@router.get("/{device_id}", response_model=DeviceInfo)
async def get_device(device_id: str):
    """Get device details by ID."""
    device = device_service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/{device_id}/connect")
async def connect_device(device_id: str):
    """Connect to a device."""
    result = device_service.connect_device(device_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to connect device")
    return {"status": "connected", "device_id": device_id}


@router.post("/{device_id}/disconnect")
async def disconnect_device(device_id: str):
    """Disconnect from a device."""
    device_service.disconnect_device(device_id)
    return {"status": "disconnected", "device_id": device_id}


@router.get("/{device_id}/screenshot")
async def get_screenshot(device_id: str):
    """Get screenshot from device."""
    screenshot_data = device_service.get_screenshot(device_id)
    if not screenshot_data:
        raise HTTPException(status_code=400, detail="Failed to capture screenshot")
    return {"screenshot_base64": screenshot_data}


@router.post("/{device_id}/launch/{app_name}")
async def launch_app(device_id: str, app_name: str):
    """Launch an app on the device."""
    result = device_service.launch_app(device_id, app_name)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to launch app")
    return {"status": "launched", "app_name": app_name}


@router.get("/{device_id}/apps")
async def get_installed_apps(device_id: str):
    """Get list of installed apps on device."""
    apps = device_service.get_installed_apps(device_id)
    return {"apps": apps}


@router.post("/tcpip/connect")
async def connect_tcpip(request: TcpIpConnectRequest):
    """Connect to an Android device via TCP/IP (e.g., 192.168.1.100:5555)."""
    success = device_service.connect_tcpip(request.ip_port)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to connect via TCP/IP")
    return {"status": "connected", "ip_port": request.ip_port}


@router.post("/tcpip/disconnect/{ip_port}")
async def disconnect_tcpip(ip_port: str):
    """Disconnect from an Android device connected via TCP/IP."""
    device_service.disconnect_tcpip(ip_port)
    return {"status": "disconnected", "ip_port": ip_port}


@router.get("/{device_id}/ip", response_model=DeviceIpResponse)
async def get_device_ip(device_id: str):
    """Get device IP address."""
    ip = device_service.get_device_ip(device_id)
    if not ip:
        raise HTTPException(status_code=404, detail="无法获取设备IP地址")
    return {"ip": ip, "interface": "wlan0"}


@router.post("/{device_id}/wireless")
async def enable_wireless(device_id: str, port: int = 5555):
    """Enable wireless connection for a USB device."""
    result = device_service.enable_wireless_connection(device_id, port)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result
