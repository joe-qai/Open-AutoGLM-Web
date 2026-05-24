# Agent 功能开发设计文档

> 基于 LOCKIN Agent Platform 现有后端架构，补全 agent 核心功能使其能端到端工作
> 
> Android 真机 + LLM 驱动 + 元素定位优先

## 一、现状诊断

现有后端已有完整的架构骨架，但 agent 功能不能正常工作。关键差距：

| 层面 | 现有状态 | 缺失 |
|------|---------|------|
| **UI 感知** | `perception.py` 可截图、获取元素树 XML | 无 XML→结构化文本转换（LLM 看不到元素列表） |
| **元素定位** | `finder.py` 简单子串匹配 | 无多策略降级定位链 |
| **决策循环** | `engine.py` 简单的 perceive→decide→act | 无分阶段 ReAct 模式（Observe→Think→Act→Reflect） |
| **实时日志** | `websocket.py` 有 ConnectionManager stub | agent 执行流未接入 WebSocket |
| **脚本导出** | task_service 有子进程执行模式 | 无从执行轨迹生成 pytest 脚本的能力 |

## 二、新增模块

### 2.1 `core/ui_tree.py` — UI 树提取器

将 Android `uiautomator2` dump 的 XML 转换为 LLM 可理解的结构化文本。

**数据结构**：
```python
@dataclass
class UIElement:
    resource_id: str
    class_name: str
    text: str
    content_desc: str
    bounds: Tuple[int, int, int, int]  # [x1, y1, x2, y2]
    enabled: bool
    clickable: bool
    focused: bool
```

**UITreeExtractor**：
- `extract()` → 调用 `adapter.dump_ui_tree()` 获取原始 XML
- `to_text(ui_xml, max_elements=30)` → 解析 XML，按定位优先级排序，输出结构化文本
- `_parse_xml()` / `_parse_element()` / `_parse_bounds()` → XML 递归解析
- `_sort_by_priority()` → resource_id(0) > content_desc(1) > text(2) > class_name(3)

**输出格式**（直接拼入 LLM prompt）：
```
=== 屏幕概览 ===
分辨率: 1080x2400
当前应用: com.taobao.taobao

=== 可交互元素 ===
+[0] id=com.taobao.taobao:id/search_bar | desc=搜索 | type=TextView @(540,120)
+[1] id=com.taobao.taobao:id/back_btn | type=ImageView @(60,120)
-[2] text=购物车 | type=TextView @(900,120)

=== 输入框 ===
[0] com.taobao.taobao:id/search_edit @(540,200)
```

### 2.2 `core/element_locator.py` — 多策略元素定位器

提供七层降级定位链，让 LLM 可以按属性定位而非仅靠坐标。

**定位优先级**：

| 优先级 | 定位方式 | 方法 | 说明 |
|--------|---------|------|------|
| 1 | `resource_id` | `find(by=resource_id, exact)` | 最稳定，跨设备一致 |
| 2 | `content_desc` | `find(by=description, exact)` | 图标按钮的辅助描述 |
| 3 | `text` | `find(by=text, exact)` | 文本精确匹配 |
| 4 | `text_contains` | `find(by=text, contains)` | 文本包含匹配 |
| 5 | `class_name + index` | `find(by=class_name)` | 类型+序号定位 |
| 6 | `semantic` | LLM 辅助选择 | 语义描述匹配 |
| 7 | `coordinates` | 直接点击 | 万不得已时使用 |

**核心接口**：
```python
class MultiStrategyElementLocator:
    def __init__(self, device_adapter: BaseDeviceAdapter)

    def locate(self, locator: ElementLocator) -> LocateResult:
        """按优先级链尝试每种定位方式，命中即返回"""
```

**集成**：替换 `agent/finder.py` 的内部实现，保持 find_element() 等外壳接口。

### 2.3 `core/react_loop.py` — ReAct 循环

**执行流**（每个迭代）：
```
OBSERVE → 截图 + UI树 + to_text() → 推 ws 日志
↓
THINK   → 构建 prompt → LLM 推理 → 解析 action/locator → 推 ws 日志
↓
ACT     → locate_element() → execute() → 推 ws 日志
↓
REFLECT → 验证结果（成功/失败原因）→ 写入 memory → 推 ws 日志
↓
判断：finish? → 结束 | 失败? → 最多重试2次 | 继续循环
```

**接口**：
```python
class ReActLoop:
    def __init__(self, ui_extractor, llm_decider, element_locator,
                 action_executor, max_iterations=50, on_step_callback=None)

    async def run(self, task: str, task_id: str = None) -> dict
    # 返回: {success, total_steps, steps[], final_message}
    # script 由 script_generator.py 消费 steps[] 后独立生成
```

### 2.4 `core/script_generator.py` — 脚本生成器

将 ReActLoop 的执行轨迹转换为 uiautomator2 pytest 脚本。

**映射规则**：
- `text` 定位 → `d(text="...")`
- `text_contains` → `d(textContains="...")`
- `resource_id` → `d(resourceId="...")`
- `coordinates` → `d.click(x, y)`
- 每一步后插入 `assert element.exists` + `time.sleep`

## 三、修改模块

### 3.1 `core/layers/perception.py`

`perceive()` 方法增加对 `UITreeExtractor.to_text()` 的调用，`PerceptionResult` 增加 `ui_text: str` 字段。

### 3.2 `core/layers/decision.py`

新增 `ACTION_SCHEMA_LLM` system prompt（基于节点优先策略），要求 LLM 输出 JSON 格式：

```json
{
    "reasoning": "当前页面是淘宝首页，需要找到搜索框",
    "action": "tap",
    "locator": {
        "type": "text",
        "value": "搜索",
        "index": 0
    },
    "fallback_coords": [540, 120]
}
```

完成任务时 `action: "finish"` + `message`。

### 3.3 `core/agent/engine.py`

`execute_task()` 内部实现替换为 `ReActLoop.run()` 调用。保留 `AgentEngine.set_device()` 等初始化逻辑不变。

### 3.4 `api/v1/websocket.py`

`ConnectionManager` 补全：
- `subscribe_task(client_id, task_id)` — 客户端订阅特定 task_id 的更新
- `send_task_update(task_id, event_data)` — 推送 OBSERVE/THINK/ACT/REFLECT 事件

**事件格式**：
```json
{
    "type": "agent_step",
    "task_id": "uuid",
    "data": {
        "step": 1,
        "phase": "observe|think|act|reflect",
        "content": "...",
        "screenshot_base64": "...",
        "timestamp": "2026-05-24T10:00:00Z"
    }
}
```

## 四、实现顺序

```
1. ui_tree.py          ← 无外部依赖
2. element_locator.py  ← 依赖 BaseDeviceAdapter 接口（已有）
3. decision.py prompt  ← 更新 LLM 输出格式
4. react_loop.py       ← 依赖 1 + 2 + 3
5. perception.py       ← 集成 ui_tree
6. engine.py           ← 改成调 react_loop
7. websocket.py        ← 接入 step_callback
8. script_generator.py ← 依赖步骤历史格式
```

## 五、不修改的文件

- `task_service.py` — 接口不变，`engine.execute_task()` 签名不变
- `api/v1/tasks.py` — API 路由不变
- `core/adapters/` — 接口不变
- `core/agent/manager.py` / `reflector.py` — 后续迭代
- `db/database.py` — schema 不变
