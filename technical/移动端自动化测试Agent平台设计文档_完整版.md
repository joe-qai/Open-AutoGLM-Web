# 移动端自动化测试 Agent 平台技术架构方案

> 基于 Open-AutoGLM + LLM + FastAPI 的前后端分离架构设计
>
> **核心原则**: 元素定位优先，坐标定位作为 fallback
> **模型配置**: 通过数据库动态管理，不硬编码

***

## 一、文档引用说明

| 引用来源     | 文档路径                                              | 主要参考内容                          |
| -------- | ------------------------------------------------- | ------------------------------- |
| **文档 A** | `technical/MobileAgent/Agent平台核心流程与代码提取.md`       | Mobile-Agent-v3.5 核心代码、ReAct 循环 |
| **文档 B** | `technical/MobileAgent/移动端自动化测试Agent设计方案.md`      | 跨平台架构、元素定位器设计                   |
| **文档 C** | `technical/MobileAgent/MCP驱动移动端自动化测试Agent设计方案.md` | 脚本生成、轨迹录制                       |
| **文档 D** | `technical/autoGLM/architecture.md`               | Open-AutoGLM v0.1.0 架构          |
| **文档 E** | `technical/autoGLM/architecture_v2.md`            | LLM/VLM 分离、Tool Registry        |

***

## 二、项目概述

### 2.1 项目目标

| 能力         | 说明                                                 |
| ---------- | -------------------------------------------------- |
| **LLM 驱动** | 使用纯文本 LLM 替代 VLM，降低成本和部署复杂度                        |
| **元素定位优先** | 优先使用 resource\_id/content\_desc/text，坐标作为 fallback |
| **多平台支持**  | Android (uiautomator2)、iOS (WDA)、HarmonyOS (HDC)   |
| **实时日志**   | WebSocket 推送执行过程                                   |
| **脚本导出**   | 自动生成 pytest 格式的 Python 自动化脚本                       |
| **动态模型配置** | 模型配置通过数据库管理，支持多模型切换                                |
| **轻量部署**   | SQLite 数据库，单 backend 服务即可运行                        |

### 2.2 技术选型

| 组件       | 技术选型                     | 说明                     |
| -------- | ------------------------ | ---------------------- |
| **后端框架** | FastAPI                  | 高性能异步 API，支持 WebSocket |
| **数据库**  | SQLite + SQLAlchemy      | 轻量级，无需额外部署             |
| **LLM**  | 国产模型 (Qwen/GLM)          | OpenAI SDK 兼容，统一接口     |
| **实时通信** | WebSocket                | 低延迟任务日志推送              |
| **设备控制** | uiautomator2 / WDA / HDC | 三平台统一适配器模式             |

### 2.3 核心设计原则：元素定位优先策略

```
元素定位优先级（从高到低）:
┌─────────────────────────────────────────────────────────────────────────┐
│  1. resource_id          → 最稳定，跨设备一致                          │
│  2. content_desc         → 辅助描述，适合图标按钮                         │
│  3. text                 → 可见文字，可能存在多语言差异                   │
│  4. class_name + 索引     → 类型定位，需要上下文                          │
│  5. semantic_description  → 语义描述（LLM理解）                          │
│  6. coordinates          → 坐标定位（仅作为 fallback）                   │
└─────────────────────────────────────────────────────────────────────────┘
```

| 定位方式          |  稳定性  | 跨设备 | 多语言 | 适用场景        |
| ------------- | :---: | :-: | :-: | ----------- |
| resource\_id  | ⭐⭐⭐⭐⭐ |  ✅  |  ✅  | 按钮、输入框等稳定元素 |
| content\_desc |  ⭐⭐⭐⭐ |  ✅  |  ⚠️ | 图标、图片按钮     |
| text          |  ⭐⭐⭐  |  ✅  |  ❌  | 文本按钮、标题     |
| class\_name   |   ⭐⭐  |  ⚠️ |  ✅  | 列表项、重复元素    |
| 坐标            |   ⭐   |  ❌  |  ✅  | 万不得已时使用     |

***

## 三、整体架构

### 3.1 架构分层

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React/Vue)                          │
│           任务创建 │ 设备管理 │ 模型配置 │ 实时日志 │ 脚本导出              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ REST API + WebSocket
┌───────────────────────────────────▼────────────────────────────────────────┐
│                              FastAPI Backend                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                          API Layer                            │ │
│  │  POST /api/tasks          ← 创建任务                         │ │
│  │  GET  /api/models         ← 模型配置管理                      │ │
│  │  WS   /ws/logs/{task_id}  ← 实时日志流                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                         Core Layer                                  │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐    │ │
│  │  │   LLMAgent      │  │  ElementLocator │  │  ScriptGenerator   │    │ │
│  │  │  (元素定位推理)  │  │  (多策略定位)    │  │  (元素定位脚本)    │    │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                     Device Abstraction Layer                          │ │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │ │
│  │  │ AndroidAdapter│ │  iOSAdapter   │ │HarmonyOSAdapter│              │ │
│  │  │uiautomator2   │ │     WDA       │ │      HDC      │              │ │
│  │  │ 元素定位优先  │ │  元素定位优先  │ │  元素定位优先  │              │ │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流

```
用户输入任务 → FastAPI POST /api/tasks → Task 创建 (pending)
                   │
                   ▼
              LLMAgent.run() - ReAct 循环
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
 1.获取UI树    2.UI树→文本     3.LLM决策(返回定位器)
                   │
                   ▼
              4.ElementLocator.locate() → 元素定位
                   │
                   ▼
              5.ActionExecutor.execute() → 执行
                   │
                   ▼
              6.WebSocket.send_step() → 推送日志
                   │
                   ▼
              Task completed → ScriptGenerator.generate()
```

***

## 四、详细设计

### 4.1 项目目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 系统配置（非模型配置）
│   │
│   ├── api/                    # API 层
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── tasks.py        # 任务管理 API
│   │   │   ├── devices.py      # 设备管理 API
│   │   │   ├── scripts.py      # 脚本导出 API
│   │   │   └── models.py       # 模型配置管理 API（新增）
│   │   └── ws.py               # WebSocket 端点
│   │
│   ├── core/                   # 核心逻辑
│   │   ├── __init__.py
│   │   ├── agent.py            # Agent 核心（元素定位优先）
│   │   ├── llm_client.py       # LLM 客户端（国产模型）
│   │   ├── ui_tree.py          # UI 树提取器
│   │   ├── element_locator.py  # 多策略元素定位器（新增）
│   │   ├── config_service.py   # 配置管理服务（新增）
│   │   └── script_generator.py # 脚本生成器（元素定位脚本）
│   │
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── schemas.py          # Pydantic 模型
│   │   └── database.py         # SQLite ORM（含 LLMModel 表）
│   │
│   └── adapters/               # 设备适配器
│       ├── __init__.py
│       ├── base.py             # 抽象基类（含元素定位接口）
│       ├── android.py          # Android uiautomator2
│       ├── ios.py              # iOS WDA
│       └── harmonyos.py        # HarmonyOS HDC
│
├── scripts/                    # 生成的脚本存储
├── db/                        # SQLite 数据库
├── logs/                      # 日志目录
├── requirements.txt
└── run.py                      # 启动脚本
```

### 4.2 API 设计

#### 4.2.1 REST API 端点

| 方法       | 路径                         | 说明       | 请求体                     |
| -------- | -------------------------- | -------- | ----------------------- |
| `POST`   | `/api/tasks`               | 创建新任务    | `TaskCreateRequest`     |
| `GET`    | `/api/tasks`               | 列出所有任务   | -                       |
| `GET`    | `/api/tasks/{task_id}`     | 获取任务状态   | -                       |
| `DELETE` | `/api/tasks/{task_id}`     | 取消任务     | -                       |
| `GET`    | `/api/devices`             | 列出可用设备   | -                       |
| `POST`   | `/api/scripts/generate`    | 生成脚本     | `ScriptGenerateRequest` |
| `GET`    | `/api/scripts/{script_id}` | 下载脚本     | -                       |
| `GET`    | `/api/models`              | 获取所有模型配置 | -                       |
| `GET`    | `/api/models/default`      | 获取默认模型   | -                       |
| `POST`   | `/api/models`              | 创建模型配置   | `LLMModelCreate`        |
| `PUT`    | `/api/models/{model_id}`   | 更新模型配置   | `LLMModelUpdate`        |
| `DELETE` | `/api/models/{model_id}`   | 删除模型配置   | -                       |
| `WS`     | `/ws/logs/{task_id}`       | 实时日志流    | -                       |

#### 4.2.2 请求/响应模型

```python
# models/schemas.py

from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

class TaskCreateRequest(BaseModel):
    task: str
    platform: Literal["android", "ios", "harmonyos"]
    device_id: Optional[str] = None
    max_steps: int = 50
    model_name: Optional[str] = None  # 可选：指定使用的模型

class StepInfo(BaseModel):
    step_index: int
    action: str
    locator: Optional[dict]  # 元素定位器信息
    success: bool
    thinking: str
    message: Optional[str] = None
    timestamp: datetime

class TaskResponse(BaseModel):
    task_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    task: str
    platform: str
    device_id: Optional[str]
    current_step: int
    steps: list[StepInfo]
    result_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

class LLMModelCreate(BaseModel):
    name: str
    base_url: str
    api_key: Optional[str] = None
    provider: Optional[str] = None
    description: Optional[str] = None
    is_default: bool = False

class LLMModelResponse(BaseModel):
    id: str
    name: str
    base_url: str
    provider: Optional[str]
    description: Optional[str]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

***

## 五、核心模块设计

### 5.0 ReAct 循环核心流程

```python
# core/react_loop.py

"""
ReAct (Reasoning + Acting) 循环核心实现

流程: 思考 → 决策 → 执行 → 验证 → 反馈
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, Callable
from datetime import datetime
import asyncio

@dataclass
class ReActStep:
    """ReAct 单步执行结果"""
    step_index: int
    phase: Literal["observe", "think", "act", "reflect"]
    ui_state: str           # 当前 UI 状态描述
    thought: str            # 思考过程
    action: str             # 执行的动作
    action_params: dict     # 动作参数
    result: str             # 执行结果
    success: bool           # 是否成功
    timestamp: datetime = field(default_factory=datetime.now)

class ReActLoop:
    """
    ReAct 循环控制器
    
    核心循环:
    ┌─────────────────────────────────────────────────────────────────┐
    │  1. OBSERVE   → 获取当前 UI 状态 (UI Tree)                      │
    │       ↓                                                        │
    │  2. THINK     → LLM 推理决策 (Reasoning)                        │
    │       ↓                                                        │
    │  3. ACT       → 执行动作 (Acting)                               │
    │       ↓                                                        │
    │  4. REFLECT   → 验证结果 (Reflection)                          │
    │       ↓                                                        │
    │  5. 判断是否完成 → 循环或结束                                    │
    └─────────────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        ui_extractor,      # UI 树提取器
        llm_decider,       # LLM 决策器
        element_locator,   # 元素定位器
        action_executor,    # 动作执行器
        max_iterations: int = 50,
        on_step: Optional[Callable[[ReActStep], None]] = None
    ):
        self.ui_extractor = ui_extractor
        self.llm_decider = llm_decider
        self.element_locator = element_locator
        self.action_executor = action_executor
        self.max_iterations = max_iterations
        self.on_step = on_step

    async def run(self, task: str, task_id: str = None) -> dict:
        """
        执行 ReAct 循环
        
        Args:
            task: 用户任务描述
            task_id: 任务 ID (用于日志推送)
            
        Returns:
            执行结果字典
        """
        history = []
        steps_log = []

        for iteration in range(self.max_iterations):
            
            # ========== 1. OBSERVE 阶段 ==========
            step = ReActStep(
                step_index=iteration + 1,
                phase="observe",
                ui_state="",
                thought="",
                action="",
                action_params={},
                result="",
                success=False
            )

            # 获取当前 UI 树并转换为文本
            ui_tree_xml = self.ui_extractor.extract()
            ui_text = self.ui_extractor.to_text(ui_tree_xml)
            step.ui_state = ui_text

            # 推送 OBSERVE 日志
            if self.on_step:
                await self.on_step({
                    "task_id": task_id,
                    "event": "observe",
                    "step": iteration + 1,
                    "ui_summary": self._summarize_ui(ui_text),
                    "timestamp": datetime.now().isoformat()
                })

            # ========== 2. THINK 阶段 ==========
            step.phase = "think"
            
            # 构建 LLM Prompt (详见 5.0.1)
            prompt = self.build_prompt(task, ui_text, history)
            
            # LLM 推理决策
            decision = await self.llm_decider.decide(prompt)
            step.thought = decision.reasoning
            step.action = decision.action
            step.action_params = decision.action_params

            # 推送 THINK 日志
            if self.on_step:
                await self.on_step({
                    "task_id": task_id,
                    "event": "think",
                    "step": iteration + 1,
                    "thought": decision.reasoning,
                    "proposed_action": decision.action,
                    "timestamp": datetime.now().isoformat()
                })

            # ========== 3. ACT 阶段 ==========
            step.phase = "act"
            
            # 元素定位 (详见 5.1)
            target_element = None
            if decision.action in ["tap", "click", "input"]:
                target_element = await self._locate_element(decision)
                step.action_params["element"] = target_element

            # 执行动作
            if decision.action == "finish":
                step.result = decision.finish_message
                step.success = True
                steps_log.append(step)
                break

            exec_result = await self.action_executor.execute(
                action=decision.action,
                params=decision.action_params,
                fallback_coords=decision.fallback_coords
            )
            
            step.result = exec_result.message
            step.success = exec_result.success

            # ========== 4. REFLECT 阶段 ==========
            step.phase = "reflect"
            
            # 验证动作执行结果
            if not step.success:
                # 动作执行失败，记录原因并继续
                step.thought += f"\n[反思] 动作执行失败: {exec_result.message}"
            
            # 记录历史
            history.append({
                "step": iteration + 1,
                "action": step.action,
                "params": step.action_params,
                "result": step.result,
                "success": step.success
            })
            
            steps_log.append(step)

            # 推送 ACT + REFLECT 日志
            if self.on_step:
                await self.on_step({
                    "task_id": task_id,
                    "event": "act",
                    "step": iteration + 1,
                    "action": step.action,
                    "params": step.action_params,
                    "result": step.result,
                    "success": step.success,
                    "timestamp": datetime.now().isoformat()
                })

            # 等待 UI 刷新
            await asyncio.sleep(1.5)

        # 循环结束
        return {
            "success": step.success if steps_log else False,
            "total_steps": len(steps_log),
            "steps": steps_log,
            "history": history,
            "final_message": step.result if step.success else f"达到最大迭代次数 ({self.max_iterations})"
        }

    async def _locate_element(self, decision) -> Optional[dict]:
        """元素定位流程"""
        locator = decision.locator
        
        if not locator:
            return None

        # 尝试精确定位
        result = await self.element_locator.locate(locator)
        if result.success:
            return result.element_info

        # 降级: 尝试语义匹配
        if hasattr(locator, 'semantic_hint'):
            semantic_result = await self.element_locator.locate_sematic(locator.semantic_hint)
            if semantic_result.success:
                return semantic_result.element_info

        # 降级: 使用 fallback 坐标
        if decision.fallback_coords:
            return {
                "x": decision.fallback_coords[0],
                "y": decision.fallback_coords[1],
                "fallback": True
            }

        return None

    def _summarize_ui(self, ui_text: str, max_length: int = 200) -> str:
        """UI 状态摘要"""
        if len(ui_text) <= max_length:
            return ui_text
        return ui_text[:max_length] + "..."

    def build_prompt(self, task: str, ui_text: str, history: list) -> str:
        """构建 LLM Prompt"""
        raise NotImplementedError("请使用具体的 PromptBuilder 实现")
```

### 5.0.1 Prompt 设计（基于 Open-AutoGLM 真实提示词）

```python
# phone_agent/config/prompts_zh.py
# 参考来源：Open-AutoGLM 真实提示词

SYSTEM_PROMPT = """你是一个智能体分析专家，可以根据操作历史和当前状态图执行一系列操作来完成任务。
你必须严格按照要求输出以下格式：
<think>{think}
</think>

<answer>{action}</answer>

其中：
- {think} 是对你为什么选择这个操作的简短推理说明。
- {action} 是本次执行的具体操作指令，必须严格遵循下方定义的指令格式。

操作指令及其作用如下：
- do(action="Launch", app="xxx")  
    Launch是启动目标app的操作，这比通过主屏幕导航更快。此操作完成后，您将自动收到结果状态的截图。
- do(action="Tap", element=[x,y])  
    Tap是点击操作，点击屏幕上的特定点。可用此操作点击按钮、选择项目、从主屏幕打开应用程序，或与任何可点击的用户界面元素进行交互。坐标系统从左上角 (0,0) 开始到右下角（999,999)结束。此操作完成后，您将自动收到结果状态的截图。
- do(action="Tap", element=[x,y], message="重要操作")  
    基本功能同Tap，点击涉及财产、支付、隐私等敏感按钮时触发。
- do(action="Type", text="xxx")  
    Type是输入操作，在当前聚焦的输入框中输入文本。使用此操作前，请确保输入框已被聚焦（先点击它）。输入的文本将像使用键盘输入一样输入。重要提示：手机可能正在使用 ADB 键盘，该键盘不会像普通键盘那样占用屏幕空间。要确认键盘已激活，请查看屏幕底部是否显示 'ADB Keyboard {ON}' 类似的文本，或者检查输入框是否处于激活/高亮状态。不要仅仅依赖视觉上的键盘显示。自动清除文本：当你使用输入操作时，输入框中现有的任何文本都会在输入新文本前自动清除。你无需在输入前手动清除文本——直接使用输入操作输入所需文本即可。操作完成后，你将自动收到结果状态的截图。
- do(action="Type_Name", text="xxx")  
    Type_Name是输入人名的操作，基本功能同Type。
- do(action="Interact")  
    Interact是当有多个满足条件的选项时而触发的交互操作，询问用户如何选择。
- do(action="Swipe", start=[x1,y1], end=[x2,y2])  
    Swipe是滑动操作，通过从起始坐标拖动到结束坐标来执行滑动手势。可用于滚动内容、在屏幕之间导航、下拉通知栏等。坐标系统从左上角 (0,0) 开始到右下角（999,999)结束。滑动持续时间会自动调整以实现自然的移动。此操作完成后，您将自动收到结果状态的截图。
- do(action="Note", message="True")  
    记录当前页面内容以便后续总结。
- do(action="Call_API", instruction="xxx")  
    总结或评论当前页面或已记录的内容。
- do(action="Long Press", element=[x,y])  
    Long Press是长按操作，在屏幕上的特定点长按指定时间。可用于触发上下文菜单、选择文本或激活长按交互。坐标系统从左上角 (0,0) 开始到右下角（999,999)结束。此操作完成后，您将自动收到结果状态的屏幕截图。
- do(action="Double Tap", element=[x,y])  
    Double Tap在屏幕上的特定点快速连续点按两次。使用此操作可以激活双击交互，如缩放、选择文本或打开项目。坐标系统从左上角 (0,0) 开始到右下角（999,999)结束。此操作完成后，您将自动收到结果状态的截图。
- do(action="Take_over", message="xxx")  
    Take_over是接管操作，表示在登录和验证阶段需要用户协助。
- do(action="Back")  
    导航返回到上一个屏幕或关闭当前对话框。相当于按下 Android 的返回按钮。使用此操作可以从更深的屏幕返回、关闭弹出窗口或退出当前上下文。此操作完成后，您将自动收到结果状态的截图。
- do(action="Home") 
    Home是回到系统桌面的操作，相当于按下 Android 主屏幕按钮。使用此操作可退出当前应用并返回启动器。此操作完成后，您将自动收到结果状态的截图。
- do(action="Wait", duration="x seconds")  
    等待页面加载，x为需要等待多少秒。
- finish(message="xxx")  
    finish是结束任务的操作，表示准确完整完成任务，message是终止信息。 

必须遵循的规则：
1. 在执行任何操作前，先检查当前app是否是目标app，如果不是，先执行 Launch。
2. 如果进入到了无关页面，先执行 Back。如果执行Back后页面没有变化，请点击页面左上角的返回键进行返回，或者右上角的X号关闭。
3. 如果页面未加载出内容，最多连续 Wait 三次，否则执行 Back重新进入。
4. 如果页面显示网络问题，需要重新加载，请点击重新加载。
5. 如果当前页面找不到目标联系人、商品、店铺等信息，可以尝试 Swipe 滑动查找。
6. 遇到价格区间、时间区间等筛选条件，如果没有完全符合的，可以放宽要求。
7. 在做小红书总结类任务时一定要筛选图文笔记。
8. 购物车全选后再点击全选可以把状态设为全不选，在做购物车任务时，如果购物车里已经有商品被选中时，你需要点击全选后再点击取消全选，再去找需要购买或者删除的商品。
9. 在做外卖任务时，如果相应店铺购物车里已经有其他商品你需要先把购物车清空再去购买用户指定的外卖。
10. 在做点外卖任务时，如果用户需要点多个外卖，请尽量在同一店铺进行购买，如果无法找到可以下单，并说明某个商品未找到。
11. 请严格遵循用户意图执行任务，用户的特殊要求可以执行多次搜索，滑动查找。
12. 在选择日期时，如果原滑动方向与预期日期越来越远，请向反方向滑动查找。
13. 执行任务过程中如果有多个可选择的项目栏，请逐个查找每个项目栏，直到完成任务，一定不要在同一项目栏多次查找，从而陷入死循环。
14. 在执行下一步操作前请一定要检查上一步的操作是否生效，如果点击没生效，可能因为app反应较慢，请先稍微等待一下，如果还是不生效请调整一下点击位置重试，如果仍然不生效请跳过这一步继续任务，并在finish message说明点击不生效。
15. 在执行任务中如果遇到滑动不生效的情况，请调整一下起始点位置，增大滑动距离重试，如果还是不生效，有可能是已经滑到底了，请继续向反方向滑动，直到顶部或底部，如果仍然没有符合要求的结果，请跳过这一步继续任务，并在finish message说明但没找到要求的项目。
16. 在做游戏任务时如果在战斗页面如果有自动战斗一定要开启自动战斗，如果多轮历史状态相似要检查自动战斗是否开启。
17. 如果没有合适的搜索结果，可能是因为搜索页面不对，请返回到搜索页面的上一级尝试重新搜索，如果尝试三次返回上一级搜索后仍然没有符合要求的结果，执行 finish(message="原因")。
18. 在结束任务前请一定要仔细检查任务是否完整准确的完成，如果出现错选、漏选、多选的情况，请返回之前的步骤进行纠正。
"""
```

### 5.0.2 Tool Registry 动态工具注册机制

**设计来源**：参考 Open-AutoGLM V2 架构的 Tool Registry 机制

```python
# core/tools/registry.py

class Tool:
    """工具基类"""
    name: str = ""
    description: str = ""
    
    def to_prompt(self) -> str:
        """转换为 Prompt 描述"""
        return f"- {self.name}: {self.description}"
    
    def execute(self, **params) -> dict:
        """执行工具"""
        raise NotImplementedError


class ToolRegistry:
    """
    工具注册表：管理所有工具的注册、发现、调用
    
    支持：
    - 统一注册工具接口
    - 按需加载工具实现
    - 动态拼入 System Prompt
    """
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Tool | None:
        """获取工具"""
        return self._tools.get(name)
    
    def execute(self, name: str, **params) -> dict:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{name}' not found")
        return tool.execute(**params)
    
    def list_tools(self) -> list[Tool]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def get_tools_description(self) -> str:
        """获取所有工具描述（用于注入 Prompt）"""
        return "\n".join(t.to_prompt() for t in self._tools.values())


class ToolLoader:
    """
    工具加载器：支持多种加载方式
    """
    
    @staticmethod
    def from_class(tool_class: type) -> Tool:
        """从 Python 类加载"""
        return tool_class()
    
    @staticmethod
    def from_mcp_server(url: str) -> list[Tool]:
        """从 MCP 服务器加载"""
        # TODO: 实现 MCP 服务器工具加载
        pass
    
    @staticmethod
    def from_entry_point(group: str = "phone_agent.tools") -> list[Tool]:
        """从 Python Entry Points 加载（插件机制）"""
        # TODO: 实现插件机制
        pass
    
    @staticmethod
    def from_config(config_path: str) -> list[Tool]:
        """从配置文件加载"""
        # TODO: 实现配置文件加载
        pass
```

### 5.0.3 工具分类设计

#### 感知工具（Perception Tools）

```python
# core/tools/perception/

class UiUnderstandTool(Tool):
    """理解当前屏幕内容，返回结构化文本描述"""
    name = "ui.understand"
    description = "理解当前屏幕内容，返回结构化文本描述（包含元素信息）"
    
    def execute(self, mode: str = "auto", **params) -> dict:
        """
        mode: auto 自动选择 | xml 仅 XML | ocr 仅 OCR | vlm VLM
        """
        ui_tree = self.device.dump_ui_tree()
        return {
            "xml": ui_tree,
            "text": self.ui_extractor.to_text(ui_tree),
            "mode": mode
        }


class UiFindTool(Tool):
    """在屏幕中查找指定元素"""
    name = "ui.find"
    description = "在屏幕中查找指定元素，返回坐标 bounds。method=semantic 时通过 LLM 语义理解定位"
    
    def execute(self, method: str = "text", target: str = "", **params) -> dict:
        """
        method: text | id | desc | semantic | class_name
        """
        locator_type_map = {
            "text": LocatorType.TEXT,
            "id": LocatorType.RESOURCE_ID,
            "desc": LocatorType.CONTENT_DESC,
            "semantic": LocatorType.SEMANTIC,
            "class_name": LocatorType.CLASS_NAME
        }
        
        locator = ElementLocator(
            locator_type=locator_type_map.get(method, LocatorType.SEMANTIC),
            value=target,
            index=params.get("index", 0)
        )
        
        result = self.element_locator.locate(locator)
        return {
            "found": result.success,
            "x": result.x,
            "y": result.y,
            "element": result.element_info
        }
```

#### 执行工具（Device Action Tools）

```python
# core/tools/device/

class DeviceTapCoordinateTool(Tool):
    """点击指定坐标"""
    name = "device.tap"
    description = "点击指定坐标 (x, y)"
    
    def execute(self, x: int, y: int, **params) -> dict:
        success = self.device.tap(x, y)
        return {"success": success, "action": "tap", "coords": [x, y]}


class DeviceTapElementTool(Tool):
    """通过定位方式点击元素"""
    name = "device.tap_element"
    description = "通过定位方式点击元素（内部调用 ui.find + device.tap）"
    
    def execute(self, method: str = "text", target: str = "", **params) -> dict:
        # 先查找元素
        find_result = UiFindTool(device=self.device, ui_extractor=self.ui_extractor).execute(
            method=method, target=target, index=params.get("index", 0)
        )
        
        if not find_result["found"]:
            return {"success": False, "error": "Element not found"}
        
        # 点击元素
        x, y = find_result["x"], find_result["y"]
        success = self.device.tap(x, y)
        
        return {"success": success, "action": "tap_element", "method": method, "target": target}


class DeviceTypeTool(Tool):
    """在当前聚焦的输入框输入文本"""
    name = "device.type"
    description = "在当前聚焦的输入框输入文本"
    
    def execute(self, text: str, **params) -> dict:
        success = self.device.input_text(text)
        return {"success": success, "action": "type", "text": text}


class DeviceSwipeTool(Tool):
    """滑动操作"""
    name = "device.swipe"
    description = "从起点滑动到终点 (start_x, start_y) -> (end_x, end_y)"
    
    def execute(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.8, **params) -> dict:
        success = self.device.swipe(start_x, start_y, end_x, end_y, int(duration * 1000))
        return {"success": success, "action": "swipe", "from": [start_x, start_y], "to": [end_x, end_y]}


class DeviceLaunchTool(Tool):
    """启动应用"""
    name = "device.launch"
    description = "启动指定应用包名"
    
    def execute(self, app: str, **params) -> dict:
        success = self.device.launch_app(app)
        return {"success": success, "action": "launch", "app": app}


class DeviceBackTool(Tool):
    """返回上一页"""
    name = "device.back"
    description = "返回上一页/关闭弹窗"
    
    def execute(self, **params) -> dict:
        success = self.device.press_back()
        return {"success": success, "action": "back"}


class DeviceHomeTool(Tool):
    """回到桌面"""
    name = "device.home"
    description = "回到系统桌面"
    
    def execute(self, **params) -> dict:
        success = self.device.press_home()
        return {"success": success, "action": "home"}


class WaitTool(Tool):
    """等待"""
    name = "device.wait"
    description = "等待指定秒数"
    
    def execute(self, duration: float = 1.0, **params) -> dict:
        import time
        time.sleep(duration)
        return {"success": True, "action": "wait", "duration": duration}


class FinishTool(Tool):
    """完成任务"""
    name = "finish"
    description = "完成任务，输出终止信息"
    
    def execute(self, message: str = "", script: str = "", **params) -> dict:
        return {
            "success": True,
            "action": "finish",
            "message": message,
            "script": script
        }
```

### 5.0.4 工具注册与初始化

```python
# core/tools/__init__.py

def register_all_tools(registry: ToolRegistry, device_adapter, ui_extractor, element_locator):
    """注册所有工具到注册表"""
    
    # 创建共享依赖
    def create_perception_tool(tool_class):
        tool = tool_class()
        tool.device = device_adapter
        tool.ui_extractor = ui_extractor
        tool.element_locator = element_locator
        return tool
    
    def create_device_tool(tool_class):
        tool = tool_class()
        tool.device = device_adapter
        return tool
    
    # 注册感知工具
    registry.register(create_perception_tool(UiUnderstandTool))
    registry.register(create_perception_tool(UiFindTool))
    
    # 注册执行工具
    registry.register(create_device_tool(DeviceTapCoordinateTool))
    registry.register(create_device_tool(DeviceTapElementTool))
    registry.register(create_device_tool(DeviceTypeTool))
    registry.register(create_device_tool(DeviceSwipeTool))
    registry.register(create_device_tool(DeviceLaunchTool))
    registry.register(create_device_tool(DeviceBackTool))
    registry.register(create_device_tool(DeviceHomeTool))
    registry.register(create_device_tool(WaitTool))
    registry.register(create_device_tool(FinishTool))


# 在 Agent 初始化时
def create_agent(config: AgentConfig, device: BaseDeviceAdapter) -> LLMAgent:
    # 创建组件
    ui_extractor = UITreeExtractor(device)
    element_locator = MultiStrategyElementLocator(device)
    
    # 创建工具注册表
    tool_registry = ToolRegistry()
    register_all_tools(tool_registry, device, ui_extractor, element_locator)
    
    # 获取工具描述
    tools_description = tool_registry.get_tools_description()
    
    # 构建完整 System Prompt
    system_prompt = SYSTEM_PROMPT + "\n\n## 可用工具\n" + tools_description
    
    # 创建 LLM 客户端
    llm_client = LLMClient(config.llm_config)
    
    # 创建 Prompt 构建器
    prompt_builder = PromptBuilder(system_prompt=system_prompt)
    
    # 创建 LLM 决策器
    llm_decider = LLMDecider(llm_client, prompt_builder)
    
    # 创建动作执行器
    action_executor = ActionExecutor(tool_registry)
    
    # 创建 ReAct 循环
    react_loop = ReActLoop(
        ui_extractor=ui_extractor,
        llm_decider=llm_decider,
        element_locator=element_locator,
        action_executor=action_executor,
        max_iterations=config.max_steps
    )
    
    return LLMAgent(react_loop=react_loop, tool_registry=tool_registry)
```

### 5.0.5 LLM 与工具的交互协议

```python
# core/llm_client.py

class LLMClient:
    """LLM 客户端 - 支持 Function Calling"""

    # LLM 请求格式
    def chat(self, messages: list[dict], tools: list[dict] = None, **kwargs) -> str:
        request = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 1500)
        }
        
        if tools:
            request["tools"] = tools
        
        response = self.client.chat.completions.create(**request)
        return response.choices[0].message.content


# LLM 与 Agent 的交互示例

# 1. Agent → LLM：请求推理
messages = [
    {"role": "system", "content": SYSTEM_PROMPT + "\n\n## 可用工具\n" + tools_description},
    {"role": "user", "content": f"任务：{task}\n\n当前界面：\n{ui_text}"}
]

# 2. LLM → Agent：返回工具调用
llm_response = {
    "thinking": "当前在桌面，需要启动淘宝",
    "tool_call": {
        "tool": "device.launch",
        "params": {"app": "com.taobao.taobao"}
    }
}

# 3. Agent → Tool：执行工具
tool_result = tool_registry.execute("device.launch", app="com.taobao.taobao")

# 4. Agent → LLM：反馈结果
messages.append({
    "role": "assistant",
    "content": f"<think>{llm_response['thinking']}\n\n<answer>do(tool_call)</answer>"
})
messages.append({
    "role": "function_result",
    "content": json.dumps(tool_result)
})
```

### 5.0.2 UI 树提取与文本转换

```python
# core/ui_tree.py

"""
UI 树提取与文本转换

功能:
1. 从设备提取 UI 树 XML
2. 转换为 LLM 可理解的文本描述
3. 按元素定位优先级组织信息
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class UIElement:
    """UI 元素"""
    resource_id: str = ""
    class_name: str = ""
    text: str = ""
    content_desc: str = ""
    bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)  # [x1, y1, x2, y2]
    enabled: bool = True
    focused: bool = False
    clickable: bool = False
    
    @property
    def center(self) -> Tuple[int, int]:
        return (
            (self.bounds[0] + self.bounds[2]) // 2,
            (self.bounds[1] + self.bounds[3]) // 2
        )
    
    @property
    def has_resource_id(self) -> bool:
        return bool(self.resource_id)
    
    def to_locator_string(self) -> str:
        """转换为定位器字符串"""
        if self.resource_id:
            return f"id={self.resource_id}"
        elif self.content_desc:
            return f"desc={self.content_desc}"
        elif self.text:
            return f"text={self.text}"
        else:
            return f"type={self.class_name.split('.')[-1]}"


class UITreeExtractor:
    """UI 树提取器"""

    def __init__(self, device_adapter):
        self.device = device_adapter

    def extract(self) -> str:
        """提取 UI 树 XML"""
        return self.device.dump_ui_tree()

    def to_text(self, ui_xml: str, max_elements: int = 30) -> str:
        """
        将 UI 树 XML 转换为文本描述
        
        转换原则:
        1. 按元素定位优先级排序 (resource_id > content_desc > text > class_name)
        2. 标注可交互元素 (clickable, enabled)
        3. 包含边界框信息用于 fallback
        """
        elements = self._parse_xml(ui_xml)
        
        # 按优先级排序
        sorted_elements = self._sort_by_priority(elements)
        
        lines = []
        lines.append(f"=== 屏幕概览 ===")
        display = self.device.get_display_info()
        lines.append(f"分辨率: {display.width}x{display.height}")
        lines.append(f"当前应用: {self.device.get_current_app()}")
        lines.append("")
        lines.append("=== 可交互元素 ===")
        
        clickable_elements = [e for e in sorted_elements if e.clickable and e.enabled]
        for i, elem in enumerate(clickable_elements[:max_elements]):
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
        
        if len(clickable_elements) > max_elements:
            lines.append(f"... (还有 {len(clickable_elements) - max_elements} 个元素)")
        
        # 添加文本输入框信息
        input_elements = [e for e in elements if 'EditText' in e.class_name and e.enabled]
        if input_elements:
            lines.append("")
            lines.append("=== 输入框 ===")
            for i, elem in enumerate(input_elements):
                lines.append(f"  [{i}] {elem.resource_id or elem.class_name.split('.')[-1]} @({elem.center[0]},{elem.center[1]})")
        
        return "\n".join(lines)

    def _parse_xml(self, ui_xml: str) -> List[UIElement]:
        """解析 UI 树 XML"""
        elements = []
        
        try:
            # 处理空或无效 XML
            if not ui_xml or not ui_xml.strip():
                return elements
                
            root = ET.fromstring(ui_xml)
            self._parse_element(root, elements)
        except ET.ParseError as e:
            # XML 解析错误，返回原始文本片段
            elements.append(UIElement(text=f"[XML解析失败: {str(e)}]"))
        except Exception as e:
            elements.append(UIElement(text=f"[提取失败: {str(e)}]"))
        
        return elements

    def _parse_element(self, element: ET.Element, results: List[UIElement]):
        """递归解析元素"""
        attrib = element.attrib
        
        # 提取边界框
        bounds_str = attrib.get('bounds', '[0,0][0,0]')
        bounds = self._parse_bounds(bounds_str)
        
        # 创建 UIElement
        ui_elem = UIElement(
            resource_id=attrib.get('resource-id', ''),
            class_name=attrib.get('class', ''),
            text=attrib.get('text', ''),
            content_desc=attrib.get('content-desc', ''),
            bounds=bounds,
            enabled=attrib.get('enabled', 'true') == 'true',
            focused=attrib.get('focused', 'false') == 'true',
            clickable=attrib.get('clickable', 'false') == 'true'
        )
        
        results.append(ui_elem)
        
        # 递归处理子元素
        for child in element:
            self._parse_element(child, results)

    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int, int, int]:
        """解析边界框字符串 [x1,y1][x2,y2]"""
        import re
        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), 
                    int(match.group(3)), int(match.group(4)))
        return (0, 0, 0, 0)

    def _sort_by_priority(self, elements: List[UIElement]) -> List[UIElement]:
        """按元素定位优先级排序"""
        def priority(elem: UIElement) -> tuple:
            # 优先级: resource_id(0) > content_desc(1) > text(2) > class_name(3)
            if elem.resource_id:
                return (0, elem.resource_id)
            elif elem.content_desc:
                return (1, elem.content_desc)
            elif elem.text:
                return (2, elem.text)
            else:
                return (3, elem.class_name)
        
        return sorted(elements, key=priority)


# ========== Android UI 树解析（兼容格式）==========

def parse_android_xml(xml_content: str, display_info, current_app: str) -> dict:
    """Android XML 解析兼容接口"""
    extractor = UITreeExtractor(None)  # display_info 和 current_app 用于补充信息
    
    return {
        "xml": xml_content,
        "display": display_info,
        "current_app": current_app,
        "text": extractor.to_text(xml_content)
    }
```

### 5.1 元素定位器（ElementLocator）

```python
# core/element_locator.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from adapters.base import BaseDeviceAdapter
from enum import Enum

class LocatorType(Enum):
    RESOURCE_ID = "resource_id"
    CONTENT_DESC = "content_desc"
    TEXT = "text"
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

class MultiStrategyElementLocator:
    """多策略元素定位器 - 优先使用元素属性，坐标作为 fallback"""

    def __init__(self, device: BaseDeviceAdapter):
        self.device = device

    def locate(self, locator: ElementLocator) -> LocateResult:
        """定位策略优先级：resource_id > content_desc > text > class_name > semantic > coordinates"""
        
        if locator.locator_type == LocatorType.RESOURCE_ID:
            return self._locate_by_resource_id(locator.value)
        elif locator.locator_type == LocatorType.CONTENT_DESC:
            return self._locate_by_content_desc(locator.value)
        elif locator.locator_type == LocatorType.TEXT:
            return self._locate_by_text(locator.value, locator.index)
        elif locator.locator_type == LocatorType.CLASS_NAME:
            return self._locate_by_class_name(locator.value, locator.index)
        elif locator.locator_type == LocatorType.SEMANTIC:
            return self._locate_by_semantic(locator.value)
        elif locator.locator_type == LocatorType.COORDINATES:
            return self._locate_by_coordinates(locator.value)
        
        return LocateResult(success=False, error_message="Unknown locator type")

    def _locate_by_resource_id(self, resource_id: str) -> LocateResult:
        try:
            result = self.device.find_element_by_resource_id(resource_id)
            if result:
                return LocateResult(success=True, x=result['x'], y=result['y'], element_info=result)
            return LocateResult(success=False, error_message="Element not found")
        except Exception as e:
            return LocateResult(success=False, error_message=str(e))

    def _locate_by_content_desc(self, content_desc: str) -> LocateResult:
        try:
            result = self.device.find_element_by_content_desc(content_desc)
            if result:
                return LocateResult(success=True, x=result['x'], y=result['y'], element_info=result)
            return LocateResult(success=False, error_message="Element not found")
        except Exception as e:
            return LocateResult(success=False, error_message=str(e))

    def _locate_by_text(self, text: str, index: int = 0) -> LocateResult:
        try:
            results = self.device.find_elements_by_text(text)
            if results and index < len(results):
                result = results[index]
                return LocateResult(success=True, x=result['x'], y=result['y'], element_info=result)
            return LocateResult(success=False, error_message=f"Element not found at index {index}")
        except Exception as e:
            return LocateResult(success=False, error_message=str(e))

    def _locate_by_class_name(self, class_name: str, index: int = 0) -> LocateResult:
        try:
            results = self.device.find_elements_by_class_name(class_name)
            if results and index < len(results):
                result = results[index]
                return LocateResult(success=True, x=result['x'], y=result['y'], element_info=result)
            return LocateResult(success=False, error_message=f"Element not found at index {index}")
        except Exception as e:
            return LocateResult(success=False, error_message=str(e))

    def _locate_by_semantic(self, description: str) -> LocateResult:
        # 语义匹配逻辑
        try:
            ui_tree = self.device.dump_ui_tree()
            return self._match_semantic(ui_tree, description)
        except Exception as e:
            return LocateResult(success=False, error_message=str(e))

    def _locate_by_coordinates(self, coords: str) -> LocateResult:
        try:
            x, y = map(int, coords.split(','))
            return LocateResult(success=True, x=x, y=y)
        except Exception as e:
            return LocateResult(success=False, error_message=str(e))
```

### 5.2 设备适配器抽象层

```python
# adapters/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

@dataclass
class DisplayInfo:
    width: int
    height: int
    density: float

class BaseDeviceAdapter(ABC):
    """设备适配器抽象基类 - 增强元素定位接口"""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id

    # 基础操作
    @abstractmethod
    def screenshot(self, save_path: str) -> str:
        pass

    @abstractmethod
    def tap(self, x: int, y: int) -> bool:
        pass

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 800) -> bool:
        pass

    @abstractmethod
    def input_text(self, text: str) -> bool:
        pass

    @abstractmethod
    def press_back(self) -> bool:
        pass

    @abstractmethod
    def press_home(self) -> bool:
        pass

    @abstractmethod
    def launch_app(self, package_name: str) -> bool:
        pass

    # 元素定位接口（新增）
    @abstractmethod
    def find_element_by_resource_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_element_by_content_desc(self, content_desc: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_elements_by_text(self, text: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_elements_by_class_name(self, class_name: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def dump_ui_tree(self) -> str:
        pass

    @abstractmethod
    def get_display_info(self) -> DisplayInfo:
        pass

    @abstractmethod
    def get_current_app(self) -> str:
        pass
```

### 5.3 Android 适配器（元素定位实现）

```python
# adapters/android.py

import uiautomator2 as u2
from adapters.base import BaseDeviceAdapter, DisplayInfo
from typing import Optional, List, Dict, Any

class AndroidAdapter(BaseDeviceAdapter):
    """Android 设备适配器 - 基于 uiautomator2，元素定位优先"""

    def __init__(self, device_id: Optional[str] = None):
        super().__init__(device_id)
        self._device = u2.connect(device_id)

    # 元素定位实现
    def find_element_by_resource_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        try:
            element = self._device(resourceId=resource_id)
            if element.exists:
                bounds = element.info.get('bounds', {})
                x1, y1 = bounds.get('left', 0), bounds.get('top', 0)
                x2, y2 = bounds.get('right', 0), bounds.get('bottom', 0)
                return {
                    'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2,
                    'bounds': [x1, y1, x2, y2],
                    'text': element.info.get('text', ''),
                    'enabled': element.info.get('enabled', True)
                }
            return None
        except Exception:
            return None

    def find_element_by_content_desc(self, content_desc: str) -> Optional[Dict[str, Any]]:
        try:
            element = self._device(description=content_desc)
            if element.exists:
                bounds = element.info.get('bounds', {})
                x1, y1 = bounds.get('left', 0), bounds.get('top', 0)
                x2, y2 = bounds.get('right', 0), bounds.get('bottom', 0)
                return {
                    'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2,
                    'bounds': [x1, y1, x2, y2],
                    'text': element.info.get('text', ''),
                    'enabled': element.info.get('enabled', True)
                }
            return None
        except Exception:
            return None

    def find_elements_by_text(self, text: str) -> List[Dict[str, Any]]:
        results = []
        try:
            elements = self._device(text=text)
            for elem in elements:
                if elem.exists:
                    bounds = elem.info.get('bounds', {})
                    x1, y1 = bounds.get('left', 0), bounds.get('top', 0)
                    x2, y2 = bounds.get('right', 0), bounds.get('bottom', 0)
                    results.append({
                        'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2,
                        'bounds': [x1, y1, x2, y2],
                        'text': elem.info.get('text', ''),
                        'enabled': elem.info.get('enabled', True)
                    })
        except Exception:
            pass
        return results

    def find_elements_by_class_name(self, class_name: str) -> List[Dict[str, Any]]:
        results = []
        try:
            elements = self._device(className=class_name)
            for elem in elements:
                if elem.exists:
                    bounds = elem.info.get('bounds', {})
                    x1, y1 = bounds.get('left', 0), bounds.get('top', 0)
                    x2, y2 = bounds.get('right', 0), bounds.get('bottom', 0)
                    results.append({
                        'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2,
                        'bounds': [x1, y1, x2, y2],
                        'text': elem.info.get('text', ''),
                        'enabled': elem.info.get('enabled', True)
                    })
        except Exception:
            pass
        return results

    # 基础操作实现
    def screenshot(self, save_path: str) -> str:
        self._device.screenshot(save_path)
        return save_path

    def tap(self, x: int, y: int) -> bool:
        self._device.click(x, y)
        return True

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 800) -> bool:
        self._device.swipe(x1, y1, x2, y2, duration_ms / 1000)
        return True

    def input_text(self, text: str) -> bool:
        self._device.set_fastinput_ime(True)
        self._device.send_keys(text)
        self._device.set_fastinput_ime(False)
        return True

    def press_back(self) -> bool:
        self._device.press("back")
        return True

    def press_home(self) -> bool:
        self._device.press("home")
        return True

    def launch_app(self, package_name: str) -> bool:
        return self._device.app_launch(package_name)

    def dump_ui_tree(self) -> str:
        return self._device.dump_xml()

    def get_display_info(self) -> DisplayInfo:
        info = self._device.info
        return DisplayInfo(width=info["screenWidth"], height=info["screenHeight"], density=info["displayDensity"])

    def get_current_app(self) -> str:
        return self._device.current_app().get("package", "")
```

### 5.4 LLM 客户端（元素定位提示词）

```python
# core/llm_client.py

from openai import OpenAI
from dataclasses import dataclass
import json
from core.element_locator import ElementLocator, LocatorType

@dataclass
class LLMConfig:
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "qwen2.5-7b-instruct"

@dataclass
class LLMDecision:
    thinking: str
    action: str
    locator: ElementLocator
    fallback_coords: Tuple[int, int] | None = None
    should_finish: bool = False
    finish_message: str = ""

class LLMClient:
    """LLM 客户端 - 元素定位优先版本"""

    SYSTEM_PROMPT = """你是一个手机自动化测试的 AI 规划专家。

【定位策略优先级】请优先选择以下定位方式（从高到低）：
1. resource_id - 最稳定，跨设备一致
2. content_desc - 适合图标按钮
3. text - 可见文字
4. class_name + 索引 - 类型定位

【可用动作】
- tap(locator): 点击元素，locator格式: {"type": "resource_id/text/content_desc/class_name", "value": "值", "index": 0}
- input(text): 在当前焦点输入文本
- swipe(direction): 滑动方向（up/down/left/right）
- back(): 返回
- home(): 主页
- launch(app_name): 启动应用
- finish(message): 完成任务

请以 JSON 格式返回决策:
{
  "thinking": "推理过程",
  "action": "动作名称",
  "locator": {"type": "定位类型", "value": "标识符", "index": 0},
  "fallback_coords": [x, y]
}
"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(base_url=config.base_url, api_key=config.api_key)

    def decide(self, ui_description: str, task: str, history: list[dict]) -> LLMDecision:
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"【任务】\n{task}\n\n【当前界面】\n{ui_description}"},
        ]
        
        if history:
            history_text = "\n".join([f"  {i+1}. {h['action']} → {h.get('result', 'unknown')}" 
                                      for i, h in enumerate(history[-5:])])
            messages.append({"role": "assistant", "content": f"【最近步骤】\n{history_text}"})

        response = self.client.chat.completions.create(
            model=self.config.model_name, messages=messages, temperature=0.1, max_tokens=1000
        )
        
        return self._parse_decision(response.choices[0].message.content)

    def _parse_decision(self, content: str) -> LLMDecision:
        try:
            data = json.loads(content)
            action = data.get("action", "").lower().strip()
            
            locator_data = data.get("locator")
            locator = None
            if locator_data:
                type_map = {
                    "resource_id": LocatorType.RESOURCE_ID,
                    "content_desc": LocatorType.CONTENT_DESC,
                    "text": LocatorType.TEXT,
                    "class_name": LocatorType.CLASS_NAME,
                }
                locator = ElementLocator(
                    locator_type=type_map.get(locator_data.get("type"), LocatorType.SEMANTIC),
                    value=locator_data.get("value", ""),
                    index=locator_data.get("index", 0)
                )

            fallback_coords = data.get("fallback_coords")
            if fallback_coords and len(fallback_coords) >= 2:
                fallback_coords = (fallback_coords[0], fallback_coords[1])

            return LLMDecision(
                thinking=data.get("thinking", ""),
                action=action,
                locator=locator,
                fallback_coords=fallback_coords,
                should_finish=action == "finish",
                finish_message=data.get("finish_message", "")
            )
        except json.JSONDecodeError:
            return LLMDecision(thinking=content[:200], action="unknown", locator=None)
```

### 5.5 Agent 核心（元素定位优先执行）

```python
# core/agent.py

from dataclasses import dataclass, field
from typing import Callable, Optional, Literal
from adapters.base import BaseDeviceAdapter
from core.llm_client import LLMClient, LLMConfig, LLMDecision
from core.element_locator import MultiStrategyElementLocator, LocateResult
from core.ui_tree import ui_tree_to_text, parse_android_xml
import asyncio
from datetime import datetime

@dataclass
class AgentConfig:
    max_steps: int = 50
    platform: Literal["android", "ios", "harmonyos"] = "android"
    device_id: Optional[str] = None
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    model_name: Optional[str] = None  # 可选：指定模型
    on_step: Callable[[dict], None] | None = None

@dataclass
class AgentResult:
    success: bool
    message: str
    steps: list[dict] = field(default_factory=list)
    total_steps: int = 0

class LLMAgent:
    """基于 LLM + 元素定位的 Agent"""

    def __init__(self, config: AgentConfig, device: BaseDeviceAdapter):
        self.config = config
        self.device = device
        self.llm = LLMClient(config.llm_config)
        self.element_locator = MultiStrategyElementLocator(device)
        self.history: list[dict] = []
        self._running = False

    async def run(self, task: str) -> AgentResult:
        self._running = True
        self.history = []

        for step in range(self.config.max_steps):
            if not self._running:
                break

            # 1. 获取 UI 树
            ui_tree = self._extract_ui_tree()
            
            # 2. UI 树 → 文本描述
            ui_text = ui_tree_to_text(ui_tree)

            # 3. LLM 决策
            decision = self.llm.decide(ui_text, task, self.history)

            # 4. 检查完成
            if decision.should_finish:
                return AgentResult(success=True, message=decision.finish_message or "任务完成",
                                  steps=self.history, total_steps=step + 1)

            # 5. 元素定位 + 执行
            result = self._execute_action_with_locator(decision)

            # 6. 记录历史
            self.history.append({
                "step": step,
                "action": decision.action,
                "locator": {"type": decision.locator.locator_type.value, "value": decision.locator.value} 
                           if decision.locator else None,
                "result": "success" if result else "failed",
                "thinking": decision.thinking
            })

            await asyncio.sleep(1)

        return AgentResult(success=False, message=f"达到最大步数限制 ({self.config.max_steps})",
                          steps=self.history, total_steps=self.config.max_steps)

    def _execute_action_with_locator(self, decision: LLMDecision) -> bool:
        """使用元素定位器执行动作"""
        action = decision.action
        locator = decision.locator
        fallback_coords = decision.fallback_coords

        # 第一步：尝试元素定位
        coord = None
        if locator:
            locate_result = self.element_locator.locate(locator)
            if locate_result.success:
                coord = (locate_result.x, locate_result.y)

        # 第二步：使用 fallback 坐标
        if coord is None and fallback_coords:
            coord = fallback_coords

        # 第三步：执行动作
        try:
            if action == "tap" and coord:
                self.device.tap(coord[0], coord[1])
                return True
            elif action == "input":
                self.device.input_text(decision.locator.value if decision.locator else "")
                return True
            elif action == "swipe" and decision.locator:
                direction = decision.locator.value
                display = self.device.get_display_info()
                if direction == "up":
                    self.device.swipe(display.width//2, display.height*3//4, display.width//2, display.height//4)
                elif direction == "down":
                    self.device.swipe(display.width//2, display.height//4, display.width//2, display.height*3//4)
                return True
            elif action == "back":
                self.device.press_back()
                return True
            elif action == "home":
                self.device.press_home()
                return True
            elif action == "launch" and decision.locator:
                self.device.launch_app(decision.locator.value)
                return True
        except Exception as e:
            print(f"Action execution failed: {e}")
        
        return False

    def _extract_ui_tree(self):
        xml = self.device.dump_ui_tree()
        display = self.device.get_display_info()
        current_app = self.device.get_current_app()
        return parse_android_xml(xml, display, current_app)
```

### 5.6 脚本生成器（元素定位脚本）

```python
# core/script_generator.py

class UIAutomator2Generator:
    """Android uiautomator2 脚本生成器 - 元素定位优先"""

    def generate(self, steps: list[dict], task: str = "") -> str:
        lines = [
            "# -*- coding: utf-8 -*-",
            f"# 任务: {task}",
            "# 框架: uiautomator2 (元素定位优先)",
            "",
            "import uiautomator2 as u2",
            "import time",
            "import pytest",
            "",
            "class TestAndroidAutomation:",
            "    @classmethod",
            "    def setup_class(cls):",
            "        cls.device = u2.connect()",
            "",
        ]

        for i, step in enumerate(steps, 1):
            action = step.get('action', '')
            locator = step.get('locator', {})

            lines.append(f"    def test_step_{i}(self):")
            lines.append(f"        '''{step.get('thinking', '')}'''")

            if action == 'tap':
                locator_type = locator.get('type')
                value = locator.get('value', '')
                if locator_type == 'resource_id':
                    lines.append(f"        self.device(resourceId='{value}').click()")
                elif locator_type == 'content_desc':
                    lines.append(f"        self.device(description='{value}').click()")
                elif locator_type == 'text':
                    lines.append(f"        self.device(text='{value}').click()")
                elif locator_type == 'class_name':
                    index = locator.get('index', 0)
                    lines.append(f"        self.device(className='{value}')[{index}].click()")

            elif action == 'input':
                text = locator.get('value', '')
                lines.append(f"        self.device.set_fastinput_ime(True)")
                lines.append(f"        self.device.send_keys('{text}')")
                lines.append(f"        self.device.set_fastinput_ime(False)")

            elif action == 'swipe':
                direction = locator.get('value', 'up')
                lines.append(f"        self.device.swipe_ext('{direction}')")

            elif action == 'back':
                lines.append(f"        self.device.press('back')")

            elif action == 'home':
                lines.append(f"        self.device.press('home')")

            elif action == 'launch':
                package = locator.get('value', '')
                lines.append(f"        self.device.app_launch('{package}')")

            lines.append(f"        time.sleep(1)")
            lines.append("")

        lines.extend([
            "if __name__ == '__main__':",
            "    pytest.main([__file__, '-v', '-s'])",
        ])

        return "\n".join(lines)
```

### 5.7 WebSocket 实时日志

```python
# api/ws.py

from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections and websocket in self.active_connections[task_id]:
            self.active_connections[task_id].remove(websocket)

    async def send_step(self, task_id: str, data: dict):
        if task_id not in self.active_connections:
            return
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_json(data)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws/logs/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "cancel":
                    await manager.send_step(task_id, {"event": "cancelled"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
```

### 5.8 数据库设计（含模型配置表）

```python
# models/database.py

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./autoglm.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    task_text = Column(Text, nullable=False)
    platform = Column(String, nullable=False)
    device_id = Column(String)
    model_name = Column(String)  # 使用的模型名称
    status = Column(String, default="pending")
    current_step = Column(Integer, default=0)
    max_steps = Column(Integer, default=50)
    result_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    steps = relationship("TaskStep", back_populates="task")

class TaskStep(Base):
    __tablename__ = "task_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    step_index = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    locator = Column(Text)  # JSON 字符串：元素定位器
    success = Column(Boolean)
    thinking = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    task = relationship("Task", back_populates="steps")

class LLMModel(Base):
    """LLM 模型配置表 - 支持多模型动态管理"""
    __tablename__ = "llm_models"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    base_url = Column(String, nullable=False)
    api_key = Column(String)
    provider = Column(String)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

class Script(Base):
    __tablename__ = "scripts"
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    platform = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    name = Column(String)
    status = Column(String, default="available")
    last_seen = Column(DateTime)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
```

### 5.9 配置管理（不硬编码模型配置）

#### 5.9.1 配置管理服务

```python
# core/config_service.py

from sqlalchemy.orm import Session
from models.database import LLMModel
from core.llm_client import LLMConfig, LLMClient

class ConfigService:
    """配置管理服务 - 动态获取模型配置"""

    def __init__(self, db: Session):
        self.db = db

    def get_default_llm_config(self) -> LLMConfig:
        """获取默认 LLM 配置"""
        model = self.db.query(LLMModel).filter(LLMModel.is_default == True).first()
        if not model:
            model = self.db.query(LLMModel).filter(LLMModel.is_active == True).first()
        
        if not model:
            return LLMConfig()  # fallback
        
        return LLMConfig(
            base_url=model.base_url,
            api_key=model.api_key or "EMPTY",
            model_name=model.name
        )

    def get_llm_config_by_name(self, model_name: str) -> LLMConfig:
        """根据模型名称获取配置"""
        model = self.db.query(LLMModel).filter(
            LLMModel.name == model_name, LLMModel.is_active == True
        ).first()
        
        if not model:
            raise ValueError(f"模型 {model_name} 不存在或未启用")
        
        return LLMConfig(
            base_url=model.base_url,
            api_key=model.api_key or "EMPTY",
            model_name=model.name
        )

    def create_llm_client(self, model_name: str = None) -> LLMClient:
        """创建 LLM 客户端（支持动态模型切换）"""
        if model_name:
            config = self.get_llm_config_by_name(model_name)
        else:
            config = self.get_default_llm_config()
        
        return LLMClient(config)
```

#### 5.9.2 系统配置

```python
# app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache

class SystemSettings(BaseSettings):
    """系统级配置（非模型配置）"""
    
    database_url: str = "sqlite:///./autoglm.db"
    android_adb_path: str = "adb"
    ios_wda_url: str = "http://localhost:8100"
    harmonyos_hdc_path: str = "hdc"
    max_steps: int = 50
    default_platform: str = "android"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    log_dir: str = "./logs"

    class Config:
        env_file = ".env"

@lru_cache
def get_system_settings():
    return SystemSettings()
```

***

## 六、脚本生成对比

### 元素定位脚本（推荐）

```python
# uiautomator2 元素定位脚本
def test_login(self):
    # 点击登录按钮（通过 resource_id）
    self.device(resourceId='com.example:id/btn_login').click()
    
    # 输入用户名（通过 resource_id）
    self.device(resourceId='com.example:id/et_username').set_text('testuser')
    
    # 输入密码（通过 resource_id）
    self.device(resourceId='com.example:id/et_password').set_text('password')
    
    # 点击提交按钮（通过文本）
    self.device(text='登录').click()
```

### 坐标定位脚本（fallback）

```python
# 坐标定位脚本（不推荐）
def test_login(self):
    self.device.click(540, 1200)  # 仅在特定分辨率下有效
    self.device.click(540, 1500)
    self.device.send_keys('testuser')
    self.device.click(540, 1800)
    self.device.send_keys('password')
    self.device.click(540, 2100)
```

***

## 七、实现优先级

| 阶段          | 模块                    | 优先级 | 说明     |
| ----------- | --------------------- | :-: | ------ |
| **Phase 1** | FastAPI 框架 + 任务 CRUD  |  P0 | <br /> |
| **Phase 1** | 模型配置 API + LLMModel 表 |  P0 | 动态配置核心 |
| **Phase 1** | Android 元素定位器         |  P0 | 核心能力   |
| **Phase 1** | Android Agent（元素定位优先） |  P0 | <br /> |
| **Phase 2** | iOS/HarmonyOS 适配器     |  P1 | <br /> |
| **Phase 2** | 元素定位脚本生成              |  P1 | <br /> |
| **Phase 2** | WebSocket 日志推送        |  P2 | <br /> |
| **Phase 3** | 前端 Web UI             |  P2 | <br /> |

***

## 八、文档参考汇总

| 设计模块         | 参考文档                     |
| ------------ | ------------------------ |
| 元素定位器设计      | 文档 B「元素定位器设计」章节          |
| 设备适配层        | 文档 B「平台适配层设计」章节          |
| Android 元素定位 | 文档 A「ADB 设备控制类」章节        |
| iOS 元素定位     | 文档 D「xctest 模块」章节        |
| 脚本生成         | 文档 C「脚本生成」章节             |
| LLM 规划器      | 文档 B、E「LLM 规划器」章节        |
| Agent 主循环    | 文档 A、E「Agent 主循环/Core」章节 |

***

## 九、总结

**核心特性**：

| 特性         | 说明                                                     |
| ---------- | ------------------------------------------------------ |
| **元素定位优先** | resource\_id > content\_desc > text > class\_name > 坐标 |
| **动态模型配置** | 通过数据库管理，支持多模型切换，不硬编码                                   |
| **前后端分离**  | FastAPI + WebSocket + SQLite                           |
| **跨平台支持**  | Android (uiautomator2)、iOS (WDA)、HarmonyOS (HDC)       |
| **实时日志**   | WebSocket 推送执行步骤                                       |
| **脚本导出**   | 自动生成 pytest 格式脚本                                       |

**设计亮点**：

1. 元素定位策略确保脚本稳定性和可维护性
2. 模型配置动态化，支持运行时切换模型
3. 优雅降级机制：元素定位失败时自动使用 fallback 坐标
4. 标准化接口设计，便于扩展新平台和新模型

