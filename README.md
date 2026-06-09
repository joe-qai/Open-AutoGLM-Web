<div align="center">

<img src="resources/logo.svg" width="150">

# Open-AutoGLM

**AI 驱动的多平台手机自动化测试平台** — Android / HarmonyOS / iOS

基于视觉语言模型 (VLM) 的手机端自动化平台。从自然语言指令到设备操作闭环，支持 Web UI 与 CLI 双模式。

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![React](https://img.shields.io/badge/React-18-61DAFB.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

</div>

---

## 核心特性

### AI 自动化引擎

- **ReActLoop 决策循环** — Observe → Think → Act → Reflect 多步闭环执行
- **四层子代理** — Manager（任务规划）、Executor（步骤执行）、Reflector（失败分析）、Finder（元素定位）
- **七层流水线** — Perception → Decision → Action → Memory → Verification → Replay 完整链路
- **双输出格式** — `pseudo`（伪代码）和 `json`（结构化数据）

### 多平台设备支持

| 平台 | 驱动 | 输入方式 |
|---|---|---|
| Android (7.0+) | ADB | uiautomator dump + ADB Keyboard |
| HarmonyOS (NEXT+) | HDC | HDC 原生控制 + Ability 启动 |
| iOS | XCTest / WDA | WebDriverAgent HTTP API |

支持 USB 有线和 TCP/IP 无线连接。

### Web 管理平台

前端基于 React + Vite + Tailwind CSS，提供以下功能页：

| 页面 | 功能 |
|---|---|
| **Dashboard** | 概览：设备状态、任务统计、快捷操作 |
| **Agent** | 自然语言驱动的智能体执行界面 |
| **Tasks** | 任务创建、执行、停止、日志查看 |
| **Scripts** | Python 脚本管理：上传、AI 生成、跨平台派生、版本控制 |
| **Projects** | 项目组织与管理 |
| **APK** | APK 上传、元数据提取、一键安装 |
| **Reports** | HTML 测试报告生成与预览 |
| **Devices** | 设备发现、连接管理、截图、应用列表 |
| **Settings** | 系统设置与模型配置 |

### 高级功能

- **实时投屏** — Scrcpy H.264 视频流，WebCodecs 解码
- **WebSocket 推送** — 任务执行进度实时推送
- **无线调试** — ADB/HDC TCP/IP 远程连接
- **人工接管** — 登录/验证码场景支持人工干预
- **APP 包映射** — 预置 150+ 应用包名（Android / HarmonyOS / iOS）
- **审计日志** — 所有操作记录至 SQLite

---

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- 目标设备（Android / HarmonyOS / iOS）
- 对应命令行工具：ADB / HDC / libimobiledevice

### 启动 Web 管理平台

```powershell
# 方式一：一键启动
.\start_all.bat

# 方式二：分别启动

# 1. 后端（端口 8005）
cd backend
pip install -r requirements.txt
python run.py

# 2. 前端（端口 3000）
cd frontend
npm install
npm run dev
```

启动后访问：

- 前端界面：http://localhost:3000
- API 文档：http://localhost:8005/docs

### 停止服务

```powershell
.\kill_ports.bat
```

### CLI 命令行模式

```powershell
# 基本用法
python main.py "打开设置，关闭蓝牙"

# 指定平台和设备
python main.py --platform android --device-id emulator-5554 "打开微信"

# 通过环境变量配置模型
$env:PHONE_AGENT_MODEL_API_URL = "http://localhost:8000/v1"
$env:PHONE_AGENT_MODEL_NAME = "autoglm-phone-9b"
python main.py "完成以下任务：打开抖音并浏览"
```

---

## 模型服务配置

后端要求模型服务为 **OpenAI 兼容接口**。支持：

| 类型 | 示例 |
|---|---|
| 本地推理 | vLLM / SGLang / Ollama |
| 云服务 | 百度千帆 / 魔搭 ModelScope / 智谱 GLM |

在 [Settings](http://localhost:3000/settings) 页面或通过 `model_configs` API 配置模型参数。

---

## 项目结构

```
.
├── main.py                     # CLI 入口 — 命令行智能体执行
├── start_all.bat               # 一键启动前后端
├── kill_ports.bat              # 释放端口 8005 + 3000
├── backend/                    # FastAPI 后端 (port 8005)
│   ├── app/
│   │   ├── main.py             # FastAPI 入口，11 个路由挂载
│   │   ├── api/v1/             # API 路由（11 个模块）
│   │   │   ├── tasks.py        # 任务管理
│   │   │   ├── devices.py      # 设备管理
│   │   │   ├── control.py      # 设备控制（点击/滑动/输入）
│   │   │   ├── scripts.py      # 脚本管理
│   │   │   ├── projects.py     # 项目管理
│   │   │   ├── apks.py         # APK 管理
│   │   │   ├── reports.py      # 报告管理
│   │   │   ├── model_configs.py # 模型配置
│   │   │   ├── settings.py     # 系统设置
│   │   │   ├── logs.py         # 审计日志
│   │   │   └── websocket.py    # WebSocket 实时推送
│   │   ├── core/
│   │   │   ├── agent/          # AgentEngine + 子代理
│   │   │   ├── adapters/       # Android/HarmonyOS/iOS 适配器
│   │   │   ├── devices/        # ADB/HDC/XCTest 设备驱动
│   │   │   ├── layers/         # 感知/决策/动作/记忆/验证/回放
│   │   │   └── react_loop.py   # ReAct 循环引擎
│   │   ├── services/           # 业务服务层（14 个服务）
│   │   └── db/                 # SQLite + aiosqlite
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   # React 前端 (port 3000)
│   ├── src/
│   │   ├── App.tsx             # 路由入口
│   │   ├── pages/              # 9 个功能页面
│   │   ├── components/         # ScrcpyPlayer / LogCard / Layout
│   │   ├── stores/             # Zustand 状态管理（7 个 store）
│   │   └── services/           # Axios API 客户端
│   └── package.json
└── README.md
```

---

## API 参考

| 模块 | 前缀 | 说明 |
|---|---|---|
| 任务管理 | `POST/GET/DELETE /api/v1/tasks` | 创建、执行、停止、批量删除、日志 |
| 设备管理 | `GET/POST /api/v1/devices` | 列表、详情、截图、无线连接 |
| 设备控制 | `POST /api/v1/control` | 点击、滑动、输入、按键、Home/Back |
| 脚本管理 | `CRUD /api/v1/scripts` | 创建、执行、AI 生成、派生、版本 |
| 项目管理 | `CRUD /api/v1/projects` | 项目 CRUD |
| APK 管理 | `CRUD /api/v1/apks` | 上传、安装、批量删除 |
| 报告管理 | `GET/DELETE /api/v1/reports` | 列表、HTML 预览、删除 |
| 模型配置 | `CRUD /api/v1/model_configs` | 配置 CRUD、测试连接 |
| 系统设置 | `GET/PUT /api/v1/settings` | 获取、更新、重置 |
| 审计日志 | `GET /api/v1/logs` | 操作日志查询 |
| 实时推送 | `WS /ws/{client_id}` | 任务进度 WebSocket |

完整文档：http://localhost:8005/docs

---

## 环境变量

所有变量使用 `PHONE_AGENT_` 前缀，在 `backend/.env` 中配置：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MODEL_API_URL` | `http://localhost:8000/v1` | OpenAI 兼容 VLM 接口 |
| `MODEL_NAME` | `autoglm-phone-9b` | 模型名称 |
| `API_KEY` | `EMPTY` | API 密钥 |
| `API_HOST` | `0.0.0.0` | 监听地址 |
| `API_PORT` | `8000` | 监听端口 |
| `MAX_STEPS` | `100` | 单次任务最大步数 |
| `DEFAULT_LANG` | `cn` | 默认语言 (cn/en) |
| `DEFAULT_FORMAT` | `pseudo` | 输出格式 (pseudo/json) |
| `DATABASE_URL` | `sqlite:///./app.db` | 数据库连接 |

---

## 智能体执行流程

```
1. 感知 (Perception)     截图 → UI 树提取 → 多策略元素定位
2. 决策 (Decision)       VLM 分析屏幕 + 任务 → 选择操作
3. 动作 (Action)         执行点击/滑动/输入/按键
4. 记忆 (Memory)         记录执行历史和中间状态
5. 验证 (Verification)   判断任务是否完成
6. 回放 (Replay)         生成 HTML 操作回放报告
```

---

## 测试

```powershell
# 后端单元测试
cd backend
pytest

# Agent 引擎集成测试
cd backend
python test_agent_engine.py

# 前端测试
cd frontend
npm test
```

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.10+ · FastAPI · Uvicorn · SQLAlchemy 2.0 · aiosqlite |
| 前端 | React 18 · TypeScript 5 · Vite 5 · Tailwind CSS 3 · Zustand |
| 实时通信 | WebSocket · Socket.IO · Scrcpy H.264 |
| 设备驱动 | ADB · HDC · XCTest / WebDriverAgent |
| 数据库 | SQLite（自动建表，无需迁移） |

---

## 许可证

MIT
