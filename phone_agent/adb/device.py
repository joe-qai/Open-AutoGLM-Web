"""Device control utilities for Android automation using uiautomator2."""

import time
from typing import Optional

import uiautomator2 as u2

from phone_agent.config.apps import APP_PACKAGES
from phone_agent.config.timing import TIMING_CONFIG

# Global device instance cache
_device_cache = {}


def _get_device(device_id: str | None = None) -> u2.Device:
    """Get uiautomator2 device instance."""
    key = device_id or "default"
    
    if key not in _device_cache:
        if device_id:
            _device_cache[key] = u2.connect(device_id)
        else:
            _device_cache[key] = u2.connect()
    
    return _device_cache[key]


def get_current_app(device_id: str | None = None) -> str:
    """
    Get the currently focused app name.

    Args:
        device_id: Optional device ID for multi-device setups.

    Returns:
        The app name if recognized, otherwise "System Home".
    """
    try:
        d = _get_device(device_id)
        info = d.app_current()
        
        if info and "package" in info:
            package = info["package"]
            for app_name, pkg in APP_PACKAGES.items():
                if pkg == package:
                    return app_name
        
        return "System Home"
    
    except Exception as e:
        # Fallback to ADB command if uiautomator2 fails
        import subprocess
        
        adb_prefix = ["adb"]
        if device_id:
            adb_prefix.extend(["-s", device_id])
        
        result = subprocess.run(
            adb_prefix + ["shell", "dumpsys", "window"], 
            capture_output=True, 
            text=True, 
            encoding="utf-8"
        )
        output = result.stdout
        if output:
            for line in output.split("\n"):
                if "mCurrentFocus" in line or "mFocusedApp" in line:
                    for app_name, package in APP_PACKAGES.items():
                        if package in line:
                            return app_name
        
        return "System Home"


def tap(
    x: int, y: int, device_id: str | None = None, delay: float | None = None
) -> None:
    """
    Tap at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        device_id: Optional device ID.
        delay: Delay in seconds after tap. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_tap_delay

    d = _get_device(device_id)
    d.click(x, y)
    time.sleep(delay)


def double_tap(
    x: int, y: int, device_id: str | None = None, delay: float | None = None
) -> None:
    """
    Double tap at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        device_id: Optional device ID.
        delay: Delay in seconds after double tap. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_double_tap_delay

    d = _get_device(device_id)
    d.double_click(x, y)
    time.sleep(delay)


def long_press(
    x: int,
    y: int,
    duration_ms: int = 3000,
    device_id: str | None = None,
    delay: float | None = None,
) -> None:
    """
    Long press at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        duration_ms: Duration of press in milliseconds.
        device_id: Optional device ID.
        delay: Delay in seconds after long press. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_long_press_delay

    d = _get_device(device_id)
    d.long_click(x, y, duration_ms / 1000)
    time.sleep(delay)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int | None = None,
    device_id: str | None = None,
    delay: float | None = None,
) -> None:
    """
    Swipe from start to end coordinates.

    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        duration_ms: Duration of swipe in milliseconds (auto-calculated if None).
        device_id: Optional device ID.
        delay: Delay in seconds after swipe. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_swipe_delay

    if duration_ms is None:
        # Calculate duration based on distance
        dist_sq = (start_x - end_x) ** 2 + (start_y - end_y) ** 2
        duration_ms = int(dist_sq / 1000)
        duration_ms = max(100, min(duration_ms, 2000))  # Clamp between 100-2000ms

    d = _get_device(device_id)
    d.swipe(start_x, start_y, end_x, end_y, duration_ms / 1000)
    time.sleep(delay)


def back(device_id: str | None = None, delay: float | None = None) -> None:
    """
    Press the back button.

    Args:
        device_id: Optional device ID.
        delay: Delay in seconds after pressing back. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_back_delay

    d = _get_device(device_id)
    d.press("back")
    time.sleep(delay)


def home(device_id: str | None = None, delay: float | None = None) -> None:
    """
    Press the home button.

    Args:
        device_id: Optional device ID.
        delay: Delay in seconds after pressing home. If None, uses configured default.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_home_delay

    d = _get_device(device_id)
    d.press("home")
    time.sleep(delay)


def launch_app(
    app_name: str, device_id: str | None = None, delay: float | None = None
) -> bool:
    """
    Launch an app by name.

    Args:
        app_name: The app name (must be in APP_PACKAGES).
        device_id: Optional device ID.
        delay: Delay in seconds after launching. If None, uses configured default.

    Returns:
        True if app was launched, False if app not found.
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_launch_delay

    if app_name not in APP_PACKAGES:
        return False

    d = _get_device(device_id)
    package = APP_PACKAGES[app_name]
    
    try:
        d.app_start(package)
        time.sleep(delay)
        return True
    except Exception:
        return False


def list_installed_apps(device_id: str | None = None) -> list:
    """
    List all installed apps on the device.

    Args:
        device_id: Optional device ID.

    Returns:
        List of app package names.
    """
    d = _get_device(device_id)
    return d.app_list()


def get_device_info(device_id: str | None = None) -> dict:
    """
    Get device information.

    Args:
        device_id: Optional device ID.

    Returns:
        Dictionary containing device info.
    """
    d = _get_device(device_id)
    return d.info


def screen_on(device_id: str | None = None) -> None:
    """
    Turn the screen on.

    Args:
        device_id: Optional device ID.
    """
    d = _get_device(device_id)
    d.screen_on()


def screen_off(device_id: str | None = None) -> None:
    """
    Turn the screen off.

    Args:
        device_id: Optional device ID.
    """
    d = _get_device(device_id)
    d.screen_off()


def unlock(device_id: str | None = None) -> None:
    """
    Unlock the device screen.

    Args:
        device_id: Optional device ID.
    """
    d = _get_device(device_id)
    d.unlock()
