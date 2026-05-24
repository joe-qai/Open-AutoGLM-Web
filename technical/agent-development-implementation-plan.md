# Agent 功能开发实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 补全 backend agent 核心功能，使其能在 Android 真机上通过 LLM 驱动+元素定位优先策略端到端运行

**架构：** 新增 4 个模块（UiTreeExtractor / MultiStrategyElementLocator / ReActLoop / ScriptGenerator），修改 4 个现有模块（perception / decision / engine / websocket）。新增模块解耦独立，修改模块只做最小接口适配。

**Tech Stack:** Python 3.10+, FastAPI, asyncio, uiautomator2, OpenAI SDK

**实现顺序（依赖关系驱动）：**

```
1. ui_tree.py          ← 无外部依赖
2. element_locator.py  ← 依赖 BaseDeviceAdapter 接口
3. decision.py prompt  ← 更新 LLM 输出格式
4. react_loop.py       ← 依赖 1 + 2 + 3
5. perception.py       ← 集成 ui_tree
6. engine.py           ← 改成调 react_loop
7. websocket.py        ← 接入 step_callback
8. script_generator.py ← 依赖步骤历史格式
```

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `backend/app/core/ui_tree.py` | XML 解析、按优先级排序、结构化文本输出 |
| Create | `backend/app/core/element_locator.py` | 七层降级定位链 |
| Create | `backend/app/core/react_loop.py` | Observe→Think→Act→Reflect 循环 |
| Create | `backend/app/core/script_generator.py` | 步骤历史 → pytest 脚本 |
| Modify | `backend/app/core/layers/perception.py` | perceive() 增加 ui_text 返回 |
| Modify | `backend/app/core/layers/decision.py` | 新增 ACTION_SCHEMA_LLM prompt |
| Modify | `backend/app/core/agent/engine.py` | execute_task() 改为 ReActLoop.run() |
| Modify | `backend/app/api/v1/websocket.py` | 补全订阅 + 推送逻辑 |

---

### Task 1: `core/ui_tree.py` — UI 树解析与文本转换

**Files:**
- Create: `backend/app/core/ui_tree.py`
- Test: 配合 perception.py 集成测试（Task 5 覆盖）

- [ ] **Step 1: 定义 UIElement dataclass 和定位优先级方法**

```python
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class UIElement:
    resource_id: str = ""
    class_name: str = ""
    text: str = ""
    content_desc: str = ""
    bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)
    enabled: bool = True
    clickable: bool = False
    focused: bool = False

    @property
    def center(self) -> Tuple[int, int]:
        return (
            (self.bounds[0] + self.bounds[2]) // 2,
            (self.bounds[1] + self.bounds[3]) // 2,
        )

    @property
    def has_resource_id(self) -> bool:
        return bool(self.resource_id)

    @property
    def priority_key(self) -> int:
        if self.resource_id:
            return 0
        if self.content_desc:
            return 1
        if self.text:
            return 2
        return 3
```

- [ ] **Step 2: 实现 UITreeExtractor 核心类**

```python
import xml.etree.ElementTree as ET
import re
from typing import List, Optional


class UITreeExtractor:
    def __init__(self, device_adapter):
        self.device = device_adapter

    def extract(self) -> str:
        return self.device.dump_ui_tree()

    def to_text(self, ui_xml: str, max_elements: int = 30) -> str:
        elements = self._parse_xml(ui_xml)
        sorted_elements = self._sort_by_priority(elements)

        lines = []
        lines.append("=== 屏幕概览 ===")
        try:
            display = self.device.get_display_info()
            lines.append(f"分辨率: {display.width}x{display.height}")
        except Exception:
            lines.append("分辨率: unknown")
        try:
            lines.append(f"当前应用: {self.device.get_current_app()}")
        except Exception:
            lines.append("当前应用: unknown")
        lines.append("")
        lines.append("=== 可交互元素 ===")

        clickable = [e for e in sorted_elements if e.clickable and e.enabled]
        for i, elem in enumerate(clickable[:max_elements]):
            prefix = "+" if elem.has_resource_id else "-"
            attrs = []
            if elem.resource_id:
                attrs.append(f"id={elem.resource_id}")
            if elem.text:
                attrs.append(f"text={elem.text}")
            if elem.content_desc:
                attrs.append(f"desc={elem.content_desc}")
            if elem.class_name:
                attrs.append(f"type={elem.class_name.split('.')[-1]}")
            x, y = elem.center
            lines.append(f"{prefix}[{i}] {' | '.join(attrs)} @({x},{y})")

        if len(clickable) > max_elements:
            lines.append(f"... (还有 {len(clickable) - max_elements} 个元素)")

        inputs = [e for e in elements if "EditText" in e.class_name and e.enabled]
        if inputs:
            lines.append("")
            lines.append("=== 输入框 ===")
            for i, elem in enumerate(inputs):
                label = elem.resource_id or elem.class_name.split(".")[-1]
                lines.append(f"  [{i}] {label} @({elem.center[0]},{elem.center[1]})")

        return "\n".join(lines)

    def _parse_xml(self, ui_xml: str) -> List[UIElement]:
        elements = []
        if not ui_xml or not ui_xml.strip():
            return elements
        try:
            root = ET.fromstring(ui_xml)
            self._parse_element(root, elements)
        except ET.ParseError:
            pass
        except Exception:
            pass
        return elements

    def _parse_element(self, element: ET.Element, results: List[UIElement]):
        attrib = element.attrib
        bounds_str = attrib.get("bounds", "[0,0][0,0]")
        ui_elem = UIElement(
            resource_id=attrib.get("resource-id", ""),
            class_name=attrib.get("class", ""),
            text=attrib.get("text", ""),
            content_desc=attrib.get("content-desc", ""),
            bounds=self._parse_bounds(bounds_str),
            enabled=attrib.get("enabled", "true") == "true",
            focused=attrib.get("focused", "false") == "true",
            clickable=attrib.get("clickable", "false") == "true",
        )
        results.append(ui_elem)
        for child in element:
            self._parse_element(child, results)

    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int, int, int]:
        match = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if match:
            return (
                int(match.group(1)), int(match.group(2)),
                int(match.group(3)), int(match.group(4)),
            )
        return (0, 0, 0, 0)

    def _sort_by_priority(self, elements: List[UIElement]) -> List[UIElement]:
        return sorted(elements, key=lambda e: e.priority_key)
```

- [ ] **Step 3: 验证文件语法**

Run: `python -c "import ast; ast.parse(open('backend/app/core/ui_tree.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/ui_tree.py
git commit -m "feat(core): add UITreeExtractor for XML-to-text conversion"
```

---

### Task 2: `core/element_locator.py` — 多策略元素定位器

**Files:**
- Create: `backend/app/core/element_locator.py`

- [ ] **Step 1: 定义基础数据结构**

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from enum import Enum


class LocatorType(str, Enum):
    RESOURCE_ID = "resource_id"
    CONTENT_DESC = "content_desc"
    TEXT = "text"
    TEXT_CONTAINS = "text_contains"
    CLASS_NAME = "class_name"
    SEMANTIC = "semantic"
    COORDINATES = "coordinates"


@dataclass
class ElementLocator:
    locator_type: LocatorType
    value: str
    index: int = 0


@dataclass
class LocateResult:
    success: bool
    x: int = 0
    y: int = 0
    element_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
```

- [ ] **Step 2: 实现 MultiStrategyElementLocator**

```python
class MultiStrategyElementLocator:
    def __init__(self, device_adapter):
        self.device = device_adapter

    def locate(self, locator: ElementLocator) -> LocateResult:
        dispatch = {
            LocatorType.RESOURCE_ID: self._locate_by_resource_id,
            LocatorType.CONTENT_DESC: self._locate_by_content_desc,
            LocatorType.TEXT: self._locate_by_text,
            LocatorType.TEXT_CONTAINS: self._locate_by_text_contains,
            LocatorType.CLASS_NAME: self._locate_by_class_name,
            LocatorType.SEMANTIC: self._locate_by_semantic,
            LocatorType.COORDINATES: self._locate_by_coordinates,
        }
        handler = dispatch.get(locator.locator_type)
        if not handler:
            return LocateResult(success=False, error_message=f"Unknown locator type: {locator.locator_type}")
        return handler(locator.value, locator.index)
```

- [ ] **Step 3: 实现各定位方法**

```python
    def _locate_by_resource_id(self, value: str, index: int = 0) -> LocateResult:
        try:
            from uiautomator2 import UiObjectNotFoundError
            element = self.device(resourceId=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True, x=cx, y=cy,
                    element_info={"resource_id": value, "bounds": bounds}
                )
        except Exception as e:
            pass
        return LocateResult(success=False, error_message=f"resource_id not found: {value}")

    def _locate_by_content_desc(self, value: str, index: int = 0) -> LocateResult:
        try:
            element = self.device(description=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True, x=cx, y=cy,
                    element_info={"content_desc": value, "bounds": bounds}
                )
        except Exception:
            pass
        return LocateResult(success=False, error_message=f"content_desc not found: {value}")

    def _locate_by_text(self, value: str, index: int = 0) -> LocateResult:
        try:
            element = self.device(text=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True, x=cx, y=cy,
                    element_info={"text": value, "bounds": bounds}
                )
        except Exception:
            pass
        return LocateResult(success=False, error_message=f"text not found: {value}")

    def _locate_by_text_contains(self, value: str, index: int = 0) -> LocateResult:
        try:
            element = self.device(textContains=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True, x=cx, y=cy,
                    element_info={"text_contains": value, "bounds": bounds}
                )
        except Exception:
            pass
        return LocateResult(success=False, error_message=f"text_contains not found: {value}")

    def _locate_by_class_name(self, value: str, index: int = 0) -> LocateResult:
        try:
            elements = self.device(className=value)
            if elements.count > index:
                el = elements[index]
                bounds = el.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True, x=cx, y=cy,
                    element_info={"class_name": value, "index": index, "bounds": bounds}
                )
        except Exception:
            pass
        return LocateResult(success=False, error_message=f"class_name[{index}] not found: {value}")

    def _locate_by_semantic(self, value: str, index: int = 0) -> LocateResult:
        return LocateResult(success=False, error_message="semantic locator not yet implemented")

    def _locate_by_coordinates(self, value: str, index: int = 0) -> LocateResult:
        try:
            parts = value.split(",")
            if len(parts) == 2:
                x, y = int(parts[0]), int(parts[1])
                return LocateResult(success=True, x=x, y=y, element_info={"coordinates": [x, y]})
        except (ValueError, IndexError):
            pass
        return LocateResult(success=False, error_message=f"invalid coordinates: {value}")
```

- [ ] **Step 3b: 添加 convenience wrapper（保持 finder.py 兼容）**

```python
    def find_element(self, criteria: dict) -> Optional[dict]:
        """兼容 agent/finder.py 的 find_element 接口"""
        locator_type_map = {
            "text": LocatorType.TEXT,
            "resource_id": LocatorType.RESOURCE_ID,
            "content_desc": LocatorType.CONTENT_DESC,
            "class_name": LocatorType.CLASS_NAME,
        }
        for key, lt in locator_type_map.items():
            if key in criteria:
                result = self.locate(ElementLocator(lt, criteria[key]))
                if result.success:
                    return result.element_info
        return None
```

- [ ] **Step 4: 验证文件语法**

Run: `python -c "import ast; ast.parse(open('backend/app/core/element_locator.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/element_locator.py
git commit -m "feat(core): add MultiStrategyElementLocator with 7-level fallback"
```

---

### Task 3: `core/layers/decision.py` — 补充元素定位优先的 prompt

**Files:**
- Modify: `backend/app/core/layers/decision.py`

- [ ] **Step 1: 添加 ACTION_SCHEMA_LLM 常量**

在 `decision.py` 开头附近（在 class DecisionLayer 之前），新增：

```python
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

# 保留旧 prompt 作为 VLM 模式备用
# SYSTEM_PROMPT_LLM 和 SYSTEM_PROMPT_VLM 保持不变
```

- [ ] **Step 2: 在 DecisionLayer 中添加 schema 选择方法**

```python
class DecisionLayer:
    # ... 已有 __init__ 不变

    def get_action_schema(self, mode: DecisionMode) -> str:
        """根据模式返回对应的 action schema"""
        if mode == DecisionMode.LLM:
            return ACTION_SCHEMA_LLM
        return SYSTEM_PROMPT_LLM
```

- [ ] **Step 3: 修改 decide() 方法支持 LLM 模式**

```python
    async def decide(
        self,
        task: str,
        screenshot_base64: Optional[str] = None,
        ui_elements: Optional[list] = None,
        ui_text: Optional[str] = None,
        history: Optional[list] = None,
        mode: DecisionMode = DecisionMode.LLM,
    ) -> ActionPlan:
        """LLM 决策，支持元素定位优先策略"""
        system_prompt = self.get_action_schema(mode)

        user_content = f"用户任务：{task}\n\n"
        if ui_text:
            user_content += f"当前屏幕信息：\n{ui_text}\n\n"

        if history:
            user_content += f"历史操作：\n"
            for h in history[-5:]:
                user_content += f"  Step {h['step']}: {h['action']} -> {'成功' if h['success'] else '失败'}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        if screenshot_base64 and mode == DecisionMode.VLM:
            messages[1] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_content},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
                    },
                ],
            }

        raw = await self._call_llm(messages)
        return self._parse_action_plan(raw)

    def _parse_action_plan(self, raw: str) -> ActionPlan:
        """从 LLM JSON 输出解析 ActionPlan"""
        import json
        try:
            data = json.loads(raw)
            return ActionPlan(
                action=data.get("action", "wait"),
                target=data.get("locator", {}).get("value", ""),
                parameters={
                    "locator_type": data.get("locator", {}).get("type"),
                    "locator_value": data.get("locator", {}).get("value"),
                    "locator_index": data.get("locator", {}).get("index", 0),
                    "fallback_coords": data.get("fallback_coords"),
                    "text": data.get("text"),
                    "app": data.get("app"),
                    "duration": data.get("duration"),
                    "start_x": data.get("start_x"),
                    "start_y": data.get("start_y"),
                    "end_x": data.get("end_x"),
                    "end_y": data.get("end_y"),
                    "message": data.get("message"),
                },
                confidence=data.get("confidence", 0.8),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, TypeError) as e:
            return ActionPlan(
                action="wait",
                target="",
                parameters={"duration": 1},
                confidence=0.1,
                reasoning=f"解析 LLM 输出失败: {e}",
            )

    async def _call_llm(self, messages: list) -> str:
        """调用 LLM API"""
        if isinstance(self.client, MockModelClient):
            return self.client.chat(messages)
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name or "default",
                messages=messages,
                temperature=0.1,
                max_tokens=1500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return json.dumps({
                "reasoning": f"LLM 调用失败: {e}",
                "action": "wait",
                "locator": None,
                "fallback_coords": None,
            })
```

- [ ] **Step 4: 验证语法**

Run: `python -c "import ast; ast.parse(open('backend/app/core/layers/decision.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/layers/decision.py
git commit -m "feat(core): add element-location-first LLM schema to DecisionLayer"
```

---

### Task 4: `core/react_loop.py` — ReAct 循环

**Files:**
- Create: `backend/app/core/react_loop.py`

- [ ] **Step 1: 定义 ReActStep dataclass**

```python
from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any, List, Callable
from datetime import datetime
import asyncio
import json
import time


@dataclass
class ReActStep:
    step_index: int
    phase: Literal["observe", "think", "act", "reflect"]
    ui_state: str = ""
    thought: str = ""
    action: str = ""
    action_params: Dict[str, Any] = field(default_factory=dict)
    result: str = ""
    success: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
```

- [ ] **Step 2: 实现 ReActLoop 类**

```python
class ReActLoop:
    def __init__(
        self,
        ui_extractor,
        llm_decider,
        element_locator,
        action_executor,
        max_iterations: int = 50,
        on_step: Optional[Callable] = None,
    ):
        self.ui_extractor = ui_extractor
        self.llm_decider = llm_decider
        self.element_locator = element_locator
        self.action_executor = action_executor
        self.max_iterations = max_iterations
        self.on_step = on_step

    async def run(self, task: str, task_id: str = None) -> dict:
        history = []
        steps_log = []

        for iteration in range(self.max_iterations):
            # ===== OBSERVE =====
            step = ReActStep(step_index=iteration + 1, phase="observe")
            try:
                ui_tree_xml = self.ui_extractor.extract()
                ui_text = self.ui_extractor.to_text(ui_tree_xml)
            except Exception as e:
                ui_text = f"[UI 提取失败: {e}]"
            step.ui_state = ui_text

            await self._emit("observe", step, task_id, {
                "ui_summary": ui_text[:200] if len(ui_text) > 200 else ui_text,
            })

            # ===== THINK =====
            step.phase = "think"
            try:
                plan = await self.llm_decider.decide(
                    task=task,
                    ui_text=ui_text,
                    history=history,
                )
            except Exception as e:
                step.thought = f"[LLM 决策失败: {e}]"
                step.action = "wait"
                step.action_params = {"duration": 1}
                step.success = False
                await self._emit("think", step, task_id, {
                    "thought": step.thought,
                    "proposed_action": step.action,
                })
                steps_log.append(step)
                await asyncio.sleep(1.5)
                continue

            step.thought = plan.reasoning
            step.action = plan.action
            step.action_params = plan.parameters

            await self._emit("think", step, task_id, {
                "thought": plan.reasoning,
                "proposed_action": plan.action,
                "params": plan.parameters,
            })

            # ===== ACT =====
            step.phase = "act"

            if plan.action == "finish":
                step.result = plan.parameters.get("message", "任务完成")
                step.success = True
                steps_log.append(step)
                await self._emit("act", step, task_id, {
                    "action": "finish",
                    "message": step.result,
                })
                break

            # 元素定位
            locator_type = plan.parameters.get("locator_type")
            locator_value = plan.parameters.get("locator_value")
            target_coords = None

            if locator_type and locator_value:
                from .element_locator import ElementLocator, LocatorType
                try:
                    lt = LocatorType(locator_type)
                    locator = ElementLocator(
                        locator_type=lt,
                        value=locator_value,
                        index=plan.parameters.get("locator_index", 0),
                    )
                    result = self.element_locator.locate(locator)
                    if result.success:
                        target_coords = (result.x, result.y)
                except Exception:
                    pass

            # fallback
            if target_coords is None:
                fb = plan.parameters.get("fallback_coords")
                if fb and len(fb) == 2:
                    target_coords = (fb[0], fb[1])

            if target_coords:
                plan.parameters["x"] = target_coords[0]
                plan.parameters["y"] = target_coords[1]

            # 执行动作
            try:
                action_result = await self.action_executor.execute(plan)
                step.result = action_result.message
                step.success = action_result.success
            except Exception as e:
                step.result = f"[执行失败: {e}]"
                step.success = False

            await self._emit("act", step, task_id, {
                "action": plan.action,
                "params": plan.parameters,
                "target_coords": target_coords,
                "result": step.result,
                "success": step.success,
            })

            # ===== REFLECT =====
            step.phase = "reflect"
            if not step.success:
                step.thought += f"\n[反思] 执行失败: {step.result}"
                if target_coords is None:
                    step.thought += " (元素未定位到)"

            history.append({
                "step": iteration + 1,
                "action": step.action,
                "params": step.action_params,
                "result": step.result,
                "success": step.success,
            })
            steps_log.append(step)

            await self._emit("reflect", step, task_id, {
                "reflection": step.thought,
                "history_summary": f"已完成 {len(history)} 步，成功 {sum(1 for h in history if h['success'])} 步",
            })

            await asyncio.sleep(1.5)

        final_step = steps_log[-1] if steps_log else ReActStep(step_index=0, phase="reflect", success=False)
        return {
            "success": final_step.success,
            "total_steps": len(steps_log),
            "steps": [
                {
                    "step_index": s.step_index,
                    "phase": s.phase,
                    "action": s.action,
                    "params": s.action_params,
                    "result": s.result,
                    "success": s.success,
                    "thought": s.thought,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in steps_log
            ],
            "history": history,
            "final_message": (
                final_step.result if final_step.success
                else f"达到最大迭代次数 ({self.max_iterations})"
            ),
        }

    async def _emit(self, phase: str, step: ReActStep, task_id: str = None, extra: dict = None):
        if not self.on_step:
            return
        data = {
            "task_id": task_id,
            "event": phase,
            "step": step.step_index,
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            data.update(extra)
        try:
            await self.on_step(data)
        except Exception:
            pass
```

- [ ] **Step 3: 验证语法**

Run: `python -c "import ast; ast.parse(open('backend/app/core/react_loop.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/react_loop.py
git commit -m "feat(core): add ReAct loop with OBSERVE-THINK-ACT-REFLECT phases"
```

---

### Task 5: `core/layers/perception.py` — 集成 UITreeExtractor

**Files:**
- Modify: `backend/app/core/layers/perception.py`

- [ ] **Step 1: 修改 PerceptionResult，增加 ui_text 字段**

```python
@dataclass
class PerceptionResult:
    screenshot_base64: str = ""
    screenshot_path: str = ""
    ui_elements: list = field(default_factory=list)
    current_app: str = ""
    ui_text: str = ""            # ← 新增
    timestamp: float = 0.0
```

- [ ] **Step 2: 修改 perceive() 方法**

在 `__init__` 中初始化 `UITreeExtractor`：

```python
class PerceptionLayer:
    def __init__(self, adapter):
        self.adapter = adapter
        self.screenshot_dir = "./screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        # 新增：UI 树提取器
        from app.core.ui_tree import UITreeExtractor
        self.ui_extractor = UITreeExtractor(adapter)
```

修改 `perceive()` 方法：

```python
    def perceive(self, step_index: int = 0) -> PerceptionResult:
        try:
            screenshot_path = self._capture_screenshot(step_index)
        except Exception as e:
            screenshot_path = ""
        try:
            with open(screenshot_path, "rb") as f:
                screenshot_base64 = base64.b64encode(f.read()).decode()
        except Exception:
            screenshot_base64 = ""

        ui_elements = []
        current_app = ""
        ui_text = ""

        try:
            ui_elements = self.get_ui_elements_summary()
        except Exception:
            pass
        try:
            current_app = self.adapter.get_current_app()
        except Exception:
            pass
        # 新增：UI 树→文本
        try:
            ui_xml = self.ui_extractor.extract()
            ui_text = self.ui_extractor.to_text(ui_xml)
        except Exception:
            ui_text = ""

        return PerceptionResult(
            screenshot_base64=screenshot_base64,
            screenshot_path=screenshot_path,
            ui_elements=ui_elements,
            current_app=current_app,
            ui_text=ui_text,
            timestamp=time.time(),
        )
```

- [ ] **Step 3: 验证语法**

Run: `python -c "import ast; ast.parse(open('backend/app/core/layers/perception.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/layers/perception.py
git commit -m "feat(core): integrate UITreeExtractor into PerceptionLayer"
```

---

### Task 6: `core/agent/engine.py` — 接入 ReActLoop

**Files:**
- Modify: `backend/app/core/agent/engine.py`

- [ ] **Step 1: 导入新模块**

在文件顶部追加 import：

```python
from app.core.react_loop import ReActLoop
from app.core.ui_tree import UITreeExtractor
from app.core.element_locator import MultiStrategyElementLocator
```

- [ ] **Step 2: 实现 _build_react_loop(self) 方法**

在 `AgentEngine` 类中新增：

```python
    def _build_react_loop(self) -> ReActLoop:
        """从当前 layers 和 agents 构建 ReActLoop"""
        ui_extractor = UITreeExtractor(self.device)
        element_locator = MultiStrategyElementLocator(self.device)

        # llm_decider 复用 DecisionLayer
        llm_decider = self.decision_layer

        # action_executor 复用 ActionLayer
        action_executor = self.action_layer

        return ReActLoop(
            ui_extractor=ui_extractor,
            llm_decider=llm_decider,
            element_locator=element_locator,
            action_executor=action_executor,
            max_iterations=self.context.max_steps,
            on_step=self._on_step_callback,
        )
```

- [ ] **Step 3: 添加 step 回调，写入 Memory + WebSocket**

```python
    async def _on_step_callback(self, data: dict):
        """ReActLoop 的 step 回调"""
        # 写入 MemoryLayer
        if self.memory_layer:
            self.memory_layer.add_memory(
                memory_type=f"step_{data.get('event', 'unknown')}",
                content=str(data),
            )
        # 这里不要直接操作 WebSocket，让 task_service 处理
```

- [ ] **Step 4: 修改 execute_task() 方法**

```python
    async def execute_task(
        self,
        task_description: str,
        max_steps: int = 100,
        step_callback: Optional[Callable] = None,
    ) -> dict:
        """主入口：通过 ReActLoop 执行任务"""
        if self.context is None:
            raise RuntimeError("AgentEngine not initialized. Call set_device() first.")

        self.context.status = AgentStatus.RUNNING
        self.context.task_description = task_description
        self.context.max_steps = max_steps
        self.context.start_time = time.time()

        # 构建 ReActLoop
        react_loop = ReActLoop(
            ui_extractor=UITreeExtractor(self.device),
            llm_decider=self.decision_layer,
            element_locator=MultiStrategyElementLocator(self.device),
            action_executor=self.action_layer,
            max_iterations=max_steps,
            on_step=step_callback or self._on_step_callback,
        )

        try:
            result = await react_loop.run(
                task=task_description,
                task_id=self.context.task_id,
            )

            self.context.status = AgentStatus.COMPLETED if result["success"] else AgentStatus.ERROR
            self.context.end_time = time.time()
            self.context.steps_completed = result["total_steps"]

            # 验证
            if self.verification_layer:
                v_result = self.verification_layer.verify(result)
                result["verification"] = v_result

            return result

        except Exception as e:
            self.context.status = AgentStatus.ERROR
            self.context.end_time = time.time()
            return {
                "success": False,
                "total_steps": 0,
                "steps": [],
                "history": [],
                "final_message": f"执行异常: {e}",
            }
```

保留 `execute_step()` 单步方法不动（可能被其他地方调用），在内部改为只执行单个 ReAct 迭代。

- [ ] **Step 5: 验证语法**

Run: `python -c "import ast; ast.parse(open('backend/app/core/agent/engine.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/agent/engine.py
git commit -m "feat(core): integrate ReActLoop into AgentEngine.execute_task"
```

---

### Task 7: `api/v1/websocket.py` — 接入真实数据流

**Files:**
- Modify: `backend/app/api/v1/websocket.py`

- [ ] **Step 1: 增强 ConnectionManager**

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        # task_id → set of client_ids
        self.task_subscriptions: Dict[str, set] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        # 清理所有订阅
        for subs in self.task_subscriptions.values():
            subs.discard(client_id)

    def subscribe_task(self, client_id: str, task_id: str):
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(client_id)

    async def send_task_update(self, task_id: str, data: dict):
        """向订阅了该 task 的所有客户端推送更新"""
        subs = self.task_subscriptions.get(task_id, set())
        if not subs:
            return
        message = {
            "type": "agent_step",
            "task_id": task_id,
            "data": data,
        }
        for client_id in list(subs):
            ws = self.active_connections.get(client_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    self.disconnect(client_id)
```

- [ ] **Step 2: 更新 WebSocket 端点支持 subscribe 消息**

```python
@router.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            if msg_type == "subscribe":
                task_id = data.get("task_id")
                if task_id:
                    manager.subscribe_task(client_id, task_id)
                    await manager.send_message(
                        {"type": "subscribed", "task_id": task_id}, client_id
                    )
            elif msg_type == "ping":
                await manager.send_message({"type": "pong"}, client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception:
        manager.disconnect(client_id)
```

- [ ] **Step 3: 现在在 task_service.py 的 task_callback 中调用 WebSocket**

修改 `backend/app/services/task_service.py` 中 `_execute_natural_language_task_bg` 方法，在 step_callback 中推送 WebSocket：

```python
# 在文件顶部导入
from app.api.v1.websocket import manager as ws_manager

# 在回调中添加：
async def _step_callback(data: dict):
    task_id = data.get("task_id")
    if task_id:
        await ws_manager.send_task_update(task_id, data)
    # 写入 DB 日志
    self._log(task_id, "INFO", f"[{data.get('event', '?')}] Step {data.get('step', 0)}: {data.get('action', '')}")
```

- [ ] **Step 4: 验证语法**

Run: `python -c "import ast; ast.parse(open('backend/app/api/v1/websocket.py').read()); print('OK')"; python -c "import ast; ast.parse(open('backend/app/services/task_service.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/websocket.py backend/app/services/task_service.py
git commit -m "feat(api): wire WebSocket to agent execution step_callback"
```

---

### Task 8: `core/script_generator.py` — 脚本生成器

**Files:**
- Create: `backend/app/core/script_generator.py`

- [ ] **Step 1: 实现脚本生成逻辑**

```python
"""从 ReAct 执行轨迹生成 uiautomator2 pytest 脚本。"""

from typing import List, Dict, Any


class ScriptGenerator:
    """将 ReActLoop 的 steps 历史转换为 pytest 自动化脚本。"""

    def generate(self, steps: List[Dict[str, Any]], task_info: Dict[str, Any] = None) -> str:
        """生成可执行的 pytest 脚本"""
        task_info = task_info or {}
        device_serial = task_info.get("device_serial", "emulator-5554")
        task_desc = task_info.get("task_description", "auto_task")

        lines = []
        lines.append('"""')
        lines.append(f"Auto-generated test: {task_desc}")
        lines.append(f"Generated at: {__import__('datetime').datetime.now()}")
        lines.append('"""')
        lines.append("")
        lines.append("import uiautomator2 as u2")
        lines.append("import time")
        lines.append("")
        lines.append("")
        lines.append(f'def test_{self._sanitize_name(task_desc)}():')
        lines.append(f'    d = u2.connect("{device_serial}")')
        lines.append("")

        for i, step in enumerate(steps):
            action = step.get("action", "")
            params = step.get("params", {})
            result = step.get("result", "")
            indent = "    "

            if action == "launch":
                app = params.get("app", "")
                lines.append(f"{indent}# Step {i+1}: 启动 {app}")
                lines.append(f'{indent}d.app_start("{app}")')
                lines.append(f"{indent}time.sleep(2)")

            elif action == "tap":
                x = params.get("x", 0)
                y = params.get("y", 0)
                locator_type = params.get("locator_type", "")
                locator_value = params.get("locator_value", "")

                lines.append(f"{indent}# Step {i+1}: 点击")
                if locator_type == "text":
                    lines.append(f'{indent}element = d(text="{locator_value}")')
                    lines.append(f"{indent}assert element.exists, '元素未找到: {locator_value}'")
                    lines.append(f"{indent}element.click()")
                elif locator_type == "text_contains":
                    lines.append(f'{indent}element = d(textContains="{locator_value}")')
                    lines.append(f"{indent}assert element.exists, '元素未找到: {locator_value}'")
                    lines.append(f"{indent}element.click()")
                elif locator_type == "resource_id":
                    lines.append(f'{indent}element = d(resourceId="{locator_value}")')
                    lines.append(f"{indent}assert element.exists, '元素未找到: {locator_value}'")
                    lines.append(f"{indent}element.click()")
                else:
                    lines.append(f"{indent}d.click({x}, {y})")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "type":
                text = params.get("text", "")
                lines.append(f"{indent}# Step {i+1}: 输入文本")
                lines.append(f'{indent}d.send_keys("{self._escape(text)}")')
                lines.append(f"{indent}time.sleep(1)")

            elif action == "swipe":
                sx = params.get("start_x", 0) or params.get("x", 0)
                sy = params.get("start_y", 0) or params.get("y", 0)
                ex = params.get("end_x", 0)
                ey = params.get("end_y", 0)
                lines.append(f"{indent}# Step {i+1}: 滑动")
                lines.append(f"{indent}d.swipe({sx}, {sy}, {ex}, {ey})")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "back":
                lines.append(f"{indent}# Step {i+1}: 返回")
                lines.append(f"{indent}d.press('back')")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "home":
                lines.append(f"{indent}# Step {i+1}: 回到桌面")
                lines.append(f"{indent}d.press('home')")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "wait":
                duration = params.get("duration", 1)
                lines.append(f"{indent}# Step {i+1}: 等待 {duration}s")
                lines.append(f"{indent}time.sleep({duration})")

            elif action == "finish":
                message = params.get("message", "完成")
                lines.append(f"{indent}# Step {i+1}: 完成 - {message}")

            if result:
                lines.append(f"{indent}# 结果: {result}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _sanitize_name(name: str) -> str:
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff_]', "_", name)
        if not sanitized:
            sanitized = "auto_task"
        return sanitized[:50]

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')
```

- [ ] **Step 2: 验证语法**

Run: `python -c "import ast; ast.parse(open('backend/app/core/script_generator.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/script_generator.py
git commit -m "feat(core): add ScriptGenerator for pytest export from execution traces"
```

---

## 执行要点

### 依赖前提
- 确保 `backend/requirements.txt` 包含 `uiautomator2`（如没有则 `pip install uiautomator2`）
- 确保 Android 设备通过 ADB 连接：`adb devices` 能看到设备

### 端到端验证方式

```bash
# 启动后端
cd backend && python run.py

# 创建任务（API）
curl -X POST http://localhost:8000/api/v1/tasks/natural-language \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "打开淘宝搜索无线耳机",
    "platform": "android",
    "device_id": "emulator-5554",
    "max_steps": 30,
    "mode": "llm"
  }'

# 查看任务日志
curl http://localhost:8000/api/v1/tasks/<task_id>/logs
```

### 需注意的 import 路径
- `react_loop.py` 中的 `from app.core.element_locator import ElementLocator, LocatorType` 是相对 backend 包的导入
- 所有新增模块都位于 `backend/app/core/` 下，符合现有包结构
- 如果 FastAPI 的 PYTHONPATH 有问题，在 `run.py` 中 `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` 确保可以找到 `app.`

### 已知的暂缓事项
- `finder.py` 的内部替换（Task 2 提供了兼容 wrapper，完整替换在后续迭代）
- `manager.py` 的 LLM 规划（当前仍用 heuristic）
- `reflector.py` 的 LLM 反思（当前仍用规则匹配）
