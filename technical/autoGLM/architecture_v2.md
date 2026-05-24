# Open-AutoGLM V2 架构方案：Agent + Tools 自动化测试脚本平台

> 本文档基于对 Open-AutoGLM v0.1.0 源码的深入分析，结合 LLM/VLM 职责分离、MCP 工具化、多模式感知等设计思想，提出下一代架构方案。

---

## 目录

- [1. 核心理念对比](#1-核心理念对比)
- [2. 总体架构](#2-总体架构)
- [3. LLM 规划器](#3-llm-规划器)
- [4. Tool Registry 工具注册表](#4-tool-registry-工具注册表)
- [5. 感知层：三模式视觉理解](#5-感知层三模式视觉理解)
- [6. 执行层](#6-执行层)
- [7. 验证层](#7-验证层)
- [8. 脚本录制层](#8-脚本录制层)
- [9. 多设备调度器](#9-多设备调度器)
- [10. 双运行模式](#10-双运行模式)
- [11. 目录结构](#11-目录结构)
- [12. 数据流详解](#12-数据流详解)
- [13. 报告输出体系](#13-报告输出体系)
- [14. 与 v0.1.0 的映射关系](#14-与-v010-的映射关系)
- [15. 关键设计决策](#15-关键设计决策)

---

## 1. 核心理念对比

### 当前架构 (v0.1.0)

```
输入: 自然语言 + 截图(base64)
              │
              ▼
        ┌─────────────┐
        │   VLM 单体    │  ← 一个模型完成所有工作
        │ 理解/推理/规划│
        │ 动作输出      │
        └──────┬──────┘
               │ do(action="Tap", element=[x,y])
               ▼
        ┌─────────────┐
        │ ActionHandler│
        │ 路由+执行    │
        └─────────────┘

问题:
· LLM 和 VLM 耦合，无法独立演进
· 纯坐标定位，跨机型脆弱
· 无执行验证，失败静默
· 无脚本产出，不留痕
· 单设备运行
```

### V2 架构

```
输入: 自然语言
        │
        ▼
  ┌──────────────────────┐
  │   LLM 规划器 (纯文本)  │  ← 专注推理、规划、决策
  │  System Prompt + 规则 │
  │  + 工具描述           │
  └─────┬──────┬────────┘
        │      │ 调用工具
        │      ▼
        │  ┌──────────────────────────┐
        │  │     Tool Registry        │
        │  │  工具发现 / 注册 / 路由   │
        │  ├──────────────────────────┤
        │  │ 视觉工具  │ 结构化工具    │
        │  │ 执行工具  │ 验证工具      │
        │  │ 定位工具  │ 信息工具      │
        │  └──────────┬───────────────┘
        │             │
        │             ▼
        │  ┌─────────────────────┐
        │  │ 感知层(多模式)       │
        │  │ VLM / uiautomator2  │
        │  │ / OCR / 融合        │
        │  └──────────┬──────────┘
        │             │
        │             ▼
        │  ┌─────────────────────┐
        │  │ 执行层 (Device)      │
        │  │ ADB / HDC / WDA     │
        │  └──────────┬──────────┘
        │             │
        │             ▼
        │  ┌─────────────────────┐
        │  │ 验证层               │
        │  │ 截图比对 / 断言检查  │
        │  └──────────┬──────────┘
        │             │
        └─────────────┤
                      ▼
              ┌──────────────┐
              │  Recorder     │
              │  DSL 脚本输出  │
              └──────────────┘

核心变化:
· LLM 与 VLM 职责分离，各司其职
· 工具化架构，每个能力是可插拔 Tool
· 多模式感知，VLM 不可用时自动降级
· 执行→验证闭环，失败自愈
· 边执行边录脚本
```

---

## 2. 总体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Orchestrator (调度层)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ LLM会话池│ │ 设备池   │ │ 任务队列  │ │ 脚本仓库 │ │ 结果汇总 │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Agent 实例 1   │  │   Agent 实例 2   │  │   Agent 实例 N   │
│ device_id: A     │  │ device_id: B     │  │ device_id: ...   │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Agent Core (执行核)                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    LLM 规划器                                  │   │
│  │  · 理解用户需求                                               │   │
│  │  · 接收工具返回的结构化信息                                    │   │
│  │  · 推理决策 → 规划步骤                                        │   │
│  │  · 以 Function Calling 调用工具                                │   │
│  └──────────┬──────────┬──────────────┬──────────────────────────┘   │
│             │          │              │                               │
│             ▼          ▼              ▼                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Tool Registry                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ 感知工具  │ │ 定位工具  │ │ 执行工具  │ │ 校验/辅助工具│   │   │
│  │  │          │ │          │ │          │ │              │   │   │
│  │  │understand│ │find_by_  │ │tap       │ │verify_screen │   │   │
│  │  │          │ │text/id/  │ │type      │ │compare_image │   │   │
│  │  │          │ │desc      │ │swipe     │ │get_app_info  │   │   │
│  │  │          │ │          │ │launch    │ │wait          │   │   │
│  │  │          │ │          │ │back/home │ │take_over     │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ Locator  │ │ Verifier │ │ Recorder │ │ Replayer │               │
│  │ 多策略定位│ │ 步骤断言  │ │ DSL录制   │ │ 脚本回放 │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. LLM 规划器

### 3.1 定位

LLM 规划器是整个 Agent 的大脑，**只处理文本信息**。它不"看"图，而是通过工具获取结构化文本描述后做出决策。

### 3.2 System Prompt 设计

```python
SYSTEM_PROMPT = """
你是一个手机自动化测试的 AI 规划专家。
你的工作是通过调用工具来完成用户的任务，并最终输出可复用的测试脚本。

## 工作流程
1. 理解用户的需求
2. 调用感知工具了解当前屏幕状态
3. 分析感知工具返回的结构化信息
4. 规划下一步操作
5. 调用执行工具完成操作
6. 调用验证工具确认操作是否生效
7. 重复 2-6 直到任务完成
8. 调用 finish 工具结束任务，产出脚本

## 可用工具
{available_tools}

## 规则约束
{domain_rules}

## 输出格式
你的每次输出必须是以下格式之一：

1. 调用工具:
   <function_call>
   {"tool": "tool_name", "params": {...}}
   </function_call>

2. 结束任务:
   <function_call>
   {"tool": "finish", "params": {"message": "...", "script": "..."}}
   </function_call>

在每次输出前使用 <think>...</think> 进行推理。
"""
```

### 3.3 与 LLM 的交互协议

LLM 与 Agent Core 之间采用 **Function Calling (MCP 风格)** 通信：

```python
# LLM 请求（Agent → LLM）
[
  {"role": "system", "content": SYSTEM_PROMPT},
  {"role": "user", "content": "打开淘宝搜索无线耳机"},
  {"role": "assistant", "content": "<think>当前不知道屏幕状态，先调用感知工具</think>"},
  {"role": "function_call", "content": '{"tool": "ui.understand", "params": {"mode": "auto"}}'},
  {"role": "function_result", "content": '{"current_app": "System Home", "elements": ["微信", "淘宝", "抖音", ...]}'}
]

# LLM 响应（LLM → Agent）
{
  "thinking": "当前在桌面，目标App是淘宝，需要先启动淘宝",
  "tool_call": {
    "tool": "device.launch",
    "params": {"app": "淘宝"}
  }
}
```

### 3.4 工具描述注入

每个工具的描述会动态拼入 System Prompt，让 LLM 知道有什么工具可用、何时用：

```python
TOOLS_DESCRIPTION = """
## 感知工具
- ui.understand(mode="auto"|"vlm"|"dump"|"ocr"):
    理解当前屏幕内容，返回结构化文本描述。
    mode=auto 时会根据可用资源自动选择最佳模式。

- ui.find(method="text"|"id"|"desc"|"semantic", target: str):
    在屏幕中查找指定元素，返回坐标 bounds。
    method=semantic 时通过 LLM 语义理解定位。

## 执行工具
- device.tap(x: int, y: int):
    点击指定坐标。
- device.tap_element(method, target):
    通过定位方式点击元素（内部调用 ui.find + device.tap）。
- device.type(text: str):
    在当前聚焦的输入框输入文本。
- device.swipe(start_x, start_y, end_x, end_y):
    从起点滑动到终点。
- device.launch(app: str):
    启动指定应用。
- device.back():
    返回上一页。
- device.home():
    回到桌面。

## 验证工具
- verify.screen(expectation: str):
    验证当前屏幕是否满足预期描述。

## 辅助工具
- device.wait(duration: float):
    等待指定秒数。
- device.take_over(message: str):
    请求人工介入。
"""
```

---

## 4. Tool Registry 工具注册表

### 4.1 设计

Tool Registry 是一个可动态注册、发现、路由工具的容器，支持统一注册工具接口，按需加载工具实现。

```python
class ToolRegistry:
    """工具注册表：管理所有工具的注册、发现、调用"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册一个工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """获取工具"""
        return self._tools.get(name)

    def call(self, name: str, params: dict) -> Any:
        """调用工具"""
        tool = self.get(name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{name}' not found")
        return tool.execute(**params)

    def list_tools(self) -> list[Tool]:
        """列出所有已注册的工具"""
        return list(self._tools.values())

    def get_tools_description(self) -> str:
        """生成 LLM 可读的工具描述"""
        return "\n".join(t.to_prompt() for t in self._tools.values())


@dataclass
class Tool:
    """工具基类"""
    name: str
    description: str
    parameters: dict  # JSON Schema 格式
    enabled: bool = True

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError

    def to_prompt(self) -> str:
        """生成 LLM Prompt 中的工具描述"""
        return f"- {self.name}({self._format_params()}): {self.description}"

    def to_openai_function(self) -> dict:
        """生成 OpenAI Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
```

### 4.2 动态加载机制

工具可以从多种来源加载，支持**热插拔**：

```python
class ToolLoader:
    """工具加载器：支持多种加载方式"""

    @staticmethod
    def from_class(tool_class: type) -> Tool:
        """从 Python 类加载"""
        ...

    @staticmethod
    def from_mcp_server(url: str) -> list[Tool]:
        """从 MCP 服务器加载"""
        ...

    @staticmethod
    def from_entry_point(group: str = "phone_agent.tools") -> list[Tool]:
        """从 Python Entry Points 加载（插件机制）"""
        ...

    @staticmethod
    def from_config(config_path: str) -> list[Tool]:
        """从配置文件加载"""
        ...
```

### 4.3 完整工具清单

```python
# ============================================================
# 感知工具（Perception Tools）
# ============================================================

class UiUnderstandTool(Tool):
    """理解当前屏幕内容，支持多模式"""
    name = "ui.understand"

    def execute(self, mode: str = "auto") -> dict:
        """
        根据 mode 参数选择不同的理解方式:
        - "vlm":  调用 VLM 截图 + 视觉理解
        - "dump": uiautomator2 dump 控件树
        - "ocr":  OCR 提取屏幕文字
        - "auto": 自动选择最佳可用方式
        """
        ...

class UiFindTool(Tool):
    """在屏幕中查找元素"""
    name = "ui.find"

    def execute(self, method: str, target: str) -> dict | None:
        """
        method:
          "text"     - 匹配 text 属性
          "id"       - 匹配 resource-id
          "desc"     - 匹配 content-desc
          "semantic" - LLM 语义理解
        returns: {"found": bool, "bounds": [x1,y1,x2,y2], "element": {...}}
        """

class UiGetAppInfoTool(Tool):
    """获取当前 App 信息"""
    name = "ui.get_app_info"

    def execute(self) -> dict:
        """返回当前 App 名称、包名、activity"""


# ============================================================
# 定位工具（Locator Tools）
# ============================================================

class LocatorTool(Tool):
    """多策略元素定位器：按优先级链重试"""
    name = "locator.find"

    def execute(self, target: str, by: str = "auto",
                timeout: float = 5.0) -> dict:
        """
        定位策略链:
        1. 当 by="text"   → 优先 text 精确匹配
        2. 当 by="id"     → 优先 resource-id 匹配
        3. 当 by="desc"   → 优先 content-desc 匹配
        4. 当 by="auto"   → 依次尝试 text → id → desc → semantic
        5. 当 by="semantic" → LLM 语义理解
        """


# ============================================================
# 执行工具（Device Action Tools）
# ============================================================

class DeviceTapCoordinateTool(Tool):
    """点击指定坐标"""
    name = "device.tap"

    def execute(self, x: int, y: int) -> dict:
        """x, y: 绝对像素坐标"""

class DeviceTapElementTool(Tool):
    """通过定位方式点击元素（组合工具）"""
    name = "device.tap_element"

    def execute(self, method: str, target: str) -> dict:
        """内部调用 locator.find + device.tap"""

class DeviceTypeTool(Tool):
    """输入文本"""
    name = "device.type"

    def execute(self, text: str) -> dict:
        """自动切换 ADB Keyboard → 输入 → 恢复"""

class DeviceSwipeTool(Tool):
    """滑动"""
    name = "device.swipe"

    def execute(self, start_x: int, start_y: int,
                end_x: int, end_y: int,
                duration_ms: int | None = None) -> dict:
        ...

class DeviceLaunchTool(Tool):
    """启动 App"""
    name = "device.launch"

    def execute(self, app: str) -> dict:
        """通过 App 名称/包名启动"""

class DeviceBackTool(Tool):
    """返回"""
    name = "device.back"

class DeviceHomeTool(Tool):
    name = "device.home"


# ============================================================
# 验证工具（Verification Tools）
# ============================================================

class VerifyScreenTool(Tool):
    """验证当前屏幕是否符合预期"""
    name = "verify.screen"

    def execute(self, expectation: str) -> dict:
        """
        expectation: "应该在淘宝搜索结果页面，显示无线耳机列表"
        内部: 截图 → VLM/LLM 判断是否符合预期
        returns: {"passed": bool, "reason": str, "screenshot": "base64..."}
        """

class CompareScreenshotTool(Tool):
    """截图比对"""
    name = "verify.compare_image"

    def execute(self, baseline: str, current: str | None = None) -> dict:
        """
        baseline: 基准截图 base64
        current:  当前截图 base64（默认自动截取）
        returns: {"match": bool, "diff_ratio": float}
        """


# ============================================================
# 辅助工具
# ============================================================

class WaitTool(Tool):
    name = "device.wait"

    def execute(self, duration: float = 1.0) -> dict:
        ...

class TakeOverTool(Tool):
    name = "device.take_over"

    def execute(self, message: str) -> dict:
        ...

class FinishTool(Tool):
    name = "finish"

    def execute(self, message: str, script: str | None = None) -> dict:
        """结束任务，可选输出录制的脚本"""
        ...
```

---

## 5. 感知层：三模式视觉理解

### 5.1 架构

这是纯 LLM 模式下替代 VLM 能力的关键模块：

```
┌─────────────────────────────────────┐
│           Perception Engine          │
│                                      │
│  ┌──────────┐  ┌──────────┐        │
│  │ Mode A   │  │ Mode B   │  Mode C │
│  │ VLM 看图 │  │ UI Dump  │  OCR   │
│  └────┬─────┘  └────┬─────┘  ─┬─── │
│       │             │         │     │
│       ▼             ▼         ▼     │
│  ┌──────────────────────────────┐  │
│  │     Screen Context Builder   │  │
│  │     合并 → 结构化 → 压缩     │  │
│  └──────────────┬───────────────┘  │
│                 │                  │
│                 ▼                  │
│  Structured Text for LLM          │
└─────────────────────────────────────┘
```

### 5.2 模式 A：VLM 看图理解

```python
class VlmPerception:
    """VLM 视觉理解模式：截图 → VLM → 文本描述"""

    def __init__(self, vlm_client: ModelClient):
        self.vlm = vlm_client

    def understand(self) -> str:
        """截图 → VLM 理解 → 返回文本描述"""
        screenshot = get_screenshot()

        prompt = """
        请详细描述当前手机屏幕内容，包括：
        1. 当前在什么 App 或界面
        2. 屏幕上有哪些可交互的元素（按钮、输入框、列表项等）
        3. 每个元素的大致位置（左上、右上、中间、底部等）
        4. 顶部和底部导航栏的内容
        5. 页面的整体布局结构
        """

        response = self.vlm.chat([
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot}"}},
                {"type": "text", "text": prompt}
            ]}
        ])

        return response.content
```

输出示例：
```
当前屏幕描述：
- App: 淘宝首页
- 顶部: 搜索框（中间区域），扫码图标（右上角），消息图标（左上角）
- 中部: 金刚区（8个图标：天猫国际、淘宝直播、充值中心...），
        限时秒杀横幅，
        推荐商品流（图文卡片列表）
- 底部导航栏: 首页 | 逛逛 | 消息 | 购物车 | 我的
  （当前选中: 首页）
```

### 5.3 模式 B：uiautomator2 Dump

```python
class UiAutomatorPerception:
    """UI Dump 模式：通过 uiautomator2 获取控件树"""

    def __init__(self, device_id: str | None = None):
        import uiautomator2 as u2
        self.device = u2.connect(device_id)

    def understand(self) -> str:
        """dump → XML → 结构化文本（给 LLM）"""
        xml = self.device.dump_hierarchy()
        root = self._parse_xml(xml)
        compressed = self._compress(root, max_items=50)
        return compressed

    def _compress(self, root, max_items: int) -> str:
        """将 XML 控件树压缩为 LLM 友好的文本格式"""
        # 过滤不可见/不可交互节点
        # 只保留 clickable=True / long-clickable=True / scrollable=True
        # 保留 text / content-desc / bounds / resource-id
        ...

    def find_by_text(self, text: str) -> dict | None:
        """直接通过 uiautomator2 查找元素"""
        element = self.device(text=text)
        if element.exists:
            bounds = element.bounds
            return {
                "found": True,
                "bounds": [bounds.left, bounds.top, bounds.right, bounds.bottom],
                "center": [bounds.center[0], bounds.center[1]],
            }
        return None
```

输出示例：
```
=== 屏幕结构 (UI Dump) ===
当前App: 淘宝 (com.taobao.taobao)

┌─ [顶部导航栏]
│  ├─ 消息 (icon, clickable) [left=0,top=0,right=100,bottom=80]
│  ├─ 搜索框 (text="搜索", clickable) [left=100,top=10,right=900,bottom=70]
│  └─ 扫码 (icon, clickable) [left=900,top=0,right=1000,bottom=80]
│
├─ [金刚区] scrollable
│  ├─ 天猫国际 (clickable) [left=30,top=150,right=150,bottom=280]
│  ├─ 淘宝直播 (clickable) [left=170,top=150,right=290,bottom=280]
│  ├─ 充值中心 (clickable) [left=310,top=150,right=430,bottom=280]
│  └─ ... (共8项)
│
├─ [限时秒杀] 横幅
│
├─ [推荐商品流] scrollable
│  ├─ 商品卡片1 (clickable) ...
│  └─ ...
│
└─ [底部导航栏]
   ● 首页 | ○ 逛逛 | ○ 消息 | ○ 购物车 | ○ 我的
   (● = 当前选中)
================================
```

### 5.4 模式 C：OCR 文字提取

```python
class OcrPerception:
    """OCR 模式：截图 → OCR → 文字区域"""

    def __init__(self, engine: str = "paddle"):
        if engine == "paddle":
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        elif engine == "easyocr":
            import easyocr
            self.ocr = easyocr.Reader(['ch_sim', 'en'])

    def understand(self) -> str:
        """截图 → OCR → 结构化文字位置描述"""
        screenshot = "screenshot.png"
        results = self.ocr.ocr(screenshot)

        lines = []
        for result in results[0]:
            bbox, (text, confidence) = result[0], result[1]
            x1, y1 = bbox[0]
            x2, y2 = bbox[2]
            lines.append(f"  [{int(x1)},{int(y1)}]-[{int(x2)},{int(y2)}]: \"{text}\" (conf:{confidence:.2f})")

        return "=== 屏幕文字 (OCR) ===\n" + "\n".join(lines)
```

输出示例：
```
=== 屏幕文字 (OCR) ===
  [40,45]-[120,75]: "淘宝" (conf:0.99)
  [130,20]-[850,70]: "搜你想搜" (conf:0.95)
  [900,25]-[980,70]: "扫一扫" (conf:0.97)
  [30,140]-[150,270]: "天猫国际" (conf:0.94)
  [170,140]-[290,270]: "淘宝直播" (conf:0.91)
  ...
  [30,1850]-[120,1900]: "首页" (conf:0.99)
  [200,1850]-[300,1900]: "逛逛" (conf:0.98)
  ...
```

### 5.5 自动模式选择器

```python
class PerceptionEngine:
    """感知引擎：自动选择最佳模式"""

    MODES = {
        "vlm": VlmPerception,
        "dump": UiAutomatorPerception,
        "ocr": OcrPerception,
    }

    def __init__(self, config: PerceptionConfig):
        self.config = config
        self._instances = {}

    def understand(self, mode: str = "auto") -> str:
        if mode == "vlm":
            return self._get("vlm").understand()

        elif mode == "dump":
            return self._get("dump").understand()

        elif mode == "ocr":
            return self._get("ocr").understand()

        else:  # mode == "auto" → 自动选择
            # 优先级: VLM > UI Dump > OCR
            if self.config.vlm_enabled:
                return self._get("vlm").understand()
            try:
                return self._get("dump").understand()
            except Exception:
                return self._get("ocr").understand()

    def find_element(self, method: str, target: str) -> dict | None:
        """智能定位元素（跨模式）"""
        # 先尝试 dump 精确匹配（最快最准）
        if method in ("text", "id", "desc"):
            dumper = self._get("dump")
            result = dumper.find_by_text(target)  # + find_by_id, find_by_desc
            if result:
                return result

        # dump 失败 → OCR 找文字区域
        if method == "text":
            ocr = self._get("ocr")
            result = ocr.find_text(target)
            if result:
                return result

        # 全部失败 → VLM 语义理解
        if self.config.vlm_enabled:
            return self._get("vlm").find_element(target)

        return None
```

---

## 6. 执行层

执行层继承并增强 v0.1.0 的 `DeviceFactory`，新增工具粒度的执行器：

```python
class DeviceExecutor:
    """设备执行器：底层操作（v0.1.0 的 DeviceFactory 增强版）"""

    def __init__(self, device_type: str = "adb",
                 device_id: str | None = None):
        self.factory = get_device_factory()  # v0.1.0 复用
        # or: self.backend = DeviceBackend.create(device_type, device_id)

    def tap(self, x: int, y: int) -> dict:
        self.factory.tap(x, y, self.device_id)
        return {"success": True, "x": x, "y": y, "action": "tap"}

    def type_text(self, text: str) -> dict:
        original_ime = self.factory.detect_and_set_adb_keyboard(self.device_id)
        self.factory.clear_text(self.device_id)
        self.factory.type_text(text, self.device_id)
        self.factory.restore_keyboard(original_ime, self.device_id)
        return {"success": True, "text": text, "action": "type"}
```

---

## 7. 验证层

验证层是保证脚本可靠性的核心新增模块：

```python
class Verifier:
    """验证器：确认操作是否生效"""

    def __init__(self, perception: PerceptionEngine,
                 llm_client: ModelClient | None = None):
        self.perception = perception
        self.llm = llm_client

    def verify_action(self, action: dict, before_screen: str,
                      after_screen: str) -> dict:
        """
        验证一个动作是否按预期执行成功

        策略链:
        1. 截面对比 → 是否发生变化
        2. VLM/LLM 判断 → 预期状态是否达到
        3. 结构化断言 → 元素是否存在/消失
        """
        ...

    def verify_screen(self, expectation: str) -> dict:
        """
        验证屏幕是否符合预期描述
        用于脚本回放时的步骤断言
        """
        current = self.perception.understand()
        ...

    def compare_screenshots(self, before: str, after: str) -> dict:
        """两帧截图做像素级/结构级对比"""
        ...
```

### 7.1 失败 → Prompt 动态增强 → LLM 重试

这是区别于简单 retry 的核心机制。当验证失败时，不是盲目重试，而是**将失败信息注入新的一轮 LLM 推理**，让 LLM 分析失败原因并调整策略：

```
正常流程:
  LLM 规划 → 执行 → 验证 → 通过 → 继续下一步

失败流程:
  LLM 规划 → 执行 → 验证 → 失败
                              ↓
                    收集失败上下文:
                    · 执行前的截图
                    · 执行后的截图
                    · 工具返回的错误信息
                    · 当前屏幕状态
                              ↓
                    构建增强 Prompt:
                    "上一步你规划了 [动作A]，
                     执行后预期 [状态B]，
                     但验证结果 [状态C]，
                     可能原因分析：
                     1. 坐标偏移
                     2. 元素未加载
                     3. 页面跳转异常
                     请分析失败原因并给出修正后的操作"
                              ↓
                    LLM 重新推理 → 调整后的动作 → 执行 → 验证
```

实现：

```python
class FailureRecovery:
    """失败恢复：收集上下文 → 增强 Prompt → 调 LLM 重试"""

    def __init__(self, llm_planner):
        self.llm = llm_planner

    def recover(self, failed_step: dict,
                before_screenshot: str,
                after_screenshot: str,
                error: str,
                max_retries: int = 3) -> tuple[bool, dict]:
        """
        失败恢复流程:
        1. 构建增强 Prompt（包含失败上下文）
        2. LLM 分析原因并输出调整后的动作
        3. 执行调整后的动作
        4. 重新验证
        """
        for attempt in range(max_retries):
            # 构建增强 Prompt
            enhanced_prompt = self._build_enhanced_prompt(
                failed_step=failed_step,
                error=error,
                attempt=attempt + 1,
                before_screenshot=before_screenshot,
                after_screenshot=after_screenshot,
            )

            # LLM 分析 + 输出新动作
            new_action = self.llm.plan(enhanced_prompt)

            # 执行新动作
            result = self.llm.execute_tool(new_action)

            # 验证
            if result.get("success"):
                return True, result

            # 更新 error 继续下一轮
            error = result.get("error", "Unknown error")

        return False, {"error": f"Failed after {max_retries} retries"}

    def _build_enhanced_prompt(self, failed_step: dict,
                                error: str,
                                attempt: int,
                                before_screenshot: str,
                                after_screenshot: str) -> str:
        """构建包含失败上下文的增强 Prompt"""
        return f"""
## 上一步执行失败

你上一步规划的动作:
  工具: {failed_step.get('tool')}
  参数: {failed_step.get('params')}

执行结果:
  错误信息: {error}

## 当前屏幕状态
{self.perception.understand(mode="dump")}

## 要求
请分析失败原因，并输出一个新的操作来解决当前问题。
注意:
- 可能是定位方式不准确，尝试切换定位方式
- 可能是页面未加载完成，先 Wait 再操作
- 可能是元素被遮挡，先 Back 或滚动再操作

请输出修正后的工具调用。
"""
```

### 7.2 自愈策略链

```python
class SelfHealingStrategy:
    """自愈策略：验证失败后的自动恢复"""

    HEALING_PIPELINE = [
        "re_prompt_llm",       # ① 增强 Prompt → LLM 重规划（首选）
        "switch_locator",      # ② 切换定位方式（text→id→desc→坐标）
        "adjust_coordinate",   # ③ 坐标偏移重试
        "wait_and_retry",      # ④ 等待后重试
        "back_and_retry",      # ⑤ 返回前一页重试
        "skip_step",           # ⑥ 跳过该步骤（标记为伪代码）
    ]

    def heal(self, step: dict, context: dict) -> HealingResult:
        for strategy in self.HEALING_PIPELINE:
            result = self._apply_strategy(strategy, step, context)
            if result.success:
                return result
        # 全部失败 → 标记为伪代码
        return HealingResult(
            success=False,
            pseudocode=self._generate_pseudocode(step, context.reason)
        )
```

---

## 8. 脚本录制层

核心原则——**三段式设计**：

```
LLM 规划执行（需 LLM）
  ↓ 录制为中间格式（结构化 JSON / YAML）
  ↓ 编译器（Compiler）编译
Python 脚本 + 移动端框架（uiautomator2 / Appium / ...） ← 执行脚本，无需 LLM
```

### 8.1 脚本三形态

```
                              ┌──────────────────┐
                              │  中间格式 (JSON)   │  ← 机器读写，录制时使用
                              │  结构化字段        │
                              │  action + method  │
                              │  + target + fb链  │
                              └────────┬─────────┘
                                       │
                       ┌───────────────┼───────────────┐
                       ▼               ▼               ▼
              ┌────────────┐  ┌────────────┐  ┌────────────┐
              │ Python脚本  │  │ Python脚本  │  │ YAML 备案  │
              │ (全部exact) │  │ (混合)      │  │ (归档)     │
              │            │  │            │  │           │
              │ pytest直接  │  │ exact可跑  │  │ 可读存档   │
              │ 无需LLM    │  │ pseudo待补 │  │ 版本管理   │
              └────────────┘  └────────────┘  └────────────┘
                     │               │
                     ▼               ▼
               pytest / uiautomator2 / Appium 直接执行
                     ║
                    LLM 完全不参与
```

各格式用途：

| 格式 | 用途 | 是否执行 | 可读性 |
|------|------|---------|-------|
| **Python** | **执行格式**，`pytest` 直接跑 | ✅ | 中等 |
| **JSON** | 内部中间格式，录制/编译用 | ❌ | 低 |
| **YAML** | **备案格式**，归档/版本管理/人工查阅 | ❌ | 高 |

### 8.2 最终产出：Python + uiautomator2 脚本

这是**唯一**的执行格式，不需要 LLM 参与，直接 `pytest` 跑：

```python
"""
AutoGLM Generated Test: 打开淘宝搜索无线耳机，筛选价格低于200元
Device: Xiaomi 14 | Android 14 | 1200x2670
Success Rate: 100% | 8/8 steps exact
"""
import uiautomator2 as u2
import time


def test_search_headphones():
    """打开淘宝搜索无线耳机，筛选价格低于200元"""
    device = u2.connect()

    # ── Step 1: Launch 淘宝 ──
    device.app_start("com.taobao.taobao")
    time.sleep(2)
    # assert device(text="搜索框").exists  ← verification

    # ── Step 2: Tap 搜索框 by text ──
    device(text="搜索框").click()
    time.sleep(1)
    # fallback chain recorded:
    #   [id: com.taobao:id/search_box]
    #   [coordinate: (500, 100)]

    # ── Step 3: Type "无线耳机" ──
    device(text="搜索框").set_text("无线耳机")
    time.sleep(1)

    # ── Step 4: Tap 搜索 by text ──
    device(text="搜索").click()
    time.sleep(2)

    # ── Step 5: Tap 价格筛选 by text ──
    device(text="价格筛选").click()
    time.sleep(1)

    # ── Step 6: Tap 200元以下 by text ──
    device(text="200元以下").click()
    time.sleep(1)

    # ── Step 7: Verify results ──
    assert device(textContains="无线耳机").exists
    assert device(textContains="¥").exists
```

对应不同框架的模板：

```python
# ── 框架: uiautomator2 ──
import uiautomator2 as u2
d = u2.connect()
d(text="搜索框").click()
d(text="搜索框").set_text("无线耳机")

# ── 框架: Appium ──
from appium import webdriver
driver.find_element(By.XPATH, "//*[@text='搜索框']").click()
driver.find_element(By.XPATH, "//*[@text='搜索框']").send_keys("无线耳机")

# ── 框架: 纯 ADB 命令 ──
import subprocess
subprocess.run(["adb", "shell", "input", "tap", "500", "100"])
subprocess.run(["adb", "shell", "am", "broadcast", "-a", "ADB_INPUT_B64", ...])
```

### 8.3 中间格式（JSON，仅录制时使用）

中间格式是结构化的、机器可读的，**不含自然语言字段**。它的唯一用途是编译为 Python 脚本：

```json
{
  "metadata": {
    "task": "打开淘宝搜索无线耳机，筛选价格低于200元",
    "framework": "uiautomator2",
    "device_info": {
      "model": "Xiaomi 14",
      "os_version": "Android 14",
      "resolution": "1200x2670"
    }
  },
  "steps": [
    {
      "id": 1,
      "action": "launch",
      "status": "exact",
      "params": {
        "app": "淘宝",
        "package": "com.taobao.taobao"
      },
      "verification": [
        {"type": "element_exists", "method": "text", "target": "搜索框"}
      ],
      "code_template": "device.app_start(\"{package}\")"
    },
    {
      "id": 2,
      "action": "tap_element",
      "status": "exact",
      "params": {
        "method": "text",
        "target": "搜索框"
      },
      "fallback_chain": [
        {"method": "id", "target": "com.taobao:id/search_box"},
        {"method": "coordinate", "x": 500, "y": 100}
      ],
      "verification": [
        {"type": "element_focused", "method": "text", "target": "搜索框"}
      ],
      "code_template": "device(text=\"{target}\").click()"
    },
    {
      "id": 3,
      "action": "type",
      "status": "exact",
      "params": {
        "text": "无线耳机"
      },
      "code_template": "device(text=\"{target}\").set_text(\"{text}\")"
    },
    {
      "id": 4,
      "action": "tap_element",
      "status": "exact",
      "params": {
        "method": "text",
        "target": "搜索"
      }
    },
    {
      "id": 5,
      "action": "tap_element",
      "status": "pseudocode",
      "params": {
        "method": "text",
        "target": "价格筛选"
      },
      "error": "Element '价格筛选' not found on screen",
      "pseudocode": "device(text=\"价格筛选\").click()",
      "suggested_fix_comment": [
        "可能原因: 筛选入口在不同App版本位置不同",
        "尝试1: device(text=\"筛选\").click()",
        "尝试2: device(text=\"排序\").click()",
        "尝试3: device(className=\"android.widget.Button\", index=3).click()",
        "参考截图: 已嵌入报告 Step 5"
      ]
    },
    {
      "id": 6,
      "action": "tap_element",
      "status": "exact",
      "params": {
        "method": "text",
        "target": "200元以下"
      }
    },
    {
      "id": 7,
      "action": "verify",
      "status": "exact",
      "params": {
        "type": "element_exists",
        "method": "text_contains",
        "target": "无线耳机"
      },
      "code_template": "assert device(textContains=\"{target}\").exists"
    }
  ]
}
```

**关键区别**：没有任何自然语言字段。`method + target` 本身就是机器可读的定位指令，Compiler 直接转成框架 API 调用。

### 8.4 Compiler：中间格式 → Python 脚本

```python
class ScriptCompiler:
    """
    编译器：将中间格式 (JSON) 编译为可执行的 Python 脚本。

    这是"不需要 LLM 参与执行"的关键——
    中间格式全部是结构化字段，Compiler 做的是 1:1 的代码生成。
    """

    # 动作 → uiautomator2 代码模板映射
    CODE_TEMPLATES_UA2 = {
        "launch":             'device.app_start("{package}")',
        "tap_element_text":   'device(text="{target}").click()',
        "tap_element_id":     'device(resourceId="{target}").click()',
        "tap_element_desc":   'device(description="{target}").click()',
        "tap_coordinate":     'device.click({x}, {y})',
        "type":               'device(text="{target}").set_text("{text}")',
        "swipe":              'device.swipe({start_x}, {start_y}, {end_x}, {end_y})',
        "back":               'device.press("back")',
        "home":               'device.press("home")',
        "wait":               'time.sleep({duration})',
        "verify_element":     'assert device(textContains="{target}").exists',
        "verify_no_element":  'assert not device(text="{target}").exists',
    }

    def compile(self, intermediate: dict,
                framework: str = "uiautomator2") -> str:
        """
        编译中间格式 → Python 脚本

        纯模板替换，不需要 LLM。
        method + target 是结构化字段，不是自然语言。
        """
        metadata = intermediate["metadata"]
        lines = [
            f'"""',
            f'AutoGLM Generated Test: {metadata["task"]}',
            f'Device: {metadata["device_info"]["model"]}',
            f'"""',
            self._import_block(framework),
            "",
        ]

        for step in intermediate["steps"]:
            if step["status"] == "exact":
                code = self._compile_exact(step, framework)
                lines.extend(self._with_comment(code, step))
            else:
                code = self._compile_pseudocode(step, framework)
                lines.append(code)
            lines.append("")

        return "\n".join(lines)

    def _compile_exact(self, step: dict, framework: str) -> str:
        """编译精确步骤"""
        action = step["action"]

        if action == "launch":
            return self.CODE_TEMPLATES_UA2["launch"].format(**step["params"])

        if action == "tap_element":
            method = step["params"]["method"]  # "text" | "id" | "desc"
            target = step["params"]["target"]
            template_key = f"tap_element_{method}"
            template = self.CODE_TEMPLATES_UA2.get(template_key)
            if template:
                return template.format(target=target)

            # fallback: 坐标
            if "fallback_chain" in step:
                for fb in step["fallback_chain"]:
                    if fb["method"] == "coordinate":
                        return self.CODE_TEMPLATES_UA2["tap_coordinate"].format(
                            x=fb["x"], y=fb["y"]
                        )

        if action == "type":
            target = step["params"].get("target", "")
            text = step["params"]["text"]
            if target:
                return f'device(text="{target}").set_text("{text}")'
            return f'device.set_text("{text}")'

        # ... 其他动作
        return f"# TODO: compile {action}"

    def _compile_pseudocode(self, step: dict, framework: str) -> str:
        """编译伪代码步骤（标记 + 修复建议）"""
        lines = [
            f"# ⚠️ PSEUDOCODE - Step {step['id']}: "
            f"需要人工验证",
        ]
        if step.get("pseudocode"):
            lines.append(f"# 建议实现:")
            lines.append(f"#   {step['pseudocode']}")
        if step.get("suggested_fix_comment"):
            for comment in step["suggested_fix_comment"]:
                lines.append(f"#   {comment}")
        lines.append("pass  # TODO: 补全此步骤")
        return "\n".join(lines)

    def _import_block(self, framework: str) -> str:
        if framework == "uiautomator2":
            return "import uiautomator2 as u2\nimport time\n\ndevice = u2.connect()"
        elif framework == "appium":
            return "from appium import webdriver\nimport time\n\n# driver = webdriver.Remote(...)"
        return "import subprocess\nimport time"
```

### 8.5 伪代码生成

失败步骤在中间格式中标记 `status: "pseudocode"`，Python 输出对应位置生成标注 + 修复建议。用户打开 `.py` 文件，搜索 `PSEUDOCODE` 关键字即可找到待补全位置：

```python
# ⚠️ PSEUDOCODE - Step 5: 需要人工验证
# 建议实现:
#   device(text="价格筛选").click()
# 可能原因: 筛选入口在不同版本位置不同
# 尝试1: device(text="筛选").click()
# 尝试2: device(className="android.widget.Button", index=3).click()
# 参考截图: 已嵌入 HTML 报告 Step 5
pass  # TODO: 补全此步骤
```

### 8.6 三场景脚本产出

```
场景 A: 全部 exact（8/8 步骤成功执行）
  → 输出完整的 Python 脚本，可直接 pytest 运行
  → 文件: test_taobao_search.py (242 行)
  → 执行: pytest test_taobao_search.py  ← LLM 不参与

场景 B: 混合（7 exact + 1 pseudocode）
  → 脚本中 exact 步骤完整生成
  → 失败步骤标记为 # PSEUDOCODE + 修复建议
  → 用户搜索 "PSEUDOCODE" 补全后即可运行
  → 执行: 用户手动编辑 → pytest

场景 C: 中断（5 exact + 3 未执行）
  → 已执行的 5 步 exact 编译
  → 未执行的 3 步根据 LLM 规划的意图生成 pseudocode
  → 输出: 可编辑的 Python 文件 + 人工补全提示
```

### 8.7 Recorder 实现

```python
class ScriptRecorder:
    """脚本录制器：记录中间格式，最终编译为 Python"""

    def __init__(self):
        self.intermediate = {
            "metadata": {
                "task": "",
                "framework": "uiautomator2",
                "device_info": {},
                "success_rate": 1.0,
            },
            "steps": [],
        }
        self.compiler = ScriptCompiler()

    def record_step(self, step: dict):
        """
        记录单步（中间格式）
        step 是全结构化的，无自然语言字段:
        {
          "id": 1,
          "action": "tap_element",
          "status": "exact",
          "params": {"method": "text", "target": "搜索框"},
          "fallback_chain": [...],
          "code_template": "device(text=\"{target}\").click()"
        }
        """
        self.intermediate["steps"].append(step)
        self._recalc_rate()

    def export_python(self, framework: str = "uiautomator2") -> str:
        """编译为可直接执行的 Python 脚本（无需 LLM）"""
        return self.compiler.compile(self.intermediate, framework)

    def export_intermediate_json(self) -> str:
        """导出中间格式 JSON"""
        return json.dumps(self.intermediate, ensure_ascii=False, indent=2)

    def export_archive_yaml(self) -> str:
        """导出 YAML 备案格式（人工可读，适合版本管理）"""
        import yaml
        return yaml.dump(self.intermediate, allow_unicode=True,
                         default_flow_style=False, sort_keys=False)
```

---

## 9. 多设备调度器

```python
class Orchestrator:
    """调度器：管理多设备并发执行"""

    def __init__(self):
        self.device_pool: dict[str, AgentInstance] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.script_store: ScriptStore = ScriptStore()

    def register_device(self, device_id: str,
                        device_type: str = "adb") -> bool:
        """注册设备到设备池"""
        if device_id in self.device_pool:
            return False
        agent = AgentInstance(device_id, device_type)
        self.device_pool[device_id] = agent
        return True

    def remove_device(self, device_id: str):
        """从设备池移除设备"""
        ...

    async def dispatch_task(self, task: str | dict,
                            device_ids: list[str] | None = None):
        """
        分发任务到指定设备（或所有空闲设备）

        task: 自然语言描述 或 DSL 脚本
        device_ids: 指定设备，None 表示选空闲设备
        """
        devices = self._get_target_devices(device_ids)
        tasks = [self._run_on_device(d, task) for d in devices]
        results = await asyncio.gather(*tasks)
        return results

    async def run_script_on_devices(self, script: dict,
                                     device_ids: list[str]):
        """在指定设备上并发回放脚本"""
        ...

    def get_device_status(self) -> dict:
        """获取所有设备状态"""
        ...

    def get_idle_devices(self) -> list[str]:
        """获取空闲设备"""
        ...


class AgentInstance:
    """单个 Agent 实例：与一个设备绑定，状态隔离"""

    def __init__(self, device_id: str, device_type: str):
        self.device_id = device_id
        self.device_type = device_type
        self.busy = False
        self.llm = LLMPlanner()
        self.tools = ToolRegistry()
        self.executor = DeviceExecutor(device_type, device_id)
        self.perception = PerceptionEngine(...)
        self.recorder = ScriptRecorder()
        self.verifier = Verifier(...)

    async def execute_task(self, task: str) -> ExecutionResult:
        """执行一个完整任务，输出结果+脚本"""
        self.busy = True
        try:
            # 注册当前设备相关的工具
            self._register_tools()

            # LLM 循环执行
            while not self._is_finished():
                # 1. LLM 规划 → 调工具
                # 2. 验证结果
                # 3. 录制步骤
                ...

            return ExecutionResult(
                success=True,
                script=self.recorder.export_python(),
                steps=len(self.recorder.intermediate["steps"]),
                snapshots=...,
            )
        finally:
            self.busy = False


### 9.1 多设备报告聚合

Orchestrator 在所有设备执行完毕后，聚合生成统一报告：

```python
class ReportAggregator:
    """多设备执行报告聚合器"""

    def __init__(self):
        self.html_gen = HtmlReportGenerator()
        self.pdf_gen = PdfReportGenerator(self.html_gen)

    def aggregate(self, task: str,
                  device_results: dict[str, ExecutionResult]) -> TestReport:
        """
        聚合多设备执行结果 → 统一报告

        Args:
            task: 原始任务描述
            device_results: {device_id: ExecutionResult}

        Returns:
            TestReport 数据模型
        """
        device_runs = []
        total_exact = 0
        total_pseudo = 0
        total_steps = 0

        for device_id, result in device_results.items():
            # 提取该设备的步骤统计
            exact = sum(1 for s in result.steps if s.status == "exact")
            pseudo = sum(1 for s in result.steps if s.status == "pseudocode")
            rate = exact / (exact + pseudo) if (exact + pseudo) > 0 else 0

            device_run = DeviceRunInfo(
                device_id=device_id,
                device_model=result.device_model,
                os_version=result.os_version,
                resolution=result.resolution,
                steps=[self._to_report_step(s) for s in result.steps],
                success_rate=rate,
                duration=result.duration,
                status="passed" if rate >= result.pass_threshold
                       else ("partial" if pseudo > 0 else "failed"),
                screenshots=result.snapshots,
            )
            device_runs.append(device_run)
            total_exact += exact
            total_pseudo += pseudo
            total_steps += len(result.steps)

        report = TestReport(
            title="手机自动化测试报告",
            task_description=task,
            created_at=datetime.now().isoformat(),
            duration_seconds=max(r.duration for r in device_results.values()),
            device_info=device_runs,
            total_devices=len(device_results),
            total_steps=total_steps,
            total_exact=total_exact,
            total_pseudocode=total_pseudo,
            global_success_rate=total_exact / total_steps if total_steps > 0 else 0,
            passed=(total_exact / total_steps) >= 0.8 if total_steps > 0 else False,
            scripts={d: r.script for d, r in device_results.items()},
            logs={d: r.logs for d, r in device_results.items()},
        )

        return report

    def generate_html(self, report: TestReport) -> str:
        """生成 HTML 报告字符串"""
        return self.html_gen.generate(report)

    def generate_pdf(self, report: TestReport, output_path: str):
        """生成 PDF 报告文件"""
        self.pdf_gen.generate(report, output_path)

    def save_report(self, report: TestReport,
                    html_path: str, pdf_path: str | None = None):
        """保存报告文件"""
        # HTML
        html = self.generate_html(report)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # PDF
        if pdf_path:
            self.generate_pdf(report, pdf_path)

        return {
            "html": html_path,
            "pdf": pdf_path,
            "total_exact": report.total_exact,
            "total_pseudocode": report.total_pseudocode,
            "success_rate": report.global_success_rate,
        }
```
```

---

## 10. 双运行模式

### 10.1 模式 A：LLM + VLM（完整模式）

```
用户: "打开淘宝搜索无线耳机"

LLM 规划器:
  1. <think>先了解当前屏幕状态</think>
  2. → 调用工具 ui.understand(mode="vlm")

VLM 工具:
  截图 → VLM 看图 → "当前在桌面，有淘宝图标"

LLM 继续:
  3. <think>在桌面，目标App是淘宝，启动它</think>
  4. → 调用工具 device.launch(app="淘宝")

LLM 继续:
  5. <think>淘宝打开了，搜索框在顶部中间，点击它</think>
  6. → 调用工具 device.tap_element(method="text", target="搜索框")

...循环直到 finish ...
```

### 10.2 模式 B：纯 LLM（降级模式）

```
用户: "打开淘宝搜索无线耳机"

LLM 规划器:
  1. <think>先了解当前屏幕状态</think>
  2. → 调用工具 ui.understand(mode="dump")

uiautomator2 工具:
  dump → XML → 结构化文本 → "当前App: System Home, 可点击元素: [微信, 淘宝, 抖音, ...]"

LLM 继续:
  3. <think>在桌面，找到"淘宝"可点击，启动它</think>
  4. → 调用工具 device.launch(app="淘宝")

LLM 继续:
  5. <think>需要确认淘宝是否已打开</think>
  6. → 调用工具 ui.understand(mode="dump")

uiautomator2 工具:
  dump → "当前App: 淘宝(com.taobao.taobao), 搜索框: text='搜索', clickable"

LLM 继续:
  7. <think>搜索框可见，用文本定位点击它</think>
  8. → 调用工具 device.tap_element(method="text", target="搜索框")

...循环直到 finish ...
```

### 10.3 模式切换逻辑

```python
class ModeSelector:
    """自动选择运行模式"""

    def select_mode(self) -> str:
        """返回 "full" 或 "text_only" """
        # 条件1: 是否有 VLM 模型可用？
        if self._check_vlm_available():
            return "full"

        # 条件2: 是否有 uiautomator2 可用？
        if self._check_uiautomator_available():
            return "text_only"

        # 条件3: 是否有 OCR 引擎可用？
        if self._check_ocr_available():
            return "text_only"

        # 全部不可用 → 报错
        raise RuntimeError("No perception backend available")

    def _check_vlm_available(self) -> bool:
        """检查 VLM API 是否可连接"""
        try:
            response = requests.get(f"{base_url}/models", timeout=3)
            return response.status_code == 200
        except Exception:
            return False
```

---

## 11. 目录结构

```
phone_agent/
├── __init__.py
│
├── core/                          # 核心循环
│   ├── planner.py                 # LLM 规划器
│   ├── agent.py                   # Agent 主类（重构）
│   └── config.py                  # AgentConfig
│
├── tools/                         # 工具注册表 + 所有工具
│   ├── __init__.py
│   ├── registry.py                # ToolRegistry + Tool 基类
│   ├── loader.py                  # ToolLoader（动态加载）
│   │
│   ├── perception/                # 感知工具
│   │   ├── understand.py          # ui.understand
│   │   ├── find.py                # ui.find
│   │   └── get_app_info.py        # ui.get_app_info
│   │
│   ├── locator/                   # 定位工具
│   │   ├── find.py                # locator.find（多策略）
│   │   └── strategies/            # 定位策略
│   │       ├── text.py            # 文本匹配
│   │       ├── id_match.py        # resource-id 匹配
│   │       ├── desc_match.py      # content-desc 匹配
│   │       └── semantic.py        # LLM 语义定位
│   │
│   ├── device/                    # 执行工具
│   │   ├── tap.py                 # device.tap
│   │   ├── tap_element.py         # device.tap_element
│   │   ├── type.py                # device.type
│   │   ├── swipe.py               # device.swipe
│   │   ├── launch.py              # device.launch
│   │   ├── back.py                # device.back
│   │   ├── home.py                # device.home
│   │   └── wait.py                # device.wait
│   │
│   ├── verify/                    # 验证工具
│   │   ├── screen.py              # verify.screen
│   │   └── compare.py             # verify.compare_image
│   │
│   └── auxiliary/                 # 辅助工具
│       ├── take_over.py           # device.take_over
│       └── finish.py              # finish
│
├── perception/                    # 感知引擎（多模式）
│   ├── __init__.py
│   ├── engine.py                  # PerceptionEngine（自动模式选择）
│   ├── vlm.py                     # VLM 看图理解
│   ├── dump.py                    # uiautomator2 dump
│   ├── ocr.py                     # OCR 文字提取
│   └── fusion.py                  # 多模式融合
│
├── device/                        # 设备驱动层（v0.1.0 的 adb/ / hdc/ / xctest/）
│   ├── __init__.py
│   ├── factory.py                 # DeviceFactory（复用）
│   ├── executor.py                # DeviceExecutor（工具粒度的执行器）
│   ├── adb/                       # Android
│   ├── hdc/                       # HarmonyOS
│   └── xctest/                    # iOS
│
├── verify/                        # 验证层
│   ├── __init__.py
│   ├── verifier.py                # Verifier（步骤验证）
│   ├── screenshot_compare.py      # 截图比对
│   └── self_heal.py               # 自愈策略
│
├── script/                        # 脚本系统
│   ├── __init__.py
│   ├── recorder.py                # ScriptRecorder：录制中间格式
│   ├── compiler.py                # ScriptCompiler：中间格式 → Python
│   ├── models.py                  # 中间格式数据模型
│   ├── replayer.py                # ScriptReplayer：回放 Python 脚本
│
├── report/                        # 报告输出
│   ├── __init__.py
│   ├── models.py                  # TestReport / DeviceRunInfo / ReportStep
│   ├── html_generator.py          # 自包含 HTML 报告（base64 内嵌）
│   ├── pdf_generator.py           # PDF 报告（weasyprint/playwright）
│   ├── screenshot_manager.py      # 截图 base64 管理
│   └── aggregator.py              # 多设备报告聚合
│
├── orchestrator/                  # 多设备调度
│   ├── __init__.py
│   ├── orchestrator.py            # Orchestrator
│   ├── device_pool.py             # 设备池
│   └── task_queue.py              # 任务队列
│   └── report_aggregator.py       # 报告聚合（调用 report/）
│
├── model/                         # 模型客户端（复用）
│   ├── __init__.py
│   └── client.py                  # ModelClient
│
└── config/                        # 配置层（扩展）
    ├── __init__.py
    ├── prompts_zh.py              # 新版 system prompt
    ├── prompts_en.py
    ├── tools_description.py       # 工具描述（注入到 prompt）
    ├── apps.py                    # App 映射
    ├── i18n.py
    └── timing.py
```

---

## 12. 数据流详解

### 12.1 单任务完整数据流

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. 用户输入                                                       │
│    "打开淘宝搜索无线耳机，筛选价格低于200元"                         │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. LLM 规划器（第1轮）                                             │
│                                                                   │
│    <think>用户要搜索无线耳机并筛选价格，先用感知工具了解当前状态     │
│    </think>                                                        │
│    → 调用: ui.understand(mode="auto")                              │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. 感知引擎                                                        │
│                                                                   │
│    模式选择: VLM可用 → 走VLM模式                                   │
│    截图 → VLM 图理解 → "当前在桌面，图标有: 微信、淘宝、..."       │
│    返回 LLM: {"current_app": "System Home", "elements": [...],    │
│               "description": "当前在系统桌面..."}                   │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. LLM 规划器（第2轮）                                             │
│                                                                   │
│    <think>当前在桌面，需要启动淘宝。启动后需要确认是否进入淘宝      │
│    </think>                                                        │
│    → 调用: device.launch(app="淘宝")                               │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. 执行层                                                         │
│                                                                   │
│    DeviceExecutor.launch("淘宝")                                   │
│    → adb shell monkey -p com.taobao.taobao ...                    │
│    → 返回: {"success": true, "action": "launch", "app": "淘宝"}   │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 6. 验证层                                                         │
│                                                                   │
│    截图 → "当前是否在淘宝首页？" → VLM: "是，已进入淘宝"            │
│    → 验证通过                                                     │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 7. 录制层                                                         │
│                                                                   │
│    ScriptRecorder.record_action({action:"launch", ...},           │
│                                 {success:true, ...})              │
│    ScriptRecorder.record_snapshot("step_2_after", screenshot)     │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 8. LLM 规划器（第3轮）... 继续循环直到 finish                      │
│                                                                   │
│    最终: finish(message="已筛选200元以下的无线耳机",               │
│                 script=recorder.export_python())                   │
└────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│ 9. 输出                                                           │
│                                                                   │
│    ① 执行结果: "任务完成，已找到符合条件的结果"                     │
│    ② Python脚本: test_taobao_search.py (执行用)                   │
│    ③ YAML 备案: test_taobao_search.yaml (归档用)                  │
│    ④ 步骤截图: {step_1_before.png, ...} (base64嵌入报告)          │
│    ⑤ 执行日志: execution.log                                      │
│    ⑥ 成功报告: {total_steps: 8, success_rate: 1.0,               │
│                 failures: []}                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 13. 报告输出体系

报告是自动化测试的最终交付物。支持 **HTML** 和 **PDF** 两种格式，**所有图片以 base64 嵌入**，删除本地文件不影响报告查看。

### 13.1 报告数据模型

```python
@dataclass
class TestReport:
    """完整测试报告"""
    # 元信息
    title: str
    task_description: str
    created_at: str
    duration_seconds: float

    # 设备信息
    device_info: list[DeviceRunInfo]  # 每台设备一个

    # 全局统计
    total_devices: int
    total_steps: int
    total_exact: int
    total_pseudocode: int
    global_success_rate: float
    passed: bool  # success_rate >= threshold

    # 原始数据
    scripts: dict[str, str]  # device_id → YAML script
    logs: dict[str, list[str]]  # device_id → log lines


@dataclass
class DeviceRunInfo:
    """单台设备的执行信息"""
    device_id: str
    device_model: str
    os_version: str
    resolution: str

    steps: list[ReportStep]
    success_rate: float
    duration: float
    status: str  # "passed" | "failed" | "partial"

    # 截图（全部以 base64 嵌入）
    screenshots: dict[str, str]  # key → base64


@dataclass
class ReportStep:
    id: int
    action: str
    status: str  # "exact" | "pseudocode" | "skipped"
    intent: str
    error: str | None
    screenshot_before: str | None  # base64
    screenshot_after: str | None   # base64
    pseudocode: str | None
    suggested_fix: str | None
    duration: float
```

### 13.2 HTML 报告

自包含单文件 HTML，所有资源内嵌：

```python
class HtmlReportGenerator:
    """生成自包含 HTML 报告（所有资源 base64 内嵌）"""

    def generate(self, report: TestReport) -> str:
        """
        返回完整的 HTML 字符串。
        可直接保存为 .html 文件，不依赖任何外部资源。
        """
        # 1. 构建报告头部（样式 + 脚本内联）
        css = self._build_inline_css()
        js = self._build_inline_js()

        # 2. 构建概览区域
        overview = self._build_overview(report)

        # 3. 构建设备 Tab 导航
        device_tabs = self._build_device_tabs(report)

        # 4. 构建每个设备的详细步骤
        device_details = ""
        for device_run in report.device_info:
            device_details += self._build_device_section(device_run)

        # 5. 构建报告底部
        footer = self._build_footer(report)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{escape(report.title)} - 测试报告</title>
    <style>{css}</style>
    <script>{js}</script>
</head>
<body>
    {overview}
    {device_tabs}
    {device_details}
    {footer}
</body>
</html>"""
        return html

    def _build_overview(self, report: TestReport) -> str:
        """构建概览区域：任务信息 + 全局统计 + 通过率仪表盘"""
        color = "#22c55e" if report.passed else "#ef4444"
        return f"""
<div class="overview">
    <h1>{escape(report.title)}</h1>
    <div class="meta">
        <span>任务: {escape(report.task_description)}</span>
        <span>时间: {report.created_at}</span>
        <span>耗时: {report.duration_seconds:.1f}s</span>
        <span>设备数: {report.total_devices}</span>
    </div>
    <div class="stats">
        <div class="stat-card" style="border-left: 4px solid {color};">
            <div class="stat-value">{report.global_success_rate:.1%}</div>
            <div class="stat-label">全局通过率</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{report.total_exact}</div>
            <div class="stat-label">精确步骤</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{report.total_pseudocode}</div>
            <div class="stat-label">需人工确认</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{report.total_steps}</div>
            <div class="stat-label">总步骤数</div>
        </div>
    </div>
</div>"""

    def _build_device_section(self, device_run: DeviceRunInfo) -> str:
        """构建设备详细执行步骤"""
        status_icon = "✅" if device_run.status == "passed" else (
            "⚠️" if device_run.status == "partial" else "❌"
        )
        sections = f"""
<div class="device-section" id="device-{device_run.device_id}">
    <h2>{status_icon} 设备: {device_run.device_model}
        <small>({device_run.device_id})</small>
    </h2>
    <div class="device-info">
        <span>系统: {device_run.os_version}</span>
        <span>分辨率: {device_run.resolution}</span>
        <span>通过率: {device_run.success_rate:.1%}</span>
        <span>耗时: {device_run.duration:.1f}s</span>
    </div>
    <table class="steps-table">
        <thead>
            <tr>
                <th>#</th>
                <th>状态</th>
                <th>操作</th>
                <th>意图</th>
                <th>截图</th>
                <th>耗时</th>
            </tr>
        </thead>
        <tbody>
"""
        for step in device_run.steps:
            sections += self._build_step_row(step)
        sections += """
        </tbody>
    </table>
</div>"""
        return sections

    def _build_step_row(self, step: ReportStep) -> str:
        """构建单行步骤（含内嵌截图）"""
        status_badge = {
            "exact": "<span class='badge exact'>✅ 精确</span>",
            "pseudocode": "<span class='badge pseudo'>⚠️ 伪代码</span>",
            "skipped": "<span class='badge skip'>⏭ 跳过</span>",
        }.get(step.status, "<span class='badge'>未知</span>")

        # 截图：base64 内嵌
        screenshots_html = ""
        if step.screenshot_before:
            screenshots_html += (
                f"<img src='data:image/png;base64,{step.screenshot_before}' "
                f"class='step-screenshot' title='执行前' />"
            )
        if step.screenshot_after:
            screenshots_html += (
                f"<img src='data:image/png;base64,{step.screenshot_after}' "
                f"class='step-screenshot' title='执行后' />"
            )

        # 伪代码行可展开
        extra = ""
        if step.pseudocode:
            extra = f"""
<div class='pseudocode-block'>
    <pre>{escape(step.pseudocode)}</pre>
</div>"""
        if step.suggested_fix:
            extra += f"""
<div class='suggested-fix'>
    <strong>修复建议:</strong>
    <pre>{escape(step.suggested_fix)}</pre>
</div>"""

        return f"""
<tr class="step-row step-{step.status}">
    <td>{step.id}</td>
    <td>{status_badge}</td>
    <td><code>{escape(step.action)}</code></td>
    <td>{escape(step.intent or '')}</td>
    <td class="screenshots-cell">{screenshots_html}</td>
    <td>{step.duration:.1f}s</td>
</tr>
<tr class="step-extra step-{step.status}">
    <td colspan="6">{extra}</td>
</tr>"""
```

HTML 报告预览示意：

```
┌──────────────────────────────────────────────────────┐
│  📊 自动化测试报告                                    │
│  任务: 打开淘宝搜索无线耳机，筛选价格低于200元          │
│  时间: 2026-05-16 14:30 | 耗时: 42.3s | 设备数: 3    │
├──────────────────────────────────────────────────────┤
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │  92.3% │ │  12 个  │ │  1 个   │ │  13 个  │       │
│  │通过率  │ │精确步骤 │ │需人工  │ │总步骤  │       │
│  └────────┘ └────────┘ └────────┘ └────────┘       │
├──────────────────────────────────────────────────────┤
│  📱 [设备1: Xiaomi 14]  [设备2: Pixel 8] [设备3: ...] │
├──────────────────────────────────────────────────────┤
│  ✅ Xiaomi 14 (Android 14) · 通过率: 100% · 42.3s   │
│  ┌─────┬──────┬────────┬──────────┬────────┬────┐  │
│  │  #  │ 状态 │ 操作   │ 意图     │ 截图   │耗时│  │
│  ├─────┼──────┼────────┼──────────┼────────┼────┤  │
│  │  1  │ ✅   │launch  │打开淘宝  │ [img]  │2.1s│  │
│  │  2  │ ✅   │tap     │点击搜索框│ [img]  │1.5s│  │
│  │  3  │ ✅   │type    │输入关键词│ [img]  │3.2s│  │
│  │  4  │ ⚠️   │tap     │点击筛选  │ [img]  │0.0s│  │
│  │     │伪代码│        │          │        │    │  │
│  │     │ ▼ 点击展开修复建议       │        │    │  │
│  │     │  # 场景：点击价格筛选    │        │    │  │
│  │     │  # 可能原因：不同版本    │        │    │  │
│  │     │  # 入口位置不同...       │        │    │  │
│  ├─────┼──────┼────────┼──────────┼────────┼────┤  │
│  │  5  │ ✅   │verify  │断言结果  │ [img]  │1.0s│  │
│  └─────┴──────┴────────┴──────────┴────────┴────┘  │
├──────────────────────────────────────────────────────┤
│  📎 脚本: test_taobao_search.py (执行)             │
│  📦 备案: test_taobao_search.yaml (归档)           │
│  📋 日志: execution.log                            │
│  📄 导出: PDF / HTML                               │
└──────────────────────────────────────────────────────┘
```

### 13.3 PDF 报告

PDF 通过 HTML → PDF 转换生成，保持与 HTML 报告一致的内容和样式：

```python
class PdfReportGenerator:
    """PDF 报告生成器"""

    def __init__(self, html_generator: HtmlReportGenerator):
        self.html_generator = html_generator

    def generate(self, report: TestReport, output_path: str):
        """
        先生成 HTML，再转换为 PDF。

        转换方案（按推荐度）:
        方案 A: weasyprint (pip install weasyprint)
          最佳 HTML→PDF 渲染，支持 CSS 完整特性

        方案 B: playwright (pip install playwright)
          浏览器渲染 → PDF，最精准
          await page.pdf(path=output_path, format='A4')

        方案 C: pdfkit (wkhtmltopdf 封装)
          轻量，但 CSS3 支持有限
        """
        html = self.html_generator.generate(report)

        # 方案 A: weasyprint
        from weasyprint import HTML
        HTML(string=html).write_pdf(output_path)

        # 或方案 B: playwright
        # from playwright.async_api import async_playwright
        # async with async_playwright() as p:
        #     browser = await p.chromium.launch()
        #     page = await browser.new_page()
        #     await page.set_content(html)
        #     await page.pdf(path=output_path, format='A4')
```

### 13.4 图片处理策略

本地部署环境的特殊要求：**引用图片不可依赖本地文件**。

```python
class ScreenshotManager:
    """截图管理器：所有截图 base64 管理，不依赖本地文件"""

    def __init__(self):
        self._store: dict[str, str] = {}  # key → base64

    def capture_and_store(self, key: str) -> str:
        """截图 → base64 → 存入内存"""
        screenshot = get_screenshot()  # 原始截图对象
        self._store[key] = screenshot.base64_data
        return screenshot.base64_data

    def get_inline_html(self, key: str, alt: str = "") -> str:
        """生成内嵌 HTML img 标签（不依赖文件路径）"""
        b64 = self._store.get(key)
        if not b64:
            return ""
        return f'<img src="data:image/png;base64,{b64}" alt="{escape(alt)}" />'

    def embed_all_into_report(self, report_html: str) -> str:
        """
        将所有截图引用替换为 base64 内嵌。
        这样即使删除 temp/ 目录下的临时截图，报告也不受影响。
        """
        for key, b64 in self._store.items():
            placeholder = f"__SCREENSHOT_{key}__"
            report_html = report_html.replace(
                placeholder,
                f"data:image/png;base64,{b64}"
            )
        return report_html

    def cleanup_temp_files(self):
        """只清理临时文件，不清理内存中的 base64"""
        import tempfile, os, glob
        pattern = os.path.join(tempfile.gettempdir(), "screenshot_*.png")
        for f in glob.glob(pattern):
            os.remove(f)
```

---

## 14. 与 v0.1.0 的映射关系

| v0.1.0 模块 | V2 中的角色 | 改动说明 |
|------------|------------|---------|
| `PhoneAgent` | `core/planner.py` + `core/agent.py` | 拆分为 LLM 规划器 + 精简 Agent；保留 `_execute_step` 骨架 |
| `ModelClient` | `model/client.py` | 基本复用，增加 Function Calling 支持 |
| `MessageBuilder` | 内联到 `core/agent.py` | 不再需要图片消息组装（V2 纯文本为主） |
| `ActionHandler` 10+ handler | `tools/device/*.py` | 拆分为独立 Tool 类，每个 tool 单一职责 |
| `parse_action()` | `tools/registry.py` + LLM Function Calling | 不再需要 ast 解析，LLM 直接输出结构化 JSON |
| `DeviceFactory` | `device/factory.py` | 复用，作为 DeviceExecutor 的后端 |
| `adb/ /hdc/ /xctest/` | `device/adb/ /hdc/ /xctest/` | 复用，增加 uiautomator2 集成 |
| `prompts_zh.py` 18条规则 | `config/prompts_zh.py` + `config/tools_description.py` | 规则保留，工具描述分离 |
| `config/apps.py` | `config/apps.py` | 复用 |
| `config/timing.py` | `config/timing.py` | 复用 |
| — | `perception/` | **新增**：多模式感知层 |
| — | `verify/` | **新增**：验证与自愈 |
| — | `script/` | **新增**：录制与回放 |
| — | `tools/locator/` | **新增**：多策略定位器 |
| — | `orchestrator/` | **新增**：多设备调度 |

---

## 15. 关键设计决策

### 15.1 为什么 LLM 和 VLM 要分离？

| 维度 | 耦合（v0.1.0） | 分离（V2） |
|------|--------------|-----------|
| 模型选择 | 必须用同型号 | LLM 可选 GPT-4o / Qwen / DeepSeek；VLM 可选 AutoGLM / Qwen-VL |
| 成本 | 每步都走多模态，token 巨大 | 感知才走 VLM，规划走便宜的纯文本 LLM |
| 降级 | 模型不可用就废 | VLM 不可用时自动降级到 dump/OCR |
| 扩展 | 加能力要改模型 | 加能力就是加 Tool |
| 调试 | 黑盒 | 每一步工具调用 + 返回都可见 |

### 15.2 为什么用 Tool Registry 而不是硬编码 ActionHandler？

- **可扩展**：新工具只需注册，不修改核心循环
- **可发现**：LLM 通过工具描述知道有什么工具可用
- **可插拔**：工具可从 MCP 服务器、配置文件动态加载
- **可测试**：每个工具独立测试

### 15.3 定位策略优先级设计

```
默认优先级链:
  text 精确匹配  →  最准确，App 内唯一标识
  resource-id    →  开发规范时的最佳选择
  content-desc   →  Accessibility 标准
  LLM 语义       →  兜底，万能但昂贵
  坐标回退       →  最终 fallback（记录但标记为低可靠）

原因:
  · text 和 id 是确定性匹配，不会因为机型不同而失效
  · 坐标是纯物理位置，跨机型必定失效，只做最后回退
```

### 15.4 脚本可靠性的三层保证

```
第一层: 感知→规划→执行→验证 闭环（运行时）
  每步验证 → 失败自愈 → 保证单次执行质量

第二层: 多模式定位链（脚本录制时）
  录制时保存所有可用的定位信息（text/id/坐标）
  回放时按优先级链重试

第三层: 跨设备兼容性（脚本回放时）
  脚本标记了录制时的机型信息
  回放不同机型时根据屏幕参数适配
```

---

*本文档基于 Open-AutoGLM v0.1.0 源码分析与架构演进讨论生成*
*V2 方案核心：LLM+VLM 职责分离 · Tool Registry 工具化 · 多模式感知 · 失败自愈 + Prompt 增强 · 完全/部分脚本双产出 · base64 内嵌报告 · 多设备并发调度*
