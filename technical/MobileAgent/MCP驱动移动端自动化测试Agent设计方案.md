# MCP 驱动的移动端自动化测试 Agent 设计方案

> 核心理念：LLM + MCP → 真机执行并验证 → 录制成功轨迹 → 解析生成框架脚本（uiautomator2 / XCUITest / 鸿蒙 UI Test）

---

## 目录

1. [设想起源与可行性结论](#1-设想起源与可行性结论)
2. [当前方案的缺陷](#2-当前方案的缺陷)
3. [MCP 是什么以及为什么用它](#3-mcp-是什么以及为什么用它)
4. [整体架构](#4-整体架构)
5. [MCP Server 详细设计](#5-mcp-server-详细设计)
6. [执行录制与轨迹解析](#6-执行录制与轨迹解析)
7. [脚本生成](#7-脚本生成)
8. [与传统方案的对比](#8-与传统方案的对比)
9. [潜在风险](#9-潜在风险)
10. [与 Mobile-Agent 现有代码的集成关系](#10-与-mobile-agent-现有代码的集成关系)
11. [附录](#11-附录)

---

## 1. 设想起源与可行性结论

### 1.1 核心设想

```
用户输入自然语言需求
        │
        ▼
LLM + System Prompt
        │
        ▼
MCP Client ──调用──▶ MCP Servers (device / locator / assertion / screenshot)
        │                         │
        │                   ┌─────┴─────┐
        │             真机执行成功    执行失败 → LLM 换策略重试
        │                   │
        ▼                   ▼
步骤录制器 ──记录每一步的──▶ Tool Name + Arguments + Screenshot + Result
        │
        ▼
脚本生成器 ──解析轨迹──▶ uiautomator2.py / XCUITest.swift / HarmonyOS.java
```

### 1.2 可行性结论

| 维度 | 结论 |
|------|------|
| 技术可行性 | **成立**。MCP 标准化工具调用描述和执行，替换当前 Mobile-Agent 的 `<tool_call>` XML 格式，无技术障碍 |
| 兼容性 | **正向兼容**。现有平台适配层（AndroidAdapter / iOSAdapter / HarmonyOSAdapter）可直接作为 MCP Tool 的底层执行器 |
| 开发成本 | **约 2-3 人周**。核心是将现有 `<tool_call>` 解析替换为 MCP 协议，新增轨迹录制和脚本生成模块 |
| 工程收益 | **高**。MCP 标准化后，外部 Agent 生态（Claude Desktop、LangChain、AutoGPT）可直接调用，可组合性大幅提升 |

### 1.3 核心优势

| 优势 | 说明 |
|------|------|
| **标准化** | MCP 协议统一工具描述、调用、响应格式，无需自定义 `<tool_call>` XML 解析 |
| **可发现** | LLM 可通过 MCP Server 的 `list_tools` 接口动态发现可用工具，无需硬编码 System Prompt |
| **可组合** | 多个 MCP Server 可组合使用（设备控制 + 定位 + 断言 + 截图），各 Server 独立部署 |
| **生态兼容** | 与 Claude Desktop、Cursor、VS Code 等 MCP 客户端即插即用 |
| **易扩展** | 新增平台只需实现对应 MCP Server，无需修改 Agent 核心逻辑 |

---

## 2. 当前方案的缺陷

### 2.1 Mobile-Agent v3.5 现有问题

1. **`<tool_call>` XML 格式非标准**：VLM 需要按特定 XML 格式输出，解析器仅支持该格式，无法与其他 Agent 生态互通
2. **动作定义与 VLM Prompt 紧耦合**：`SYSTEM_PROMPT` 中硬编码工具 Schema，修改工具需同步修改 Prompt
3. **无标准化错误处理**：工具调用失败后的错误格式不统一，LLM 难以自主恢复
4. **无轨迹录制**：当前 ReAct 循环只传截图+历史，没有结构化记录成功路径
5. **无脚本生成**：测试通过后无法产出可复用的自动化脚本，只能通过 VLM 重复执行

### 2.2 竞争对手方案对比

| 方案 | MCP 程度 | 可组合性 | 脚本产出 | 生态兼容 |
|------|---------|---------|---------|---------|
| Mobile-Agent v3.5 | ❌ 自定义 XML | ❌ 单体 | ❌ 无 | ❌ 封闭 |
| Midscene | ✅ 完整 MCP | ✅ 多 Server | ⚠️ YAML 缓存 | ✅ 与 Claude 互操作 |
| autoGLM V2 | ⚠️ 函数调用风格 | ⚠️ Registry | ✅ Python/YAML | ⚠️ OpenAI 格式 |
| 本方案 | ✅ 完整 MCP | ✅ 多 Server | ✅ Python/多框架 | ✅ Claude + 任意 MCP Client |

---

## 3. MCP 是什么以及为什么用它

### 3.1 MCP 协议概述

MCP（Model Context Protocol）是 Anthropic 推出的开放标准协议，定义了大语言模型与外部工具/数据源之间的通信方式：

```
LLM Application
    │
    ├── MCP Client (Host)
    │       │
    │       ├── STDIO / HTTP / SSE
    │       │
    ▼       ▼
MCP Server A    MCP Server B    MCP Server C
(device)        (locator)       (assertion)
```

### 3.2 核心接口

```typescript
// 工具列表（LLM 可发现）
tools/list → ToolDescription[]

// 工具调用
tools/call {
  name: string,
  arguments: Record<string, unknown>
} → ToolResult {
  content: Array<{ type: 'text'|'image'|'resource', text/data/mimeType }>,
  isError?: boolean
}
```

### 3.3 为什么 MCP 比自定义 XML 更好

| 维度 | `<tool_call>` XML | MCP 协议 |
|------|-------------------|---------|
| 工具发现 | VLM 靠 Prompt 知道工具 | 运行时 `list_tools` 接口动态发现 |
| Schema 格式 | 在 Prompt 中用 JSON 描述 | 标准化的 Tool Schema（Zod 验证） |
| 结果格式 | 自定义 | `{content, isError}` 标准格式 |
| 多工具组合 | 需在 Prompt 中合并 | 多 Server 可独立部署、自由组合 |
| 错误处理 | 无标准格式 | `isError=True` + 结构化错误信息 |
| 生态兼容 | 仅 Mobile-Agent | Claude Desktop / VS Code / Cursor 等均兼容 |

---

## 4. 整体架构

### 4.1 分层架构

```
┌──────────────────────────────────────────────────┐
│                  应用层                           │
│    Web UI / CLI / Claude Desktop / 外部 Agent    │
├──────────────────────────────────────────────────┤
│                  MCP 协议层                      │
│    MCP Client (Agent Host) ── STDIO/HTTP/SSE     │
├──────────────────────────────────────────────────┤
│                  MCP Server 层                   │
│  ┌─────────┐┌─────────┐┌─────────┐┌──────────┐  │
│  │ Device  ││ Locator ││Assertion││Screenshot│  │
│  │ Server  ││ Server  ││ Server  ││  Server  │  │
│  └────┬────┘└────┬────┘└────┬────┘└────┬─────┘  │
│       │          │          │           │         │
├───────┴──────────┴──────────┴───────────┴────────┤
│                  抽象设备层                      │
│    BaseDeviceAdapter (unified interface)         │
├──────────┬──────────┬──────────┬─────────────────┤
│  Android │   iOS    │ HarmonyOS│  Web (扩展)     │
│  ADB+u2  │  WDA     │   HDC    │  Playwright     │
└──────────┴──────────┴──────────┴─────────────────┘
```

### 4.2 MCP Server 拆分策略

采用**多 Server 拆分**，每个 Server 独立进程部署，通过 STDIO 或 HTTP 与 MCP Client 通信：

| Server 名称 | 职责 | 工具数量 | 状态 |
|------------|------|---------|------|
| `mobile-device` | 设备操作（点击、输入、滑动手势） | 10 | 必需 |
| `mobile-locator` | 元素定位（多种策略） | 2 | 必需 |
| `mobile-assert` | 屏幕断言 | 2 | 可选 |
| `mobile-screenshot` | 截图 | 1 | 必需 |
| `mobile-app` | 应用管理（安装、卸载、启动） | 4 | 可选 |

### 4.3 数据流

```
Step 1 (失败重试)
  ┌─────┐    screenshot    ┌──────────┐  tool_call  ┌─────────┐
  │ LLM │◄────────────────│ MCP Client│◄──────────│ MCP     │
  │     │                  │           │──────────►│ Servers │
  │     │  tool_result     │           │  execute   │         │
  └─────┘                  └───────────┘           └─────────┘
                               │
                               │ 记录成功轨迹
                               ▼
                          ┌──────────┐
                          │ 轨迹录制器 │
                          └─────┬────┘
                                │
                          ┌─────▼────┐
                          │ 脚本生成器 │
                          └──────────┘
```

---

## 5. MCP Server 详细设计

### 5.1 基础类设计

```python
from dataclasses import dataclass, field
from typing import Any, Optional
import json


@dataclass
class MCPTool:
    """单个 MCP 工具封装"""
    name: str
    description: str
    input_schema: dict  # JSON Schema
    handler: Any        # Callable 或 ActionHandler 实例
    enabled: bool = True

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }

    def to_mcp_tool_definition(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class MCPServer:
    """MCP Server —— 管理一组 MCPTool 实例"""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tools: dict[str, MCPTool] = {}

    def register_tool(self, tool: MCPTool):
        self.tools[tool.name] = tool

    def list_tools(self) -> list[dict]:
        return [
            t.to_mcp_tool_definition()
            for t in self.tools.values()
            if t.enabled
        ]

    def call_tool(self, name: str, arguments: dict) -> dict:
        if name not in self.tools:
            return {"content": [{"type": "text", "text": f"Tool '{name}' not found"}],
                    "isError": True}
        tool = self.tools[name]
        try:
            result = tool.handler(**arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": str(e)}],
                    "isError": True}

    def get_system_prompt_block(self) -> str:
        return json.dumps([t.to_openai_tool() for t in self.tools.values() if t.enabled],
                          indent=2, ensure_ascii=False)
```

### 5.2 设备控制 MCP Server

```python
def create_device_server(device: BaseDeviceAdapter) -> MCPServer:
    """创建设备控制 MCP Server"""
    server = MCPServer("mobile_device", "移动设备基础操作")

    server.register_tool(MCPTool(
        name="click",
        description="点击屏幕指定坐标位置",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X 坐标（0-1000 归一化坐标）"},
                "y": {"type": "integer", "description": "Y 坐标（0-1000 归一化坐标）"},
            },
            "required": ["x", "y"],
        },
        handler=lambda x, y: device.click(x, y),
    ))

    server.register_tool(MCPTool(
        name="type",
        description="输入指定文本",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要输入的文本内容"},
                "mode": {"type": "string", "enum": ["normal", "clear_first", "search"],
                         "description": "输入模式", "default": "normal"},
            },
            "required": ["text"],
        },
        handler=lambda text, mode="normal": device.type(text, mode),
    ))

    server.register_tool(MCPTool(
        name="swipe",
        description="在屏幕上滑动",
        input_schema={
            "type": "object",
            "properties": {
                "x1": {"type": "integer"},
                "y1": {"type": "integer"},
                "x2": {"type": "integer"},
                "y2": {"type": "integer"},
                "duration_ms": {"type": "integer", "description": "滑动持续时间(毫秒)", "default": 500},
            },
            "required": ["x1", "y1", "x2", "y2"],
        },
        handler=lambda x1, y1, x2, y2, duration_ms=500: device.swipe(x1, y1, x2, y2, duration_ms),
    ))

    server.register_tool(MCPTool(
        name="open_app",
        description="打开指定应用",
        input_schema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "应用包名或 Bundle ID"},
            },
            "required": ["app_id"],
        },
        handler=lambda app_id: device.open_app(app_id),
    ))

    server.register_tool(MCPTool(
        name="press_back",
        description="按下返回键",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: device.press_back(),
    ))

    server.register_tool(MCPTool(
        name="press_home",
        description="按下 Home 键",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: device.press_home(),
    ))

    server.register_tool(MCPTool(
        name="wait",
        description="等待指定时间（秒）",
        input_schema={
            "type": "object",
            "properties": {
                "seconds": {"type": "number", "description": "等待秒数", "default": 2},
            },
            "required": [],
        },
        handler=lambda seconds=2: __import__("time").sleep(seconds),
    ))

    server.register_tool(MCPTool(
        name="screenshot",
        description="截取当前屏幕并返回 Base64 编码的图片",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: device.screenshot_base64(),
    ))

    server.register_tool(MCPTool(
        name="terminate_app",
        description="关闭指定应用",
        input_schema={
            "type": "object",
            "properties": {
                "app_id": {"type": "string"},
            },
            "required": ["app_id"],
        },
        handler=lambda app_id: device.terminate_app(app_id),
    ))

    return server
```

### 5.3 元素定位 MCP Server

```python
def create_locator_server(locator: ElementLocatorEngine) -> MCPServer:
    server = MCPServer("mobile_locator", "跨设备元素定位")

    server.register_tool(MCPTool(
        name="find_element",
        description="查找屏幕上匹配的元素，返回坐标和属性",
        input_schema={
            "type": "object",
            "properties": {
                "by": {"type": "string", "enum": ["text", "id", "content_desc", "xpath", "semantic"],
                       "description": "定位策略"},
                "value": {"type": "string", "description": "定位值"},
                "timeout": {"type": "number", "description": "超时秒数", "default": 10},
            },
            "required": ["by", "value"],
        },
        handler=lambda by, value, timeout=10: locator.find(by, value, timeout),
    ))

    server.register_tool(MCPTool(
        name="tap_element",
        description="点击指定元素（先定位再点击）",
        input_schema={
            "type": "object",
            "properties": {
                "by": {"type": "string", "enum": ["text", "id", "content_desc", "xpath", "semantic"]},
                "value": {"type": "string"},
                "timeout": {"type": "number", "default": 10},
            },
            "required": ["by", "value"],
        },
        handler=lambda by, value, timeout=10: locator.find_and_tap(by, value, timeout),
    ))

    return server
```

### 5.4 截图 MCP Server

```python
def create_screenshot_server(device: BaseDeviceAdapter) -> MCPServer:
    server = MCPServer("mobile_screenshot", "屏幕截图服务")

    server.register_tool(MCPTool(
        name="take_screenshot",
        description="截取当前设备屏幕，返回 Base64 PNG",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: device.screenshot_base64(),
    ))

    return server
```

### 5.5 MCP Server 启动方式

支持 STDIO 和 HTTP 两种模式：

```python
import subprocess
import json
import sys


class STDIOTransport:
    """STDIO 模式 MCP Server 传输层"""
    def __init__(self, server: MCPServer):
        self.server = server

    def run(self):
        """从 STDIN 读取 JSON-RPC 请求，处理后写入 STDOUT"""
        for line in sys.stdin:
            request = json.loads(line.strip())
            method = request.get("method")
            params = request.get("params", {})

            if method == "tools/list":
                response = {"id": request["id"], "result": self.server.list_tools()}
            elif method == "tools/call":
                result = self.server.call_tool(params["name"], params.get("arguments", {}))
                response = {"id": request["id"], "result": result}
            else:
                response = {"id": request["id"],
                            "error": {"code": -32601, "message": "Method not found"}}

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
```

### 5.6 MCP Client（Agent 端集成）

```python
import json
import subprocess
import requests
from typing import Optional


class MCPClient:
    """MCP Client —— 连接一个或多个 MCP Server"""

    def __init__(self, server_configs: list[dict]):
        """
        server_configs: [
            {"name": "device", "mode": "stdio", "command": ["python", "device_server.py"]},
            {"name": "locator", "mode": "http", "url": "http://localhost:3001"},
        ]
        """
        self.servers = {}
        self._processes = []
        for config in server_configs:
            self._connect(config)

    def _connect(self, config: dict):
        if config["mode"] == "stdio":
            proc = subprocess.Popen(
                config["command"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._processes.append(proc)
            self.servers[config["name"]] = {
                "mode": "stdio",
                "process": proc,
            }
        elif config["mode"] == "http":
            self.servers[config["name"]] = {
                "mode": "http",
                "url": config["url"],
            }

    def _call_stdio(self, server, method: str, params: dict = None) -> dict:
        request = json.dumps({
            "method": method,
            "params": params or {},
            "id": 1,
        })
        proc = server["process"]
        proc.stdin.write(request + "\n")
        proc.stdin.flush()
        response = json.loads(proc.stdout.readline())
        return response.get("result", response)

    def _call_http(self, server, method: str, params: dict = None) -> dict:
        if method == "tools/list":
            resp = requests.get(f"{server['url']}/tools")
        elif method == "tools/call":
            resp = requests.post(f"{server['url']}/tools/call",
                                 json={"name": params["name"], "arguments": params.get("arguments", {})})
        return resp.json()

    def list_all_tools(self) -> list[dict]:
        all_tools = []
        for name, server in self.servers.items():
            if server["mode"] == "stdio":
                tools = self._call_stdio(server, "tools/list")
            else:
                tools = self._call_http(server, "tools/list")
            for tool in tools:
                tool["server"] = name
            all_tools.extend(tools)
        return all_tools

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        # 查找所属 Server
        for name, server in self.servers.items():
            tools = self.list_all_tools()
            for t in tools:
                if t["name"] == tool_name and t.get("server") == name:
                    if server["mode"] == "stdio":
                        return self._call_stdio(server, "tools/call",
                                                {"name": tool_name, "arguments": arguments})
                    else:
                        return self._call_http(server, "tools/call",
                                               {"name": tool_name, "arguments": arguments})
        return {"content": [{"type": "text", "text": f"Tool '{tool_name}' not found"}],
                "isError": True}

    def close(self):
        for proc in self._processes:
            proc.terminate()
```

### 5.7 基于 MCP 的 ReAct 引擎

```python
class MCPReActEngine:
    """基于 MCP 协议的 ReAct 执行引擎"""

    def __init__(self, client: MCPClient, llm, max_steps: int = 50):
        self.client = client
        self.llm = llm
        self.max_steps = max_steps
        self.trace = TraceStore()

    def build_system_prompt(self) -> str:
        tools = self.client.list_all_tools()
        tool_descs = "\n".join([
            f"- {t['name']}: {t['description']} (参数: {json.dumps(t.get('inputSchema', {}), ensure_ascii=False)})"
            for t in tools
        ])
        return f"""你是一个移动端自动化测试 Agent。你可以使用以下工具与手机交互：

{tool_descs}

每次响应格式：
1. 思考：描述当前观察和计划
2. 工具调用：<tool_call>{{"name": "...", "arguments": {{...}}}}</tool_call>

如果任务完成，返回：<finish message="完成描述"/>"""

    def execute_step(self, step: int, tool_name: str, arguments: dict) -> dict:
        """执行单步工具调用，录制轨迹"""
        result = self.client.call_tool(tool_name, arguments)
        is_error = result.get("isError", False)
        content = result.get("content", [])

        # 录制轨迹
        self.trace.record(
            step_id=step,
            tool_name=tool_name,
            arguments=arguments,
            result="failure" if is_error else "success",
            error=content[0]["text"] if is_error else None,
        )

        return result

    def run(self, task: str) -> bool:
        messages = [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": task},
        ]

        for step in range(1, self.max_steps + 1):
            # 调用 LLM 获取下一步操作
            response = self.llm.chat(messages)

            if "<finish" in response:
                return True

            # 解析 tool_call
            tool_call = self._parse_tool_call(response)
            if not tool_call:
                continue

            # 执行工具
            result = self.execute_step(step, tool_call["name"], tool_call["arguments"])

            # 追加到消息历史
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "tool", "content": str(result),
                             "tool_call_id": tool_call["name"]})

        return False

    def _parse_tool_call(self, text: str) -> Optional[dict]:
        """解析 <tool_call>...</tool_call> 中的 JSON"""
        import re
        match = re.search(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return None
```

---

## 6. 执行录制与轨迹解析

### 6.1 轨迹数据结构

```python
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json


@dataclass
class TraceStep:
    """单步轨迹记录"""
    step_id: int
    tool_name: str                    # click / type / swipe / ...
    arguments: dict                   # {"x": 100, "y": 200}
    result: str                       # "success" | "failure"
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TraceStore:
    """轨迹存储 —— 记录成功执行路径"""

    def __init__(self):
        self.steps: list[TraceStep] = []
        self._context = {}

    def record(self, step_id: int, tool_name: str, arguments: dict,
               result: str, error: str = None, screenshot_path: str = None):
        step = TraceStep(
            step_id=step_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            error=error,
            screenshot_path=screenshot_path,
        )
        self.steps.append(step)
        return step

    def get_successful_steps(self) -> list[TraceStep]:
        """获取所有成功步骤"""
        return [s for s in self.steps if s.result == "success"]

    def save(self, path: str):
        """保存轨迹到 JSON 文件"""
        data = {
            "version": "1.0",
            "total_steps": len(self.steps),
            "success_count": len(self.get_successful_steps()),
            "steps": [
                {"step_id": s.step_id, "tool_name": s.tool_name,
                 "arguments": s.arguments, "result": s.result,
                 "error": s.error}
                for s in self.steps
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: str):
        """从 JSON 文件加载轨迹"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.steps = [TraceStep(**s) for s in data["steps"]]
```

### 6.2 轨迹解析与优化

```python
class TraceOptimizer:
    """轨迹优化：去重、合并、删除冗余步骤"""

    @staticmethod
    def optimize(steps: list[TraceStep]) -> list[TraceStep]:
        result = []
        i = 0
        while i < len(steps):
            # 合并连续等待
            if steps[i].tool_name == "wait":
                total_wait = steps[i].arguments.get("seconds", 0)
                while i + 1 < len(steps) and steps[i + 1].tool_name == "wait":
                    i += 1
                    total_wait += steps[i].arguments.get("seconds", 0)
                steps[i].arguments["seconds"] = total_wait
                result.append(steps[i])
            else:
                result.append(steps[i])
            i += 1
        return result

    @staticmethod
    def remove_redundant_screenshots(steps: list[TraceStep]) -> list[TraceStep]:
        """保留最后一条截图，删除中间冗余截图"""
        return [
            s for i, s in enumerate(steps)
            if not (s.tool_name == "screenshot"
                    and i < len(steps) - 1
                    and steps[i + 1].result == "success")
        ]
```

---

## 7. 脚本生成

### 7.1 框架发射器设计

```python
from abc import ABC, abstractmethod


class FrameworkEmitter(ABC):
    """框架脚本生成器基类"""

    @abstractmethod
    def step_to_code(self, step: TraceStep) -> str:
        """将单步轨迹转换为框架代码"""
        pass

    def emit_header(self) -> str:
        """生成文件头"""
        return ""

    def emit_footer(self) -> str:
        """生成文件尾"""
        return ""

    def emit(self, trace: TraceStore) -> str:
        """生成完整脚本"""
        lines = [self.emit_header()]
        for step in trace.get_successful_steps():
            code = self.step_to_code(step)
            if code:
                lines.append(code)
        lines.append(self.emit_footer())
        return "\n".join(lines)
```

### 7.2 uiautomator2 脚本生成

```python
class UIAutomator2Emitter(FrameworkEmitter):
    """Android uiautomator2 脚本生成器"""

    def emit_header(self) -> str:
        return """import uiautomator2 as us
import pytest


class TestMobile:
    def setup_method(self):
        self.d = us.connect()

"""

    def step_to_code(self, step: TraceStep) -> str:
        if step.tool_name == "click":
            x, y = step.arguments["x"], step.arguments["y"]
            return f"        self.d.click({x}, {y})  # 点击坐标"
        elif step.tool_name == "type":
            text = step.arguments["text"]
            return f"        self.d.send_keys('{text}')  # 输入文本"
        elif step.tool_name == "swipe":
            a = step.arguments
            return f"        self.d.swipe({a['x1']}, {a['y1']}, {a['x2']}, {a['y2']})"
        elif step.tool_name == "open_app":
            app = step.arguments["app_id"]
            return f"        self.d.app_start('{app}')"
        elif step.tool_name == "press_back":
            return "        self.d.press('back')"
        elif step.tool_name == "wait":
            return f"        self.d.wait_timeout({step.arguments.get('seconds', 2)})"
        return ""

    def emit_footer(self) -> str:
        return ""
```

### 7.3 XCUITest 脚本生成

```python
class XCUITestEmitter(FrameworkEmitter):
    """iOS XCUITest 脚本生成器"""

    def emit_header(self) -> str:
        return """import XCTest

class MobileTest: XCTestCase {
    let app = XCUIApplication()

    override func setUp() {
        super.setUp()
        app.launch()
    }

"""

    def step_to_code(self, step: TraceStep) -> str:
        if step.tool_name == "click":
            x, y = step.arguments["x"], step.arguments["y"]
            return f"        app.coordinate(withNormalizedOffset: CGVector(dx: {x/1000}, dy: {y/1000})).tap()"
        elif step.tool_name == "type":
            text = step.arguments["text"]
            return f'        app.typeText("{text}")'
        elif step.tool_name == "press_back":
            return "        app.navigationBars.element(boundBy: 0).buttons.element(boundBy: 0).tap()"
        return ""

    def emit_footer(self) -> str:
        return "}"
```

### 7.4 鸿蒙 UI Test 脚本生成

```python
class HarmonyOSEmitter(FrameworkEmitter):
    """HarmonyOS UI Test 脚本生成器"""

    def emit_header(self) -> str:
        return """import { Driver, ON } from '@ohos.UiTest'
import { describe, it, beforeAll } from '@ohos/hypium'


export default function harmonyTest() {
    describe('MobileTest', () => {
        let driver = Driver.create()

        beforeAll(() => {
            driver.pressHome()
        })

"""

    def step_to_code(self, step: TraceStep) -> str:
        if step.tool_name == "click":
            x, y = step.arguments["x"], step.arguments["y"]
            return f"        driver.click({x}, {y})"
        elif step.tool_name == "type":
            text = step.arguments["text"]
            return f'        driver.input(\'{text}\')'
        elif step.tool_name == "press_back":
            return "        driver.pressBack()"
        return ""

    def emit_footer(self) -> str:
        return "    })\n}"
```

### 7.5 脚本生成器工厂

```python
class ScriptGenerator:
    """脚本生成器入口 —— 根据平台选择发射器"""

    EMITTERS = {
        "uiautomator2": UIAutomator2Emitter,
        "xcuitest": XCUITestEmitter,
        "harmonyos": HarmonyOSEmitter,
    }

    @classmethod
    def generate(cls, trace: TraceStore, platform: str = "uiautomator2") -> str:
        emitter_cls = cls.EMITTERS.get(platform)
        if not emitter_cls:
            raise ValueError(f"Unsupported platform: {platform}")
        emitter = emitter_cls()
        return emitter.emit(trace)

    @classmethod
    def generate_all(cls, trace: TraceStore) -> dict[str, str]:
        return {
            platform: cls.generate(trace, platform)
            for platform in cls.EMITTERS
        }
```

---

## 8. 与传统方案的对比

### 8.1 与直接 VLM 驱动对比

| 维度 | 直接 VLM 驱动 | MCP + 轨迹录制 + 脚本生成 |
|------|-------------|------------------------|
| 执行速度 | 每次调用 VLM，耗时 2-5 秒/步 | 脚本执行 0.1-0.5 秒/步 |
| 运行成本 | 每次执行都消耗 token | 脚本执行零 token 成本 |
| 可靠性 | VLM 可能在不同次输出不同动作 | 脚本确定性执行 |
| 调试方式 | 修改 Prompt → 重新规划（消耗 token） | 直接编辑脚本 → 设备调试 |
| 可复用性 | 仅限同一 Agent 环境 | Python/Swift/Java 脚本可在标准 CI 中运行 |
| CI 集成 | 需要 GPU/云 LLM 服务 | 仅需设备 + adb/wda |

### 8.2 与其他 MCP 方案对比

| 维度 | Midscene | autoGLM V2 | SmartAI Bot | 本方案 |
|------|---------|-----------|-------------|-------|
| MCP 协议 | 完整 MCP | 函数调用风格 | 无 | 完整 MCP |
| 设备控制 | MCP Tool AutoGen | Tool Registry | ActionHandler | MCP Server 拆分 |
| 定位策略 | AI 定位 | 多策略定位器 | SoM 标注 | 独立 Locator Server |
| 轨迹录制 | ⚠️ YAML 缓存 | 无 | 无 | 结构化 TraceStore |
| 脚本生成 | ⚠️ 不生成 | Python + YAML | Python / Pseudo | 三框架（Android/iOS/HarmonyOS） |
| 重试机制 | 返回截图由上游决定 | 自愈链 | 4 级 LLM 重试 | ReAct 内自动重试 |

### 8.3 脚本生成能力对比

| 方案 | 输出格式 | 直接可运行 | 可编辑性 | 跨平台 |
|------|---------|-----------|---------|-------|
| Midscene | YAML（缓存） | ❌ 需 Midscene Agent | ⚠️ 可编辑 YAML | ✅ Web/Android/iOS |
| autoGLM V2 | Python / YAML | ✅ pytest | ✅ 可直接编辑 | ⚠️ 需适配 |
| SmartAI Bot | Python + 伪代码 | ⚠️ 部分可用 | ✅ 可直接编辑 | ❌ Android |
| **本方案** | Python / Swift / Java | ✅ 三平台可直接运行 | ✅ 可直接编辑 | ✅ Android/iOS/HarmonyOS |

---

## 9. 潜在风险

### 9.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| MCP 协议版本变更 | 低 | 中 | 封装协议适配层，隔离 SDK 变更 |
| MCP Server 进程崩溃 | 中 | 高 | 进程管理器自动重启 + 心跳检测 |
| STDIO 通信阻塞 | 低 | 高 | 设置 STDOUT 超时时间，支持 HTTP 模式备用 |
| 轨迹录制丢失步骤 | 中 | 中 | 每步同步写入 + 异常时持久化缓冲 |
| 脚本生成覆盖率不足 | 中 | 低 | 支持自定义 Emitter 扩展 |

### 9.2 设计风险

| 风险 | 说明 |
|------|------|
| Prompt 膨胀 | 工具数量增多后 System Prompt 过长，需要按需加载 |
| 多 Server 状态同步 | 截图 Server 和设备 Server 如果连接不同设备，需确保一致性 |
| 脚本可维护性 | 生成的脚本缺少注释和结构化，需要后处理增强 |
| 跨平台差异 | 同一操作在不同平台上的实现差异（如坐标归一化、手势参数） |

### 9.3 与现有架构的兼容风险

- **双系统并行期**：MCP Server 需要与现有 `<tool_call>` 解析器并存，过渡期会引入代码复杂度
- **v3.5 的 VLM 轮询逻辑**：当前 `run_gui_owl_1_5_for_mobile.py` 中的 ReAct 循环需要修改为调用 MCP Client 而非直接调用 ActionHandler
- **配置管理**：需新增 MCP Server 地址、端口、平台映射等配置项

---

## 10. 与 Mobile-Agent 现有代码的集成关系

### 10.1 集成策略

采用**渐进式替换**，分三个阶段：

```
阶段一（并行）：MCP Server + 原有 ReAct 并存，验证可行性
阶段二（替换）：MCP Client 替换原有 ActionHandler
阶段三（增强）：加入轨迹录制 + 脚本生成
```

### 10.2 代码变更映射

| 现有文件 | 变更内容 | 影响范围 |
|---------|---------|---------|
| `utils.py` | 新增 `MCPServer` / `MCPTool` 类 | 新增模块，不破坏现有 |
| `run_gui_owl_1_5_for_mobile.py` | 新增 `MCPReActEngine` 分支 | 通过配置开关切换新旧 |
| `packages.py` | 无需修改 | - |
| 新增 `mcp_client.py` | MCP Client 实现 | 新建 |
| 新增 `trace_store.py` | 轨迹录制 | 新建 |
| 新增 `emitters/` | 多框架脚本生成 | 新建 |
| 新增 `servers/device_server.py` | 设备 MCP Server | 新建 |
| 新增 `servers/locator_server.py` | 定位 MCP Server | 新建 |

### 10.3 依赖关系

```
Mobile-Agent 现有代码
    │
    ├── utils.py ─────────► MCPServer / MCPTool (新增)
    ├── run_gui_owl... ──► MCPReActEngine (新增)
    │                        │
    │                        ├── mcp_client.py (新增)
    │                        ├── trace_store.py (新增)
    │                        └── emitters/ (新增)
    │
    ├── packages.py ─────► (无变更)
    └── BaseDeviceAdapter ──► MCP Server Handlers (适配)
```

### 10.4 配置示例

```json
{
  "mcp": {
    "enabled": true,
    "servers": [
      {
        "name": "device",
        "mode": "stdio",
        "command": ["python", "servers/device_server.py"],
        "platform": "android"
      },
      {
        "name": "locator",
        "mode": "http",
        "url": "http://localhost:3001"
      },
      {
        "name": "screenshot",
        "mode": "stdio",
        "command": ["python", "servers/screenshot_server.py"],
        "platform": "android"
      }
    ],
    "script_generation": {
      "enabled": true,
      "output_dir": "./generated_tests",
      "platforms": ["uiautomator2", "xcuitest", "harmonyos"]
    }
  }
}
```

---

## 11. 附录

### 11.1 目录结构

```
mcp_agent/
├── __init__.py
├── config.py                    # MCP 配置加载
├── mcp_client.py                # MCP Client 实现
├── trace_store.py               # 轨迹录制
├── servers/
│   ├── __init__.py
│   ├── base_server.py           # MCPServer / MCPTool 基类
│   ├── device_server.py         # 设备控制 Server
│   ├── locator_server.py        # 元素定位 Server
│   ├── screenshot_server.py     # 截图 Server
│   └── app_server.py            # 应用管理 Server
├── emitters/
│   ├── __init__.py
│   ├── base.py                  # FrameworkEmitter 基类
│   ├── uiautomator2.py          # Android 脚本生成
│   ├── xcuitest.py              # iOS 脚本生成
│   └── harmonyos.py             # 鸿蒙脚本生成
├── engine/
│   ├── __init__.py
│   ├── react_engine.py          # MCPReActEngine
│   └── prompt_builder.py        # System Prompt 动态构建
└── examples/
    ├── stdio_server.py          # STDIO 模式示例
    └── http_server.py           # HTTP 模式示例
```

### 11.2 快速开始示例

```bash
# 1. 启动设备 MCP Server（STDIO 模式）
python servers/device_server.py --platform android

# 2. 启动定位 MCP Server（HTTP 模式）
python servers/locator_server.py --port 3001

# 3. 运行 MCP ReAct Agent
python -m mcp_agent.engine.react_engine \
    --task "打开淘宝，搜索'手机'，截图" \
    --config config.json

# 4. 生成脚本
python -m mcp_agent.emitters.generate \
    --trace traces/2025-01-01.json \
    --platform uiautomator2
```

### 11.3 MCP Tool Schema 完整列表

```json
[
  {
    "server": "mobile_device",
    "name": "click",
    "description": "点击屏幕指定坐标位置",
    "inputSchema": {
      "type": "object",
      "properties": {
        "x": {"type": "integer", "description": "X 坐标（0-1000）"},
        "y": {"type": "integer", "description": "Y 坐标（0-1000）"}
      },
      "required": ["x", "y"]
    }
  },
  {
    "server": "mobile_device",
    "name": "type",
    "description": "输入指定文本",
    "inputSchema": {
      "type": "object",
      "properties": {
        "text": {"type": "string"},
        "mode": {"type": "string", "enum": ["normal", "clear_first", "search"]}
      },
      "required": ["text"]
    }
  },
  {
    "server": "mobile_device",
    "name": "swipe",
    "description": "在屏幕上滑动",
    "inputSchema": {
      "type": "object",
      "properties": {
        "x1": {"type": "integer"},
        "y1": {"type": "integer"},
        "x2": {"type": "integer"},
        "y2": {"type": "integer"},
        "duration_ms": {"type": "integer"}
      },
      "required": ["x1", "y1", "x2", "y2"]
    }
  },
  {
    "server": "mobile_device",
    "name": "open_app",
    "description": "打开指定应用",
    "inputSchema": {
      "type": "object",
      "properties": {
        "app_id": {"type": "string"}
      },
      "required": ["app_id"]
    }
  },
  {
    "server": "mobile_device",
    "name": "press_back",
    "description": "按下返回键",
    "inputSchema": {"type": "object", "properties": {}}
  },
  {
    "server": "mobile_device",
    "name": "press_home",
    "description": "按下 Home 键",
    "inputSchema": {"type": "object", "properties": {}}
  },
  {
    "server": "mobile_device",
    "name": "wait",
    "description": "等待指定时间（秒）",
    "inputSchema": {
      "type": "object",
      "properties": {
        "seconds": {"type": "number"}
      }
    }
  },
  {
    "server": "mobile_device",
    "name": "screenshot",
    "description": "截取当前屏幕并返回 Base64",
    "inputSchema": {"type": "object", "properties": {}}
  },
  {
    "server": "mobile_device",
    "name": "terminate_app",
    "description": "关闭指定应用",
    "inputSchema": {
      "type": "object",
      "properties": {
        "app_id": {"type": "string"}
      },
      "required": ["app_id"]
    }
  },
  {
    "server": "mobile_locator",
    "name": "find_element",
    "description": "查找屏幕上匹配的元素，返回坐标和属性",
    "inputSchema": {
      "type": "object",
      "properties": {
        "by": {"type": "string", "enum": ["text", "id", "content_desc", "xpath", "semantic"]},
        "value": {"type": "string"},
        "timeout": {"type": "number"}
      },
      "required": ["by", "value"]
    }
  },
  {
    "server": "mobile_locator",
    "name": "tap_element",
    "description": "点击指定元素（先定位再点击）",
    "inputSchema": {
      "type": "object",
      "properties": {
        "by": {"type": "string", "enum": ["text", "id", "content_desc", "xpath", "semantic"]},
        "value": {"type": "string"}
      },
      "required": ["by", "value"]
    }
  }
]
```

---

> 本文档由自动化测试 Agent 平台设计方案综合分析生成，整合了 Midscene、autoGLM、Mobile-Agent、SmartAI Bot 等方案的 MCP 集成最佳实践。
