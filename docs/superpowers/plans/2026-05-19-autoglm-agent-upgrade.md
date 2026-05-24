# Open-AutoPhone 多端Agent测试平台 - 完整实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于Open-AutoPhone构建完整的多端Agent测试平台，支持Android/iOS/鸿蒙三平台，FastAPI后台+React前端，多Agent/6层Agent架构�?
**Architecture:**
- 后台：FastAPI微服务架构，WebSocket实时通信
- 前端：React + TypeScript + Vite
- Agent�?层架�?+ 多Agent协作
- 平台：统一设备适配器模�?
**Tech Stack:** Python 3.10+, FastAPI, React 18, TypeScript, WebSocket, ADB/HDC/XCTest

---

## 一、系统架�?
### 1.1 整体架构�?
```
┌─────────────────────────────────────────────────────────────────────────�?�?                          Frontend (React)                              �?�? ┌─────────────�? ┌─────────────�? ┌─────────────�? ┌─────────────�? �?�? �? Dashboard  �? �?Task Runner �? �? Device Map �? �?  Reports   �? �?�? └──────┬──────�? └──────┬──────�? └──────┬──────�? └──────┬──────�? �?�?        └─────────────────┴─────────────────┴─────────────────�?       �?�?                                 �?REST API + WebSocket                 �?└──────────────────────────────────┼─────────────────────────────────────�?                                   �?┌──────────────────────────────────┼─────────────────────────────────────�?�?                       Backend (FastAPI)                                �?�? ┌─────────────────────────────────────────────────────────────────�?  �?�? �?                       API Gateway                               �?  �?�? �?                  (Router + Auth + Rate Limit)                  �?  �?�? └─────────────────────────────────────────────────────────────────�?  �?�?        �?                   �?                   �?                    �?�? ┌──────┴──────�?    ┌──────┴──────�?    ┌──────┴──────�?            �?�? �?Task Service�?    │Device Service�?   │Report Service�?           �?�? └──────┬──────�?    └──────┬──────�?    └──────┬──────�?            �?�?        �?                   �?                   �?                    �?�? ┌──────┴────────────────────┴────────────────────┴──────�?            �?�? �?             6-Layer Agent Engine                      �?            �?�? �? ┌────────�?┌────────�?┌────────�?┌────────�?┌────────�?┌────────┐│
�? �? │Percept │→│Decision│→�?Action │→�?Memory │→│Verify  │→�?Replay ││
�? �? └────────�?└────────�?└────────�?└────────�?└────────�?└────────┘│
�? └──────────────────────────────────────────────────────────────�?     �?�?        �?                   �?                   �?                    �?�? ┌──────┴──────�?    ┌──────┴──────�?    ┌──────┴──────�?            �?�? �?  Manager   �?    �?  Executor  �?    �? Reflector  �? ...        �?�? �?  Agent     �?    �?  Agent     �?    �?  Agent     �?            �?�? └─────────────�?    └─────────────�?    └─────────────�?            �?└──────────────────────────────────┼─────────────────────────────────────�?                                   �?┌──────────────────────────────────┼─────────────────────────────────────�?�?                       Device Layer                                     �?�? ┌─────────────�? ┌─────────────�? ┌─────────────�?                    �?�? �?  Android   �? �?    iOS     �? �? HarmonyOS  �?                    �?�? �? (ADB+UIA2) �? �?  (XCTest)  �? �?   (HDC)    �?                    �?�? └─────────────�? └─────────────�? └─────────────�?                    �?└─────────────────────────────────────────────────────────────────────────�?```

### 1.2 项目目录结构

```
Open-AutoPhone/
├── backend/                              # FastAPI后台
�?  ├── app/
�?  �?  ├── __init__.py
�?  �?  ├── main.py                      # FastAPI入口
�?  �?  ├── config.py                    # 配置管理
�?  �?  ├── api/                         # API路由
�?  �?  �?  ├── __init__.py
�?  �?  �?  ├── v1/
�?  �?  �?  �?  ├── tasks.py             # 任务管理API
�?  �?  �?  �?  ├── devices.py           # 设备管理API
�?  �?  �?  �?  ├── reports.py           # 报告API
�?  �?  �?  �?  └── websocket.py         # WebSocket API
�?  �?  �?  └── deps.py                  # 依赖注入
�?  �?  ├── core/                        # 核心模块
�?  �?  �?  ├── agent/                   # Agent引擎
�?  �?  �?  �?  ├── __init__.py
�?  �?  �?  �?  ├── engine.py            # Agent引擎
�?  �?  �?  �?  ├── manager.py           # Manager Agent
�?  �?  �?  �?  ├── executor.py          # Executor Agent
�?  �?  �?  �?  ├── reflector.py         # Reflector Agent
�?  �?  �?  �?  └── finder.py            # Finder Agent
�?  �?  �?  ├── layers/                  # 6层架�?�?  �?  �?  �?  ├── __init__.py
�?  �?  �?  �?  ├── perception.py         # 感知�?�?  �?  �?  �?  ├── decision.py          # 决策�?�?  �?  �?  �?  ├── action.py            # 行动�?�?  �?  �?  �?  ├── memory.py            # 记忆�?�?  �?  �?  �?  ├── verification.py      # 验证�?�?  �?  �?  �?  └── replay.py            # 回放�?�?  �?  �?  └── adapters/                # 设备适配�?�?  �?  �?      ├── __init__.py
�?  �?  �?      ├── base.py              # 基类
�?  �?  �?      ├── android.py           # Android
�?  �?  �?      ├── ios.py               # iOS
�?  �?  �?      └── harmonyos.py         # 鸿蒙
�?  �?  ├── models/                      # 数据模型
�?  �?  �?  ├── __init__.py
�?  �?  �?  ├── task.py
�?  �?  �?  ├── device.py
�?  �?  �?  └── report.py
�?  �?  ├── schemas/                     # Pydantic schemas
�?  �?  �?  ├── __init__.py
�?  �?  �?  ├── task.py
�?  �?  �?  ├── device.py
�?  �?  �?  └── report.py
�?  �?  ├── services/                    # 业务服务
�?  �?  �?  ├── __init__.py
�?  �?  �?  ├── task_service.py
�?  �?  �?  ├── device_service.py
�?  �?  �?  └── report_service.py
�?  �?  └── db/                          # 数据�?�?  �?      ├── __init__.py
�?  �?      └── database.py
�?  ├── requirements.txt
�?  └── run.py                           # 启动脚本
�?├── frontend/                            # React前端
�?  ├── src/
�?  �?  ├── main.tsx
�?  �?  ├── App.tsx
�?  �?  ├── api/                        # API调用
�?  �?  �?  ├── client.ts               # API客户�?�?  �?  �?  ├── tasks.ts
�?  �?  �?  ├── devices.ts
�?  �?  �?  └── reports.ts
�?  �?  ├── components/                  # 组件
�?  �?  �?  ├── common/
�?  �?  �?  ├── Dashboard/
�?  �?  �?  ├── TaskRunner/
�?  �?  �?  ├── DeviceMap/
�?  �?  �?  └── Reports/
�?  �?  ├── hooks/                       # 自定义Hook
�?  �?  �?  ├── useTask.ts
�?  �?  �?  ├── useDevice.ts
�?  �?  �?  └── useWebSocket.ts
�?  �?  ├── pages/                       # 页面
�?  �?  �?  ├── Dashboard.tsx
�?  �?  �?  ├── TaskRunner.tsx
�?  �?  �?  ├── DeviceManager.tsx
�?  �?  �?  └── ReportViewer.tsx
�?  �?  ├── store/                       # 状态管�?�?  �?  �?  └── index.ts
�?  �?  ├── types/                       # TypeScript类型
�?  �?  �?  └── index.ts
�?  �?  └── utils/                       # 工具函数
�?  ├── package.json
�?  ├── tsconfig.json
�?  └── vite.config.ts
�?├── phone_agent/                         # 原有核心Agent代码（保留）
�?  ├── __init__.py
�?  ├── agent.py
�?  ├── agent_ios.py
�?  ├── device_factory.py
�?  ├── model/
�?  �?  └── client.py
�?  ├── adb/
�?  ├── hdc/
�?  ├── xctest/
�?  └── config/
�?├── docs/superpowers/plans/
�?  └── 2026-05-19-AutoPhone-agent-upgrade.md
�?└── README.md
```

---

## 二、开发工时评�?
### 2.1 工时汇总表

| 模块 | 任务 | 预估工时(人天) | 优先�?|
|------|------|---------------|--------|
| **后台基础设施** | FastAPI项目搭建 | 1 | P0 |
| | 数据库设计与集成 | 1 | P0 |
| | REST API开�?| 3 | P0 |
| | WebSocket实时通信 | 2 | P0 |
| **设备适配�?* | 统一适配器基�?| 0.5 | P0 |
| | Android适配�?| 1 | P0 |
| | iOS适配�?| 1.5 | P1 |
| | 鸿蒙适配�?| 1.5 | P1 |
| **6层Agent架构** | 感知�?| 1 | P0 |
| | 决策�?| 1.5 | P0 |
| | 行动�?| 1 | P0 |
| | 记忆�?| 1 | P1 |
| | 验证�?| 1.5 | P1 |
| | 回放�?| 1 | P1 |
| **多Agent协作** | Manager Agent | 1 | P0 |
| | Executor Agent | 1 | P0 |
| | Reflector Agent | 1 | P1 |
| | Finder Agent | 1 | P1 |
| | Coordinator | 1.5 | P1 |
| **前端开�?* | 项目初始�?Vite | 0.5 | P0 |
| | 基础组件�?| 2 | P0 |
| | Dashboard页面 | 2 | P0 |
| | 任务执行页面 | 3 | P0 |
| | 设备管理页面 | 2 | P1 |
| | 报告查看页面 | 2 | P1 |
| | WebSocket集成 | 1 | P0 |
| **测试与部�?* | 单元测试 | 3 | P1 |
| | API集成测试 | 2 | P1 |
| | 前端E2E测试 | 2 | P2 |
| | Docker部署 | 1 | P1 |
| **合计** | | **40** | |

### 2.2 阶段划分

```
阶段1：基础设施 (5�?
├── 后台：FastAPI搭建 + 数据�?+ REST API + WebSocket
└── 前端：项目初始化 + 基础组件 + 布局框架

阶段2：核心Agent (8�?
├── 设备适配层：4个平台适配�?├── 6层架构：感知→决策→行动→记忆→验证→回�?└── 多Agent：Manager + Executor + Reflector + Finder

阶段3：业务功�?(5�?
├── 任务管理：创�?执行/暂停/取消
├── 设备管理：连�?监控/分配
└── 报告生成：HTML/PDF + 问题分类

阶段4：前端开�?(6�?
├── Dashboard：设备状�?+ 任务概览
├── 任务执行：实时日�?+ 步骤展示
├── 设备管理：多设备地图 + 状态监�?└── 报告查看：图�?+ 详情

阶段5：测试与部署 (5�?
├── 单元测试 + 集成测试
├── 前端E2E测试
├── Docker镜像 + docker-compose
└── 部署文档
```

---

## 三、详细实施任�?
### Task 1: 后台基础设施搭建

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/requirements.txt`

- [ ] **Step 1: 创建FastAPI主入�?*

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from phone_agent.core.adapters import DeviceAdapterFactory
from phone_agent.core.layers.perception import PerceptionLayer
from phone_agent.core.layers.decision import DecisionLayer
from phone_agent.core.layers.action import ActionLayer
from phone_agent.core.layers.memory import MemoryLayer
from phone_agent.core.layers.verification import VerificationLayer
from phone_agent.core.layers.replay import ReplayLayer
from phone_agent.core.agent.manager import ManagerAgent
from phone_agent.core.agent.executor import ExecutorAgent
from phone_agent.core.agent.reflector import ReflectorAgent
from phone_agent.core.agent.finder import FinderAgent
from phone_agent.core.agent.engine import AgentEngine
from phone_agent.model import ModelClient, ModelConfig

from app.api.v1 import tasks, devices, reports, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_config = ModelConfig(
        base_url=os.getenv("MODEL_API_URL", "http://localhost:8000/v1"),
        model_name=os.getenv("MODEL_NAME", "AutoPhone-phone-9b"),
        api_key=os.getenv("API_KEY", "EMPTY"),
    )
    model_client = ModelClient(model_config)
    
    app.state.agent_engine = AgentEngine(model_client)
    
    yield
    
    pass


app = FastAPI(
    title="Open-AutoPhone Agent Platform",
    description="Multi-platform Mobile Agent Testing Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

- [ ] **Step 2: 创建设备管理API**

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.device import DeviceInfo, DeviceStatus
from app.services.device_service import DeviceService

router = APIRouter()
device_service = DeviceService()


@router.get("/", response_model=List[DeviceInfo])
async def list_devices():
    return device_service.list_devices()


@router.get("/{device_id}", response_model=DeviceInfo)
async def get_device(device_id: str):
    device = device_service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/{device_id}/connect")
async def connect_device(device_id: str):
    result = device_service.connect_device(device_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to connect device")
    return {"status": "connected", "device_id": device_id}


@router.post("/{device_id}/disconnect")
async def disconnect_device(device_id: str):
    device_service.disconnect_device(device_id)
    return {"status": "disconnected", "device_id": device_id}


@router.get("/{device_id}/screenshot")
async def get_screenshot(device_id: str):
    screenshot_path = device_service.get_screenshot(device_id)
    if not screenshot_path:
        raise HTTPException(status_code=400, detail="Failed to capture screenshot")
    return {"screenshot_path": screenshot_path}
```

- [ ] **Step 3: 创建任务管理API**

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
from app.schemas.task import TaskCreate, TaskResponse, TaskStatus
from app.services.task_service import TaskService

router = APIRouter()
task_service = TaskService()


class TaskCreateRequest(BaseModel):
    task_name: str
    task_type: str  # "compatibility", "functional", "crash"
    platform: str  # "android", "ios", "harmonyos"
    devices: list[str]
    steps: list[dict]


@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreateRequest):
    task_id = task_service.create_task(
        name=task.task_name,
        task_type=task.task_type,
        platform=task.platform,
        devices=task.devices,
        steps=task.steps,
    )
    return TaskResponse(task_id=task_id, status="created")


@router.post("/{task_id}/execute")
async def execute_task(task_id: str, background_tasks: BackgroundTasks):
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    background_tasks.add_task(task_service.execute_task, task_id)
    return {"task_id": task_id, "status": "executing"}


@router.post("/{task_id}/stop")
async def stop_task(task_id: str):
    task_service.stop_task(task_id)
    return {"task_id": task_id, "status": "stopped"}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
```

- [ ] **Step 4: 创建WebSocket实时通信**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
    
    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_json(message)
    
    async def broadcast(self, message: dict):
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "task_update":
                await manager.send_message(message, client_id)
            elif message.get("type") == "device_status":
                await manager.broadcast(message)
            elif message.get("type") == "agent_thinking":
                await manager.send_message(message, client_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
```

---

### Task 2: 设备适配层重�?
**Files:**
- Create: `backend/app/core/adapters/base.py`
- Create: `backend/app/core/adapters/android.py`
- Create: `backend/app/core/adapters/ios.py`
- Create: `backend/app/core/adapters/harmonyos.py`
- Create: `backend/app/core/adapters/factory.py`

- [ ] **Step 1: 创建统一适配器基�?*

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import base64


class Platform(Enum):
    ANDROID = "android"
    IOS = "ios"
    HARMONYOS = "harmonyos"


@dataclass
class DisplayInfo:
    width: int
    height: int
    density: float
    status_bar_height: int
    navigation_bar_height: int
    
    def normalize_coord(self, x: int, y: int) -> tuple[float, float]:
        return (x / self.width * 1000, y / self.height * 1000)
    
    def denormalize_coord(self, nx: float, ny: float) -> tuple[int, int]:
        return (int(nx / 1000 * self.width), int(ny / 1000 * self.height))


@dataclass
class UIElement:
    index: int
    bbox_normalized: Dict[str, float]
    bbox_pixel: Optional[Dict[str, int]] = None
    resource_id: Optional[str] = None
    text: Optional[str] = None
    content_desc: Optional[str] = None
    class_name: Optional[str] = None
    package_name: Optional[str] = None
    clickable: bool = False
    enabled: bool = True
    
    def center(self) -> tuple[float, float]:
        return (
            self.bbox_normalized["x"] + self.bbox_normalized["w"] / 2,
            self.bbox_normalized["y"] + self.bbox_normalized["h"] / 2,
        )


class BaseDeviceAdapter(ABC):
    @property
    @abstractmethod
    def platform(self) -> Platform:
        pass
    
    @property
    @abstractmethod
    def device_id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def display_info(self) -> DisplayInfo:
        pass
    
    @abstractmethod
    def get_screenshot(self, save_path: str) -> bool:
        pass
    
    def get_screenshot_base64(self) -> str:
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            save_path = f.name
        self.get_screenshot(save_path)
        with open(save_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        os.unlink(save_path)
        return data
    
    @abstractmethod
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        pass
    
    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        pass
    
    @abstractmethod
    def click_element(self, element: UIElement) -> bool:
        pass
    
    @abstractmethod
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        pass
    
    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        pass
    
    @abstractmethod
    def type_text(self, text: str) -> bool:
        pass
    
    @abstractmethod
    def press_key(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def launch_app(self, package_name: str) -> bool:
        pass
    
    @abstractmethod
    def get_current_app(self) -> str:
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        pass
```

- [ ] **Step 2: 创建Android适配�?*

```python
import subprocess
import os
import time
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict

from .base import BaseDeviceAdapter, Platform, DisplayInfo, UIElement


class AndroidAdapter(BaseDeviceAdapter):
    def __init__(self, adb_path: str = "adb", device_serial: Optional[str] = None):
        self._adb_path = adb_path
        self._device_serial = device_serial
        self._display_info: Optional[DisplayInfo] = None
        self._load_display_info()
    
    @property
    def platform(self) -> Platform:
        return Platform.ANDROID
    
    @property
    def device_id(self) -> str:
        if self._device_serial:
            return self._device_serial
        result = self._run("devices")
        for line in result.stdout.splitlines():
            if "\tdevice" in line:
                return line.split("\t")[0]
        return "unknown"
    
    @property
    def display_info(self) -> DisplayInfo:
        if self._display_info is None:
            self._load_display_info()
        return self._display_info
    
    def _load_display_info(self):
        result = self._run("shell wm size")
        match = re.search(r"(\d+)x(\d+)", result.stdout)
        width, height = (int(match.group(1)), int(match.group(2))) if match else (1080, 1920)
        
        result = self._run("shell wm density")
        density_match = re.search(r"(\d+)", result.stdout)
        density = int(density_match.group(1)) if density_match else 320
        
        self._display_info = DisplayInfo(
            width=width, height=height, density=density,
            status_bar_height=0, navigation_bar_height=0
        )
    
    def _run(self, args: str) -> subprocess.CompletedProcess:
        cmd = f"{self._adb_path}"
        if self._device_serial:
            cmd += f" -s {self._device_serial}"
        cmd += f" {args}"
        return subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    def get_screenshot(self, save_path: str) -> bool:
        cmd = f"{self._adb_path}"
        if self._device_serial:
            cmd += f" -s {self._device_serial}"
        cmd += f" exec-out screencap -p > {save_path}"
        
        for _ in range(3):
            subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                return True
            time.sleep(0.1)
        return False
    
    def get_element_tree(self, screenshot_path: str) -> List[UIElement]:
        xml_path = "/data/local/tmp/uidump.xml"
        self._run(f"shell uiautomator dump {xml_path}")
        local_xml = f"{screenshot_path}.xml"
        self._run(f"pull {xml_path} {local_xml}")
        
        if not os.path.exists(local_xml):
            return []
        
        tree = ET.parse(local_xml)
        root = tree.getroot()
        elements = []
        self._parse_node(root, elements, index=0)
        
        os.remove(local_xml)
        return elements
    
    def _parse_node(self, node, elements: List, index: int) -> int:
        bounds = node.attrib.get("bounds", "")
        match = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if not match:
            return index
        
        x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        w, h = x2 - x1, y2 - y1
        
        if w < 10 or h < 10:
            return index
        
        sw, sh = self.display_info.width, self.display_info.height
        nx, ny = x1 / sw * 1000, y1 / sh * 1000
        nw, nh = w / sw * 1000, h / sh * 1000
        
        clickable = node.attrib.get("clickable", "false") == "true"
        
        if clickable or len(list(node)) == 0:
            element = UIElement(
                index=index,
                bbox_normalized={"x": nx, "y": ny, "w": nw, "h": nh},
                bbox_pixel={"x": x1, "y": y1, "w": w, "h": h},
                resource_id=node.attrib.get("resource-id", ""),
                text=node.attrib.get("text", ""),
                content_desc=node.attrib.get("content-desc", ""),
                class_name=node.attrib.get("class", ""),
                package_name=node.attrib.get("package", ""),
                clickable=clickable,
                enabled=node.attrib.get("enabled", "true") == "true"
            )
            elements.append(element)
            index += 1
        
        for child in node:
            index = self._parse_node(child, elements, index)
        
        return index
    
    def click(self, x: int, y: int) -> bool:
        self._run(f"shell input tap {x} {y}")
        return True
    
    def click_element(self, element: UIElement) -> bool:
        cx, cy = element.center()
        px, py = self.display_info.denormalize_coord(cx, cy)
        return self.click(px, py)
    
    def long_press(self, x: int, y: int, duration: int = 800) -> bool:
        self._run(f"shell input swipe {x} {y} {x} {y} {duration}")
        return True
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        self._run(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
        return True
    
    def type_text(self, text: str) -> bool:
        escaped = text.replace('"', '\\"').replace("'", "\\'")
        commands = [
            "shell ime enable com.android.adbkeyboard/.AdbIME",
            "shell ime set com.android.adbkeyboard/.AdbIME",
            f'shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped}"',
        ]
        for cmd in commands:
            self._run(cmd)
            time.sleep(0.05)
        return True
    
    def press_key(self, key: str) -> bool:
        key_map = {"BACK": "4", "HOME": "3", "MENU": "82", "ENTER": "66", "DELETE": "67"}
        key_code = key_map.get(key.upper(), key)
        self._run(f"shell input keyevent {key_code}")
        return True
    
    def launch_app(self, package_name: str) -> bool:
        self._run(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        return True
    
    def get_current_app(self) -> str:
        result = self._run("shell dumpsys window | grep mCurrentFocus")
        match = re.search(r"([a-zA-Z0-9.]+)/", result.stdout)
        return match.group(1) if match else ""
    
    def is_connected(self) -> bool:
        result = self._run("devices")
        device_flag = self._device_serial or self.device_id
        return device_flag in result.stdout and "device" in result.stdout
```

---

### Task 3: 6层Agent架构实现

**Files:**
- Create: `backend/app/core/layers/perception.py`
- Create: `backend/app/core/layers/decision.py`
- Create: `backend/app/core/layers/action.py`
- Create: `backend/app/core/layers/memory.py`
- Create: `backend/app/core/layers/verification.py`
- Create: `backend/app/core/layers/replay.py`

- [ ] **Step 1: 创建感知�?*

```python
import os
import base64
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..adapters.base import BaseDeviceAdapter, UIElement


@dataclass
class PerceptionResult:
    screenshot_base64: str
    screenshot_path: str
    ui_elements: List[UIElement]
    current_app: str
    timestamp: float


class PerceptionLayer:
    def __init__(self, adapter: BaseDeviceAdapter):
        self.adapter = adapter
        self.screenshot_dir = "./screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def perceive(self, step_index: int = 0) -> PerceptionResult:
        timestamp = time.time()
        screenshot_path = os.path.join(
            self.screenshot_dir, f"step_{step_index:03d}_{int(timestamp)}.png"
        )
        
        self.adapter.get_screenshot(screenshot_path)
        
        with open(screenshot_path, 'rb') as f:
            screenshot_base64 = base64.b64encode(f.read()).decode()
        
        ui_elements = self.adapter.get_element_tree(screenshot_path)
        current_app = self.adapter.get_current_app()
        
        return PerceptionResult(
            screenshot_base64=screenshot_base64,
            screenshot_path=screenshot_path,
            ui_elements=ui_elements,
            current_app=current_app,
            timestamp=timestamp
        )
    
    def perceive_lightweight(self) -> Dict[str, Any]:
        screenshot_base64 = self.adapter.get_screenshot_base64()
        current_app = self.adapter.get_current_app()
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        
        self.adapter.get_screenshot(temp_path)
        ui_elements = self.adapter.get_element_tree(temp_path)
        os.unlink(temp_path)
        
        return {
            "screenshot_base64": screenshot_base64,
            "ui_elements": [
                {
                    "index": e.index,
                    "text": e.text,
                    "resource_id": e.resource_id,
                    "content_desc": e.content_desc,
                    "bbox_normalized": e.bbox_normalized,
                    "clickable": e.clickable,
                }
                for e in ui_elements
            ],
            "current_app": current_app,
        }
```

- [ ] **Step 2: 创建决策�?*

```python
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from ....model import ModelClient, ModelConfig


@dataclass
class ActionPlan:
    action: str
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    reasoning: str = ""


class DecisionLayer:
    SYSTEM_PROMPT = """你是一个智能移动端测试Agent，负责分析屏幕截图和UI元素，做出正确的决策�?
可用工具:
1. tap_element - 点击元素
2. type_text - 输入文本
3. swipe - 滑动屏幕
4. long_press - 长按
5. back - 返回
6. home - 返回主页
7. launch_app - 启动应用
8. wait - 等待

输出格式:
{
    "action": "工具名称",
    "target": "目标元素描述",
    "parameters": {...},
    "confidence": 0.0-1.0,
    "reasoning": "决策理由"
}
"""
    
    def __init__(self, model_client: ModelClient):
        self.model_client = model_client
    
    def decide(
        self, task: str, screenshot_base64: str, ui_elements: List[Dict], history: List[Dict]
    ) -> ActionPlan:
        elements_str = "\n".join([
            f"- text='{e.get('text', '')}', id='{e.get('resource_id', '')}', desc='{e.get('content_desc', '')}'"
            for e in ui_elements[:30]
        ])
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *history,
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}},
                    {"type": "text", "text": f"任务: {task}\n\n当前UI元素:\n{elements_str}"}
                ]
            }
        ]
        
        response = self.model_client.request(messages)
        
        try:
            plan = json.loads(response.action)
            return ActionPlan(
                action=plan.get("action", ""),
                target=plan.get("target"),
                parameters=plan.get("parameters", {}),
                confidence=plan.get("confidence", 1.0),
                reasoning=plan.get("reasoning", "")
            )
        except json.JSONDecodeError:
            return ActionPlan(
                action="wait",
                reasoning=f"无法解析响应: {response.action[:100]}"
            )
```

---

### Task 4: 多Agent协作架构

**Files:**
- Create: `backend/app/core/agent/manager.py`
- Create: `backend/app/core/agent/executor.py`
- Create: `backend/app/core/agent/reflector.py`
- Create: `backend/app/core/agent/finder.py`
- Create: `backend/app/core/agent/engine.py`

- [ ] **Step 1: 创建Agent引擎（协调器�?*

```python
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import time

from ...model import ModelClient
from ..layers.perception import PerceptionLayer, PerceptionResult
from ..layers.decision import DecisionLayer, ActionPlan
from ..layers.action import ActionLayer, ActionResult
from ..layers.memory import MemoryLayer, MemoryItem
from ..layers.verification import VerificationLayer, VerificationResult
from ..layers.replay import ReplayLayer, StepLog
from ..adapters.base import BaseDeviceAdapter


@dataclass
class AgentConfig:
    max_steps: int = 100
    verification_enabled: bool = True
    reflection_enabled: bool = True
    memory_enabled: bool = True
    on_step_complete: Optional[Callable] = None
    on_task_complete: Optional[Callable] = None
    on_error: Optional[Callable] = None


@dataclass
class StepResult:
    step_index: int
    action_plan: ActionPlan
    action_result: ActionResult
    perception: PerceptionResult
    verification: Optional[VerificationResult] = None


class AgentEngine:
    def __init__(self, model_client: ModelClient, adapter: BaseDeviceAdapter, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.model_client = model_client
        
        self.perception = PerceptionLayer(adapter)
        self.decision = DecisionLayer(model_client)
        self.action = ActionLayer(adapter)
        self.memory = MemoryLayer()
        self.verification = VerificationLayer(model_client)
        self.replay = ReplayLayer()
        
        self._step_results: List[StepResult] = []
    
    async def execute_task(self, task: str, on_progress: Optional[Callable] = None) -> Dict[str, Any]:
        self._step_results = []
        history = []
        
        for step_index in range(self.config.max_steps):
            perception = self.perception.perceive(step_index)
            
            ui_elements = [
                {
                    "text": e.text,
                    "resource_id": e.resource_id,
                    "content_desc": e.content_desc,
                    "bbox_normalized": e.bbox_normalized,
                    "clickable": e.clickable,
                }
                for e in perception.ui_elements
            ]
            
            action_plan = self.decision.decide(task, perception.screenshot_base64, ui_elements, history)
            
            if action_plan.action in ["finish", "done", "end"]:
                break
            
            action_result = self.action.execute(
                action=action_plan.action,
                target=action_plan.target,
                parameters=action_plan.parameters
            )
            
            verification = None
            if self.config.verification_enabled and action_result.success:
                verification = self.verification.verify(
                    task=task,
                    steps=[{"action": action_plan.action, "target": action_plan.target}],
                    screenshot_base64=perception.screenshot_base64
                )
            
            step_result = StepResult(
                step_index=step_index,
                action_plan=action_plan,
                action_result=action_result,
                perception=perception,
                verification=verification
            )
            self._step_results.append(step_result)
            
            if on_progress:
                await on_progress(step_result)
            
            if self.config.memory_enabled:
                self.memory.add(MemoryItem(
                    timestamp=time.time(),
                    action=action_plan.action,
                    result=action_result.success,
                    screenshot_base64=perception.screenshot_base64,
                    reasoning=action_plan.reasoning
                ))
            
            history.append({
                "role": "assistant",
                "content": json.dumps({
                    "action": action_plan.action,
                    "target": action_plan.target,
                    "reasoning": action_plan.reasoning
                })
            })
            
            if not action_result.success:
                if self.config.reflection_enabled:
                    reflection = self._reflect_on_failure(action_plan, action_result, history)
                    if reflection.should_retry and reflection.retry_strategy:
                        action_plan = self._apply_retry_strategy(action_plan, reflection)
                        continue
                
                if self.config.on_error:
                    await self.config.on_error(step_result)
        
        return self._generate_final_report(task)
    
    def _reflect_on_failure(self, action_plan: ActionPlan, action_result: ActionResult, history: List[Dict]) -> ReflectionResult:
        from .reflector import ReflectorAgent
        reflector = ReflectorAgent(self.model_client)
        return reflector.reflect(
            failed_step={"action": action_plan.action, "target": action_plan.target},
            error=action_result.error or "Unknown error",
            history=history
        )
    
    def _generate_final_report(self, task: str) -> Dict[str, Any]:
        step_logs = [
            StepLog(
                step_id=s.step_index,
                action=s.action_plan.action,
                target=s.action_plan.target or "",
                timestamp=s.perception.timestamp,
                duration=s.action_result.duration,
                success=s.action_result.success,
                screenshot_path=s.perception.screenshot_path,
                error=s.action_result.error
            )
            for s in self._step_results
        ]
        
        report = self.replay.generate_report(task, step_logs, {
            "platform": self.perception.adapter.platform.value,
            "device_id": self.perception.adapter.device_id
        })
        
        return {
            "task": task,
            "passed": report.passed,
            "total_steps": report.total_steps,
            "passed_steps": report.passed_steps,
            "success_rate": report.success_rate,
            "duration": report.duration,
            "report_path": f"./reports/{report.generated_at}.html"
        }
```

---

### Task 5: 前端开�?
**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/TaskRunner.tsx`
- Create: `frontend/src/pages/DeviceManager.tsx`
- Create: `frontend/src/pages/ReportViewer.tsx`

- [ ] **Step 1: 创建API客户�?*

```typescript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface Task {
  task_id: string;
  task_name: string;
  task_type: string;
  platform: string;
  status: 'created' | 'executing' | 'completed' | 'failed' | 'stopped';
  created_at: string;
  updated_at: string;
}

interface Device {
  device_id: string;
  platform: 'android' | 'ios' | 'harmonyos';
  status: 'online' | 'offline' | 'busy';
  model?: string;
  os_version?: string;
}

interface Report {
  report_id: string;
  task_id: string;
  task_name: string;
  passed: boolean;
  success_rate: number;
  total_steps: number;
  passed_steps: number;
  duration: number;
  generated_at: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  async listDevices(): Promise<Device[]> {
    return this.request<Device[]>('/api/v1/devices/');
  }

  async createTask(task: {
    task_name: string;
    task_type: string;
    platform: string;
    devices: string[];
    steps: any[];
  }): Promise<{ task_id: string }> {
    return this.request('/api/v1/tasks/', {
      method: 'POST',
      body: JSON.stringify(task),
    });
  }

  async getTask(taskId: string): Promise<Task> {
    return this.request<Task>(`/api/v1/tasks/${taskId}`);
  }

  async executeTask(taskId: string): Promise<{ task_id: string; status: string }> {
    return this.request(`/api/v1/tasks/${taskId}/execute`, {
      method: 'POST',
    });
  }

  async stopTask(taskId: string): Promise<{ task_id: string; status: string }> {
    return this.request(`/api/v1/tasks/${taskId}/stop`, {
      method: 'POST',
    });
  }

  async listReports(): Promise<Report[]> {
    return this.request<Report[]>('/api/v1/reports/');
  }

  async getReport(reportId: string): Promise<Report> {
    return this.request<Report>(`/api/v1/reports/${reportId}`);
  }
}

export const apiClient = new ApiClient();
export type { Task, Device, Report };
```

- [ ] **Step 2: 创建任务执行页面**

```typescript
import React, { useState, useEffect, useCallback } from 'react';
import { apiClient, Task } from '../api/client';

interface TaskRunnerProps {
  taskId?: string;
}

interface StepProgress {
  step_index: number;
  action: string;
  target: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  screenshot?: string;
  error?: string;
}

export const TaskRunner: React.FC<TaskRunnerProps> = ({ taskId }) => {
  const [task, setTask] = useState<Task | null>(null);
  const [steps, setSteps] = useState<StepProgress[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isExecuting, setIsExecuting] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const connectWebSocket = () => {
      const socket = new WebSocket(`ws://localhost:8000/ws/${taskId}`);
      
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'task_update') {
          const { step_index, action, status, screenshot, error } = data;
          setSteps(prev => [...prev, { step_index, action, target: '', status, screenshot, error }]);
          setCurrentStep(step_index);
        }
      };

      socket.onclose = () => {
        setTimeout(connectWebSocket, 3000);
      };

      setWs(socket);
    };

    connectWebSocket();

    return () => {
      ws?.close();
    };
  }, [taskId]);

  const handleStart = async () => {
    if (!taskId) return;
    setIsExecuting(true);
    await apiClient.executeTask(taskId);
  };

  const handleStop = async () => {
    if (!taskId) return;
    setIsExecuting(false);
    await apiClient.stopTask(taskId);
  };

  return (
    <div className="task-runner">
      <div className="task-header">
        <h2>{task?.task_name || '任务执行'}</h2>
        <div className="task-actions">
          {!isExecuting ? (
            <button onClick={handleStart}>开始执�?/button>
          ) : (
            <button onClick={handleStop}>停止</button>
          )}
        </div>
      </div>

      <div className="task-content">
        <div className="steps-list">
          <h3>执行步骤</h3>
          {steps.map((step, index) => (
            <div key={index} className={`step-item ${step.status}`}>
              <span className="step-number">{step.step_index + 1}</span>
              <span className="step-action">{step.action}</span>
              <span className="step-target">{step.target}</span>
              <span className={`step-status status-${step.status}`}>
                {step.status === 'executing' ? '执行�?..' : step.status}
              </span>
            </div>
          ))}
        </div>

        <div className="screenshot-preview">
          {steps[currentStep]?.screenshot && (
            <img
              src={`data:image/png;base64,${steps[currentStep].screenshot}`}
              alt="当前截图"
            />
          )}
        </div>
      </div>
    </div>
  );
};
```

---

## 四、开发优先级与里程碑

### Phase 1: MVP (2�?
**目标:** 核心功能可用
- [ ] FastAPI后台基础 + REST API
- [ ] Android设备适配�?- [ ] 6层Agent核心（感知→决策→行动）
- [ ] 简单任务执行功�?- [ ] 基础前端Dashboard

### Phase 2: 完整功能 (2�?
**目标:** 所有平台支持，完整Agent能力
- [ ] iOS/HarmonyOS适配�?- [ ] 多Agent协作（Manager+Executor�?- [ ] 记忆�?+ 验证�?- [ ] 报告生成
- [ ] WebSocket实时通信
- [ ] 设备管理页面

### Phase 3: 生产就绪 (1�?
**目标:** 测试完善，可部署
- [ ] 单元测试 + 集成测试
- [ ] Docker部署
- [ ] 错误处理优化
- [ ] 性能优化
- [ ] 文档完善

---

## 五、模型服务层（LLM/VLM�?
### 5.1 模型配置架构

```
┌────────────────────────────────────────────────────────────────────�?�?                       模型服务�?(Model Service)                    �?├────────────────────────────────────────────────────────────────────�?�?                                                                    �?�? ┌──────────────────────────────────────────────────────────────�? �?�? �?                   ModelGateway (模型网关)                      �? �?�? �? - 统一接口封装                                                  �? �?�? �? - 模型路由（自�?手动�?                                        �? �?�? �? - 熔断�?限流                                                  �? �?�? �? - 密钥管理                                                    �? �?�? └──────────────────────────────────────────────────────────────�? �?�?                             �?                                    �?�?        ┌────────────────────┼────────────────────�?               �?�?        �?                   �?                   �?               �?�? ┌─────────────────────────────────────────────────────────────�? �?�? �?                  支持的模型类�?                              �? �?�? ├───────────────┬───────────────┬───────────────┬──────────────�? �?�? �? AutoPhone      �?  GLM-4V     �?  Qwen-VL    �? GPT-4V     �? �?�? �? Phone-9B     �?  (智谱)     �?  (通义)     �? (OpenAI)   �? �?�? �? 【推荐�?    �?             �?             �?             �? �?�? └───────────────┴───────────────┴───────────────┴──────────────�? �?�?                                                                    �?└─────────────────────────────────────────────────────────────────────�?```

### 5.2 模型配置接口

```python
# backend/app/core/model/config.py
from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum


class ModelProvider(Enum):
    AutoPhone = "AutoPhone"
    ZHIPU = "zhipu"
    QWEN = "qwen"
    OPENAI = "openai"
    CUSTOM = "custom"


class ModelConfig(BaseModel):
    provider: ModelProvider = ModelProvider.AutoPhone
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "AutoPhone-phone-9b"
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    timeout_ms: int = 120000
    
    class Config:
        extra = "allow"


class ModelCapability(BaseModel):
    vision: bool = True
    function_calling: bool = False
    streaming: bool = True
    max_image_size: Optional[int] = None


class ModelInfo(BaseModel):
    name: str
    provider: ModelProvider
    capabilities: ModelCapability
    recommended_for: list[str] = []


DEFAULT_MODELS = {
    "AutoPhone-phone-9b": ModelInfo(
        name="AutoPhone Phone 9B",
        provider=ModelProvider.AutoPhone,
        capabilities=ModelCapability(vision=True, streaming=True),
        recommended_for=["手机UI理解", "多步骤任�?, "中文交互"]
    ),
    "glm-4v": ModelInfo(
        name="GLM-4V",
        provider=ModelProvider.ZHIPU,
        capabilities=ModelCapability(vision=True, function_calling=True, streaming=True),
        recommended_for=["视觉理解", "通用任务"]
    ),
    "qwen-vl-max": ModelInfo(
        name="Qwen-VL Max",
        provider=ModelProvider.QWEN,
        capabilities=ModelCapability(vision=True, function_calling=True, streaming=True, max_image_size=4096),
        recommended_for=["高精度视�?, "复杂场景"]
    ),
    "gpt-4o": ModelInfo(
        name="GPT-4o",
        provider=ModelProvider.OPENAI,
        capabilities=ModelCapability(vision=True, function_calling=True, streaming=True),
        recommended_for=["通用场景", "高可靠�?]
    ),
}
```

### 5.3 模型客户端封�?
```python
# backend/app/core/model/client.py
import json
import time
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

import httpx

from .config import ModelConfig, ModelCapability


@dataclass
class ModelResponse:
    thinking: str
    action: str
    raw_content: str
    time_to_first_token: Optional[float] = None
    total_time: Optional[float] = None


class ModelClient:
    """统一模型客户端，支持多种LLM/VLM后端"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.capabilities = self._detect_capabilities()
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=httpx.Timeout(config.timeout_ms / 1000),
        )
    
    async def request(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = True,
    ) -> ModelResponse:
        """发送请求到模型"""
        start_time = time.time()
        time_to_first = None
        
        async with self._client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "stream": stream,
            }
        ) as response:
            content = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("choices"):
                        delta = data["choices"][0].get("delta", {})
                        if delta.get("content"):
                            if time_to_first is None:
                                time_to_first = time.time() - start_time
                            content += delta["content"]
                
                elif line == "data: [DONE]":
                    break
            
            total_time = time.time() - start_time
            thinking, action = self._parse_response(content)
            
            return ModelResponse(
                thinking=thinking,
                action=action,
                raw_content=content,
                time_to_first_token=time_to_first,
                total_time=total_time,
            )
    
    def _parse_response(self, content: str) -> tuple[str, str]:
        """解析模型响应，提取thinking和action"""
        # JSON格式
        if "<json_answer>" in content:
            parts = content.split("<json_answer>")
            thinking = parts[0].replace("<json_think>", "").replace("</json_think>", "").strip()
            action = parts[1].replace("</json_answer>", "").strip() if len(parts) > 1 else ""
            return thinking, action
        
        # Pseudo-code格式
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            return parts[0].strip(), "finish(message=" + parts[1]
        
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            return parts[0].strip(), "do(action=" + parts[1]
        
        return "", content
    
    def _detect_capabilities(self) -> ModelCapability:
        """检测模型能�?""
        return ModelCapability(
            vision=True,
            streaming=True,
        )
    
    async def close(self):
        await self._client.aclose()
```

### 5.4 模型服务API

```python
# backend/app/api/v1/models.py
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.core.model.config import ModelConfig, DEFAULT_MODELS, ModelProvider
from app.core.model.client import ModelClient

router = APIRouter()


class ModelListResponse(BaseModel):
    models: List[dict]


class ModelTestRequest(BaseModel):
    model_name: str
    test_message: str = "请描述当前屏幕内�?


class ModelTestResponse(BaseModel):
    success: bool
    response_time: float
    thinking: Optional[str] = None
    action: Optional[str] = None
    error: Optional[str] = None


@router.get("/", response_model=ModelListResponse)
async def list_models():
    """列出所有可用模�?""
    models = []
    for name, info in DEFAULT_MODELS.items():
        models.append({
            "name": name,
            "provider": info.provider.value,
            "capabilities": {
                "vision": info.capabilities.vision,
                "function_calling": info.capabilities.function_calling,
                "streaming": info.capabilities.streaming,
            },
            "recommended_for": info.recommended_for,
        })
    return ModelListResponse(models=models)


@router.post("/test", response_model=ModelTestResponse)
async def test_model(request: ModelTestRequest):
    """测试模型连接"""
    import time
    start = time.time()
    
    try:
        config = ModelConfig(model_name=request.model_name)
        client = ModelClient(config)
        
        messages = [
            {"role": "user", "content": request.test_message}
        ]
        
        response = await client.request(messages, stream=False)
        await client.close()
        
        return ModelTestResponse(
            success=True,
            response_time=time.time() - start,
            thinking=response.thinking,
            action=response.action,
        )
    except Exception as e:
        return ModelTestResponse(
            success=False,
            response_time=time.time() - start,
            error=str(e),
        )


@router.get("/config")
async def get_model_config():
    """获取当前模型配置"""
    return {
        "default_model": os.getenv("DEFAULT_MODEL", "AutoPhone-phone-9b"),
        "api_base": os.getenv("MODEL_API_URL", "http://localhost:8000/v1"),
    }
```

---

## 六、技术选型理由

| 组件 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | 异步高性能，自动OpenAPI文档，类型安�?|
| 前端框架 | React 18 | 生态丰富，Hooks完美配合状态管�?|
| 状态管�?| Zustand | 轻量简洁，TypeScript支持�?|
| UI组件 | TailwindCSS + HeadlessUI | 定制灵活，无样式冲突 |
| 实时通信 | WebSocket | 实时任务进度推送，低延�?|
| 数据�?| SQLite/PostgreSQL | 开发简单，生产可选PG |
| 部署 | Docker + docker-compose | 环境一致，一键部�?|
| **模型后端** | **OpenAI Compatible API** | **兼容所有主流LLM/VLM** |
| **推荐模型** | **AutoPhone Phone-9B** | **专为手机UI任务优化** |

---

## 七、环境变量配�?
```bash
# .env 示例
# 模型配置
MODEL_API_URL=http://localhost:8000/v1
MODEL_NAME=AutoPhone-phone-9b
API_KEY=EMPTY

# 可选：其他模型
# ZHIPU_API_KEY=your-key-here
# QWEN_API_KEY=your-key-here

# 服务器配�?HOST=0.0.0.0
PORT=8000
DEBUG=false

# 数据�?DATABASE_URL=sqlite:///./AutoPhone.db

# 前端
VITE_API_BASE=http://localhost:8000
```

---

## 八、前端详细设�?
详细设计参见：[2026-05-19-frontend-design.md](./2026-05-19-frontend-design.md)

### 8.1 页面结构

| 页面 | 路由 | 说明 | 优先�?|
|------|------|------|--------|
| 仪表�?| `/dashboard` | 统计数据、趋势图表、最近任�?| P0 |
| 项目管理 | `/projects` | 管理测试项目和应用配�?| P1 |
| APK管理 | `/apk` | 上传和管理测试APK | P1 |
| **Agent** | `/agent` | **核心脚本生成页面** | **P0** |
| 脚本管理 | `/scripts` | AI生成和外部导入脚�?| P1 |
| 设备管理 | `/devices` | Android/iOS/鸿蒙设备 | P0 |
| 任务管理 | `/tasks` | 任务创建、运行、监�?| P0 |
| 模型配置 | `/settings` | LLM/VLM模型配置和测�?| P0 |

### 8.2 核心页面 - Agent 脚本生成

```
┌─────────────────────────────────────────────────────────────────────�?�? Agent 脚本生成                                                      �?├─────────────────────────────────────────────────────────────────────�?�?                                                                    �?�? ┌──────────────────────────────�? ┌──────────────────────────────┐│
�? �?     任务配置                 �? �?     实时预览                 ││
�? �? - 项目选择                   �? �? - 设备屏幕预览               ││
�? �? - 目标平台(多�?             �? �? - 执行日志�?                ││
�? �? - 模型选择                   �? �? - 当前步骤指示               ││
�? �? - 任务描述                   �? �?                             ││
�? └──────────────────────────────�? └──────────────────────────────┘│
�?                                                                    �?�? ┌────────────────────────────────────────────────────────────────�?�?�? �? 生成的脚�?(多平�?                                             �?�?�? �? - Android (Python/Appium)                                      �?�?�? �? - iOS (Swift/XCTest)                                          �?�?�? �? - HarmonyOS (待定)                                             �?�?�? └────────────────────────────────────────────────────────────────�?�?└─────────────────────────────────────────────────────────────────────�?```

### 8.3 技术栈详情

| 层级 | 技�?| 版本 |
|------|------|------|
| 框架 | React | 18.2+ |
| 语言 | TypeScript | 5.3+ |
| 构建 | Vite | 5.1+ |
| 路由 | React Router | v6 |
| 状�?| Zustand | 4.5+ |
| 样式 | TailwindCSS | 3.4+ |
| 图表 | Recharts | 2.12+ |
| 动画 | Framer Motion | 11+ |
| HTTP | Axios + React Query | - |

---

**Plan saved to:** `docs/superpowers/plans/2026-05-19-AutoPhone-agent-upgrade.md`

