<div align="center">

<img src=resources/logo.svg width="150">

# Open-AutoGLM

**AI 驱动的多平台手机自动化测试平台** - 支持 Android / HarmonyOS / iOS，Web UI 与 CLI 双模式

从自然语言指令到设备操作闭环：基于视觉语言模型（VLM）理解屏幕内容，通过 ADB / HDC / XCTest 驱动设备，实现端到端自动化

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![React](https://img.shields.io/badge/React-18-61DAFB.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)

</div>

## ✨ 核心特性

### 🤖 AI 自动化能力

- **ReActLoop 引擎** - Observe → Think → Act → Reflect 闭环决策，支持 VLM 多模态感知
- **四层子代理** - Manager（任务规划）、Executor（步骤执行）、Reflector（失败分析）、Finder（元素定位）
- **七层流水线** - Perception → Decision → Action → Memory → Verification → Replay 完整链路
- **双输出格式** - 支持 `pseudo`（Python 伪代码）和 `json`（通用 JSON）两种动作格式

### 📱 多平台支持

- **🤖 Android (ADB)** - `uiautomator dump` UI 树 + ADB Keyboard 文本输入，支持 USB / WiFi 连接
- **🔷 HarmonyOS (HDC)** - HDC 原生控制 + 自定义 Ability 启动，无需额外输入法
- **🍎 iOS (WebDriverAgent)** - WDA HTTP API 驱动，支持 USB 端口映射与 WiFi 连接

### 💻 Web 管理平台

- **设备管理** - 设备发现、连接/断开、实时截图、应用列表
- **任务编排** - 创建、执行、停止、批量管理，支持自然语言指令直接下发
- **脚本系统** - Python 脚本上传、AI 生成、版本控制、跨平台派生
- **APK 管理** - 上传、元数据提取、一键安装到设备
- **实时监控** - WebSocket 任务推送 + Scrcpy H.264 视频流实时预览
- **报告生成** - HTML 测试报告，失败步骤自动截图

### 🎯 高级功能

- **无线调试** - ADB/HDC TCP/IP 远程连接，无需 USB 数据线
- **人工接管** - 登录/验证码场景下支持人工干预
- **APP 包映射** - 预置 150+ 应用包名映射（Android / HarmonyOS / iOS）
- **记忆与回放** - JSON 持久化记忆 + 执行步骤完整录制与回放
- **审计日志** - 所有操作记录至 SQLite，支持查询与统计

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- Android / HarmonyOS / iOS 设备（按平台选择）
- ADB / HDC / WebDriverAgent 命令行工具

### 方式一：启动 Web 管理平台

```bash
# 1. 启动后端（端口 8005）
cd backend
pip install -r requirements.txt
python run.py

# 2. 启动前端（端口 3000，自动代理 API 到后端）
cd frontend
npm install
npm run dev
```

一键启动（Windows）：

```bash
start_all.bat
```

### 方式二：CLI 命令行

```bash
# Android 设备 - 交互模式
python main.py --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b"

# 指定任务
python main.py --base-url http://localhost:8000/v1 "打开美团搜索附近的火锅店"

# HarmonyOS 设备
python main.py --device-type hdc --base-url http://localhost:8000/v1 "打开美团"

# iOS 设备
python main.py --device-type ios --base-url http://localhost:8000/v1 --wda-url http://localhost:8100 "Open Safari"
```

### 🎯 模型服务配置

Open-AutoGLM 只需要一个 OpenAI 兼容的 VLM 模型服务：

| 服务商 | Base URL | 模型名 |
|--------|----------|--------|
| 智谱 BigModel | `https://open.bigmodel.cn/api/paas/v4` | `AutoPhone-phone` |
| ModelScope | `https://api-inference.modelscope.cn/v1` | `ZhipuAI/AutoPhone-Phone-9B` |

```bash
# 使用智谱 BigModel
python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "AutoPhone-phone" --apikey "your-key" "打开美团搜索火锅"

# 指向自建服务
python main.py --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b" "打开小红书"
```

## 🛠️ 开发指南

### 源码安装

```bash
# 克隆仓库
git clone https://github.com/joe-qai/Open-AutoGLM-Web.git
cd Open-AutoGLM-Web

# 后端依赖
cd backend && pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 项目结构

```
backend/                    # FastAPI 后端
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── api/v1/            # 11 个路由模块
│   ├── core/              # 核心引擎
│   │   ├── agent/         # AgentEngine + 子代理
│   │   ├── layers/        # 七层流水线
│   │   ├── adapters/      # 平台适配器
│   │   ├── devices/       # ADB/HDC/XCTest 驱动
│   │   └── model/         # 模型客户端
│   ├── services/          # 业务逻辑层
│   └── db/                # SQLite
└── tests/                 # Pytest 测试

frontend/                   # React 前端
├── src/
│   ├── App.tsx            # 路由入口
│   ├── pages/             # 10 个功能页面
│   ├── components/        # 通用组件
│   ├── stores/            # Zustand 状态管理
│   └── services/          # API 客户端
```

### 测试

```bash
cd backend && pytest
cd backend && python test_agent_engine.py
```

## 🔧 架构概览

### 整体架构

```
用户层: Web UI (React + Vite) / CLI (Python)
  ↓
API层: FastAPI (11 路由模块)
  ↓
服务层: TaskService / DeviceService / ScriptService / ...
  ↓
引擎层: AgentEngine (ReActLoop)
  ├─ 子代理: Manager → Executor → Reflector → Finder
  └─ 流水线: Perception → Decision → Action → Memory → Verification → Replay
  ↓
适配层: AndroidAdapter / HarmonyOSAdapter / IOSAdapter
  ↓
驱动层: ADB / HDC / XCTest
  ↓
设备层: Android 7.0+ / HarmonyOS NEXT+ / iOS
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ · FastAPI · Uvicorn · aiosqlite · SQLite |
| 前端 | React 18 · TypeScript 5 · Vite 5 · Tailwind CSS 3 · Zustand |
| 模型 | OpenAI SDK · Anthropic SDK · GLM-4.1V-9B-Thinking |
| 实时 | WebSocket · Socket.IO · Scrcpy H.264 |
| 设备 | ADB · HDC · WebDriverAgent |

## 📝 许可证

本项目基于 Open-AutoGLM 开源协议，请遵守相关许可证要求。

原 Open-AutoGLM 地址如下：`https://github.com/zai-org/Open-AutoGLM.git`

### 获取帮助

使用 `/help` 查看可用命令，或访问项目文档。
