"""Action layer for the Agent architecture."""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..adapters.base import BaseDeviceAdapter, UIElement
from .decision import ActionPlan

try:
    from ..config.app_packages import get_package_name
except ImportError:
    def get_package_name(app_name: str):
        return app_name if '.' in app_name else None


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool
    action: str
    message: str = ""
    error: Optional[str] = None


class ActionLayer:
    """Action layer - executes actions on device."""

    def __init__(self, adapter: BaseDeviceAdapter):
        self.adapter = adapter

    def execute(self, plan: ActionPlan) -> ActionResult:
        """Execute an action plan."""
        try:
            action_method = getattr(self, f"_action_{plan.action.lower()}", None)
            if action_method:
                result = action_method(plan)
                return result
            else:
                return ActionResult(
                    success=False,
                    action=plan.action,
                    error=f"Unknown action: {plan.action}"
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action=plan.action,
                error=str(e)
            )

    def _action_tap_element(self, plan: ActionPlan) -> ActionResult:
        """Tap on an element."""
        parameters = plan.parameters

        if parameters.get("element_index") is not None:
            element_idx = parameters["element_index"]
            from .perception import PerceptionLayer
            perception = PerceptionLayer(self.adapter)
            perception_data = perception.perceive_lightweight()
            elements = perception_data.get("ui_elements", [])

            if 0 <= element_idx < len(elements):
                element = elements[element_idx]
                bbox = element.get("bbox_normalized", {})
                x = bbox.get("x", 0) + bbox.get("w", 0) / 2
                y = bbox.get("y", 0) + bbox.get("h", 0) / 2
                px, py = self.adapter.display_info.denormalize_coord(x, y)
                self.adapter.click(px, py)
                return ActionResult(
                    success=True,
                    action="tap_element",
                    message=f"点击元素 [{element_idx}]: {element.get('text', '')}"
                )
            else:
                return ActionResult(
                    success=False,
                    action="tap_element",
                    error=f"元素索引 {element_idx} 超出范围"
                )

        elif parameters.get("description") is not None:
            desc = parameters["description"].lower()
            from .perception import PerceptionLayer
            perception = PerceptionLayer(self.adapter)
            perception_data = perception.perceive_lightweight()
            elements = perception_data.get("ui_elements", [])

            for element in elements:
                if element.get("clickable", False):
                    text = str(element.get("text", "")).lower()
                    content_desc = str(element.get("content_desc", "")).lower()
                    if desc in text or desc in content_desc:
                        bbox = element.get("bbox_normalized", {})
                        x = bbox.get("x", 0) + bbox.get("w", 0) / 2
                        y = bbox.get("y", 0) + bbox.get("h", 0) / 2
                        px, py = self.adapter.display_info.denormalize_coord(x, y)
                        self.adapter.click(px, py)
                        return ActionResult(
                            success=True,
                            action="tap_element",
                            message=f"点击元素: {element.get('text', '')}"
                        )

            return ActionResult(
                success=False,
                action="tap_element",
                error=f"未找到匹配描述的元素: {desc}"
            )

        elif parameters.get("x") is not None and parameters.get("y") is not None:
            x, y = parameters["x"], parameters["y"]
            px, py = self.adapter.display_info.denormalize_coord(x, y)
            self.adapter.click(px, py)
            return ActionResult(
                success=True,
                action="tap_element",
                message=f"Tapped at ({x}, {y}) normalized"
            )

        return ActionResult(
            success=False,
            action="tap_element",
            error="No valid target specified"
        )

    def _action_type_text(self, plan: ActionPlan) -> ActionResult:
        """Type text into input field."""
        text = plan.parameters.get("text", "")
        if text:
            self.adapter.type_text(text)
            return ActionResult(
                success=True,
                action="type_text",
                message=f"Typed: {text}"
            )
        return ActionResult(
            success=False,
            action="type_text",
            error="No text provided"
        )

    def _action_swipe(self, plan: ActionPlan) -> ActionResult:
        """Swipe on screen."""
        params = plan.parameters

        direction = params.get("direction", "down").lower()
        x1, y1, x2, y2 = 500, 800, 500, 200

        if direction == "up":
            x1, y1, x2, y2 = 500, 800, 500, 200
        elif direction == "down":
            x1, y1, x2, y2 = 500, 200, 500, 800
        elif direction == "left":
            x1, y1, x2, y2 = 800, 500, 200, 500
        elif direction == "right":
            x1, y1, x2, y2 = 200, 500, 800, 500

        if params.get("x1") is not None:
            x1 = params.get("x1", 500)
        if params.get("y1") is not None:
            y1 = params.get("y1", 500)
        if params.get("x2") is not None:
            x2 = params.get("x2", 500)
        if params.get("y2") is not None:
            y2 = params.get("y2", 500)

        px1, py1 = self.adapter.display_info.denormalize_coord(x1, y1)
        px2, py2 = self.adapter.display_info.denormalize_coord(x2, y2)

        self.adapter.swipe(px1, py1, px2, py2)
        return ActionResult(
            success=True,
            action="swipe",
            message=f"Swipe from ({x1},{y1}) to ({x2},{y2})"
        )

    def _action_long_press(self, plan: ActionPlan) -> ActionResult:
        """Long press on screen."""
        params = plan.parameters
        x, y = params.get("x", 500), params.get("y", 500)
        duration = params.get("duration", 800)

        px, py = self.adapter.display_info.denormalize_coord(x, y)
        self.adapter.long_press(px, py, duration)
        return ActionResult(
            success=True,
            action="long_press",
            message=f"Long pressed at ({x},{y}) for {duration}ms"
        )

    def _action_back(self, plan: ActionPlan) -> ActionResult:
        """Press back button."""
        self.adapter.press_key("BACK")
        return ActionResult(
            success=True,
            action="back",
            message="Pressed back"
        )

    def _action_home(self, plan: ActionPlan) -> ActionResult:
        """Press home button."""
        self.adapter.press_key("HOME")
        return ActionResult(
            success=True,
            action="home",
            message="Pressed home"
        )

    def _action_launch_app(self, plan: ActionPlan) -> ActionResult:
        """Launch an application."""
        app_name = plan.parameters.get("app_name", "")
        if not app_name:
            return ActionResult(
                success=False,
                action="launch_app",
                error="No app name provided"
            )

        package_name = get_package_name(app_name)
        if package_name:
            self.adapter.launch_app(package_name)
            return ActionResult(
                success=True,
                action="launch_app",
                message=f"Launched app: {app_name} ({package_name})"
            )
        else:
            self.adapter.launch_app(app_name)
            return ActionResult(
                success=True,
                action="launch_app",
                message=f"Launched app: {app_name}"
            )

    def _action_wait(self, plan: ActionPlan) -> ActionResult:
        """Wait for specified duration."""
        import time
        duration = plan.parameters.get("duration", 1000)
        time.sleep(duration / 1000)
        return ActionResult(
            success=True,
            action="wait",
            message=f"Waited {duration}ms"
        )

    def _action_finish(self, plan: ActionPlan) -> ActionResult:
        """Mark task as finished."""
        message = plan.parameters.get("message", "Task completed")
        return ActionResult(
            success=True,
            action="finish",
            message=message
        )
