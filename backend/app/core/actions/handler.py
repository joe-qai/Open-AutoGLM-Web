# -*- coding: utf-8 -*-
"""Action handler for processing AI model outputs.

Ported from phone_agent.actions.handler — all imports now reference backend modules.
"""

import ast
import json
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable

from backend.app.core.config.timing import TIMING_CONFIG
from backend.app.core.adapters.base import BaseDeviceAdapter


@dataclass
class ActionResult:
    """Result of an action execution."""

    success: bool
    should_finish: bool
    message: str | None = None
    requires_confirmation: bool = False


class ActionHandler:
    """
    Handles execution of actions from AI model output.

    Args:
        device: Device adapter for executing actions.
        confirmation_callback: Optional callback for sensitive action confirmation.
        takeover_callback: Optional callback for takeover requests (login, captcha).
    """

    def __init__(
        self,
        device: BaseDeviceAdapter,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.device = device
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover

    def execute(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> ActionResult:
        """
        Execute an action from the AI model.

        Args:
            action: The action dictionary from the model.
            screen_width: Current screen width in pixels.
            screen_height: Current screen height in pixels.

        Returns:
            ActionResult indicating success and whether to finish.
        """
        action_type = action.get("_metadata")

        if action_type == "finish":
            return ActionResult(
                success=True, should_finish=True, message=action.get("message")
            )

        if action_type != "do":
            return ActionResult(
                success=False,
                should_finish=True,
                message=f"Unknown action type: {action_type}",
            )

        action_name = action.get("action")
        handler_method = self._get_handler(action_name)

        if handler_method is None:
            return ActionResult(
                success=False,
                should_finish=False,
                message=f"Unknown action: {action_name}",
            )

        try:
            return handler_method(action, screen_width, screen_height)
        except Exception as e:
            return ActionResult(
                success=False, should_finish=False, message=f"Action failed: {e}"
            )

    def _get_handler(self, action_name: str) -> Callable | None:
        """Get the handler method for an action."""
        handlers = {
            "Launch": self._handle_launch,
            "Tap": self._handle_tap,
            "Type": self._handle_type,
            "Type_Name": self._handle_type,
            "Swipe": self._handle_swipe,
            "Back": self._handle_back,
            "Home": self._handle_home,
            "Double Tap": self._handle_double_tap,
            "Long Press": self._handle_long_press,
            "Wait": self._handle_wait,
            "Take_over": self._handle_takeover,
            "Note": self._handle_note,
            "Call_API": self._handle_call_api,
            "Interact": self._handle_interact,
        }
        return handlers.get(action_name)

    def _convert_relative_to_absolute(
        self, element: list[int], screen_width: int, screen_height: int
    ) -> tuple[int, int]:
        """Convert relative coordinates (0-999) to absolute pixels."""
        x = int(element[0] / 1000 * screen_width)
        y = int(element[1] / 1000 * screen_height)
        return x, y

    def _handle_launch(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle app launch action."""
        app_name = action.get("app")
        if not app_name:
            return ActionResult(False, False, "No app name specified")

        # Resolve app name to package/bundle ID using platform-aware config
        resolved = self._resolve_app_name(app_name)
        if resolved:
            success = self.device.launch_app(resolved)
            if success:
                return ActionResult(True, False)
            # Package found but launch failed
            self.device.press_key("HOME")
            time.sleep(TIMING_CONFIG.device.default_home_delay)
            return ActionResult(
                False, False,
                f"App '{app_name}' ({resolved}) launch failed. Went to Home screen."
            )

        # App not found in supported list — go to Home screen
        self.device.press_key("HOME")
        time.sleep(TIMING_CONFIG.device.default_home_delay)
        return ActionResult(
            False, False,
            f"App '{app_name}' not in supported list. Went to Home screen. "
            f"Please find the app icon and tap it (use Tap action).",
        )

    def _resolve_app_name(self, app_name: str) -> str | None:
        """Resolve app name to package/bundle ID based on device platform."""
        from backend.app.core.config.app_packages import get_package_name_for_platform

        platform = "android"
        if hasattr(self.device, 'platform'):
            from backend.app.core.adapters.base import Platform
            if self.device.platform == Platform.HARMONYOS:
                platform = "harmonyos"
            elif self.device.platform == Platform.IOS:
                platform = "ios"

        return get_package_name_for_platform(platform, app_name)

    def _handle_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle tap action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)

        # Check for sensitive operation
        if "message" in action:
            if not self.confirmation_callback(action["message"]):
                return ActionResult(
                    success=False,
                    should_finish=True,
                    message="User cancelled sensitive operation",
                )

        self.device.click(x, y)
        return ActionResult(True, False)

    def _handle_type(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle text input action."""
        text = action.get("text", "")

        # Switch to ADB keyboard if available (Android only)
        original_ime = None
        if hasattr(self.device, 'detect_and_set_adb_keyboard'):
            original_ime = self.device.detect_and_set_adb_keyboard()
            time.sleep(TIMING_CONFIG.action.keyboard_switch_delay)

        # Clear existing text and type new text
        if hasattr(self.device, 'clear_text'):
            self.device.clear_text()
            time.sleep(TIMING_CONFIG.action.text_clear_delay)

        self.device.type_text(text)
        time.sleep(TIMING_CONFIG.action.text_input_delay)

        # Restore original keyboard
        if original_ime and hasattr(self.device, 'restore_keyboard'):
            self.device.restore_keyboard(original_ime)
            time.sleep(TIMING_CONFIG.action.keyboard_restore_delay)

        return ActionResult(True, False)

    def _handle_swipe(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle swipe action."""
        start = action.get("start")
        end = action.get("end")

        if not start or not end:
            return ActionResult(False, False, "Missing swipe coordinates")

        start_x, start_y = self._convert_relative_to_absolute(start, width, height)
        end_x, end_y = self._convert_relative_to_absolute(end, width, height)

        self.device.swipe(start_x, start_y, end_x, end_y)
        return ActionResult(True, False)

    def _handle_back(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle back button action."""
        self.device.press_key("BACK")
        return ActionResult(True, False)

    def _handle_home(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle home button action."""
        self.device.press_key("HOME")
        return ActionResult(True, False)

    def _handle_double_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle double tap action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        if hasattr(self.device, 'double_tap'):
            self.device.double_tap(x, y)
        else:
            # Fallback: two rapid taps
            self.device.click(x, y)
            time.sleep(TIMING_CONFIG.device.double_tap_interval)
            self.device.click(x, y)
        return ActionResult(True, False)

    def _handle_long_press(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle long press action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        duration = action.get("duration", 3000)
        self.device.long_press(x, y, duration)
        return ActionResult(True, False)

    def _handle_wait(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle wait action."""
        duration_str = action.get("duration", "1 seconds")
        try:
            duration = float(duration_str.replace("seconds", "").strip())
        except ValueError:
            duration = 1.0

        time.sleep(duration)
        return ActionResult(True, False)

    def _handle_takeover(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle takeover request (login, captcha, etc.)."""
        message = action.get("message", "User intervention required")
        self.takeover_callback(message)
        return ActionResult(True, False)

    def _handle_note(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle note action (placeholder for content recording)."""
        return ActionResult(True, False)

    def _handle_call_api(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle API call action (placeholder for summarization)."""
        return ActionResult(True, False)

    def _handle_interact(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle interaction request (user choice needed)."""
        return ActionResult(True, False, message="User interaction required")

    def _send_keyevent(self, keycode: str) -> None:
        """Send a keyevent to the device."""
        from backend.app.core.adapters.base import Platform

        if hasattr(self.device, 'platform') and self.device.platform == Platform.HARMONYOS:
            hdc_prefix = ["hdc"]
            if hasattr(self.device, '_device_serial') and self.device._device_serial:
                hdc_prefix.extend(["-t", self.device._device_serial])

            if keycode == "KEYCODE_ENTER" or keycode == "66":
                subprocess.run(
                    hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "2054"],
                    capture_output=True, text=True,
                )
            elif keycode.startswith("KEYCODE_"):
                if "ENTER" in keycode:
                    subprocess.run(
                        hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "2054"],
                        capture_output=True, text=True,
                    )
                else:
                    subprocess.run(
                        hdc_prefix + ["shell", "input", "keyevent", keycode],
                        capture_output=True, text=True,
                    )
            else:
                subprocess.run(
                    hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", str(keycode)],
                    capture_output=True, text=True,
                )
        else:
            adb_prefix = ["adb"]
            device_serial = getattr(self.device, '_device_serial', None)
            if device_serial:
                adb_prefix.extend(["-s", device_serial])
            subprocess.run(
                adb_prefix + ["shell", "input", "keyevent", keycode],
                capture_output=True, text=True,
            )

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """Default confirmation callback using console input."""
        response = input(f"Sensitive operation: {message}\nConfirm? (Y/N): ")
        return response.upper() == "Y"

    @staticmethod
    def _default_takeover(message: str) -> None:
        """Default takeover callback using console input."""
        input(f"{message}\nPress Enter after completing manual operation...")


def parse_action(response: str) -> dict[str, Any]:
    """
    Parse action from model response.

    Supports two formats:
    - Python pseudo-code (AutoPhone native): do(action="Tap", element=[x,y]), finish(message="xxx")
    - JSON (generic cloud models): {"action": "Tap", "element": [x,y]}

    Args:
        response: Raw response string from the model.

    Returns:
        Parsed action dictionary with '_metadata' field.

    Raises:
        ValueError: If the response cannot be parsed.
    """
    try:
        response = response.strip()

        # --- JSON format ---
        if response.startswith("{"):
            try:
                action_dict = json.loads(response)
                if action_dict.get("action") == "finish":
                    action_dict["_metadata"] = "finish"
                else:
                    action_dict["_metadata"] = "do"
                return action_dict
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON action: {e}")

        # --- Python pseudo-code format (AutoPhone native) ---
        if response.startswith('do(action="Type"') or response.startswith(
            'do(action="Type_Name"'
        ):
            text = response.split("text=", 1)[1][1:-2]
            action = {"_metadata": "do", "action": "Type", "text": text}
            return action
        elif response.startswith("do"):
            try:
                response = response.replace('\n', '\\n')
                response = response.replace('\r', '\\r')
                response = response.replace('\t', '\\t')

                tree = ast.parse(response, mode="eval")
                if not isinstance(tree.body, ast.Call):
                    raise ValueError("Expected a function call")

                call = tree.body
                action = {"_metadata": "do"}
                for keyword in call.keywords:
                    key = keyword.arg
                    value = ast.literal_eval(keyword.value)
                    action[key] = value

                return action
            except (SyntaxError, ValueError) as e:
                raise ValueError(f"Failed to parse do() action: {e}")

        elif response.startswith("finish"):
            action = {
                "_metadata": "finish",
                "message": response.replace("finish(message=", "")[1:-2],
            }
        else:
            raise ValueError(f"Failed to parse action: {response}")
        return action
    except Exception as e:
        raise ValueError(f"Failed to parse action: {e}")


def do(**kwargs) -> dict[str, Any]:
    """Helper function for creating 'do' actions."""
    kwargs["_metadata"] = "do"
    return kwargs


def finish(**kwargs) -> dict[str, Any]:
    """Helper function for creating 'finish' actions."""
    kwargs["_metadata"] = "finish"
    return kwargs