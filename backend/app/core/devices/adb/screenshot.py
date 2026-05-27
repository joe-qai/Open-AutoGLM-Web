"""Screenshot capture via ADB."""

import subprocess
from typing import Optional


def get_screenshot(device_id: Optional[str] = None, timeout: int = 10) -> bytes:
    """
    Capture screenshot from Android device via ADB.

    Returns:
        PNG image data as bytes.
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["exec-out", "screenshot"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        raise RuntimeError(f"Screenshot failed: returncode={result.returncode}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Screenshot timed out")
    except FileNotFoundError:
        raise RuntimeError("ADB not found")
