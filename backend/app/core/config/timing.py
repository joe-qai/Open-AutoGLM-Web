# -*- coding: utf-8 -*-
"""Timing configuration for action handlers.

This module defines all configurable waiting times used throughout the action
execution pipeline. Users can customize these values by setting environment
variables prefixed with PHONE_AGENT_.
"""

import os
from dataclasses import dataclass


@dataclass
class ActionTimingConfig:
    """Configuration for action handler timing delays."""

    # Text input related delays (in seconds)
    keyboard_switch_delay: float = 1.0  # Delay after switching to ADB keyboard
    text_clear_delay: float = 1.0  # Delay after clearing text
    text_input_delay: float = 1.0  # Delay after typing text
    keyboard_restore_delay: float = 1.0  # Delay after restoring original keyboard

    def __post_init__(self):
        """Load values from environment variables if present."""
        self.keyboard_switch_delay = float(
            os.getenv("PHONE_AGENT_KEYBOARD_SWITCH_DELAY", self.keyboard_switch_delay)
        )
        self.text_clear_delay = float(
            os.getenv("PHONE_AGENT_TEXT_CLEAR_DELAY", self.text_clear_delay)
        )
        self.text_input_delay = float(
            os.getenv("PHONE_AGENT_TEXT_INPUT_DELAY", self.text_input_delay)
        )
        self.keyboard_restore_delay = float(
            os.getenv("PHONE_AGENT_KEYBOARD_RESTORE_DELAY", self.keyboard_restore_delay)
        )


@dataclass
class DeviceTimingConfig:
    """Configuration for device operation timing delays."""

    # Default delays for various device operations (in seconds)
    default_tap_delay: float = 1.0  # Default delay after tap
    default_double_tap_delay: float = 1.0  # Default delay after double tap
    double_tap_interval: float = 0.1  # Interval between two taps in double tap
    default_long_press_delay: float = 1.0  # Default delay after long press
    default_swipe_delay: float = 1.0  # Default delay after swipe
    default_back_delay: float = 1.0  # Default delay after back button
    default_home_delay: float = 1.0  # Default delay after home button
    default_launch_delay: float = 1.0  # Default delay after launching app

    def __post_init__(self):
        """Load values from environment variables if present."""
        self.default_tap_delay = float(
            os.getenv("PHONE_AGENT_TAP_DELAY", self.default_tap_delay)
        )
        self.default_double_tap_delay = float(
            os.getenv("PHONE_AGENT_DOUBLE_TAP_DELAY", self.default_double_tap_delay)
        )
        self.double_tap_interval = float(
            os.getenv("PHONE_AGENT_DOUBLE_TAP_INTERVAL", self.double_tap_interval)
        )
        self.default_long_press_delay = float(
            os.getenv("PHONE_AGENT_LONG_PRESS_DELAY", self.default_long_press_delay)
        )
        self.default_swipe_delay = float(
            os.getenv("PHONE_AGENT_SWEEP_DELAY", self.default_swipe_delay)
        )
        self.default_back_delay = float(
            os.getenv("PHONE_AGENT_BACK_DELAY", self.default_back_delay)
        )
        self.default_home_delay = float(
            os.getenv("PHONE_AGENT_HOME_DELAY", self.default_home_delay)
        )
        self.default_launch_delay = float(
            os.getenv("PHONE_AGENT_LAUNCH_DELAY", self.default_launch_delay)
        )


@dataclass
class ConnectionTimingConfig:
    """Configuration for ADB/HDC connection timing delays."""

    # Server and connection delays (in seconds)
    adb_restart_delay: float = 2.0  # Wait time after enabling TCP/IP mode
    server_restart_delay: float = 1.0  # Wait time between killing and starting server

    def __post_init__(self):
        """Load values from environment variables if present."""
        self.adb_restart_delay = float(
            os.getenv("PHONE_AGENT_ADB_RESTART_DELAY", self.adb_restart_delay)
        )
        self.server_restart_delay = float(
            os.getenv("PHONE_AGENT_SERVER_RESTART_DELAY", self.server_restart_delay)
        )


@dataclass
class TimingConfig:
    """Master timing configuration combining all timing settings."""

    action: ActionTimingConfig
    device: DeviceTimingConfig
    connection: ConnectionTimingConfig

    def __init__(self):
        """Initialize all timing configurations."""
        self.action = ActionTimingConfig()
        self.device = DeviceTimingConfig()
        self.connection = ConnectionTimingConfig()


# Global timing configuration instance
TIMING_CONFIG = TimingConfig()


def get_timing_config() -> TimingConfig:
    """
    Get the global timing configuration.

    Returns:
        The global TimingConfig instance.
    """
    return TIMING_CONFIG


def update_timing_config(
    action: ActionTimingConfig | None = None,
    device: DeviceTimingConfig | None = None,
    connection: ConnectionTimingConfig | None = None,
) -> None:
    """
    Update the global timing configuration.

    Args:
        action: New action timing configuration.
        device: New device timing configuration.
        connection: New connection timing configuration.
    """
    global TIMING_CONFIG
    if action is not None:
        TIMING_CONFIG.action = action
    if device is not None:
        TIMING_CONFIG.device = device
    if connection is not None:
        TIMING_CONFIG.connection = connection


__all__ = [
    "ActionTimingConfig",
    "DeviceTimingConfig",
    "ConnectionTimingConfig",
    "TimingConfig",
    "TIMING_CONFIG",
    "get_timing_config",
    "update_timing_config",
]
