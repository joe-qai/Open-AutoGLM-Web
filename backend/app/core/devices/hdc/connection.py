"""HDC connection management for HarmonyOS."""

import subprocess
from typing import Optional


class HDCConnection:
    """Manages HDC connection to HarmonyOS devices."""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id

    def _build_command(self, *args) -> list[str]:
        cmd = ["hdc"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    def execute(self, *args, timeout: int = 30) -> tuple[int, str, str]:
        cmd = self._build_command(*args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", "HDC not found"

    def is_connected(self) -> bool:
        _, stdout, _ = self.execute("list", "targets")
        return "device" in stdout.lower()
