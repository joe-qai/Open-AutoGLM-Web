# -*- coding: utf-8 -*-
"""iOS PhoneAgent class for orchestrating iOS phone automation via backend adapters.

Ported from phone_agent.agent_ios -- uses backend IOSAdapter and IOSActionHandler
instead of phone_agent.xctest directly.
"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from backend.app.core.actions.handler_ios import IOSActionHandler
from backend.app.core.adapters.ios import IOSAdapter
from backend.app.core.model.client import ModelClient, ModelConfig, MessageBuilder
from backend.app.core.config.app_packages import get_package_name_ios
from backend.app.core.config.i18n import get_messages, get_message
from backend.app.core.actions.handler import do, finish, parse_action



@dataclass
class IOSAgentConfig:
    """Configuration for the iOS PhoneAgent."""

    max_steps: int = 100
    wda_url: str = "http://localhost:8100"
    session_id: str | None = None
    device_id: str | None = None  # iOS device UDID
    lang: str = "cn"
    format: str = "pseudo"  # Output format
    system_prompt: str | None = None
    verbose: bool = True

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang, self.format)


@dataclass
class StepResult:
    """Result of a single agent step."""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None


class IOSPhoneAgent:
    """
    AI-powered agent for automating iOS phone interactions.

    The agent uses a vision-language model to understand screen content
    and decide on actions to complete user tasks via WebDriverAgent,
    using the backend IOSAdapter for device communication.

    Args:
        device: IOSAdapter instance for device operations.
        model_config: Configuration for the AI model.
        agent_config: Configuration for the iOS agent behavior.
        confirmation_callback: Optional callback for sensitive action confirmation.
        takeover_callback: Optional callback for takeover requests.
    """

    def __init__(
        self,
        device: IOSAdapter,
        model_config: ModelConfig | None = None,
        agent_config: IOSAgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.device = device
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or IOSAgentConfig()

        # Sync WDA URL from device if agent_config does not specify one
        if self.agent_config.wda_url == "http://localhost:8100" and hasattr(device, "_wda_url"):  # noqa: E501
            self.agent_config.wda_url = device._wda_url

        self.model_client = ModelClient(self.model_config)

        self.action_handler = IOSActionHandler(
            device=self.device,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0

    def run(self, task: str) -> str:
        """
        Run the agent to complete a task.

        Args:
            task: Natural language description of the task.

        Returns:
            Final message from the agent.
        """
        self._context = []
        self._step_count = 0

        # First step with user prompt
        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        # Continue until finished or max steps reached
        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.

        Useful for manual control or debugging.

        Args:
            task: Task description (only needed for first step).

        Returns:
            StepResult with step details.
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = []
        self._step_count = 0

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        self._step_count += 1

        # Capture current screen state via IOSAdapter
        screenshot_b64 = self.device.get_screenshot_base64()
        current_app = self.device.get_current_app()
        display = self.device.display_info
        screen_width = display.width
        screen_height = display.height

        # Build messages
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}" + "\n\n" + screen_info

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot_b64
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = "** Screen Info **\n\n" + screen_info

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot_b64
                )
            )

        # Get model response
        try:
            response = self.model_client.request(self._context)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}"
            )

        # Parse action from response
        try:
            action = parse_action(response.action)
        except ValueError:
            if self.agent_config.verbose:
                traceback.print_exc()
            action = finish(message=response.action)

        if self.agent_config.verbose:
            # Print thinking process
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print("💭 " + msgs["thinking"] + ":")
            print("-" * 50)
            print(response.thinking)
            print("-" * 50)
            print("🎯 " + msgs["action"] + ":")
            print(json.dumps(action, ensure_ascii=False, indent=2))
            print("=" * 50 + "\n")

        # Remove image from context to save space
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # Execute action
        try:
            result = self.action_handler.execute(
                action, screen_width, screen_height
            )
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            result = self.action_handler.execute(
                finish(message=str(e)), screen_width, screen_height
            )

        # Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                response.thinking + "\n<answer>" + response.action + "</answer>"
            )
        )

        # If the action failed, add a feedback message so the model knows what happened
        if not result.success and result.message:
            self._context.append(
                MessageBuilder.create_user_message(
                    text=f"[Action failed: {result.message}]"
                )
            )

        # Check if finished
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 48)
            task_msg = result.message or action.get("message", msgs["done"])
            print("🎉 " + msgs["task_completed"] + ": " + task_msg)
            print("=" * 50 + "\n")

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get the current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count
