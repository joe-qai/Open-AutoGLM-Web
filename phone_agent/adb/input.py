"""Input utilities for Android device text input."""

import base64
import os
import subprocess
from typing import Optional


def type_text(text: str, device_id: str | None = None) -> None:
    """
    Type text into the currently focused input field using ADB Keyboard.

    Args:
        text: The text to type.
        device_id: Optional ADB device ID for multi-device setups.

    Note:
        Requires ADB Keyboard to be installed on the device.
        See: https://github.com/nicnocquee/AdbKeyboard
    """
    adb_prefix = _get_adb_prefix(device_id)
    encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "am",
            "broadcast",
            "-a",
            "ADB_INPUT_B64",
            "--es",
            "msg",
            encoded_text,
        ],
        capture_output=True,
        text=True,
    )


def clear_text(device_id: str | None = None) -> None:
    """
    Clear text in the currently focused input field.

    Args:
        device_id: Optional ADB device ID for multi-device setups.
    """
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"],
        capture_output=True,
        text=True,
    )


def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    """
    Detect current keyboard and switch to ADB Keyboard if needed.

    Args:
        device_id: Optional ADB device ID for multi-device setups.

    Returns:
        The original keyboard IME identifier for later restoration.
    """
    adb_prefix = _get_adb_prefix(device_id)

    # Get current IME
    result = subprocess.run(
        adb_prefix + ["shell", "settings", "get", "secure", "default_input_method"],
        capture_output=True,
        text=True,
    )
    current_ime = (result.stdout + result.stderr).strip()

    # Switch to ADB Keyboard if not already set
    if "com.android.adbkeyboard/.AdbIME" not in current_ime:
        subprocess.run(
            adb_prefix + ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
            capture_output=True,
            text=True,
        )

    # Warm up the keyboard
    type_text("", device_id)

    return current_ime


def restore_keyboard(ime: str, device_id: str | None = None) -> None:
    """
    Restore the original keyboard IME.

    Args:
        ime: The IME identifier to restore.
        device_id: Optional ADB device ID for multi-device setups.
    """
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "ime", "set", ime], capture_output=True, text=True
    )


def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]


def install_adb_keyboard(device_id: str | None = None) -> tuple[bool, str]:
    """
    Install and enable ADB Keyboard on the connected device.

    Downloads the bundled ADBKeyboard.apk from the resources directory,
    installs it via adb, enables it as an input method, and verifies
    the installation.

    Args:
        device_id: Optional ADB device ID for multi-device setups.

    Returns:
        Tuple of (success, message).
    """
    # Find the bundled APK
    apk_path = _find_apk_path()
    if not apk_path:
        return False, "ADBKeyboard.apk not found in resources directory"

    adb_prefix = _get_adb_prefix(device_id)

    # Step 1: Install the APK
    print("📦 Installing ADB Keyboard...", end=" ")
    result = subprocess.run(
        adb_prefix + ["install", "-r", apk_path],  # -r for reinstall/overwrite
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr

    if "Success" in output:
        print("✅ APK installed")
    else:
        # Check if already installed
        if "already exists" in output or "INSTALL_FAILED_ALREADY_EXISTS" in output:
            print("✅ Already installed, updating...")
        else:
            print("❌ FAILED")
            return False, f"APK installation failed: {output.strip()}"

    # Step 2: Enable the input method
    print("🔧 Enabling ADB Keyboard...", end=" ")
    result = subprocess.run(
        adb_prefix + ["shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    print("✅ Enabled")

    # Step 3: Set as default input method (optional — we'll switch at runtime)
    # Don't set as permanent default, just make it available for detect_and_set_adb_keyboard

    # Step 4: Verify installation
    print("🔍 Verifying installation...", end=" ")
    result = subprocess.run(
        adb_prefix + ["shell", "ime", "list", "-s"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    ime_list = result.stdout.strip()

    if "com.android.adbkeyboard/.AdbIME" in ime_list:
        print("✅ ADB Keyboard is ready!")
        return True, "ADB Keyboard installed and enabled successfully"
    else:
        print("❌ FAILED")
        return False, "ADB Keyboard was installed but not detected in IME list. Please enable it manually in Settings > Input Method"


def _find_apk_path() -> str | None:
    """
    Find the bundled ADBKeyboard.apk file.

    Searches in the resources/ directory relative to the package root.

    Returns:
        Absolute path to the APK file, or None if not found.
    """
    # Try relative to the package directory
    package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    apk_path = os.path.join(package_dir, "resources", "ADBKeyboard.apk")

    if os.path.exists(apk_path):
        return apk_path

    # Try relative to the current working directory
    apk_path = os.path.join("resources", "ADBKeyboard.apk")
    if os.path.exists(apk_path):
        return os.path.abspath(apk_path)

    return None
# -*- coding: utf-8 -*-