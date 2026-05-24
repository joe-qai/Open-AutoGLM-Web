"""Decision layer for the Agent architecture."""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from openai import OpenAI

    has_openai = True
except ImportError:
    has_openai = False

try:
    from ..config.app_packages import get_package_name, get_supported_apps_text

    has_app_packages = True
except ImportError:
    has_app_packages = False

    def get_package_name(app_name: str):
        return app_name if "." in app_name else None

    def get_supported_apps_text():
        return ""


class DecisionMode(str, Enum):
    """Decision mode: LLM (text-only) or VLM (with image)."""

    LLM = "llm"
    VLM = "vlm"
    AUTO = "auto"


@dataclass
class ModelConfig:
    """Model configuration."""

    base_url: str = os.environ.get(
        "PHONE_AGENT_MODEL_API_URL", "http://localhost:8000/v1"
    )
    model_name: str = os.environ.get("PHONE_AGENT_MODEL_NAME", "autoglm-phone-9b")
    api_key: str = os.environ.get("PHONE_AGENT_API_KEY", "EMPTY")
    mode: DecisionMode = DecisionMode.LLM


class MockModelClient:
    """Mock model client for testing."""

    def __init__(self, config: ModelConfig):
        self.config = config

    def request(self, messages: List[Dict]) -> Any:
        """Mock request method."""

        class Response:
            thinking = "Mock thinking"
            action = '{"action": "wait", "parameters": {"duration": 1000}, "reasoning": "Mock response"}'

        return Response()


class OpenAIModelClient:
    """OpenAI-compatible model client."""

    def __init__(self, config: ModelConfig):
        self.config = config
        # 配置客户端，允许无API key（用于本地模型）
        client_kwargs = {"base_url": config.base_url}
        if config.api_key and config.api_key != "EMPTY":
            client_kwargs["api_key"] = config.api_key
        else:
            # 本地模型可能不需要API key，设置一个空字符串
            client_kwargs["api_key"] = "sk-no-key-required"
        self.client = OpenAI(**client_kwargs)

    def request(self, messages: List[Dict]) -> Any:
        """Make request to LLM."""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )

            content = response.choices[0].message.content

            class Response:
                thinking = ""
                action = content

            return Response()
        except Exception as e:

            class Response:
                thinking = ""
                action = f'{{"action": "wait", "parameters": {{"duration": 2000}}, "reasoning": "Model request failed: {str(e)}"}}'

            return Response()


@dataclass
class ActionPlan:
    """Plan for next action."""

    action: str
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    reasoning: str = ""


class DecisionLayer:
    """Decision layer - makes decisions based on perception data."""

    # 元素定位优先的 LLM Action Schema
    ACTION_SCHEMA_LLM = """你是一个手机自动化操作专家。你的任务是根据用户指令，分析当前手机屏幕内容，决定下一步操作。

## 输出格式
你必须以 JSON 格式输出，包含以下字段：
{
    "reasoning": "你的思考过程",
    "action": "要执行的动作",
    "locator": {
        "type": "定位方式",
        "value": "定位值",
        "index": 0
    },
    "fallback_coords": [x, y]
}

## 可用动作
- tap: 点击元素。必须提供 locator。
- type: 在输入框中输入文本。先点击输入框再输入，参数中需包含 text 字段。
- swipe: 滑动操作。参数中需包含 start_x, start_y, end_x, end_y。
- back: 返回上一页。
- home: 回到桌面。
- launch: 启动应用。参数中需包含 app 字段（包名）。
- wait: 等待。参数中需包含 duration（秒）。
- finish: 完成任务。参数中需包含 message。

## 定位优先级（从高到低）
1. resource_id — 最稳定，如 com.xxx:id/btn_search
2. content_desc — 图标按钮的辅助描述
3. text — 文本精确匹配，如 "搜索"
4. text_contains — 文本包含匹配，如 "搜"
5. class_name — 类型定位，如 android.widget.TextView
6. coordinates — 坐标 fallback

## 屏幕信息说明
以下信息来自手机 UI 树的提取结果，包含当前屏幕的布局信息。
带 + 号的是有 resource_id 的稳定元素，优先使用。
坐标是元素中心点 (x, y)。"""

    # LLM 模式系统提示（仅 UI 元素）
    SYSTEM_PROMPT_LLM = """你是一个智能移动端自动化Agent，负责根据 UI 元素分析和用户任务，做出操作决策。

## 你的核心能力
1. 理解用户的自然语言任务描述
2. 分析当前屏幕的 UI 元素
3. 自主决定下一步操作并执行
4. 循环执行直到任务完成

## 可用操作
1. **launch_app** - 启动应用（任务第一步通常使用）
   参数: app_name (应用包名或应用名称，如"微信"、"com.tencent.mm")
   注意：如果任务描述中提到了要打开某个APP，直接使用这个操作

2. **tap_element** - 点击元素（最常用）
   参数: element_index (元素索引，从0开始) 或 x,y (归一化坐标，0-999) 或 description (元素文本描述)
   优先级: element_index > description > x,y

3. **type_text** - 输入文本
   参数: text (要输入的文本)
   注意：需要先点击输入框使其获得焦点

4. **swipe** - 滑动屏幕
   参数: direction (方向: up/down/left/right，默认down) 或 x1,y1,x2,y2 (归一化坐标)

5. **long_press** - 长按
   参数: element_index 或 x,y 或 description

6. **back** - 返回上一页
   无参数

7. **home** - 返回主页
   无参数

8. **wait** - 等待
   参数: duration (等待毫秒数，默认1000)

9. **finish** - 完成任务
   参数: message (完成消息)

## UI 元素格式
每个元素包含:
- index: 索引（从0开始，用于精确定位）
- text: 文本内容
- resource_id: 资源ID
- content_desc: 内容描述
- bbox_normalized: 归一化包围盒 {x, y, w, h}，坐标范围 0-999
- clickable: 是否可点击

## 决策规则

### 启动应用规则
- 如果任务要求打开某个APP（如"打开微信"），首先使用 launch_app 操作
- 支持中文应用名（如"微信"、"淘宝"）和包名（如"com.tencent.mm"）

### 点击规则
- 优先使用 element_index（最精确）
- 其次使用 description（文本匹配）
- 最后使用坐标（x,y）

### 页面分析规则
- 如果当前页面没有目标元素，考虑向上滑动查找
- 如果进入错误页面，使用 back 返回
- 如果页面未加载完成，等待后重试

### 任务理解规则
- 仔细理解用户的任务描述
- 如果任务复杂，将其分解为多个步骤
- 每执行完一步，检查是否达到目标

## 输出格式
必须是有效的JSON:
{
    "action": "操作名称",
    "target": "目标描述",
    "parameters": {"参数名": "参数值"},
    "confidence": 0.0-1.0,
    "reasoning": "决策理由说明"
}
"""

    # VLM 模式系统提示（截图 + UI 元素）
    SYSTEM_PROMPT_VLM = """你是一个智能移动端自动化Agent，负责根据屏幕截图和 UI 元素分析，做出操作决策。

## 你的核心能力
1. 理解用户的自然语言任务描述
2. 分析当前屏幕的截图和 UI 元素
3. 自主决定下一步操作并执行
4. 循环执行直到任务完成

## 可用操作
1. **launch_app** - 启动应用
   参数: app_name (应用包名或应用名称，如"微信"、"com.tencent.mm")

2. **tap_element** - 点击元素
   参数: element_index (元素索引，从0开始) 或 x,y (归一化坐标，0-999) 或 description (元素文本描述)

3. **type_text** - 输入文本
   参数: text (要输入的文本)

4. **swipe** - 滑动屏幕
   参数: direction (方向: up/down/left/right，默认down) 或 x1,y1,x2,y2 (归一化坐标)

5. **long_press** - 长按
   参数: element_index 或 x,y 或 description

6. **back** - 返回上一页

7. **home** - 返回主页

8. **wait** - 等待
   参数: duration (等待毫秒数，默认1000)

9. **finish** - 完成任务
   参数: message (完成消息)

## UI 元素格式
每个元素包含:
- index: 索引（从0开始）
- text: 文本内容
- resource_id: 资源ID
- content_desc: 内容描述
- bbox_normalized: 归一化包围盒 {x, y, w, h}，坐标范围 0-999
- clickable: 是否可点击

## 决策规则
- 优先使用 element_index 定位元素（最精确）
- 其次使用 description（文本匹配）
- 最后使用坐标（x,y）
- 如果任务要求打开APP，首先使用 launch_app
- 完成任务后使用 finish 结束

## 输出格式
必须是有效的JSON:
{
    "action": "操作名称",
    "target": "目标描述",
    "parameters": {"参数名": "参数值"},
    "confidence": 0.0-1.0,
    "reasoning": "决策理由说明"
}
"""

    def __init__(
        self, model_client: Optional[Any] = None, mode: DecisionMode = DecisionMode.LLM
    ):
        self.mode = mode
        if model_client:
            self.model_client = model_client
        elif has_openai:
            self.model_client = OpenAIModelClient(ModelConfig())
        else:
            self.model_client = MockModelClient(ModelConfig())

    def _format_ui_elements(self, ui_elements: List[Dict]) -> str:
        """Format UI elements for LLM."""
        if not ui_elements:
            return "无UI元素"

        lines = []
        for i, e in enumerate(ui_elements[:50]):
            text = e.get("text", "")
            resource_id = e.get("resource_id", "")
            desc = e.get("content_desc", "")
            bbox = e.get("bbox_normalized", {})
            clickable = e.get("clickable", False)

            line = f"[{i}] text='{text}' id='{resource_id}' desc='{desc}' bbox=({bbox.get('x', 0)},{bbox.get('y', 0)},{bbox.get('w', 0)},{bbox.get('h', 0)}) clickable={clickable}"
            lines.append(line)

        return "\n".join(lines)

    def get_action_schema(self, mode: DecisionMode) -> str:
        if mode == DecisionMode.LLM:
            return self.ACTION_SCHEMA_LLM
        return self.SYSTEM_PROMPT_LLM

    def _build_system_prompt(self, decision_mode: DecisionMode) -> str:
        """Build system prompt with app context."""
        prompt = (
            self.SYSTEM_PROMPT_VLM
            if decision_mode == DecisionMode.VLM
            else self.SYSTEM_PROMPT_LLM
        )

        if has_app_packages:
            apps_text = get_supported_apps_text()
            if apps_text:
                prompt += f"\n\n## 支持的应用\n{apps_text}\n"

        return prompt

    def decide(
        self,
        task: str,
        screenshot_base64: Optional[str] = None,
        ui_elements: Optional[List[Dict]] = None,
        ui_text: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        mode: Optional[DecisionMode] = None,
    ) -> ActionPlan:
        """
        Make decision based on current state.

        Args:
            task: Task description
            screenshot_base64: Screenshot in base64 (optional for LLM mode)
            ui_elements: List of UI elements
            ui_text: UI tree text description (for element-location-first strategy)
            history: Conversation history
            mode: Decision mode (LLM/VLM/AUTO, defaults to self.mode)
        """
        decision_mode = mode or self.mode

        if decision_mode == DecisionMode.AUTO:
            decision_mode = DecisionMode.VLM if screenshot_base64 else DecisionMode.LLM

        elements_str = self._format_ui_elements(ui_elements or [])

        messages = []

        if decision_mode == DecisionMode.LLM:
            system_prompt = self.get_action_schema(decision_mode)
        else:
            system_prompt = self._build_system_prompt(decision_mode)
        messages.append({"role": "system", "content": system_prompt})

        if history:
            history_content = ""
            for h in history[-5:]:
                step = h.get("step", "?")
                action = h.get("action", "")
                success = h.get("success", False)
                history_content += (
                    f"  Step {step}: {action} -> {'成功' if success else '失败'}\n"
                )
            if history_content:
                messages.append(
                    {"role": "user", "content": f"历史操作:\n{history_content}"}
                )

        text_content = f"任务: {task}\n\n"
        if ui_text:
            text_content += f"当前屏幕信息:\n{ui_text}\n\n"
        else:
            text_content += f"当前UI元素:\n{elements_str}"

        if decision_mode == DecisionMode.VLM and screenshot_base64:
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
                },
                {"type": "text", "text": text_content},
            ]
        else:
            user_content = text_content

        messages.append({"role": "user", "content": user_content})

        try:
            response = self.model_client.request(messages)

            try:
                plan = json.loads(response.action)
                locator = plan.get("locator", {})
                return ActionPlan(
                    action=plan.get("action", "wait"),
                    target=locator.get("value", ""),
                    parameters={
                        "locator_type": locator.get("type"),
                        "locator_value": locator.get("value"),
                        "locator_index": locator.get("index", 0),
                        "fallback_coords": plan.get("fallback_coords"),
                        "text": plan.get("text"),
                        "app": plan.get("app"),
                        "duration": plan.get("duration"),
                        "start_x": plan.get("start_x"),
                        "start_y": plan.get("start_y"),
                        "end_x": plan.get("end_x"),
                        "end_y": plan.get("end_y"),
                        "message": plan.get("message"),
                    },
                    confidence=plan.get("confidence", 0.8),
                    reasoning=plan.get("reasoning", ""),
                )
            except json.JSONDecodeError:
                return ActionPlan(
                    action="wait",
                    reasoning=f"无法解析响应: {getattr(response, 'action', str(response))[:150]}",
                )
        except Exception as e:
            return ActionPlan(
                action="wait",
                parameters={"duration": 2000},
                reasoning=f"模型请求失败: {str(e)}",
            )

    def decide_simple(
        self, task: str, perception_data: Dict, mode: Optional[DecisionMode] = None
    ) -> ActionPlan:
        """Simplified decision method."""
        return self.decide(
            task=task,
            screenshot_base64=perception_data.get("screenshot_base64"),
            ui_elements=perception_data.get("ui_elements", []),
            history=[],
            mode=mode,
        )
