"""Input operations via ADB."""

import subprocess
from typing import Optional


def tap(x: int, y: int, device_id: Optional[str] = None) -> None:
    """Tap at coordinates."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "tap", str(x), str(y)])
    subprocess.run(cmd, capture_output=True, timeout=10)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: Optional[int] = None,
    device_id: Optional[str] = None
) -> None:
    """Swipe from start to end."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "swipe",
                str(start_x), str(start_y), str(end_x), str(end_y)])
    if duration_ms:
        cmd.append(str(duration_ms))
    subprocess.run(cmd, capture_output=True, timeout=10)


def long_press(x: int, y: int, duration_ms: int = 1000,
               device_id: Optional[str] = None) -> None:
    """Long press at coordinates using swipe to same location."""
    swipe(x, y, x, y, duration_ms, device_id)


def type_text(text: str, device_id: Optional[str] = None) -> None:
    """Type text."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    escaped_text = text.replace(" ", "%s").replace("'", "\\'")
    cmd.extend(["shell", "input", "text", escaped_text])
    subprocess.run(cmd, capture_output=True, timeout=10)


def back(device_id: Optional[str] = None) -> None:
    """Press back button."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "keyevent", "KEYCODE_BACK"])
    subprocess.run(cmd, capture_output=True, timeout=10)


def home(device_id: Optional[str] = None) -> None:
    """Press home button."""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "keyevent", "KEYCODE_HOME"])
    subprocess.run(cmd, capture_output=True, timeout=10)


def press_key(key: str, device_id: Optional[str] = None) -> None:
    """Press hardware key by name."""
    key_map = {
        "back": "KEYCODE_BACK",
        "home": "KEYCODE_HOME",
        "power": "KEYCODE_POWER",
        "volume_up": "KEYCODE_VOLUME_UP",
        "volume_down": "KEYCODE_VOLUME_DOWN",
        "menu": "KEYCODE_MENU",
        "search": "KEYCODE_SEARCH",
    }
    keycode = key_map.get(key.lower(), key.upper())
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "keyevent", keycode])
    subprocess.run(cmd, capture_output=True, timeout=10)
