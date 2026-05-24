# Open-AutoGLM 二开开发方案：自动化测试 Agent 平台

> 基于 v0.1.0 源码，以最小改动、最快验证、渐进增强的方式改造为自动化测试脚本平台。

---

## 目录

- [1. 总体策略](#1-总体策略)
- [2. 阶段一：基础设施 & 核心循环](#2-阶段一基础设施--核心循环)
- [3. 阶段二：感知 & 定位层](#3-阶段二感知--定位层)
- [4. 阶段三：验证 & 自愈](#4-阶段三验证--自愈)
- [5. 阶段四：脚本录制 & 编译](#5-阶段四脚本录制--编译)
- [6. 阶段五：前端开发](#6-阶段五前端开发)
- [7. 阶段六：报告系统](#7-阶段六报告系统)
- [8. 阶段七：多设备调度](#8-阶段七多设备调度)
- [9. 端到端验收场景](#9-端到端验收场景)
- [10. 现有代码复用清单](#10-现有代码复用清单)
- [11. 新增代码清单](#11-新增代码清单)
- [12. 测试策略](#12-测试策略)
- [13. 核心风险前置验证实验](#13-核心风险前置验证实验)
- [14. 里程碑 & 交付物](#14-里程碑--交付物)

---

## 1. 总体策略

### 1.1 核心原则

```
1. 不动现有可用的代码：adb/ hdc/ xctest/ DeviceFactory 等驱动层全部保持原样
2. 新增目录，不改旧模块：新代码放在新目录中，通过 import 引用旧模块
3. 渐进替换：Agent 主循环从 v0 逐步迁移到 v2，中间可以共存
4. 每阶段可验证：每个阶段结束时都有可运行、可测试的产出
```

### 1.2 源码目录结构变化

```
phone_agent/
├── __init__.py          # 导出 PhoneAgent（v0）和 NewAgent（v2）
│
├── agent.py             # v0.1.0 PhoneAgent — 不动
├── agent_ios.py         # v0.1.0 IOSPhoneAgent — 不动
├── device_factory.py    # v0.1.0 DeviceFactory — 不动
│
├── adb/                 # v0.1.0 — 不动
├── hdc/                 # v0.1.0 — 不动
├── xctest/              # v0.1.0 — 不动
│
├── model/               # v0.1.0 — 增加 Function Calling 支持
│   ├── __init__.py      # 不动
│   └── client.py        # [改] 增加 stream_function_call()
│
├── config/              # 增加工具描述等
│   ├── __init__.py      # [改] 增加导入
│   ├── prompts_zh.py    # [改] v2 的 system prompt
│   ├── tools_description.py  # [新] 工具描述
│   └── ...              # 其余不动
│
├── actions/             # v0.1.0 — 不动
│   └── handler.py       # 保留，v2 新方案不再走这里
│
├── NEW: core/           # 新的 Agent 核心
├── NEW: tools/          # 工具注册表
├── NEW: perception/     # 感知引擎
├── NEW: verify/         # 验证层
├── NEW: script/         # 脚本系统
├── NEW: report/         # 报告输出
├── NEW: orchestrator/   # 多设备调度
├── NEW: web/            # Web 前端 + API 后端
│
└── tests/               # [新] 测试目录
    ├── test_tools/
    ├── test_perception/
    ├── test_compiler/
    └── ...
```

### 1.3 与 v0 主循环共存策略

```
# 独立入口，互不干扰：
# main.py          → 走原来的 PhoneAgent（完全不动）
# main_v2.py       → 走新的 NewAgent

# PhoneAgent（v0）：保持不变，原有用户不受影响
# NewAgent（v2）：新代码，逐步替代
```

#### `main_v2.py` — 独立入口

```python
"""v2 独立入口，与 main.py 完全解耦。"""

import argparse

def main():
    parser = argparse.ArgumentParser(prog="open-autoglm-v2")
    parser.add_argument("prompt", nargs="?", default="",
                        help="自然语言任务描述")
    parser.add_argument("--web", action="store_true",
                        help="启动 Web 服务")
    parser.add_argument("--port", type=int, default=8000,
                        help="Web 端口 (默认 8000)")
    parser.add_argument("--device", type=str, default="",
                        help="指定设备 ID (默认自动检测)")
    parser.add_argument("--script", type=str, default="",
                        help="批量回放脚本目录")
    args = parser.parse_args()

    if args.web:
        from phone_agent.web.main import start_web
        start_web(port=args.port)
    elif args.script:
        from phone_agent.orchestrator.replay import batch_run
        batch_run(args.script, device_id=args.device)
    else:
        from phone_agent.core.agent import NewAgent
        agent = NewAgent(device_id=args.device)
        result = agent.run(args.prompt)
        print(result.python_script)
        if result.yaml_archive:
            with open("output.yaml", "w") as f:
                f.write(result.yaml_archive)

if __name__ == "__main__":
    main()
```

**三种运行模式**：

```bash
# 模式 1：CLI 单次执行
python main_v2.py "打开微信给张三发消息"

# 模式 2：Web 服务
python main_v2.py --web --port 8000

# 模式 3：批量回放脚本
python main_v2.py --script ./scripts/ --device emulator-5554
```

---

### 1.4 新增依赖清单

> 全量强依赖，`pip install phone-agent` 一步安装所有。

#### Python 依赖

| 依赖 | 版本 | 用途 | 所属阶段 |
|------|------|------|---------|
| `uiautomator2` | >=3.0.0 | Android UI dump（感知） | P2 |
| `lxml` | >=5.0.0 | XML 解析（dump 结果） | P2 |
| `Pillow` | >=10.0.0 | 截图对比 | P3 |
| `numpy` | >=1.24.0 | 像素级 diff | P3 |
| `PyYAML` | >=6.0 | YAML 备案输出 | P4 |
| `fastapi` | >=0.110.0 | REST + WebSocket API | P5 |
| `uvicorn[standard]` | >=0.27.0 | ASGI 服务器 | P5 |
| `websockets` | >=12.0 | WebSocket 协议 | P5 |
| `python-multipart` | >=0.0.9 | 文件上传 | P5 |
| `weasyprint` | >=62 | HTML → PDF 报告 | P6 |
| `jinja2` | >=3.1 | 报告模板引擎 | P6 |
| `pytest-asyncio` | >=0.24.0 | 异步测试 | 测试 |

#### Node.js 依赖（前端）

```json
{
  "dependencies": {
    "react": "^19.0.0", "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "antd": "^5.22.0", "@ant-design/icons": "^5.5.0",
    "zustand": "^5.0.0", "dayjs": "^1.11.0"
  },
  "devDependencies": {
    "vite": "^6.0.0", "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "@types/react": "^19.0.0", "@types/react-dom": "^19.0.0"
  }
}
```

---

## 2. 阶段一：基础设施 & 核心循环

**目标**：让纯文本 LLM 能通过 Tool Registry 完成简单任务。这是技术可行性验证阶段。

**耗时**：5-7 天

**验证标准**：LLM 收到 `"打开微信"` 后，能正确调用 `device.launch(app="微信")` 并执行成功。

---

### 2.1 新增：`phone_agent/core/`

```
core/
├── __init__.py
├── planner.py           # LLM 规划器
├── agent.py             # NewAgent (v2 主类)
└── config.py            # NewAgentConfig
```

#### `core/planner.py` — LLM 规划器

```python
"""LLM 规划器：接收结构化感知输入，输出 Function Calling 指令。"""

class LLMPlanner:
    """
    封装 ModelClient，增加 Function Calling 支持。

    输入: 系统提示词 + 工具描述 + 感知结果（结构化文本）
    输出: {"tool": "tool_name", "params": {...}}
    """

    def __init__(self, model_config: ModelConfig):
        self.client = ModelClient(model_config)  # 复用 v0 的 ModelClient
        self.system_prompt = self._build_system_prompt()
        self.tools_description = ""

    def plan(self, context: PluginContext) -> ToolCall:
        """
        核心方法：接收上下文，输出工具调用。

        Args:
            context: 包含系统提示、对话历史、感知结果

        Returns:
            ToolCall: {"tool": str, "params": dict}
        """
        messages = self._build_messages(context)
        # 使用 v0 ModelClient 的流式请求，但解析 Function Calling 格式
        response = self.client.request(messages)
        return self._parse_tool_call(response.action)
```

#### `core/agent.py` — NewAgent 主类

```python
"""NewAgent: v2 核心主循环，与 v0 PhoneAgent 同名不同包。"""

class NewAgent:
    """
    Agent + Tools 架构的新 Agent。

    复用原则:
    - ModelClient     → 来自 phone_agent.model（改）
    - DeviceFactory   → 来自 phone_agent.device_factory（不动）
    - adb.hdc.xctest  → 通过 DeviceFactory 调用（不动）
    """

    def __init__(self, model_config: ModelConfig,
                 tools: list[Tool] | None = None):
        self.planner = LLMPlanner(model_config)
        self.registry = ToolRegistry()
        self.device = get_device_factory()  # 复用 v0

        # 注册默认工具
        self._register_default_tools()
        # 注册自定义工具
        if tools:
            for t in tools:
                self.registry.register(t)

    def _register_default_tools(self):
        """注册基础工具集，复用 v0 的 DeviceFactory 实现"""
        # 感知工具
        self.registry.register(UiUnderstandTool(self.device))
        self.registry.register(UiFindTool(self.device))
        # 执行工具（直接包装 DeviceFactory 方法）
        self.registry.register(DeviceTapTool(self.device))
        self.registry.register(DeviceTypeTool(self.device))
        self.registry.register(DeviceLaunchTool(self.device))
        self.registry.register(DeviceSwipeTool(self.device))
        self.registry.register(DeviceBackTool(self.device))
        self.registry.register(DeviceHomeTool(self.device))
        self.registry.register(WaitTool())
        # 辅助工具
        self.registry.register(FinishTool())

    def run(self, task: str) -> ExecutionResult:
        """执行任务，产出脚本。"""
        self.recorder = ScriptRecorder()

        while not self._should_stop():
            # 1. 感知当前屏幕
            screen = self._perceive()

            # 2. LLM 规划 → 工具调用
            action = self.planner.plan(task, screen)

            # 3. 执行工具
            result = self.registry.call(action["tool"], **action["params"])

            # 4. 验证
            verified = self.verifier.verify(action, result)

            # 5. 录制
            self.recorder.record(action, result, verified)

            # 6. 如果失败 → 自愈
            if not verified.passed:
                action = self.healer.heal(action, result)
                if action:
                    continue  # 重试

        return ExecutionResult(
            success=self.recorder.success_rate >= 0.8,
            python_script=self.recorder.export_python(),
            yaml_archive=self.recorder.export_archive_yaml(),
        )
```

### 2.2 新增：`phone_agent/tools/`

```
tools/
├── __init__.py
├── registry.py          # ToolRegistry + Tool 基类
├── loader.py            # ToolLoader
└── device/              # 执行工具
    ├── __init__.py
    ├── tap.py
    ├── type.py
    ├── launch.py
    ├── swipe.py
    ├── back.py
    ├── home.py
    └── wait.py
```

#### `tools/registry.py` — 工具注册表

```python
"""
工具注册表：管理工具注册、发现、调用。

每个 Tool 封装一个单一能力，内部实现可以:
- 直接调用 v0 的 DeviceFactory 方法
- 调用 adb/ / hdc/ / xctest/ 模块函数
- 调用外部 API
"""

class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError

    def to_openai_function(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def call(self, name: str, params: dict) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ToolNotFoundError(name)
        return tool.execute(**params)
```

#### 执行工具实现示例（复用 v0 代码）

```python
# tools/device/launch.py
class DeviceLaunchTool(Tool):
    name = "device.launch"
    description = "启动指定应用"
    parameters = {
        "type": "object",
        "properties": {
            "app": {"type": "string", "description": "应用名称，如 微信、淘宝"}
        },
        "required": ["app"]
    }

    def __init__(self, device_factory):
        self.device = device_factory

    def execute(self, app: str) -> dict:
        # 直接复用 v0 的 DeviceFactory.launch_app()
        success = self.device.launch_app(app)
        return {"success": success, "app": app}
```

### 2.3 改动：`model/client.py`

**改动量很小**，增加一个方法：

```python
# 在 ModelClient 中新增
def request_with_functions(
    self,
    messages: list[dict],
    tools: list[dict]  # OpenAI Function Calling 格式
) -> FunctionCallResponse:
    """
    支持 Function Calling 的请求方法。
    复用现有的 stream=True 流式处理逻辑。
    """
    response = self.client.chat.completions.create(
        messages=messages,
        model=self.config.model_name,
        tools=tools,  # ← 新增
        tool_choice="auto",
        stream=True,
    )
    # 解析返回的 tool_calls
    ...
```

### 2.4 改动：`config/prompts_zh.py`

```python
# v2 system prompt：从 VLM 看图改为工具驱动
SYSTEM_PROMPT_V2 = """
你是一个手机自动化测试专家。你通过调用工具来完成任务。

## 工作流程
1. 调用感知工具了解当前屏幕
2. 分析返回的结构化信息
3. 调用执行工具完成操作
4. 重复直到任务完成

## 可用工具
{tools_description}

## 规则
{domain_rules}

每次输出必须是以下格式：
<think>推理过程</think>
<function_call>{"tool": "...", "params": {...}}</function_call>
"""
```

### 2.5 阶段一验收

```bash
# 验证：纯文本 LLM + Tool Registry 能否完成简单任务
python -m phone_agent.core.agent \
  --mode v2 \
  --base-url http://localhost:8000/v1 \
  --model "qwen2.5-7b-instruct" \
  "打开微信"

# 预期输出:
# ✅ launch(app="微信") → success
# ✅ 已完成
```

---

## 3. 阶段二：感知 & 定位层

**目标**：让系统不依赖 VLM 也能理解屏幕内容。这是纯 LLM 模式能否跑通的关键。

**耗时**：5-7 天

**验证标准**：纯文本 LLM 通过 `ui.understand(mode="dump")` 获取控件树后，能正确识别当前界面状态。

---

### 3.1 新增：`phone_agent/perception/`

```
perception/
├── __init__.py
├── engine.py              # PerceptionEngine 自动模式选择
├── vlm.py                 # VLM 看图（可选）
├── dump.py                # uiautomator2 dump
├── ocr.py                 # OCR 文字提取（可选）
└── fusion.py              # 多模式融合（可选）
```

#### `perception/dump.py` — 核心感知方式

```python
"""
uiautomator2 dump 模式：
通过 adb shell uiautomator dump 获取控件树，压缩为 LLM 友好的文本。

依赖: 无（直接使用 adb 命令）
增强: 如果安装了 uiautomator2 Python 包，可以用更精确的 API
"""

import subprocess
import xml.etree.ElementTree as ET


class DumpPerception:
    """UI Dump 感知：adb dump → XML → 结构化文本"""

    def __init__(self, device_id: str | None = None):
        self.device_id = device_id
        self._prefix = ["adb", "-s", device_id] if device_id else ["adb"]

    def understand(self) -> str:
        """返回结构化屏幕描述，给 LLM 推理用"""
        xml = self._dump()
        tree = ET.fromstring(xml)
        compressed = self._compress(tree)
        return compressed

    def find_element(self, method: str, target: str) -> dict | None:
        """精确查找元素，返回坐标 bounds"""
        xml = self._dump()
        tree = ET.fromstring(xml)

        for node in tree.iter("node"):
            text = node.get("text", "")
            rid = node.get("resource-id", "")
            desc = node.get("content-desc", "")
            clickable = node.get("clickable", "false")

            if method == "text" and target == text:
                bounds = node.get("bounds", "")
                return {
                    "found": True,
                    "bounds": self._parse_bounds(bounds),
                    "clickable": clickable == "true",
                }
            if method == "id" and target in rid:
                bounds = node.get("bounds", "")
                return {
                    "found": True,
                    "bounds": self._parse_bounds(bounds),
                    "clickable": clickable == "true",
                }

        return {"found": False}

    def _dump(self) -> str:
        """执行 adb shell uiautomator dump"""
        # 方案 A：用 adb 命令（零依赖）
        subprocess.run(
            self._prefix + ["shell", "uiautomator", "dump", "/sdcard/ui.xml"],
            capture_output=True, timeout=10
        )
        subprocess.run(
            self._prefix + ["pull", "/sdcard/ui.xml", "/tmp/ui.xml"],
            capture_output=True, timeout=5
        )
        with open("/tmp/ui.xml", "r") as f:
            return f.read()

    def _compress(self, root: ET.Element, indent: int = 0) -> str:
        """将 XML 压缩为 LLM 友好的文本树"""
        lines = []
        prefix = "  " * indent

        for node in root.findall("node"):
            text = node.get("text", "")
            rid = node.get("resource-id", "")
            desc = node.get("content-desc", "")
            clz = node.get("class", "").split(".")[-1]
            bounds = node.get("bounds", "")
            clickable = node.get("clickable", "false") == "true"
            checkable = node.get("checkable", "false") == "true"
            scrollable = node.get("scrollable", "false") == "true"

            # 跳过不可见/无用节点
            if not text and not rid and not desc:
                if not clickable and not scrollable:
                    continue

            # 构建一行描述
            parts = []
            if clickable:
                parts.append("[可点击]")
            if text:
                parts.append(f'text="{text}"')
            if rid:
                short_id = rid.split("/")[-1] if "/" in rid else rid
                parts.append(f"id={short_id}")
            if bounds:
                b = self._parse_bounds(bounds)
                parts.append(f"[{b[0]},{b[1]}]")
            if scrollable:
                parts.append("[可滚动]")

            if parts:
                lines.append(f"{prefix}{' '.join(parts)}")

            # 递归子节点
            children = self._compress(node, indent + 1)
            if children:
                lines.append(children)

        return "\n".join(lines)

    def _parse_bounds(self, bounds_str: str) -> list[int]:
        import re
        nums = re.findall(r"\d+", bounds_str)
        return [int(n) for n in nums] if len(nums) == 4 else [0, 0, 0, 0]
```

#### `perception/engine.py` — 自动模式选择

```python
class PerceptionEngine:
    """感知引擎：自动选择最佳模式"""

    MODES = {
        "dump": DumpPerception,
    }

    def __init__(self, device_id: str | None = None):
        self.device_id = device_id
        self._instances = {}

        # 可选模式
        try:
            from phone_agent.perception.vlm import VlmPerception
            self.MODES["vlm"] = VlmPerception
        except ImportError:
            pass

        try:
            from phone_agent.perception.ocr import OcrPerception
            self.MODES["ocr"] = OcrPerception
        except ImportError:
            pass

    def understand(self, mode: str = "auto") -> str:
        if mode == "vlm" and "vlm" in self.MODES:
            return self._get("vlm").understand()
        if mode == "ocr" and "ocr" in self.MODES:
            return self._get("ocr").understand()
        # auto 或 dump: 默认走 dump
        return self._get("dump").understand()
```

### 3.2 阶段二验收

```bash
# 验证：纯文本 LLM 能否通过 dump 感知屏幕
python -m phone_agent.perception.engine \
  --mode dump

# 预期输出:
# [可点击] text="微信" id=mm [100,200]
# [可点击] text="淘宝" id=taobao [100,400]
# [可点击] text="抖音" id=aweme [100,600]
# ...

# 验证：LLM 能否理解 dump 输出做决策
python -c "
from phone_agent.core.planner import LLMPlanner
planner = LLMPlanner(...)
action = planner.plan('打开微信',
  screen='当前桌面，可点击元素：[微信(100,200), 淘宝(100,400)]')
print(action)  # 预期: {'tool': 'device.launch', 'params': {'app': '微信'}}
"
```

---

## 4. 阶段三：验证 & 自愈

**目标**：每步执行后验证是否生效，失败时自动恢复。

**耗时**：4-5 天

**验证标准**：故意让某一步失败（如点击错误坐标），系统能检测到失败并通过重试/切换定位方式自行恢复。

---

### 4.1 新增：`phone_agent/verify/`

```
verify/
├── __init__.py
├── verifier.py          # 步骤验证
├── screenshot_compare.py # 截图比对
└── self_heal.py          # 自愈策略
```

#### `verify/verifier.py`

```python
class Verifier:
    """步骤验证器：判断动作是否生效"""

    def __init__(self, perception: PerceptionEngine):
        self.perception = perception

    def verify(self, action: dict, before: str,
               after_screen: str) -> VerificationResult:
        """
        验证动作是否生效。

        验证策略链:
        1. 截面对比 → 内容是否变化
        2. 结构化断言 → 预期元素是否出现/消失
        3. LLM 判断 → 当前状态是否符合预期
        """
        ...
```

#### `verify/self_heal.py`

```python
class SelfHealer:
    """自愈策略：失败 → 分析 → 重试"""

    HEALING_STRATEGIES = [
        "switch_locator",    # 切换定位方式 text→id→坐标
        "adjust_coordinate", # 坐标偏移 ±20px
        "wait_and_retry",    # 等待 2s 后重试
        "re_prompt_llm",     # 增强 Prompt → LLM 重规划
    ]

    def heal(self, failed_step: dict, error: str,
             perception) -> HealingResult:
        for strategy in self.HEALING_STRATEGIES:
            result = self._try_strategy(strategy, failed_step)
            if result.success:
                return result
        return HealingResult(
            success=False,
            mark_as="pseudocode"  # 标记为伪代码
        )
```

---

## 5. 阶段四：脚本录制 & 编译

**目标**：边执行边录制，产出 Python + YAML 双格式脚本。

**耗时**：4-5 天

**验证标准**：一个完整任务执行后，产出可运行的 `.py` 文件和可读的 `.yaml` 备案文件。

---

### 5.1 新增：`phone_agent/script/`

```
script/
├── __init__.py
├── recorder.py          # ScriptRecorder
├── compiler.py          # ScriptCompiler (中间格式 → Python)
└── models.py            # 中间格式数据模型
```

#### `script/compiler.py` — 核心编译逻辑

```python
class ScriptCompiler:
    """编译器：结构化中间格式 → 可执行 Python 脚本"""

    TEMPLATES = {
        "uiautomator2": {
            "launch":        'd.app_start("{package}")',
            "tap_text":      'd(text="{target}").click()',
            "tap_id":        'd(resourceId="{target}").click()',
            "tap_coord":     'd.click({x}, {y})',
            "type":          'd(text="{target}").set_text("{text}")',
            "swipe":         'd.swipe({sx}, {sy}, {ex}, {ey})',
            "back":          'd.press("back")',
            "home":          'd.press("home")',
            "wait":          'time.sleep({duration})',
            "verify":        'assert d(textContains="{target}").exists',
            "verify_not":    'assert not d(text="{target}").exists',
        }
    }

    def compile(self, intermediate: dict,
                framework: str = "uiautomator2") -> str:
        """中间格式 → Python 脚本字符串"""
        lines = [self._header(intermediate["metadata"])]
        for step in intermediate["steps"]:
            if step["status"] == "exact":
                code = self._compile_exact(step, framework)
                lines.extend(self._wrap(code, step))
            else:
                lines.append(self._compile_pseudo(step))
        return "\n".join(lines)

    def _compile_exact(self, step: dict, framework: str) -> str:
        """精确步骤 → 一行 Python 代码，纯模板替换"""
        action = step["action"]
        params = step["params"]
        templates = self.TEMPLATES[framework]

        if action == "launch":
            return templates["launch"].format(**params)
        if action == "tap_element":
            method = params["method"]  # text / id / coord
            key = f"tap_{method}"
            if key in templates:
                return templates[key].format(**params)
        if action == "type":
            return templates["type"].format(**params)
        # ... 其他动作

    def _compile_pseudo(self, step: dict) -> str:
        """伪代码步骤 → 注释 + pass"""
        lines = [
            f"# ⚠️ PSEUDOCODE - Step {step['id']}",
            f"# 意图: {step.get('intent', '')}",
        ]
        if step.get("suggested_fix"):
            for fix in step["suggested_fix"]:
                lines.append(f"# {fix}")
        lines.append("pass  # TODO: 补全此步骤")
        return "\n".join(lines)
```

---

## 6. 阶段五：前端开发

**目标**：构建 Web 前端界面 + FastAPI 后端，支持自然语言输入、实时执行可视化、脚本/报告管理等完整用户体验。

**耗时**：8-10 天

**验证标准**：浏览器打开页面后，用户输入自然语言任务 → 实时看到执行进度和截图 → 完成后可下载 Python 脚本和 HTML 报告。

---

### 6.1 整体架构

```
┌──────────────────────────────────────────────────┐
│                   Browser (React SPA)            │
│  ┌──────────┐ ┌──────────┐ ┌───────┐ ┌────────┐ │
│  │ Dashboard│ │ Task     │ │Scripts│ │Reports │ │
│  │ +Devices  │ │ Input    │ │Browse │ │Viewer  │ │
│  └────┬─────┘ └────┬─────┘ └───┬───┘ └───┬────┘ │
│       │            │           │          │       │
│  ┌────┴────────────┴───────────┴──────────┴───┐   │
│  │         API Client (fetch + WebSocket)      │   │
│  └────────────────────┬───────────────────────┘   │
└───────────────────────┼───────────────────────────┘
                        │ HTTP + WS
┌───────────────────────┼───────────────────────────┐
│          FastAPI Backend (phone_agent/web/)        │
│  ┌────────────────────┴───────────────────────┐   │
│  │              API Routes (REST + WS)         │   │
│  │  /api/devices  /api/tasks  /api/scripts    │   │
│  │  /api/reports  /ws/execution/{task_id}     │   │
│  └────┬───────────┬───────────┬───────────────┘   │
│       │           │           │                     │
│  ┌────┴────┐ ┌────┴────┐ ┌───┴────────┐           │
│  │ Device  │ │ NewAgent│ │ Script     │           │
│  │ Pool    │ │ Runner  │ │ Manager    │           │
│  └─────────┘ └─────────┘ └────────────┘           │
└──────────────────────────────────────────────────┘
```

**技术选型建议**：

| 组件 | 推荐 | 备选 |
|------|------|------|
| 后端框架 | FastAPI（Python 原生，天然支持 async + WebSocket） | Flask + Flask-SocketIO |
| 前端框架 | React 18 + TypeScript | Vue 3 + TypeScript |
| 状态管理 | React Context / Zustand | Redux Toolkit |
| UI 组件库 | Ant Design / shadcn/ui | Element Plus (Vue) |
| 实时通信 | WebSocket（FastAPI 原生支持） | SSE (Server-Sent Events) |
| 打包部署 | Vite + 单页输出，FastAPI 直接 serve 静态文件 | Nginx 反代 |

---

### 6.2 新增：`phone_agent/web/`

```
web/
├── __init__.py
├── main.py                  # FastAPI 应用入口
├── config.py                # Web 后端配置
│
├── api/
│   ├── __init__.py
│   ├── routes.py            # 注册所有路由
│   ├── devices.py           # 设备管理 API
│   ├── tasks.py             # 任务执行 API
│   ├── scripts.py           # 脚本管理 API
│   └── reports.py           # 报告管理 API
│
├── ws/
│   ├── __init__.py
│   └── execution.py         # 执行进度 WebSocket
│
├── services/
│   ├── __init__.py
│   ├── task_runner.py       # 后台任务执行器
│   └── script_manager.py    # 脚本文件管理
│
├── models/
│   ├── __init__.py
│   ├── device.py            # 设备模型
│   ├── task.py              # 任务模型
│   └── script.py            # 脚本模型
│
└── ui/                      # React 前端构建产物 + 源码
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    │
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── api/
    │   │   ├── client.ts           # HTTP 客户端封装
    │   │   └── websocket.ts        # WebSocket 客户端
    │   │
    │   ├── pages/
    │   │   ├── Dashboard.tsx        # 总览仪表盘
    │   │   ├── TaskInput.tsx        # 自然语言任务输入
    │   │   ├── Execution.tsx        # 执行进度实时展示
    │   │   ├── Scripts.tsx          # 脚本列表/查看/下载
    │   │   ├── Reports.tsx          # 报告列表/查看/下载
    │   │   └── Devices.tsx          # 设备管理
    │   │
    │   ├── components/
    │   │   ├── Layout.tsx           # 全局布局
    │   │   ├── DeviceCard.tsx       # 设备卡片
    │   │   ├── StepTimeline.tsx     # 执行步骤时间线
    │   │   ├── ScreenshotViewer.tsx # 截图查看器
    │   │   └── ReportPreview.tsx    # 报告内嵌预览
    │   │
    │   └── styles/
    │       └── global.css
    │
    └── public/
        └── favicon.ico
```

---

### 6.3 前端状态管理 & 组件树

#### Zustand Store 设计

```typescript
// web/ui/src/stores/deviceStore.ts
interface DeviceStore {
  devices: Device[];
  loading: boolean;
  fetchDevices: () => Promise<void>;
  refreshDevices: () => Promise<void>;
}

// web/ui/src/stores/taskStore.ts
interface TaskStore {
  currentTask: Task | null;
  steps: StepState[];
  logs: LogEntry[];
  // WebSocket 生命周期
  connect: (taskId: string) => void;
  disconnect: () => void;
  cancel: () => void;
}

// web/ui/src/stores/scriptStore.ts
interface ScriptStore {
  scripts: Script[];
  selected: Script | null;
  fetchScripts: () => Promise<void>;
  downloadScript: (id: string) => void;
}

// web/ui/src/stores/reportStore.ts
interface ReportStore {
  reports: Report[];
  selected: Report | null;
  fetchReports: () => Promise<void>;
  previewReport: (id: string) => string; // HTML
}
```

#### 组件树

```
<App>
  <BrowserRouter>
    <Layout>                     # 全局布局：侧边栏 + 顶栏 + 内容区
      <Sidebar />                # 导航菜单
      <Header />                 # 顶栏（设备状态指示器）
      <Content>
        <Routes>
          <Route path="/"        element={<Dashboard />} />
          <Route path="/new"     element={<TaskInput />} />
          <Route path="/tasks/:id" element={<Execution />} />
          <Route path="/scripts" element={<Scripts />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/devices" element={<Devices />} />
        </Routes>
      </Content>
    </Layout>
  </BrowserRouter>
</App>

# 页面 → 组件分解
Dashboard  → DeviceCard[] + StatCard[] + RecentTaskTable
TaskInput  → DeviceSelector + PromptTextArea + SubmitButton
Execution  → StepTimeline + ScreenshotViewer + LogPanel + ControlBar
Scripts    → ScriptTable + ScriptPreview + DownloadButton
Reports    → ReportTable + ReportPreview (iframe)
Devices    → DeviceCard[] + RefreshButton
```

---

### 6.4 WebSocket 消息协议

```python
# web/ws/execution.py — 完整消息类型

# ====== 服务端 → 客户端 ======
{
    "type": "task_queued",
    "task_id": "uuid",
    "device_id": "str"
}
{
    "type": "task_start",
    "task_id": "uuid",
    "prompt": "str",
    "total_steps": 5
}
{
    "type": "step_plan",
    "task_id": "uuid",
    "step": 1,
    "action": "tap",
    "params": {"text": "朋友圈"},
    "desc": "点击底部'发现'标签"
}
{
    "type": "step_start",
    "task_id": "uuid",
    "step": 1
}
{
    "type": "step_screenshot",
    "task_id": "uuid",
    "step": 1,
    "screenshot_b64": "base64..."
}
{
    "type": "step_done",
    "task_id": "uuid",
    "step": 1,
    "result": "success" | "pseudo" | "failed",
    "duration_ms": 3200
}
{
    "type": "step_error",
    "task_id": "uuid",
    "step": 2,
    "error": "element not found: 朋友圈",
    "suggestion": "尝试切换到 OCR 模式定位"
}
{
    "type": "task_done",
    "task_id": "uuid",
    "script_id": "uuid" | null,
    "report_id": "uuid" | null,
    "total_duration_ms": 45000
}
{
    "type": "task_error",
    "task_id": "uuid",
    "error": "设备连接断开"
}

# ====== 客户端 → 服务端 ======
{
    "type": "cancel",
    "task_id": "uuid"
}
{
    "type": "pause",
    "task_id": "uuid"
}
{
    "type": "resume",
    "task_id": "uuid"
}
```

#### WebSocket 客户端封装

```typescript
// web/ui/src/api/websocket.ts
class ExecutionSocket {
  private ws: WebSocket | null = null;

  connect(taskId: string) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/execution/${taskId}`);
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case "step_screenshot":
          taskStore.getState().appendScreenshot(msg.step, msg.screenshot_b64);
          break;
        case "step_done":
          taskStore.getState().updateStep(msg.step, msg.result);
          break;
        case "task_done":
          taskStore.getState().setComplete(msg.script_id, msg.report_id);
          break;
        case "step_error":
          taskStore.getState().setError(msg.step, msg.error, msg.suggestion);
          break;
        // ...
      }
    };
  }

  send(msg: { type: string; task_id: string }) {
    this.ws?.send(JSON.stringify(msg));
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}
```

#### HTTP Client 封装

```typescript
// web/ui/src/api/client.ts
const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, err.detail);
  }
  return res.json();
}

// 类型化 API 方法
export const api = {
  // 设备
  devices: {
    list: () => request<Device[]>("/devices"),
    refresh: () => request<Device[]>("/devices/refresh", { method: "POST" }),
  },
  // 任务
  tasks: {
    create: (body: TaskInput) =>
      request<Task>("/tasks", { method: "POST", body: JSON.stringify(body) }),
    list: () => request<Task[]>("/tasks"),
    get: (id: string) => request<Task>(`/tasks/${id}`),
  },
  // 脚本
  scripts: {
    list: () => request<Script[]>("/scripts"),
    get: (id: string) => request<Script>(`/scripts/${id}`),
    download: (id: string) => `${BASE}/scripts/${id}/download`,
  },
  // 报告
  reports: {
    list: () => request<Report[]>("/reports"),
    downloadHtml: (id: string) => `${BASE}/reports/${id}/download/html`,
    downloadPdf: (id: string) => `${BASE}/reports/${id}/download/pdf`,
  },
};
```

---

### 6.5 后端 API 设计

```python
# web/api/routes.py — 路由总览

# ========== 设备管理 ==========
GET    /api/devices                          # 获取设备列表（含状态）
POST   /api/devices/refresh                  # 重新扫描 ADB 设备
GET    /api/devices/{id}                     # 获取单设备详情
DELETE /api/devices/{id}                     # 移除设备

# ========== 任务执行 ==========
POST   /api/tasks                            # 提交自然语言任务
GET    /api/tasks                            # 获取历史任务列表
GET    /api/tasks/{id}                       # 获取任务详情
DELETE /api/tasks/{id}                       # 删除任务

# ========== WebSocket ==========
WS     /ws/execution/{task_id}               # 实时推送执行进度+截图

# ========== 脚本管理 ==========
GET    /api/scripts                          # 获取脚本列表
GET    /api/scripts/{id}                     # 获取脚本详情（含源码）
GET    /api/scripts/{id}/download            # 下载 Python 脚本
DELETE /api/scripts/{id}                     # 删除脚本

# ========== 报告管理 ==========
GET    /api/reports                          # 获取报告列表
GET    /api/reports/{id}                     # 获取报告详情
GET    /api/reports/{id}/download/html       # 下载 HTML 报告
GET    /api/reports/{id}/download/pdf        # 下载 PDF 报告
DELETE /api/reports/{id}                     # 删除报告
```

#### `web/api/tasks.py` — 核心接口

```python
"""任务执行 API：接收自然语言 → 后台异步执行 → WebSocket 推送进度"""

from fastapi import APIRouter, WebSocket, BackgroundTasks
from ..services.task_runner import TaskRunner

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("")
async def create_task(task_input: TaskInputRequest,
                      background_tasks: BackgroundTasks):
    """
    接收自然语言任务，创建后台执行任务。

    Request body:
        {"device_id": "xxx", "prompt": "打开微信并给XXX发消息说..."}

    Response:
        {"task_id": "uuid", "status": "queued"}
    """
    task = TaskService.create(
        device_id=task_input.device_id,
        prompt=task_input.prompt,
    )
    # 后台异步执行，不阻塞 HTTP 响应
    background_tasks.add_task(TaskRunner.run, task.id)
    return {"task_id": task.id, "status": "queued"}


@router.websocket("/ws/execution/{task_id}")
async def execution_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket 实时推送执行进度。

    推送消息格式:
        {"type": "step_start", "step": 1, "action": "tap",
         "desc": "点击搜索框"}
        {"type": "step_done",  "step": 1, "screenshot": "base64..."}
        {"type": "error",      "step": 2, "message": "..."}
        {"type": "done",       "script_id": "uuid", "report_id": "uuid"}
    """
    await websocket.accept()
    async for message in ExecutionEventStream.subscribe(task_id):
        await websocket.send_json(message)
```

---

### 6.6 前端页面设计

#### Dashboard（总览仪表盘）

```
┌────────────────────────────────────────────────────┐
│  Open-AutoGLM  Test Platform         [设备: 2/3 在线] │
├────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │  今日执行次数  │ │  生成脚本数  │ │  通过率      │ │
│  │     12       │ │      8      │ │    92%      │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ │
│                                                      │
│  设备状态 ───────────────────────────────────────── │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │ Pixel 6    │  │ Mi 13      │  │ 模拟器-1   │   │
│  │ ● 在线     │  │ ● 在线     │  │ ○ 离线     │   │
│  │ Android 14 │  │ HyperOS    │  │ Android 13│   │
│  └────────────┘  └────────────┘  └────────────┘   │
│                                                      │
│  最近执行记录 ──────────────────────────────────── │
│  │ 14:23 │ 微信发朋友圈    │ Pixel 6  │ ✓ 34s    ││
│  │ 14:15 │ 淘宝搜索商品    │ Mi 13    │ ✓ 52s    ││
│  │ 13:58 │ 抖音评论        │ Pixel 6  │ ✗ 超时   ││
└────────────────────────────────────────────────────┘
```

#### TaskInput（任务输入）

```
┌────────────────────────────────────────────────────┐
│  新建任务                                             │
├────────────────────────────────────────────────────┤
│                                                      │
│  选择设备: [▼ Pixel 6  ●]  [Mi 13  ●]  [模拟器-1 ○]│
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ 请描述你想要执行的操作...                         │ │
│  │                                                │ │
│  │ 例如: "打开微信，给张三发一条消息说'晚上一起吃饭'，│ │
│  │        然后回到桌面"                             │ │
│  │                                                │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  [开始执行]  [生成脚本 (跳过执行)]                     │
└────────────────────────────────────────────────────┘
```

#### Execution（实时执行展示）

```
┌────────────────────────────────────────────────────┐
│  执行中 · 微信发朋友圈                  [终止]  [Pause]│
├────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌─────────────────────────┐   │
│  │ 步骤 1/5     │    │ ┌─────────────────────┐ │   │
│  │ ✓ 打开微信   │    │ │                     │ │   │
│  │ ✓ 点击发现   │    │ │   当前截图           │ │   │
│  │ ◉ 点击朋友圈 │    │ │   (实时更新)         │ │   │
│  │ ○ 输入文字   │    │ │                     │ │   │
│  │ ○ 点击发表   │    │ └─────────────────────┘ │   │
│  │              │    │                         │   │
│  │ 当前: 第 3 步 │    │ 动作: 点击 "朋友圈"      │   │
│  │ 耗时: 12s    │    │ 位置: [320, 480]        │   │
│  └──────────────┘    └─────────────────────────┘   │
│  日志:                                                │
│  [14:23:01] 启动微信                              │
│  [14:23:05] 等待首页加载 ✓                        │
│  [14:23:08] 点击底部"发现"选项卡 ✓                  │
│  [14:23:11] 正在定位"朋友圈"按钮...                  │
└────────────────────────────────────────────────────┘
```

---

### 6.7 部署运行方式

```python
# web/main.py — FastAPI 应用入口

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api.routes import router as api_router

app = FastAPI(title="Open-AutoGLM Test Platform")

# API 路由
app.include_router(api_router, prefix="/api")

# 前端静态文件（React build 产物）
app.mount("/", StaticFiles(directory="phone_agent/web/ui/dist",
                           html=True), name="ui")
```

```bash
# 开发模式（前后端分离）
# 终端 1: 后端
uvicorn phone_agent.web.main:app --reload --port 8000

# 终端 2: 前端 dev server
cd phone_agent/web/ui
npm install
npm run dev   # 代理到 http://localhost:8000/api/*

# 生产模式
cd phone_agent/web/ui
npm run build
# FastAPI 自动 serve 构建产物，单端口部署
```

---

### 6.8 ui-automation vs. web-automation 场景说明

> 本项目的 Web 前端仅用于**任务提交、执行监控、结果查看**的操作界面，不涉及任何 Web 自动化测试。
> 实际的设备端自动化操作始终通过 `adb/uiautomator2` 在手机上执行，两者互不干扰。

---

### 6.9 并行时间线 & 关键路径

```
Week 1       Week 2       Week 3       Week 4       Week 5       Week 6       Week 7
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
██████████  P1 core + tools (5-7天)
           ██████████████  P2 perception (5-7天)
                         ██████████████  P4 script (4-5天)
                                 ████████████████████████  P6 report (3-4天) + P7 orch (5-6天)
                         ██████████  P3 verify (4-5天)
                         ████████████████████  P5 API 后端 (4-5天)
                                             ████████████████████  P5 前端 UI (4-5天)
                                                                   ██████████  P5 联调 (2天)

M1 (d7)      M2 (d14)    M3 (d19)    M4 (d24)    M5 (d34)    M6 (d38)    M7 (d44)    M8 (d50)
```

**关键路径**（决定了总工期）：
```
P1 → P2 → P3 → P4 → P6 → P7   (后端主线，44天)
P1 → P2 → P5 API → P5 UI       (前端支线，并行于后端)
```

**并行策略**：
- P5 API 后端在 P2 完成后即可启动（不需要等 P3/P4），与后端开发**并行**
- P5 前端 UI 在 P5 API 路由稳定后启动，与 P5 API 重叠 1 周
- P3（verify）紧接 P2 后启动，与 P5 API 同期并行
- **2 人并行可将总工期从 50 天压缩到 35 天**
- 单人串行开发严格按编号顺序

---

## 7. 阶段六：报告系统

**目标**：产出自包含 HTML 报告 + PDF，所有截图 base64 内嵌。

**耗时**：3-4 天

**验证标准**：多设备执行后生成一份统一报告，HTML 报告离线可打开，PDF 排版正常。

---

### 7.1 新增：`phone_agent/report/`

```
report/
├── __init__.py
├── models.py                  # 数据模型
├── html_generator.py          # HTML 报告
├── pdf_generator.py           # PDF 报告
├── screenshot_manager.py      # 截图 base64 管理
└── aggregator.py              # 多设备聚合
```

#### `report/html_generator.py`

```python
class HtmlReportGenerator:
    """生成自包含 HTML 报告，所有截图以 base64 内嵌。"""

    def generate(self, report: TestReport) -> str:
        """返回可直接保存为 .html 的字符串，不依赖任何外部文件。"""
        css = self._inline_css()
        overview = self._build_overview(report)
        device_sections = ""
        for device in report.device_info:
            device_sections += self._build_device_section(device)

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{report.title}</title>
<style>{css}</style></head>
<body>
  {overview}
  {device_sections}
</body>
</html>"""

    def _inline_css(self) -> str:
        """所有样式内联，不依赖外部 CSS 文件"""
        return """
        body { font-family: -apple-system, sans-serif; margin: 20px; }
        .overview { background: #f8fafc; padding: 20px; border-radius: 8px; }
        .stats { display: flex; gap: 20px; }
        .stat-card { background: white; padding: 15px; border-radius: 6px; }
        .step-exact { background: #f0fdf4; }
        .step-pseudo { background: #fffbeb; }
        .step-screenshot { width: 120px; border: 1px solid #ddd; }
        ...
        """
```

#### `report/screenshot_manager.py`

```python
class ScreenshotManager:
    """截图管理：全部 base64 存内存，不依赖本地文件。"""

    def __init__(self):
        self._store: dict[str, str] = {}  # key → base64

    def capture(self, key: str) -> str:
        """截图 → base64 → 存入内存"""
        from phone_agent.adb.screenshot import get_screenshot
        shot = get_screenshot()
        self._store[key] = shot.base64_data
        return shot.base64_data

    def embed_in_html(self, key: str) -> str:
        """生成内嵌 img 标签"""
        b64 = self._store.get(key, "")
        if not b64:
            return ""
        return f'<img src="data:image/png;base64,{b64}" ' \
               f'class="step-screenshot" />'

    def cleanup_temp(self):
        """只删临时文件，不删 base64 缓存"""
        import glob, os, tempfile
        for f in glob.glob(os.path.join(tempfile.gettempdir(), "screenshot_*.png")):
            os.remove(f)
```

---

## 8. 阶段七：多设备调度

**目标**：支持 N 台设备并发执行脚本，各设备状态隔离，结果统一汇总。

**耗时**：5-6 天

**验证标准**：同时向 3 台设备分发同一个脚本，3 台同时执行完成且互不干扰，输出聚合报告。

---

### 8.1 新增：`phone_agent/orchestrator/`

```
orchestrator/
├── __init__.py
├── orchestrator.py          # Orchestrator 调度器
├── device_pool.py           # 设备池
└── task_queue.py            # 任务队列
```

#### `orchestrator/orchestrator.py`

```python
class Orchestrator:
    """多设备调度器"""

    def __init__(self):
        self.device_pool = DevicePool()
        self.task_queue = asyncio.Queue()

    def register_device(self, device_id: str) -> bool:
        """注册设备到池中"""
        agent = NewAgent(
            model_config=...,
            device_id=device_id,
        )
        self.device_pool.add(device_id, agent)
        return True

    async def dispatch_script(self, python_script: str,
                               device_ids: list[str] | None = None):
        """将 Python 脚本分发到指定设备并发执行"""
        targets = self.device_pool.get_devices(device_ids)
        tasks = [self._run_on_device(d, python_script)
                 for d in targets]
        results = await asyncio.gather(*tasks)
        return self._aggregate_results(results)
```

---

## 9. 端到端验收场景

### 9.1 场景一：微信发消息

**输入**：`"打开微信，给张三发消息说'晚上一起吃饭'，然后回到桌面"`

**期望产出的 Python 脚本**：

```python
# test_wechat_message.py
class TestWechatMessage:
    def test_send_message(self, d: Device):
        d.launch_app("com.tencent.mm")                      # 启动微信
        d.wait(3)                                            # 等待首页加载
        d.tap(text="张三")                                   # dump 定位联系人
        d.type(text="晚上一起吃饭")                           # 输入文字
        d.tap(resource_id="com.tencent.mm:id/btn_send")     # 点击发送
        d.assert_visible(text="晚上一起吃饭")                 # 验证发送成功
        d.back()
        d.home()
```

### 9.2 场景二：淘宝搜索商品

**输入**：`"打开淘宝，搜索'iPhone 15 手机壳'，按销量排序"`

**期望产出的 Python 脚本**：

```python
# test_taobao_search.py
class TestTaobaoSearch:
    def test_search_product(self, d: Device):
        d.launch_app("com.taobao.taobao")
        d.wait(5)
        d.tap(resource_id="com.taobao.taobao:id/home_search")
        d.type(text="iPhone 15 手机壳")
        d.tap(text="搜索")
        d.wait(3)
        d.tap(text="销量")
        d.assert_visible(text="按销量排序")
        d.screenshot("search_result.png")
```

### 9.3 验收矩阵

| 阶段 | 输入 | 期望产出 | 验证方式 | 通过标准 |
|------|------|---------|---------|---------|
| **P1** | `"打开微信"` | LLM 输出 `{tool: "launch", params: {app: "com.tencent.mm"}}` | `pytest tests/test_tools/test_registry.py -k test_plan_tool_call` | 准确率 ≥80% |
| **P2** | 微信首页截图 + dump XML | LLM 输出 `{tool: "tap", params: {text: "张三"}}` | `pytest tests/test_perception/test_dump.py` | 关键元素识别率 ≥70% |
| **P3** | tap 操作后截图 | Verifier 返回 `passed=True` 或自愈成功 | `pytest tests/test_verify/test_verifier.py` | 自愈恢复率 ≥60% |
| **P4** | 完整执行轨迹 JSON | 生成 `test_wechat_message.py` + `.yaml` | `pytest tests/test_compiler/test_compiler_exact.py` | 模板替换 100% 精确 |
| **P5** | Web 输入任务 | 浏览器实时 5 步执行完成 | 手动走查 | 全流程无报错 |
| **P6** | 执行记录 | HTML 报告离线可打开 + 截图内嵌可见 | 手动打开 `.html` | 报告完整可读 |
| **P7** | 3 台设备脚本 | 并发执行完成 + 日志隔离 + 聚合报告 | 日志检查 | 每设备日志独立无串扰 |

---

## 10. 现有代码复用清单

### 10.1 不复用，保留原样

| 文件 | 原因 |
|------|------|
| `phone_agent/agent.py` | v0 PhoneAgent，保留兼容 |
| `phone_agent/agent_ios.py` | iOS 版本，不动 |
| `phone_agent/actions/handler.py` | v0 的动作处理器，v2 不再走这里 |
| `phone_agent/actions/handler_ios.py` | iOS 动作处理器，不动 |
| `phone_agent/config/apps.py` | App 包名映射，稳定不动 |
| `phone_agent/config/apps_harmonyos.py` | 不动 |
| `phone_agent/config/apps_ios.py` | 不动 |
| `phone_agent/config/i18n.py` | 不动 |
| `phone_agent/config/timing.py` | 不动 |
| `phone_agent/hdc/` | 整套不动 |
| `phone_agent/xctest/` | 整套不动 |

### 10.2 直接 import 调用（不修改源文件）

| v0 模块 | 在 v2 中的调用方式 |
|---------|------------------|
| `adb/device.py`: `tap()`, `swipe()`, `back()`, `home()`, `launch_app()`, `get_current_app()` | `from phone_agent.adb.device import tap` → DeviceTool 内部调用 |
| `adb/screenshot.py`: `get_screenshot()` | `from phone_agent.adb.screenshot import get_screenshot` → Perception/VLM 使用 |
| `adb/input.py`: `type_text()`, `clear_text()`, `detect_and_set_adb_keyboard()` | `from phone_agent.adb.input import type_text` → DeviceTypeTool 内部调用 |
| `adb/connection.py`: `ADBConnection` | 设备管理工具调用 |
| `device_factory.py`: `DeviceFactory`, `get_device_factory()` | 作为执行工具的统一后端 |
| `model/client.py`: `ModelClient` | LLMPlanner 内部使用 |

### 10.3 需微调后复用

| v0 模块 | 改动 | 改动量 |
|---------|------|--------|
| `model/client.py` | 增加 `request_with_functions()` 方法 | +30 行 |
| `config/prompts_zh.py` | 增加 `SYSTEM_PROMPT_V2`（不删旧的） | +80 行 |
| `config/__init__.py` | 增加导入 `SYSTEM_PROMPT_V2` | +2 行 |

---

## 11. 新增代码清单

| 模块 | 文件 | 预估行数 | 工作量 |
|------|------|---------|-------|
| **core/** | `planner.py`, `agent.py`, `config.py` | 350 | 3 天 |
| **tools/** | `registry.py`, `loader.py` | 200 | 1 天 |
| **tools/device/** | `tap.py`, `type.py`, `launch.py`, `swipe.py`, `back.py`, `home.py`, `wait.py` | 250 | 1.5 天 |
| **perception/** | `engine.py`, `dump.py` (vlm.py/ocr.py 可选) | 400 | 3 天 |
| **verify/** | `verifier.py`, `self_heal.py`, `screenshot_compare.py` | 300 | 2.5 天 |
| **script/** | `recorder.py`, `compiler.py`, `models.py` | 350 | 2.5 天 |
| **report/** | `html_generator.py`, `pdf_generator.py`, `screenshot_manager.py`, `aggregator.py` | 500 | 3 天 |
| **orchestrator/** | `orchestrator.py`, `device_pool.py`, `task_queue.py` | 350 | 3 天 |
| **web/api/** | `main.py`, `routes.py`, `devices.py`, `tasks.py`, `scripts.py`, `reports.py` | 350 | 2.5 天 |
| **web/services/** | `task_runner.py`, `script_manager.py` | 200 | 1.5 天 |
| **web/models/** | `device.py`, `task.py`, `script.py` | 100 | 0.5 天 |
| **web/ws/** | `execution.py` | 80 | 0.5 天 |
| **web/ui/** | React 前端（`src/stores/*`, `src/pages/*`, `src/components/*`, `src/api/*`） | ~900 | 4.5 天 |
| **tools/test_poc/** | `verify_function_calling.py`, `dump_coverage.py` | 60 | 0.5 天 |
| **模型改动** | `model/client.py` 微调 | 30 | 0.5 天 |
| **配置改动** | `config/` 微调 | 80 | 0.5 天 |
| **合计** | ~32 个文件 | ~4650 行 | ~30 天 |

---

## 12. 测试策略

### 12.1 测试层级

```
单元测试          → 每个 Tool、Compiler 模板替换
集成测试          → Tool → DeviceFactory → ADB（需真机/模拟器）
端到端测试        → 完整流程：自然语言 → 执行 → 脚本产出
回归测试          → 确保 v0 原有功能不受影响
```

### 12.2 测试文件结构

```
tests/
├── conftest.py                    # 全局 fixtures
├── test_imports.py                # 确保所有 import 不报错
│
├── test_tools/
│   ├── test_registry.py           # 注册/发现/调用
│   ├── test_device_tools.py       # 执行工具（mock 设备）
│   └── test_perception_tools.py   # 感知工具（mock dump）
│
├── test_perception/
│   ├── test_dump.py               # XML 解析 + 压缩
│   └── test_engine.py             # 模式选择逻辑
│
├── test_compiler/
│   ├── test_compiler_exact.py     # exact 步骤编译
│   ├── test_compiler_pseudo.py    # pseudocode 输出
│   └── test_frameworks.py         # uiautomator2 / appium 模板
│
├── test_verify/
│   ├── test_verifier.py
│   └── test_self_heal.py
│
├── test_report/
│   ├── test_html_generator.py
│   └── test_screenshot_manager.py
│
├── test_orchestrator/
│   ├── test_device_pool.py
│   └── test_task_queue.py
│
└── test_web/
    ├── test_api_devices.py     # 设备 API（mock 设备池）
    ├── test_api_tasks.py       # 任务 API（mock runner）
    ├── test_api_scripts.py     # 脚本 API
    ├── test_api_reports.py     # 报告 API
    └── test_websocket.py       # WebSocket 推送
```

### 12.3 Mock 策略

```python
# conftest.py
@pytest.fixture
def mock_device():
    """Mock DeviceFactory，不连真机"""
    with patch("phone_agent.device_factory.get_device_factory") as mock:
        factory = MagicMock()
        factory.tap.return_value = None
        factory.launch_app.return_value = True
        factory.get_screenshot.return_value = Screenshot(
            base64_data="...", width=1080, height=2400
        )
        mock.return_value = factory
        yield factory

@pytest.fixture
def mock_dump():
    """Mock uiautomator dump，返回预设 XML"""
    return """
    <node resource-id="com.taobao:id/home">
      <node text="搜索框" resource-id="com.taobao:id/search"
            clickable="true" bounds="[100,50][800,150]"/>
      <node text="购物车" resource-id="com.taobao:id/cart"
            clickable="true" bounds="[900,50][1000,150]"/>
    </node>
    """
```

### 12.4 运行方式

```bash
# 全部测试
pytest tests/ -v

# 按模块
pytest tests/test_compiler/ -v

# 覆盖率
pytest tests/ --cov=phone_agent --cov-report=html
```

---

## 13. 核心风险前置验证实验

> 以下两个实验必须在 Phase 1 正式开发前执行，验证架构最核心的两个假设。
> **如果不通过，需要先回退方案再启动 Phase 1。**

### 13.1 实验 A：LLM Function Calling 合规率

```python
# tools/test_poc/verify_function_calling.py
"""
目标：确认当前 ModelClient 能否稳定输出 Function Calling 格式。
方法：用 20 个典型手机操作指令，统计 LLM 输出解析成功率。
"""

TEST_CASES = [
    ("打开微信",         "launch_app",     {"app": "com.tencent.mm"}),
    ("点击搜索框",       "tap",            {"text": "搜索框"}),
    ("输入 hello",       "type",           {"text": "hello"}),
    ("返回上一页",       "back",           {}),
    ("回到桌面",         "home",           {}),
    ("向下滑动",         "swipe",          {"direction": "up"}),
    # ... 共 20 条
]

def test_function_calling_rate():
    """通过标准：≥80% 可直接解析为 {tool, params}"""
    client = ModelClient(config)
    passed = 0
    failures = []
    for prompt, expected_tool, expected_params in TEST_CASES:
        result = client.request_with_functions(
            messages=[{"role": "user", "content": prompt}],
            tools=ALL_TOOLS,
        )
        if result.tool == expected_tool:
            passed += 1
        else:
            failures.append((prompt, result, expected_tool))
    rate = passed / len(TEST_CASES)
    assert rate >= 0.8, f"合规率 {rate:.0%} < 80%，失败: {failures}"
```

**若不通过** → 备选方案：
1. `json:{schema}` prompting（显式要求 JSON 输出）
2. 正则 + AST 解析（复用 v0 已有的 `parse_action()`）

### 13.2 实验 B：uiautomator2 dump 覆盖率

```python
# tools/test_poc/dump_coverage.py
"""
目标：确认目标 App 的 dump 覆盖率是否足够。
方法：对 3 个 App（微信/淘宝/抖音）手动执行 10 个典型操作，
      每次操作前 dump，统计可交互元素数量/比例。
"""

TARGET_APPS = {
    "微信":   "com.tencent.mm",
    "淘宝":   "com.taobao.taobao",
    "抖音":   "com.ss.android.ugc.aweme",
}

def test_dump_coverage():
    """通过标准：关键 UI 元素 ≥70% 可被 dump 识别"""
    for name, pkg in TARGET_APPS.items():
        launch_app(pkg)
        for action in TYPICAL_ACTIONS[name]:
            dump_result = get_ui_dump()
            # 统计 dump 中可交互元素数量 vs 屏幕实际可见元素
            coverage = evaluate_coverage(dump_result, action)
            print(f"{name}: {coverage:.0%}")
            assert coverage >= 0.7, f"{name} 覆盖率不足 {coverage:.0%}"
```

**若不通过** → 备选方案：
1. patch 加入 OCR 定位（识别文本元素）
2. 特殊 App 支持自定义定位策略

### 13.3 其他风险 & 缓解措施

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| **LLM 指令遵循不足**：输出格式不符合 Function Calling 规范 | 中 | 高 | 阶段一前执行实验 A（13.1）；备选 `json:{schema}`；兜底正则+ast 解析 |
| **uiautomator dump 覆盖率低**：部分 App/Flutter/游戏拿不到控件数据 | 中 | 高 | 阶段二前执行实验 B（13.2）；不够加 OCR；VLM 最终兜底 |
| **ADB 命令执行失败**：设备断开/权限问题 | 低 | 中 | v0 已有完善错误处理，v2 继承；加重试逻辑 |
| **图片 base64 过大**：HTML 报告臃肿 | 低 | 中 | 截图压缩（JPEG 80% 质量）；可选只嵌入关键步骤截图 |
| **多设备并发竞态**：adb 命令互相干扰 | 低 | 中 | 每步使用 `-s device_id` 隔离；v0 已有 `_get_adb_prefix()` 模式 |
| **依赖冲突**：`uiautomator2` / `PaddleOCR` / `weasyprint` | 中 | 低 | 全量强依赖安装，如遇冲突在 CI 中提前暴露 |
| **前端-后端版本不一致**：API 变更导致前端请求失败 | 中 | 中 | 前后端同仓开发，API 路由统一注册于 `web/api/routes.py`；前端 TypeScript 类型定义后端返回值 |

---

## 14. 里程碑 & 交付物

### 14.1 里程碑

```
M1 (第 7 天)  — 阶段一完成
  → 纯文本 LLM + Tool Registry 能完成简单任务
  → 产出: core/ + tools/ 可运行

M2 (第 14 天) — 阶段二完成
  → uiautomator2 dump 感知可工作
  → 纯文本 LLM 能理解屏幕并正确决策
  → 产出: perception/ 可运行

M3 (第 19 天) — 阶段三完成
  → 步骤验证 + 自愈策略可工作
  → 失败能自动恢复或标记伪代码
  → 产出: verify/ 可运行

M4 (第 24 天) — 阶段四完成
  → 完整任务可产出 Python 脚本 + YAML 备案
  → 产出: script/ 可运行 + 示例脚本

M5 (第 34 天) — 阶段五完成
  → Web 前端 + API 后端可用
  → 浏览器可提交任务、实时查看执行、下载脚本/报告
  → 产出: web/ 可运行 + 开发/生产模式文档

M6 (第 38 天) — 阶段六完成
  → HTML + PDF 报告可生成
  → 报告截图内嵌，离线可看
  → 产出: report/ 可运行 + 示例报告

M7 (第 44 天) — 阶段七完成
  → 多设备并发执行 + 聚合报告
  → 产出: orchestrator/ 可运行

M8 (第 50 天) — 集成测试 + 修复
  → 全链路端到端通过（CLI + Web 两种入口）
  → 所有测试通过
  → 产出: 完整可运行的 v2 系统
```

### 14.2 交付物清单

```
📁 phone_agent/
  ├── core/          — NewAgent 主循环
  ├── tools/         — 工具注册表 + 所有工具
  ├── perception/    — 感知引擎
  ├── verify/        — 验证 + 自愈
  ├── script/        — 录制 + 编译
  ├── web/           — Web 前端 (React) + API 后端 (FastAPI)
  │   ├── api/       — REST + WebSocket 路由
  │   ├── services/  — 后台服务
  │   ├── models/    — 数据模型
  │   ├── ws/        — WebSocket 实时推送
  │   └── ui/        — React SPA 源码 + 构建产物
  ├── report/        — 报告输出
  └── orchestrator/  — 多设备调度

📁 tests/
  ├── 8 个测试模块，预计 250+ 测试用例

📁 tools/test_poc/
  ├── verify_function_calling.py  — LLM Function Calling 合规率验证
  └── dump_coverage.py            — uiautomator2 dump 覆盖率验证

📄 产出文件示例:
  test_wechat_message.py   (可执行 Python 脚本，验收场景一)
  test_taobao_search.py    (可执行 Python 脚本，验收场景二)
  test_wechat_message.yaml (可读备案文件)
  report_20260516.html     (自包含 HTML 报告)
  report_20260516.pdf      (PDF 报告)

🌐 前端页面:
  Dashboard / 仪表盘       — http://localhost:8000/
  TaskInput / 任务输入     — http://localhost:8000/task-input
  Execution / 实时执行      — http://localhost:8000/execution/{id}
  Scripts / 脚本管理       — http://localhost:8000/scripts
  Reports / 报告管理       — http://localhost:8000/reports
  Devices / 设备管理       — http://localhost:8000/devices

📋 验收矩阵:
  见 §9.3 验收矩阵  — 7 个阶段、每个阶段输入/产出/验证方式/通过标准
```

---

*本文档基于 Open-AutoGLM v0.1.0 源码分析 + V2 架构方案制定。*
