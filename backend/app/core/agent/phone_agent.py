"""PhoneAgent class for orchestrating Android/HarmonyOS phone automation.

Ported from phone_agent.agent — all imports reference backend modules.
The agent uses a vision-language model to understand screen content
and decide on actions to complete user tasks.

This implementation follows the ReAct (Reasoning + Acting) framework:
1. Perceive: Capture current screen state and UI elements
2. Think: Analyze state and decide next action using VLM
3. Act: Execute the action
4. Reflect: Review outcome and learn from experience
"""

import asyncio
import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from app.core.actions.handler import ActionHandler, do, finish, parse_action
from app.core.config.i18n import get_messages, get_message
from app.core.config.prompts import get_system_prompt
from app.core.model.client import ModelClient, ModelConfig, MessageBuilder, ContentModerationError
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
        self._action_history: list[dict[str, Any]] = []  # Track executed actions for deduplication

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
        self._action_history = []

    def _is_redundant_action(self, action: dict[str, Any]) -> bool:
        """Check if the action would be redundant given the current state.
        
        Uses perception-based reasoning to detect:
        1. Direct action duplicates (same action type + same target) that failed before
        2. Actions that won't change the current state based on recent failures
        
        Returns True if this action should be skipped to avoid redundant work.
        """
        action_type = action.get("action")
        element = action.get("element")
        
        if not action_type:
            return False
        
        # Only block if we've seen this exact action fail recently
        # This allows learning from failures rather than preventing all repeats
        recent_actions = self._action_history[-3:]
        
        for prev_action in recent_actions:
            prev_type = prev_action.get("action")
            prev_element = prev_action.get("element")
            prev_skipped = prev_action.get("skipped", False)
            
            # Only block if the previous identical action was already skipped
            # or if we detect an infinite loop pattern
            if action_type == prev_type and prev_skipped:
                if action_type == "Tap" and element == prev_element:
                    return True
                if action_type == "Back" and prev_type == "Back":
                    return True
        
        return False

    def _analyze_state_change(self, screenshot_b64: str) -> bool:
        """Analyze if the screen state has changed significantly.
        
        This is a perception-based check to help the agent understand
        if previous actions had any effect.
        
        Returns True if state changed significantly.
        """
        if not hasattr(self, '_prev_screenshot_hash'):
            self._prev_screenshot_hash = hash(screenshot_b64)
            return True
        
        current_hash = hash(screenshot_b64)
        state_changed = current_hash != self._prev_screenshot_hash
        self._prev_screenshot_hash = current_hash
        
        return state_changed

    def _check_task_completion(self, user_prompt: str, current_app: str) -> bool:
        """Check if the task has been completed based on action history.
        
        This method analyzes the sequence of actions to detect if:
        1. The main task steps have been executed
        2. We've returned to a reasonable end state
        3. No more actions are needed
        
        Returns True if task appears to be complete.
        """
        if not user_prompt or not self._action_history:
            return False
        
        # Check for "返回上一层" pattern
        if "返回" in user_prompt or "Back" in user_prompt or "返回上一层" in user_prompt:
            # Look for patterns like: Launch -> Tap -> Tap -> Back
            if len(self._action_history) >= 3:
                last_actions = [a.get("action") for a in self._action_history[-3:]]
                if last_actions == ["Tap", "Tap", "Back"]:
                    return True
                # Pattern: Launch -> Tap -> Tap -> Back
                if len(self._action_history) >= 4:
                    last_4_actions = [a.get("action") for a in self._action_history[-4:]]
                    if last_4_actions[:3] == ["Launch", "Tap", "Tap"] and last_4_actions[-1] == "Back":
                        return True
        
        # Check for "美好时光" specific pattern
        if "美好时光" in user_prompt:
            # Count taps and backs
            tap_count = sum(1 for a in self._action_history if a.get("action") == "Tap")
            back_count = sum(1 for a in self._action_history if a.get("action") == "Back")
            
            # If we've done multiple taps and then a back, task might be complete
            if tap_count >= 2 and back_count >= 1:
                # Check if the last action was Back
                if self._action_history[-1].get("action") == "Back":
                    return True
        
        return False

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

        # Check for task completion before proceeding
        # If we've completed the main sequence of actions, suggest finishing
        if self._check_task_completion(user_prompt, current_app):
            if self.agent_config.verbose:
                print("✅ 检测到任务已完成，建议结束任务")
            return StepResult(
                success=True,
                finished=True,
                action=None,
                thinking="任务已完成，所有步骤都已执行完毕",
                message="任务执行完成",
            )

        # Store screenshot for callback
        self._current_screenshot = screenshot_b64

        # Get model response
        try:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print(f"💭 {msgs['thinking']}:")
            print("-" * 50)
            response = self.model_client.request(self._context)
        except ContentModerationError as e:
            # Content moderation error - retry without image
            if self.agent_config.verbose:
                print(f"内容审核过滤: {e}")
            
            # Remove image from last message and retry
            last_msg = self._context[-1]
            if last_msg.get("image_url"):
                last_msg_no_image = {
                    "role": last_msg["role"],
                    "content": [
                        {
                            "type": "text",
                            "text": last_msg["content"][0]["text"] if isinstance(last_msg.get("content"), list) else last_msg.get("content")
                        }
                    ]
                }
                self._context[-1] = last_msg_no_image
                
                print("\n[系统] 检测到截图内容审核过滤，移除截图后重试...")
                try:
                    response = self.model_client.request(self._context)
                except Exception as retry_error:
                    if self.agent_config.verbose:
                        traceback.print_exc()
                    message = f"截图内容被审核过滤，移除截图后重试仍然失败: {str(retry_error)}"
                    return StepResult(
                        success=False,
                        finished=False,
                        action=None,
                        message=message,
                    )
            else:
                message = f"模型内容审核失败: {str(e)}"
                return StepResult(
                    success=False,
                    finished=False,
                    action=None,
                    message=message,
                )
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

        # Check if Tap action is missing coordinates (vision model should provide them!)
        action_type = action.get("action")
        element = action.get("element")
        if action_type == "Tap" and not element:
            if self.agent_config.verbose:
                print("⚠️  Tap动作缺少坐标！作为视觉模型，你应该提供点击坐标。")
            
            # Add feedback to context so the model can reflect and provide coordinates
            self._context.append(
                MessageBuilder.create_user_message(
                    text="[视觉反馈] 作为视觉模型，你应该能够看到屏幕并提供精确的点击坐标。请重新观察屏幕，确定目标元素的位置，并在Tap动作中提供element参数，例如：do(action=\"Tap\", element=[x,y])"
                )
            )
            
            # Return without executing to let model re-think
            if self._step_callback:
                try:
                    self._step_callback({
                        "step": self._step_count,
                        "event": "warning",
                        "action": "missing_coordinates",
                        "thinking": "Tap动作缺少坐标，需要重新观察屏幕",
                        "message": "Tap动作缺少坐标，请提供element参数",
                        "success": False,
                    })
                except Exception:
                    pass
            
            # Force rethinking by returning success=False without finishing
            return StepResult(
                success=False,
                finished=False,
                action=None,
                thinking="Tap动作缺少坐标，需要重新观察屏幕提供精确坐标",
                message="缺少点击坐标，请重新观察屏幕",
            )

        # Check for redundant actions using perception-based reasoning
        if self._is_redundant_action(action):
            action_type = action.get("action")
            element = action.get("element")
            if self.agent_config.verbose:
                print(f"⚠️  检测到重复操作: {action_type} {element}，跳过此步骤")
            
            # Record this redundant action in history to prevent future repeats
            self._action_history.append({
                "action": action_type,
                "element": element,
                "app": action.get("app"),
                "step": self._step_count,
                "skipped": True,
            })
            
            # Send duplicate warning to callback
            if self._step_callback:
                try:
                    self._step_callback({
                        "step": self._step_count,
                        "event": "warning",
                        "action": "redundant_action",
                        "thinking": f"检测到重复操作，已跳过: {action_type}",
                        "message": f"检测到重复操作: {action_type}，已跳过以避免循环",
                        "success": False,
                    })
                except Exception:
                    pass
            
            # Add feedback to context so the model can reflect and choose differently
            # This helps the model learn from its mistakes
            self._context.append(
                MessageBuilder.create_assistant_message(
                    f"<answer>反思：检测到重复操作 {action_type}。我需要重新评估当前状态，尝试不同的方法来完成任务。</answer>"
                )
            )
            
            # Add user feedback to context with state analysis
            self._context.append(
                MessageBuilder.create_user_message(
                    f"[状态反馈] 检测到重复操作。当前屏幕状态未发生变化，请重新观察当前界面，分析可用选项，尝试不同的操作路径。"
                )
            )
            
            # Return a result indicating redundant action was detected
            return StepResult(
                success=False,
                finished=False,
                action=action,
                thinking=f"反思：检测到重复操作 {action_type}，已跳过。需要重新分析当前状态。",
                message=f"检测到重复操作，已跳过以避免循环",
            )

        if self.agent_config.verbose:
            print("-" * 50)
            print(f"🎯 {msgs['action']}:")
            print(json.dumps(action, ensure_ascii=False, indent=2))
            print("=" * 50 + "\n")

        # Send thinking phase update via callback
        if self._step_callback:
            try:
                callback_data = {
                    "step": self._step_count,
                    "event": "think",
                    "thinking": response.thinking if hasattr(response, 'thinking') else "",
                    "proposed_action": action.get("action", ""),
                    "full_response": response.raw_content if hasattr(response, 'raw_content') else "",
                    "screenshot_base64": self._current_screenshot,
                }
                # Check if callback is async
                if asyncio.iscoroutinefunction(self._step_callback):
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(self._step_callback(callback_data), loop)
                else:
                    self._step_callback(callback_data)
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

        # Record action in history for deduplication
        self._action_history.append({
            "action": action.get("action"),
            "element": action.get("element"),
            "app": action.get("app"),
            "step": self._step_count,
        })

        # Refresh screenshot after action execution for callback
        post_action_screenshot = self.device.get_screenshot_base64()

        # Analyze state change - this is the perception-based reflection
        state_changed = self._analyze_state_change(post_action_screenshot)
        
        # If action succeeded but state didn't change, provide feedback to model
        if result.success and not state_changed and action.get("action") not in ["Wait", "Back"]:
            if self.agent_config.verbose:
                print(f"💡 反思：操作执行成功但屏幕状态未变化")
            
            self._context.append(
                MessageBuilder.create_assistant_message(
                    f"<answer>反思：操作执行成功，但屏幕状态似乎没有发生变化。我需要重新观察当前界面，确认操作是否真的生效，或者尝试其他方法。</answer>"
                )
            )
            self._context.append(
                MessageBuilder.create_user_message(
                    "[状态反馈] 操作已执行，但界面未发生明显变化。请仔细观察当前屏幕状态，分析是否需要等待页面加载，或者尝试不同的操作方式。"
                )
            )

        # Call step callback if provided
        if self._step_callback:
            try:
                callback_data = {
                    "step": self._step_count,
                    "action": action.get("action", ""),
                    "thinking": response.thinking if hasattr(response, 'thinking') else "",
                    "message": result.message,
                    "success": result.success,
                    "state_changed": state_changed,
                    "screenshot_base64": post_action_screenshot,
                }
                # Check if callback is async
                if asyncio.iscoroutinefunction(self._step_callback):
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(self._step_callback(callback_data), loop)
                else:
                    self._step_callback(callback_data)
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