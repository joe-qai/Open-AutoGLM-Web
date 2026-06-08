"""PhoneAgent class for orchestrating Android/HarmonyOS phone automation.

Ported from phone_agent.agent — all imports reference backend modules.
The agent uses a vision-language model to understand screen content
and decide on actions to complete user tasks.
"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from app.core.actions.handler import ActionHandler, do, finish, parse_action
from app.core.config.i18n import get_messages, get_message
from app.core.config.prompts import get_system_prompt
from app.core.model.client import ModelClient, ModelConfig, MessageBuilder
from app.core.adapters.base import BaseDeviceAdapter


@dataclass
class AgentConfig:
    """Configuration for the PhoneAgent."""

    max_steps: int = 100
    device_id: str | None = None
    lang: str = "cn"
    format: str = "pseudo"  # 'pseudo' (AutoPhone) or 'json' (generic cloud models)
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


class PhoneAgent:
    """
    AI-powered agent for automating phone interactions.

    Uses a vision-language model to understand screen content
    and decide on actions to complete user tasks.

    Args:
        device: Device adapter (AndroidAdapter, HarmonyOSAdapter, etc.)
        model_config: Configuration for the AI model.
        agent_config: Configuration for the agent behavior.
        confirmation_callback: Optional callback for sensitive action confirmation.
        takeover_callback: Optional callback for takeover requests.
        step_callback: Optional callback for each step execution.
    """

    def __init__(
        self,
        device: BaseDeviceAdapter,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
        step_callback: Callable[[dict], None] | None = None,
    ):
        self.device = device
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device=device,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        self._step_callback = step_callback

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

        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.

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

        # Capture current screen state
        screenshot_b64 = self.device.get_screenshot_base64()
        current_app = self.device.get_current_app()
        screen_width = self.device.display_info.width
        screen_height = self.device.display_info.height

        # Build messages
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot_b64
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot_b64
                )
            )

        # Get model response
        try:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print(f"💭 {msgs['thinking']}:")
            print("-" * 50)
            response = self.model_client.request(self._context)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            
            # Provide more helpful error messages based on error type
            error_msg = str(e)
            if "Connection error" in error_msg or "WinError 10054" in error_msg:
                message = "无法连接到模型服务器，请检查：\n1. 模型服务是否正常运行\n2. 模型服务地址配置是否正确\n3. 网络连接是否正常"
            elif "timeout" in error_msg.lower():
                message = "请求模型超时，请检查：\n1. 模型服务是否响应缓慢\n2. 增加超时时间配置\n3. 网络连接是否稳定"
            elif "authentication" in error_msg.lower() or "API key" in error_msg:
                message = "模型认证失败，请检查API密钥配置是否正确"
            else:
                message = f"模型请求失败: {error_msg}"
                
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=message,
            )

        # Parse action from response
        try:
            action = parse_action(response.action)
        except ValueError as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            # Send parse error to callback
            if self._step_callback:
                try:
                    self._step_callback({
                        "step": self._step_count,
                        "event": "error",
                        "action": "parse_error",
                        "thinking": "",
                        "message": f"动作解析失败: {str(e)}, 原始响应: {response.action}",
                        "success": False,
                    })
                except Exception:
                    pass
            action = finish(message=f"动作解析失败: {str(e)}")

        if self.agent_config.verbose:
            print("-" * 50)
            print(f"🎯 {msgs['action']}:")
            print(json.dumps(action, ensure_ascii=False, indent=2))
            print("=" * 50 + "\n")

        # Send thinking phase update via callback
        if self._step_callback:
            try:
                self._step_callback({
                    "step": self._step_count,
                    "event": "think",
                    "thinking": response.thinking if hasattr(response, 'thinking') else "",
                    "proposed_action": action.get("action", ""),
                    "full_response": response.raw_content if hasattr(response, 'raw_content') else "",
                })
            except Exception:
                pass

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

        # Call step callback if provided
        if self._step_callback:
            try:
                self._step_callback({
                    "step": self._step_count,
                    "action": action.get("action", ""),
                    "thinking": response.thinking if hasattr(response, 'thinking') else "",
                    "message": result.message,
                    "success": result.success,
                })
            except Exception:
                pass

        # Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<answer>{response.action}</answer>"
            )
        )

        # If the action failed, add a feedback message
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
            print(
                f"✅ {msgs['task_completed']}: {result.message or action.get('message', msgs['done'])}"
            )
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