# LOCKIN Agent Platform - 全功能实现设计文�?
**项目名称**: LOCKIN Agent Platform  
**版本**: 1.0.0  
**日期**: 2026-05-19  
**状�?*: 设计�?
---

## 1. 项目概述

### 1.1 项目背景

LOCKIN Agent Platform 是一个移动设备自动化测试管理平台，支�?Android、iOS、HarmonyOS 等多平台设备的自动化测试脚本管理、任务执行和结果分析�?
### 1.2 项目目标

实现完整的全栈功能，包括�?- 设备管理（USB、ADB TCPIP 连接�?- 脚本管理（AI 生成、手动创建）
- 任务管理（执行、监控、日志）
- APK 管理（上传、下载、删除）
- 项目管理（项目维度的脚本和任务管理）
- 报表生成（测试报告）
- 系统设置（配置管理）

### 1.3 技术栈

**前端**:
- React 18 + TypeScript
- Vite (构建工具)
- Tailwind CSS (样式)
- Zustand (状态管�?
- React Router (路由)
- Recharts (图表)
- Axios (HTTP 客户�?

**后端**:
- Python 3.10+
- FastAPI (Web 框架)
- Uvicorn (ASGI 服务�?
- SQLAlchemy (ORM)
- SQLite (数据�?
- ADB (Android 设备连接)
- HDC (HarmonyOS 设备连接)

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────�?    ┌─────────────�?    ┌─────────────�?�?  前端      �?←→  �?  后端 API   �?←→  �?  数据�?    �?�? React      �?    �? FastAPI    �?    �? SQLite     �?└─────────────�?    └─────────────�?    └─────────────�?                           �?                    ┌─────────────�?                    �? 设备适配�? �?                    �?ADB/HDC/iOS �?                    └─────────────�?```

### 2.2 目录结构

```
Open-AutoPhone/
├── frontend/                    # 前端应用
�?  ├── src/
�?  �?  ├── components/          # 可复用组�?�?  �?  ├── pages/              # 页面组件
�?  �?  �?  ├── Agent/
�?  �?  �?  ├── Apk/
�?  �?  �?  ├── Dashboard/
�?  �?  �?  ├── Device/
�?  �?  �?  ├── Project/
�?  �?  �?  ├── Script/
�?  �?  �?  ├── Settings/
�?  �?  �?  └── Task/
�?  �?  ├── services/           # API 服务
�?  �?  ├── stores/             # 状态管�?�?  �?  └── styles/             # 全局样式
�?  └── package.json
�?├── backend/                    # 后端应用
�?  ├── app/
�?  �?  ├── api/v1/            # API 路由
�?  �?  ├── core/              # 核心模块
�?  �?  ├── schemas/           # Pydantic 模型
�?  �?  ├── services/         # 业务逻辑
�?  �?  └── main.py           # 应用入口
�?  └── requirements.txt
�?└── docs/                      # 文档
```

---

## 3. 模块详细设计

### 3.1 设备管理模块

#### 3.1.1 功能列表

1. **设备发现**
   - USB 连接设备自动发现
   - ADB TCPIP 连接（`adb connect <ip>:<port>`�?   - HDC 连接（HarmonyOS�?   - WebDriverAgent 连接（iOS�?   - 手动添加设备

2. **设备操作**
   - 连接/断开设备
   - 获取设备信息（型号、系统版本、分辨率�?   - 实时截图
   - 应用列表查询
   - 应用启动

3. **设备监控**
   - 连接状态实时更�?   - 设备忙碌状态检�?   - 自动刷新设备列表

#### 3.1.2 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/devices` | 获取设备列表 |
| GET | `/api/v1/devices/{device_id}` | 获取设备详情 |
| POST | `/api/v1/devices/{device_id}/connect` | 连接设备 |
| POST | `/api/v1/devices/{device_id}/disconnect` | 断开设备 |
| GET | `/api/v1/devices/{device_id}/screenshot` | 获取截图 |
| GET | `/api/v1/devices/{device_id}/apps` | 获取应用列表 |
| POST | `/api/v1/devices/{device_id}/launch/{app_name}` | 启动应用 |
| POST | `/api/v1/devices/discover` | 触发设备发现 |
| POST | `/api/v1/devices/connect-tcpip` | TCPIP 连接 |

#### 3.1.3 数据模型

```python
class DeviceInfo:
    device_id: str          # 设备唯一标识
    name: str               # 设备名称
    platform: PlatformType   # android/ios/harmonyos
    status: DeviceStatus     # connected/disconnected/busy
    model: Optional[str]     # 设备型号
    manufacturer: Optional[str]  # 制造商
    os_version: Optional[str]     # 系统版本
    screen_width: Optional[int]    # 屏幕宽度
    screen_height: Optional[int]  # 屏幕高度
    ip_address: Optional[str]     # IP地址（TCPIP连接�?    created_at: str          # 创建时间
    updated_at: str          # 更新时间
```

---

### 3.2 脚本管理模块

#### 3.2.1 功能列表

1. **脚本 CRUD**
   - 创建脚本（手动、AI 生成�?   - 查看脚本列表和详�?   - 编辑脚本内容
   - 删除脚本
   - 脚本版本管理

2. **脚本生成**
   - AI 生成脚本（对接外�?AI 模型�?   - 任务描述转脚�?   - 跨平台脚本派�?
3. **脚本执行**
   - 选择设备执行
   - 实时执行状�?   - 执行结果记录

#### 3.2.2 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/scripts` | 获取脚本列表 |
| GET | `/api/v1/scripts/{script_id}` | 获取脚本详情 |
| POST | `/api/v1/scripts` | 创建脚本 |
| PUT | `/api/v1/scripts/{script_id}` | 更新脚本 |
| DELETE | `/api/v1/scripts/{script_id}` | 删除脚本 |
| POST | `/api/v1/scripts/generate` | AI 生成脚本 |
| POST | `/api/v1/scripts/{script_id}/execute` | 执行脚本 |
| GET | `/api/v1/scripts/{script_id}/versions` | 获取版本历史 |

#### 3.2.3 数据模型

```python
class ScriptResponse:
    script_id: str
    name: str
    content: str
    script_type: ScriptType   # ai_generated/imported/manual
    platform: PlatformType
    project_id: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: str
    version: int
```

---

### 3.3 任务管理模块

#### 3.3.1 功能列表

1. **任务管理**
   - 创建任务（关联脚本和设备�?   - 查看任务列表
   - 任务详情（进度、结果、日志）
   - 删除任务

2. **任务执行**
   - 立即执行
   - 定时执行（可选）
   - 停止执行
   - 实时日志�?
3. **任务监控**
   - 进度实时更新
   - 状态变化通知
   - 执行历史记录

#### 3.3.2 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/tasks` | 获取任务列表 |
| GET | `/api/v1/tasks/{task_id}` | 获取任务详情 |
| POST | `/api/v1/tasks` | 创建任务 |
| POST | `/api/v1/tasks/{task_id}/execute` | 执行任务 |
| POST | `/api/v1/tasks/{task_id}/stop` | 停止任务 |
| DELETE | `/api/v1/tasks/{task_id}` | 删除任务 |
| GET | `/api/v1/tasks/{task_id}/logs` | 获取任务日志 |
| GET | `/api/v1/ws/tasks/{task_id}/logs` | WebSocket 日志�?|

#### 3.3.3 数据模型

```python
class TaskResponse:
    task_id: str
    name: str
    description: Optional[str]
    script_id: str
    device_id: str
    status: TaskStatus  # pending/running/completed/failed/stopped
    progress: int       # 0-100
    result: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
```

---

### 3.4 APK 管理模块

#### 3.4.1 功能列表

1. **APK 上传**
   - 文件上传
   - 元数据提取（包名、版本、大小）
   - 文件存储

2. **APK 管理**
   - APK 列表查看
   - APK 详情
   - APK 下载
   - APK 删除

3. **APK 安装**
   - 一键安装到设备（可选）

#### 3.4.2 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/apks` | 获取 APK 列表 |
| GET | `/api/v1/apks/{apk_id}` | 获取 APK 详情 |
| POST | `/api/v1/apks/upload` | 上传 APK |
| DELETE | `/api/v1/apks/{apk_id}` | 删除 APK |
| GET | `/api/v1/apks/{apk_id}/download` | 下载 APK |
| POST | `/api/v1/apks/{apk_id}/install/{device_id}` | 安装到设�?|

#### 3.4.3 数据模型

```python
class ApkResponse:
    apk_id: str
    name: str
    package_name: str
    version: str
    version_code: int
    size: int           # bytes
    file_path: str       # 存储路径
    platform: PlatformType
    uploaded_at: str
    md5: str            # 文件校验
```

#### 3.4.4 文件存储

```
backend/
├── uploads/
�?  └── apks/
�?      └── {apk_id}/
�?          └── {filename}.apk
```

---

### 3.5 项目管理模块

#### 3.5.1 功能列表

1. **项目管理**
   - 创建项目
   - 查看项目列表
   - 编辑项目
   - 删除项目

2. **项目关联**
   - 关联脚本
   - 关联任务
   - 关联设备

3. **项目统计**
   - 脚本数量
   - 任务数量
   - 通过率统�?
#### 3.5.2 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/projects` | 获取项目列表 |
| GET | `/api/v1/projects/{project_id}` | 获取项目详情 |
| POST | `/api/v1/projects` | 创建项目 |
| PUT | `/api/v1/projects/{project_id}` | 更新项目 |
| DELETE | `/api/v1/projects/{project_id}` | 删除项目 |
| GET | `/api/v1/projects/{project_id}/scripts` | 获取项目脚本 |
| GET | `/api/v1/projects/{project_id}/tasks` | 获取项目任务 |
| GET | `/api/v1/projects/{project_id}/stats` | 获取项目统计 |

#### 3.5.3 数据模型

```python
class ProjectResponse:
    project_id: str
    name: str
    description: Optional[str]
    script_count: int
    task_count: int
    device_count: int
    created_at: str
    updated_at: str
    last_run: Optional[str]
```

---

### 3.6 报表模块

#### 3.6.1 功能列表

1. **报表生成**
   - 基于任务结果生成
   - 支持多种格式（HTML、PDF、JSON�?
2. **报表内容**
   - 测试概要
   - 通过率统�?   - 执行详情
   - 错误日志
   - 截图附件

#### 3.6.2 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/reports` | 获取报表列表 |
| GET | `/api/v1/reports/{report_id}` | 获取报表详情 |
| POST | `/api/v1/reports/generate/{task_id}` | 生成报表 |
| GET | `/api/v1/reports/{report_id}/download` | 下载报表 |

#### 3.6.3 数据模型

```python
class ReportResponse:
    report_id: str
    task_id: str
    name: str
    format: ReportFormat  # html/pdf/json
    file_path: Optional[str]
    summary: ReportSummary
    created_at: str

class ReportSummary:
    total_cases: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    duration: str
```

---

### 3.7 设置模块

#### 3.7.1 功能列表

1. **系统设置**
   - AI 模型配置
   - 默认参数配置
   - 超时设置

2. **用户设置**
   - 界面偏好
   - 通知设置

#### 3.7.2 API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/settings` | 获取设置 |
| PUT | `/api/v1/settings` | 更新设置 |
| GET | `/api/v1/settings/ai-models` | 获取 AI 模型列表 |
| POST | `/api/v1/settings/test-connection` | 测试连接 |

#### 3.7.3 数据模型

```python
class SettingsResponse:
    ai_model_url: str
    ai_model_name: str
    ai_api_key: Optional[str]  # 脱敏显示
    max_execution_time: int    # �?    screenshot_quality: int    # 1-100
    notification_enabled: bool
    language: str              # cn/en
    theme: str                 # dark/light
```

---

## 4. 实施计划

### 4.1 第一阶段：基础管理模块（预�?1-2 天）

#### Day 1
- [ ] APK 管理后端 API 实现
- [ ] APK 管理前端页面实现
- [ ] 项目管理后端 API 实现
- [ ] 项目管理前端页面实现

#### Day 2
- [ ] 设置后端 API 实现
- [ ] 设置前端页面实现
- [ ] 基础测试和修�?
### 4.2 第二阶段：核心功能完善（预计 2-3 天）

#### Day 3
- [ ] 设备发现增强（TCPIP 连接�?- [ ] 设备状态实时更�?- [ ] 截图功能优化

#### Day 4
- [ ] 脚本生成 AI 模型对接
- [ ] 脚本执行优化

#### Day 5
- [ ] 任务执行完善
- [ ] WebSocket 日志推�?- [ ] 实时进度更新

### 4.3 第三阶段：高级功能（预计 1-2 天）

#### Day 6
- [ ] 报表生成后端实现
- [ ] 报表前端展示
- [ ] 多格式导�?
#### Day 7
- [ ] 前端错误处理优化
- [ ] 加载状态优�?- [ ] 单元测试
- [ ] 集成测试

---

## 5. 数据库设�?
### 5.1 ER �?
```
Project 1───N Script
Project 1───N Task
Script 1───N Task
Task 1───1 Report
Device 1───N Task
Device 1───N Apk (optional)
```

### 5.2 表结�?
#### projects
| 字段 | 类型 | 说明 |
|------|------|------|
| project_id | VARCHAR(50) PK | 项目ID |
| name | VARCHAR(200) | 项目名称 |
| description | TEXT | 项目描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

#### scripts
| 字段 | 类型 | 说明 |
|------|------|------|
| script_id | VARCHAR(50) PK | 脚本ID |
| project_id | VARCHAR(50) FK | 所属项�?|
| name | VARCHAR(200) | 脚本名称 |
| content | TEXT | 脚本内容 |
| script_type | VARCHAR(20) | 类型 |
| platform | VARCHAR(20) | 平台 |
| description | TEXT | 描述 |
| version | INT | 版本�?|
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

#### tasks
| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | VARCHAR(50) PK | 任务ID |
| script_id | VARCHAR(50) FK | 关联脚本 |
| device_id | VARCHAR(100) | 执行设备 |
| name | VARCHAR(200) | 任务名称 |
| status | VARCHAR(20) | 状�?|
| progress | INT | 进度 |
| result | TEXT | 结果 |
| error_message | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |
| started_at | DATETIME | 开始时�?|
| completed_at | DATETIME | 完成时间 |

#### reports
| 字段 | 类型 | 说明 |
|------|------|------|
| report_id | VARCHAR(50) PK | 报表ID |
| task_id | VARCHAR(50) FK | 关联任务 |
| name | VARCHAR(200) | 报表名称 |
| format | VARCHAR(20) | 格式 |
| file_path | VARCHAR(500) | 文件路径 |
| summary | JSON | 摘要数据 |
| created_at | DATETIME | 创建时间 |

#### apks
| 字段 | 类型 | 说明 |
|------|------|------|
| apk_id | VARCHAR(50) PK | APK ID |
| name | VARCHAR(200) | APK 名称 |
| package_name | VARCHAR(200) | 包名 |
| version | VARCHAR(50) | 版本 |
| version_code | INT | 版本�?|
| size | BIGINT | 文件大小 |
| file_path | VARCHAR(500) | 存储路径 |
| md5 | VARCHAR(32) | MD5 校验 |
| uploaded_at | DATETIME | 上传时间 |

---

## 6. 前端页面设计

### 6.1 路由结构

```
/                     �?Dashboard
/devices             �?DevicePage
/scripts             �?ScriptPage
/tasks               �?TaskPage
/projects            �?ProjectPage
/apks               �?ApkPage
/reports             �?ReportPage (可�?
/settings           �?SettingsPage
```

### 6.2 页面组件

每个页面应包含：
- Header（标�?+ 操作按钮�?- 列表/网格视图
- 空状态提�?- 加载状�?- 错误提示
- 分页（列表页�?
---

## 7. 安全考虑

### 7.1 API 安全
- 请求超时设置
- 错误日志记录
- 输入验证

### 7.2 文件上传安全
- 文件类型验证（仅允许 .apk�?- 文件大小限制
- MD5 校验

### 7.3 敏感信息
- API Key 脱敏
- 环境变量配置
- 不在前端暴露密钥

---

## 8. 性能优化

### 8.1 前端
- 组件懒加�?- 状态管理优�?- API 请求缓存
- 图片压缩

### 8.2 后端
- 数据库索�?- 分页查询
- 异步任务队列
- 连接池复�?
---

## 9. 测试计划

### 9.1 单元测试
- API 接口测试
- 服务层测�?- 工具函数测试

### 9.2 集成测试
- 前端 API 对接测试
- 设备连接测试
- 端到端流程测�?
### 9.3 手动测试
- 各模块功能测�?- 边界条件测试
- 异常情况测试

---

## 10. 文档

- API 接口文档（Swagger/OpenAPI�?- 用户使用手册
- 部署文档
- README.md

---

**下一�?*:
1. 详细设计评审
2. 实施计划确认
3. 开始第一阶段实现

---

*文档版本: 1.0.0*  
*最后更�? 2026-05-19*

