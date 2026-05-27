#!/usr/bin/env python3
"""
Phone Agent CLI - AI-powered phone automation.

Usage:
    python main.py [OPTIONS]

Environment Variables:
    PHONE_AGENT_BASE_URL: Model API base URL (default: http://localhost:8000/v1)
    PHONE_AGENT_MODEL: Model name (default: AutoPhone-phone-9b)
    PHONE_AGENT_API_KEY: API key for model authentication (default: EMPTY)
    PHONE_AGENT_MAX_STEPS: Maximum steps per task (default: 100)
    PHONE_AGENT_DEVICE_ID: ADB device ID for multi-device setups
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from urllib.parse import urlparse

import requests
from openai import OpenAI

from backend.app.core.agent.phone_agent import PhoneAgent, AgentConfig
from backend.app.core.agent.ios_agent import IOSPhoneAgent, IOSAgentConfig
from backend.app.core.model.client import ModelConfig
from backend.app.core.adapters.factory import DeviceAdapterFactory
from backend.app.core.adapters.base import Platform
from backend.app.core.adapters.android import AndroidAdapter
from backend.app.core.adapters.harmonyos import HarmonyOSAdapter
from backend.app.core.adapters.ios import IOSAdapter
from backend.app.core.config.app_packages import (
    list_supported_apps, APP_PACKAGES_HARMONYOS, APP_PACKAGES_IOS,
    get_package_name, get_package_name_for_platform,
)

# ──────────────────────────────────────────────────────────────
# Inline connection management (replaces phone_agent ADBConnection/HDCConnection)
# ──────────────────────────────────────────────────────────────

_HDC_VERBOSE = False


def _run_hdc_command(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """Run HDC command with optional verbose output."""
    if _HDC_VERBOSE:
        print(f"[HDC] Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if _HDC_VERBOSE and result.returncode != 0:
        print(f"[HDC] Command failed with return code {result.returncode}")
        if hasattr(result, 'stderr') and result.stderr:
            print(f"[HDC] Error: {result.stderr}")
    return result


def set_hdc_verbose(verbose: bool):
    """Set HDC verbose mode globally."""
    global _HDC_VERBOSE
    _HDC_VERBOSE = verbose


def _adb_connect(address: str, timeout: int = 10) -> tuple[bool, str]:
    """Connect to a remote Android device via TCP/IP."""
    if ":" not in address:
        address = f"{address}:5555"
    try:
        result = subprocess.run(
            ["adb", "connect", address],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        if "connected" in output.lower():
            return True, f"Connected to {address}"
        elif "already connected" in output.lower():
            return True, f"Already connected to {address}"
        else:
            return False, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Connection timeout after {timeout}s"
    except Exception as e:
        return False, f"Connection error: {e}"


def _adb_disconnect(address: str | None = None) -> tuple[bool, str]:
    """Disconnect from a remote Android device."""
    try:
        cmd = ["adb", "disconnect"]
        if address:
            cmd.append(address)
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        output = result.stdout + result.stderr
        return True, output.strip() or "Disconnected"
    except Exception as e:
        return False, f"Disconnect error: {e}"


def _adb_enable_tcpip(port: int = 5555, device_id: str | None = None) -> tuple[bool, str]:
    """Enable TCP/IP debugging on a USB-connected Android device."""
    try:
        cmd = ["adb"]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["tcpip", str(port)])
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        output = result.stdout + result.stderr
        if "restarting" in output.lower() or result.returncode == 0:
            time.sleep(2)
            return True, f"TCP/IP mode enabled on port {port}"
        else:
            return False, output.strip()
    except Exception as e:
        return False, f"Error enabling TCP/IP: {e}"


def _adb_get_device_ip(device_id: str | None = None) -> str | None:
    """Get the IP address of a connected Android device."""
    try:
        cmd = ["adb"]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["shell", "ip", "route"])
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        for line in result.stdout.split("\n"):
            if "src" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "src" and i + 1 < len(parts):
                        return parts[i + 1]
        cmd2 = ["adb"]
        if device_id:
            cmd2.extend(["-s", device_id])
        cmd2.extend(["shell", "ip", "addr", "show", "wlan0"])
        result = subprocess.run(
            cmd2, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        for line in result.stdout.split("\n"):
            if "inet " in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    return parts[1].split("/")[0]
        return None
    except Exception as e:
        print(f"Error getting device IP: {e}")
        return None


def _hdc_connect(address: str, timeout: int = 10) -> tuple[bool, str]:
    """Connect to a remote HarmonyOS device via TCP/IP."""
    if ":" not in address:
        address = f"{address}:5555"
    try:
        result = _run_hdc_command(
            ["hdc", "tconn", address],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        if "Connect OK" in output or "connected" in output.lower():
            return True, f"Connected to {address}"
        elif "already connected" in output.lower():
            return True, f"Already connected to {address}"
        else:
            return False, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Connection timeout after {timeout}s"
    except Exception as e:
        return False, f"Connection error: {e}"


def _hdc_disconnect(address: str | None = None) -> tuple[bool, str]:
    """Disconnect from a remote HarmonyOS device."""
    try:
        if address is None:
            result = _run_hdc_command(
                ["hdc", "list", "targets"],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=5,
            )
            remote_devices = []
            for line in result.stdout.strip().split("\n"):
                stripped = line.strip()
                if stripped and ":" in stripped:
                    remote_devices.append(stripped)
            if not remote_devices:
                return True, "No remote devices to disconnect"
            for dev in remote_devices:
                _run_hdc_command(
                    ["hdc", "tdisconn", dev],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=5,
                )
            return True, "Disconnected all remote devices"
        cmd = ["hdc", "tdisconn", address]
        result = _run_hdc_command(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        output = result.stdout + result.stderr
        return True, output.strip() or "Disconnected"
    except Exception as e:
        return False, f"Disconnect error: {e}"


def _hdc_enable_tcpip(port: int = 5555, device_id: str | None = None) -> tuple[bool, str]:
    """Enable TCP/IP debugging on a USB-connected HarmonyOS device."""
    try:
        cmd = ["hdc"]
        if device_id:
            cmd.extend(["-t", device_id])
        cmd.extend(["tmode", "port", str(port)])
        result = _run_hdc_command(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or "success" in output.lower():
            time.sleep(2)
            return True, f"TCP/IP mode enabled on port {port}"
        else:
            return False, output.strip()
    except Exception as e:
        return False, f"Error enabling TCP/IP: {e}"


def _hdc_get_device_ip(device_id: str | None = None) -> str | None:
    """Get the IP address of a connected HarmonyOS device."""
    try:
        cmd = ["hdc"]
        if device_id:
            cmd.extend(["-t", device_id])
        cmd.extend(["shell", "ifconfig"])
        result = _run_hdc_command(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        for line in result.stdout.split("\n"):
            if "inet addr:" in line or "inet " in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if "addr:" in part:
                        ip = part.split(":")[1]
                        if not ip.startswith("127."):
                            return ip
                    elif part == "inet" and i + 1 < len(parts):
                        ip = parts[i + 1].split("/")[0]
                        if not ip.startswith("127."):
                            return ip
        return None
    except Exception as e:
        print(f"Error getting device IP: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# Inline iOS helpers (replaces phone_agent XCTestConnection)
# ──────────────────────────────────────────────────────────────

def _ios_list_devices() -> list[dict]:
    """List connected iOS devices via idevice_id + ideviceinfo."""
    try:
        result = subprocess.run(
            ["idevice_id", "-ln"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        devices = []
        for line in result.stdout.strip().split("\n"):
            udid = line.strip()
            if not udid:
                continue
            conn_type = "network" if "-" in udid and len(udid) > 40 else "usb"
            details = _ios_get_device_details(udid)
            devices.append({
                "device_id": udid,
                "connection_type": conn_type,
                "model": details.get("model"),
                "ios_version": details.get("ios_version"),
                "device_name": details.get("name"),
                "status": "connected",
            })
        return devices
    except FileNotFoundError:
        print("Error: idevice_id not found. Install libimobiledevice.")
        return []
    except Exception as e:
        print(f"Error listing devices: {e}")
        return []


def _ios_get_device_details(udid: str) -> dict[str, str]:
    """Get detailed info about a specific iOS device via ideviceinfo."""
    try:
        result = subprocess.run(
            ["ideviceinfo", "-u", udid],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        info = {}
        for line in result.stdout.split("\n"):
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.strip()
                value = value.strip()
                if key == "ProductType":
                    info["model"] = value
                elif key == "ProductVersion":
                    info["ios_version"] = value
                elif key == "DeviceName":
                    info["name"] = value
        return info
    except Exception:
        return {}


def _ios_pair_device(device_id: str | None = None) -> tuple[bool, str]:
    """Pair with an iOS device via idevicepair."""
    try:
        cmd = ["idevicepair"]
        if device_id:
            cmd.extend(["-u", device_id])
        cmd.append("pair")
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        output = result.stdout + result.stderr
        if "SUCCESS" in output or "already paired" in output.lower():
            return True, "Device paired successfully"
        else:
            return False, output.strip()
    except FileNotFoundError:
        return False, "idevicepair not found. Install libimobiledevice."
    except Exception as e:
        return False, f"Error pairing device: {e}"


def _ios_is_wda_ready(wda_url: str, timeout: int = 2) -> bool:
    """Check if WebDriverAgent is running and accessible."""
    try:
        response = requests.get(f"{wda_url}/status", timeout=timeout, verify=False)
        return response.status_code == 200
    except Exception:
        return False


def _ios_get_wda_status(wda_url: str) -> dict | None:
    """Get WebDriverAgent status information."""
    try:
        response = requests.get(f"{wda_url}/status", timeout=5, verify=False)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# Inline ADB Keyboard installer (replaces phone_agent.adb.input.install_adb_keyboard)
# ──────────────────────────────────────────────────────────────

def _find_apk_path() -> str | None:
    """Find the bundled ADBKeyboard.apk file."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    apk_path = os.path.join(project_dir, "resources", "ADBKeyboard.apk")
    if os.path.exists(apk_path):
        return apk_path
    apk_path = os.path.join("resources", "ADBKeyboard.apk")
    if os.path.exists(apk_path):
        return os.path.abspath(apk_path)
    return None


def _install_adb_keyboard(device_id: str | None = None) -> tuple[bool, str]:
    """Install and enable ADB Keyboard on the connected device."""
    apk_path = _find_apk_path()
    if not apk_path:
        return False, "ADBKeyboard.apk not found in resources directory"

    adb_prefix = ["adb"]
    if device_id:
        adb_prefix = ["adb", "-s", device_id]

    # Step 1: Install the APK
    print("Installing ADB Keyboard APK...", end=" ")
    result = subprocess.run(
        adb_prefix + ["install", "-r", apk_path],
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout + result.stderr

    if "Success" in output:
        print("APK installed")
    else:
        if "already exists" in output or "INSTALL_FAILED_ALREADY_EXISTS" in output:
            print("Already installed, updating...")
        else:
            print("FAILED")
            return False, f"APK installation failed: {output.strip()}"

    # Step 2: Enable the input method
    print("Enabling ADB Keyboard...", end=" ")
    subprocess.run(
        adb_prefix + ["shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"],
        capture_output=True, text=True, timeout=10,
    )
    print("Enabled")

    # Step 3: Verify installation
    print("Verifying installation...", end=" ")
    result = subprocess.run(
        adb_prefix + ["shell", "ime", "list", "-s"],
        capture_output=True, text=True, timeout=10,
    )
    ime_list = result.stdout.strip()

    if "com.android.adbkeyboard/.AdbIME" in ime_list:
        print("ADB Keyboard is ready!")
        return True, "ADB Keyboard installed and enabled successfully"
    else:
        print("FAILED")
        return False, "ADB Keyboard was installed but not detected in IME list. Please enable it manually in Settings > Input Method"
