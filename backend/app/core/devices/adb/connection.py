"""ADB connection management."""

import subprocess
import re
from typing import Optional


class ADBConnection:
    """Manages ADB connection to Android devices."""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id

    def _build_command(self, *args) -> list[str]:
        """Build ADB command with device targeting."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    def execute(self, *args, timeout: int = 30) -> tuple[int, str, str]:
        """Execute ADB command and return (returncode, stdout, stderr)."""
        cmd = self._build_command(*args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", "ADB not found"

    def get_state(self) -> str:
        """Get device state."""
        _, stdout, _ = self.execute("get-state")
        return stdout

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.get_state() == "device"

    def list_devices(self) -> list[str]:
        """List all connected devices."""
        _, stdout, _ = self.execute("devices")
        devices = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def get_property(self, property_name: str) -> str:
        """Get device property via getprop."""
        _, stdout, _ = self.execute("shell", "getprop", property_name)
        return stdout

    def get_model(self) -> str:
        """Get device model name."""
        return self.get_property("ro.product.model")

    def get_screen_size(self) -> tuple[int, int]:
        """Get screen size as (width, height)."""
        _, stdout, _ = self.execute("shell", "wm", "size")
        match = re.search(r"(\d+)x(\d+)", stdout)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 1080, 1920

    def get_screen_density(self) -> int:
        """Get screen density."""
        _, stdout, _ = self.execute("shell", "wm", "density")
        match = re.search(r"(\d+)", stdout)
        if match:
            return int(match.group(1))
        return 320
