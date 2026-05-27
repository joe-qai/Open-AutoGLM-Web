# PhoneAgent 平台化迁移设计文档

## 1. 需求分析

### 1.1 背景
当前项目中 `phone_agent/` 目录作为独立的 CLI 工具存在，与 `backend/` 形成并行架构。为了实现平台化目标，需要将 `phone_agent` 的全部核心能力迁移到 `backend` 中，最终删除 `phone_agent/` 目录。

### 1.2 核心需求

| 需求编号 | 需求描述 | 来源 |
|----------|----------|------|
| REQ-001 | 支持 Android、HarmonyOS、iOS 三平台设备控制 | phone_agent/adb, hdc, xctest |
| REQ-002 | 支持 AI 驱动的任务自动执行（VLM 推理） | phone_agent/model, agent.py |
| REQ-003 | 支持动作解析和执行引擎 | phone_agent/actions |
| REQ-004 | 提供 REST API 接口供前端调用 | 平台化需求 |
| REQ-005 | 支持实时日志和截图推送（WebSocket） | 平台化需求 |
| REQ-006 | 支持多设备并发执行 | 平台化需求 |

### 1.3 目标状态
- ✅ 删除 `phone_agent/` 目录
- ✅ 所有 Agent 能力通过 REST API 和 WebSocket 对外提供
- ✅ 支持 Android/HarmonyOS/iOS 三平台
- ✅ 完整的 Agent 循环（截图→思考→动作→重复）

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     API Gateway (FastAPI)                          │
│  /api/v1/agent/tasks    /api/v1/devices    /api/v1/models          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                      Agent Engine                                  │
│  (协调任务编排、AI 推理、动作执行、设备控制)                         │
└───────────────────────────┬─────────────────────────────────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Model API   │   │  Action Exec  │   │  Device API   │
│  (AI 推理)    │   │  (动作解析)    │   │  (设备控制)    │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 2.2 模块划分

| 模块 | 路径 | 职责 | 来源 |
|------|------|------|------|
| `core/agent/` | `backend/app/core/agent/` | Agent 核心循环 | `phone_agent/agent.py`, `agent_ios.py` |
| `core/actions/` | `backend/app/core/actions/` | 动作解析和执行 | `phone_agent/actions/` |
| `core/devices/` | `backend/app/core/devices/` | 设备抽象层 | `phone_agent/adb/`, `hdc/`, `xctest/` |
| `core/model/` | `backend/app/core/model/` | AI 模型客户端 | `phone_agent/model/` |
| `core/config/` | `backend/app/core/config/` | 配置管理 | `phone_agent/config/` |
| `api/v1/agent/` | `backend/app/api/v1/agent/` | Agent API 端点 | 新增 |

### 2.3 核心数据流

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────▶│  Agent API   │────▶│  Agent      │
│  (任务请求)  │     │  (任务创建)   │     │  Engine     │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
        ┌────────────────────────────────────────┼─────────────────────────┐
        ▼                                        ▼                         ▼
┌─────────────┐                          ┌─────────────┐           ┌─────────────┐
│   Device    │◀──── Capture ────│   Model     │◀─── Request ───│   Action    │
│   Service   │   Screenshot       │   Client    │    Thinking    │   Handler   │
└──────┬──────┘                    └──────┬──────┘                └──────┬──────┘
       │                                  │                              │
       │ Execute                          │ Response                     │ Parse
       │◀────────────────────────────────┼───────────────────────────────│
       │                                  │                              │
       ▼                                  ▼                              ▼
┌─────────────┐                    ┌─────────────┐                ┌─────────────┐
│  设备操作    │                    │  AI 推理    │                │  动作解析    │
│ (Tap/Swipe/ │                    │  (VLM)      │                │  (JSON/Code) │
│  Launch)    │                    └─────────────┘                └─────────────┘
└─────────────┘
```

---

## 3. 目录结构

```
backend/app/
├── api/
│   └── v1/
│       └── agent/              # Agent API 端点
│           ├── __init__.py
│           ├── tasks.py        # 任务管理 API
│           └── execution.py    # 执行控制 API
├── core/
│   ├── agent/                  # Agent 核心循环
│   │   ├── __init__.py
│   │   ├── base_agent.py       # 抽象 Agent 基类
│   │   ├── android_agent.py    # Android Agent
│   │   ├── ios_agent.py        # iOS Agent
│   │   └── harmonyos_agent.py  # HarmonyOS Agent
│   ├── actions/                # 动作处理引擎
│   │   ├── __init__.py
│   │   ├── handler.py          # 动作解析器
│   │   ├── action_types.py     # 动作类型定义
│   │   └── action_result.py    # 动作结果
│   ├── devices/                # 设备抽象层
│   │   ├── __init__.py
│   │   ├── base_device.py      # 抽象设备基类
│   │   ├── adb/                # Android ADB
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   ├── device.py
│   │   │   ├── input.py
│   │   │   └── screenshot.py
│   │   ├── hdc/                # HarmonyOS HDC
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   ├── device.py
│   │   │   ├── input.py
│   │   │   └── screenshot.py
│   │   └── xctest/             # iOS XCTest
│   │       ├── __init__.py
│   │       ├── connection.py
│   │       ├── device.py
│   │       ├── input.py
│   │       └── screenshot.py
│   ├── model/                  # AI 模型客户端
│   │   ├── __init__.py
│   │   ├── client.py           # 模型客户端
│   │   └── config.py           # 模型配置
│   └── config/                # 配置管理
│       ├── __init__.py
│       ├── prompts.py          # 系统提示词
│       ├── apps.py             # 应用包名映射
│       ├── i18n.py             # 国际化
│       └── timing.py           # 时序配置
├── schemas/
│   └── agent.py                # Agent 相关数据模型
└── services/
    └── agent_service.py        # Agent 业务服务
```

---

## 4. API 设计

### 4.1 Agent 任务 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/agent/tasks` | 创建 Agent 任务 |
| GET | `/api/v1/agent/tasks` | 获取任务列表 |
| GET | `/api/v1/agent/tasks/{task_id}` | 获取任务详情 |
| POST | `/api/v1/agent/tasks/{task_id}/execute` | 执行任务 |
| POST | `/api/v1/agent/tasks/{task_id}/stop` | 停止任务 |
| GET | `/api/v1/agent/tasks/{task_id}/logs` | 获取执行日志 |

#### POST /api/v1/agent/tasks

**请求体：**
```json
{
  "description": "打开微信查看消息",
  "device_id": "11f16a99",
  "platform": "android",
  "max_steps": 100,
  "model_config_id": "model-123"
}
```

**响应体：**
```json
{
  "id": "task-abc123",
  "description": "打开微信查看消息",
  "device_id": "11f16a99",
  "platform": "android",
  "status": "pending",
  "created_at": "2026-05-27T10:00:00Z"
}
```

### 4.2 设备控制 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/agent/devices` | 列出可用设备 |
| POST | `/api/v1/agent/devices/{device_id}/tap` | 点击操作 |
| POST | `/api/v1/agent/devices/{device_id}/swipe` | 滑动操作 |
| POST | `/api/v1/agent/devices/{device_id}/launch` | 启动应用 |
| GET | `/api/v1/agent/devices/{device_id}/screenshot` | 获取截图 |

### 4.3 WebSocket 实时推送

**连接地址：** `ws://localhost:8000/api/v1/agent/ws`

**事件类型：**

| 事件 | 描述 | 数据结构 |
|------|------|----------|
| `task_status` | 任务状态变更 | `{task_id, status, step}` |
| `step_update` | 步骤执行更新 | `{task_id, step_number, thinking, action, screenshot}` |
| `task_finished` | 任务完成 | `{task_id, status, message}` |

---

## 5. 核心数据模型

### 5.1 AgentTask

```python
class AgentTask(BaseModel):
    id: str                          # 任务唯一标识
    description: str                 # 用户自然语言描述
    device_id: str                   # 目标设备ID
    platform: PlatformType           # 平台类型 (android/ios/harmonyos)
    status: TaskStatus               # 状态: pending/running/finished/failed
    max_steps: int = 100             # 最大执行步骤
    model_config_id: str | None      # 模型配置ID
    steps: List[TaskStep] = []       # 执行步骤记录
    created_at: datetime             # 创建时间
    started_at: datetime | None      # 开始时间
    finished_at: datetime | None     # 完成时间
    result_message: str | None       # 结果消息
```

### 5.2 TaskStep

```python
class TaskStep(BaseModel):
    step_number: int                 # 步骤编号
    screenshot: str                  # 截图 (base64)
    thinking: str                    # AI 思考内容
    action: dict[str, Any]           # 执行的动作
    success: bool                    # 是否成功
    timestamp: datetime              # 执行时间
```

### 5.3 AgentAction

```python
class AgentAction(BaseModel):
    type: str                        # 动作类型: tap/swipe/launch/type/back/home
    element: List[int] | None        # 目标元素坐标
    text: str | None                 # 输入文本
    app_name: str | None             # 应用名称
    duration: int | None             # 持续时间(ms)
```

---

## 6. Agent 核心循环

### 6.1 执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Execution Loop                         │
├─────────────────────────────────────────────────────────────────┤
│  for step in 1..max_steps:                                      │
│      ┌─────────────────────┐                                   │
│      │ 1. Capture Screenshot │                                  │
│      │    device.screenshot() │                                 │
│      └───────────┬───────────┘                                 │
│                  ↓                                             │
│      ┌─────────────────────┐                                   │
│      │ 2. Build Message    │                                   │
│      │    - screenshot     │                                   │
│      │    - history        │                                   │
│      │    - user prompt    │                                   │
│      └───────────┬───────────┘                                 │
│                  ↓                                             │
│      ┌─────────────────────┐                                   │
│      │ 3. Call AI Model    │                                   │
│      │    model.request()  │                                   │
│      └───────────┬───────────┘                                 │
│                  ↓                                             │
│      ┌─────────────────────┐                                   │
│      │ 4. Parse Action     │                                   │
│      │    parse_action()   │                                   │
│      └───────────┬───────────┘                                 │
│                  ↓                                             │
│      ┌─────────────────────┐                                   │
│      │ 5. Check Finish     │                                   │
│      │    if finish():     │                                   │
│      │        break        │                                   │
│      └───────────┬───────────┘                                 │
│                  ↓                                             │
│      ┌─────────────────────┐                                   │
│      │ 6. Execute Action   │                                   │
│      │    action_handler.  │                                   │
│      │    execute()        │                                   │
│      └───────────┬───────────┘                                 │
│                  ↓                                             │
│      ┌─────────────────────┐                                   │
│      │ 7. Push Update      │                                   │
│      │    WebSocket        │                                   │
│      └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 动作类型

| 动作 | 描述 | 参数 |
|------|------|------|
| `Tap` | 点击 | `element: [x, y]` |
| `Swipe` | 滑动 | `element: [x1, y1, x2, y2]`, `duration` |
| `LongPress` | 长按 | `element: [x, y]`, `duration` |
| `Type` | 输入文本 | `text: str` |
| `Type_Name` | 输入应用名称 | `text: str` |
| `Launch` | 启动应用 | `app_name: str` |
| `Back` | 返回 | 无 |
| `Home` | 返回主页 | 无 |
| `Wait` | 等待 | `duration` |
| `Finish` | 完成任务 | `message: str` |

---

## 7. 数据库设计

### 7.1 agent_tasks 表

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 任务ID (UUID) |
| description | TEXT | NOT NULL | 用户描述 |
| device_id | VARCHAR(64) | NOT NULL | 设备ID |
| platform | VARCHAR(16) | NOT NULL | 平台类型 |
| status | VARCHAR(16) | NOT NULL | 状态 |
| max_steps | INTEGER | DEFAULT 100 | 最大步骤 |
| model_config_id | VARCHAR(36) | NULL | 模型配置ID |
| steps_json | TEXT | NULL | 步骤记录(JSON) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| started_at | TIMESTAMP | NULL | 开始时间 |
| finished_at | TIMESTAMP | NULL | 完成时间 |
| result_message | TEXT | NULL | 结果消息 |

### 7.2 agent_execution_logs 表

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 日志ID |
| task_id | VARCHAR(36) | FOREIGN KEY | 关联任务ID |
| step_number | INTEGER | NOT NULL | 步骤编号 |
| thinking | TEXT | NULL | AI思考内容 |
| action | TEXT | NULL | 执行动作(JSON) |
| screenshot_path | VARCHAR(255) | NULL | 截图路径 |
| success | BOOLEAN | NOT NULL | 是否成功 |
| timestamp | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 时间戳 |

---

## 8. 安全考虑

### 8.1 认证与授权
- API 请求需携带 JWT Token
- 任务执行需验证设备访问权限
- 日志和截图需按用户隔离

### 8.2 输入验证
- 设备ID格式校验
- 坐标范围校验 (0-屏幕尺寸)
- 文本长度限制
- 恶意输入过滤

### 8.3 资源限制
- 任务并发数限制
- 单任务步骤数限制
- 截图存储大小限制

---

## 9. 部署与集成

### 9.1 依赖要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行环境 |
| FastAPI | 0.100+ | Web 框架 |
| SQLAlchemy | 2.0+ | ORM |
| openai | 1.0+ | AI 模型客户端 |
| websockets | 11.0+ | WebSocket 支持 |

### 9.2 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| AGENT_MAX_STEPS | 100 | 最大步骤数 |
| AGENT_TIMEOUT | 300 | 任务超时(秒) |
| MODEL_BASE_URL | http://localhost:8000/v1 | 模型API地址 |
| WEBSOCKET_PORT | 8000 | WebSocket端口 |

---

## 10. 实现计划

### Phase 1: 模块迁移 (1-2天)
- 迁移 `phone_agent/adb/` → `backend/app/core/devices/adb/`
- 迁移 `phone_agent/hdc/` → `backend/app/core/devices/hdc/`
- 迁移 `phone_agent/xctest/` → `backend/app/core/devices/xctest/`

### Phase 2: 核心层实现 (2-3天)
- 实现 `core/agent/base_agent.py`
- 实现 `core/actions/handler.py`
- 实现 `core/model/client.py`
- 迁移配置文件到 `core/config/`

### Phase 3: API 层实现 (2天)
- 实现 `api/v1/agent/tasks.py`
- 实现 WebSocket 实时推送
- 实现数据库模型

### Phase 4: 测试与验证 (2天)
- 单元测试
- 集成测试
- 删除 `phone_agent/` 目录验证

---

## 11. 验收标准

| 验收项 | 描述 | 通过条件 |
|--------|------|----------|
| 多平台支持 | Android/HarmonyOS/iOS | 三平台设备控制 API 正常工作 |
| Agent 循环 | 截图→思考→动作 | 完整执行流程正常 |
| API 功能 | 任务 CRUD | REST API 响应正确 |
| 实时推送 | WebSocket | 日志和截图实时推送 |
| 平台化 | 删除 phone_agent | 删除后系统正常运行 |