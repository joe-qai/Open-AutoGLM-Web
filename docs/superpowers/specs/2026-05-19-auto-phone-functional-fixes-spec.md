# AutoPhone 功能修复与增强 - 需求规格说明

**项目名称**: AutoPhone (Phone Agent)  
**版本**: 1.0.0  
**日期**: 2026-05-19  
**状态**: 设计中  

---

## 1. 需求概述

### 1.1 需求来源
根据 `questions.txt` 中的14个功能需求，整理为以下核心模块的修复与增强：

| 序号 | 需求描述 | 优先级 | 关联模块 |
|------|----------|--------|----------|
| 1 | 脚本管理 - 上传本地Python脚本无效 | 高 | 脚本管理 |
| 2 | 任务管理 - 缺少新增任务入口 | 高 | 任务管理 |
| 3 | 任务创建 - 需要选择脚本、APK、设备 | 高 | 任务管理 |
| 4 | 报告管理 - 新增菜单及HTML下载功能 | 高 | 报告管理 |
| 5 | 日志模块 - API执行记录跟踪可追溯 | 中 | 日志管理 |
| 6 | 脚本编辑器 - iOS/HarmonyOS语法高亮 | 中 | Agent页面 |
| 7 | 任务列表 - 显示优化（名称、状态、设备、进度） | 高 | 任务管理 |
| 8 | 报告列表 - 空白问题修复 | 高 | 报告管理 |
| 9 | 脚本执行器 - 本地上传脚本真机执行 | 高 | 脚本管理 |
| 10 | 仪表盘 - 设备数量统计去重 | 中 | 仪表盘 |
| 11 | 仪表盘 - 任务跳转功能 | 中 | 仪表盘 |
| 12 | APK管理 - 显示原始文件名、版本号、包名 | 中 | APK管理 |
| 13 | Agent脚本 - iOS/HarmonyOS语法高亮 | 中 | Agent页面 |
| 14 | 脚本管理 - 本地脚本支持执行、编辑、下载、删除 | 高 | 脚本管理 |

### 1.2 技术栈
**前端**: React 18 + TypeScript + Vite + Tailwind CSS + Zustand + React Router  
**后端**: Python 3.10+ + FastAPI + SQLAlchemy + SQLite  

---

## 2. 模块详细设计

### 2.1 脚本管理模块

#### 2.1.1 功能需求

| 功能点 | 描述 | 需求来源 |
|--------|------|----------|
| 脚本上传 | 支持本地上传Python脚本，区分agent生成和本地上传 | 需求1、14 |
| 脚本执行 | 本地脚本支持真机执行 | 需求9、14 |
| 脚本编辑 | 支持编辑脚本内容 | 需求14 |
| 脚本下载 | 支持下载脚本文件 | 需求14 |
| 脚本删除 | 支持删除脚本 | 需求14 |
| 脚本标识 | 脚本列表显示agent/local标签 | 需求3 |

#### 2.1.2 API接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/scripts` | 获取脚本列表 |
| POST | `/api/v1/scripts/upload` | 上传本地脚本（multipart/form-data） |
| POST | `/api/v1/scripts/{script_id}/execute` | 执行脚本 |
| PUT | `/api/v1/scripts/{script_id}` | 更新脚本 |
| GET | `/api/v1/scripts/{script_id}/download` | 下载脚本 |
| DELETE | `/api/v1/scripts/{script_id}` | 删除脚本 |

#### 2.1.3 数据模型

```python
class ScriptResponse:
    script_id: str
    name: str
    content: str
    script_type: str  # agent/local
    platform: str     # android/ios/harmonyos
    description: Optional[str]
    created_at: str
    updated_at: str
```

---

### 2.2 任务管理模块

#### 2.2.1 功能需求

| 功能点 | 描述 | 需求来源 |
|--------|------|----------|
| 新增任务 | 添加创建任务入口 | 需求2 |
| 任务配置 | 选择脚本（带agent/local标签）、APK（非必填）、设备 | 需求3 |
| 任务列表优化 | 显示脚本名称+icon、中文状态、设备列表（可展开/收起）、进度百分比 | 需求7 |
| 任务操作 | 支持中止、删除任务 | 需求7 |

#### 2.2.2 API接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/tasks` | 获取任务列表 |
| POST | `/api/v1/tasks` | 创建任务 |
| POST | `/api/v1/tasks/{task_id}/stop` | 中止任务 |
| DELETE | `/api/v1/tasks/{task_id}` | 删除任务 |

#### 2.2.3 数据模型

```python
class TaskResponse:
    task_id: str
    name: str
    script_id: str
    script_name: str
    script_type: str  # agent/local
    apk_id: Optional[str]
    device_ids: List[str]
    status: str       # pending/running/completed/failed/stopped
    progress: int     # 0-100
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
```

---

### 2.3 报告管理模块

#### 2.3.1 功能需求

| 功能点 | 描述 | 需求来源 |
|--------|------|----------|
| 报告列表 | 显示报告名称、终端系统、执行时长、执行状态、创建时间 | 需求4、8 |
| 报告下载 | 支持HTML格式下载，图片转base64内嵌 | 需求4 |
| 报告删除 | 支持删除报告 | 需求4 |
| 列表修复 | 修复空白列表问题 | 需求8 |

#### 2.3.2 API接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/reports` | 获取报告列表 |
| GET | `/api/v1/reports/{report_id}/download` | 下载HTML报告 |
| DELETE | `/api/v1/reports/{report_id}` | 删除报告 |

#### 2.3.3 数据模型

```python
class ReportResponse:
    report_id: str
    name: str
    task_name: str
    platform: str           # android/ios/harmonyos
    duration: str           # 执行时长
    status: str             # success/failed
    created_at: str
```

---

### 2.4 日志模块

#### 2.4.1 功能需求

| 功能点 | 描述 | 需求来源 |
|--------|------|----------|
| API日志 | 记录所有API请求和响应 | 需求5 |
| 执行日志 | 记录脚本执行过程 | 需求5 |
| 日志查询 | 支持按时间、级别、模块筛选 | 需求5 |
| 日志追溯 | 支持查看完整执行链路 | 需求5 |

#### 2.4.2 API接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/logs` | 查询日志列表 |
| GET | `/api/v1/logs/{log_id}` | 获取日志详情 |
| GET | `/api/v1/logs/summary` | 获取日志统计摘要 |

#### 2.4.3 数据模型

```python
class LogEntry:
    log_id: str
    level: str          # info/warning/error
    type: str           # api/execution/system
    endpoint: Optional[str]
    method: Optional[str]
    status_code: Optional[int]
    duration: Optional[float]  # ms
    message: str
    created_at: str
```

---

### 2.5 脚本编辑器模块

#### 2.5.1 功能需求

| 功能点 | 描述 | 需求来源 |
|--------|------|----------|
| 语法高亮 | iOS和HarmonyOS脚本支持语法高亮 | 需求6、13 |
| 平台区分 | 根据平台切换不同高亮样式 | 需求6、13 |
| 颜色优化 | 颜色不能太亮，保持可读性 | 需求6 |

#### 2.5.2 技术方案

- 使用 `react-syntax-highlighter` 库
- Android: Python语法高亮
- iOS: Swift语法高亮
- HarmonyOS: Java语法高亮

---

### 2.6 仪表盘模块

#### 2.6.1 功能需求

| 功能点 | 描述 | 需求来源 |
|--------|------|----------|
| 设备去重 | USB和WiFi连接同一设备需去重统计 | 需求10 |
| 任务跳转 | 点击"查看全部"跳转任务管理页 | 需求11 |

---

### 2.7 APK管理模块

#### 2.7.1 功能需求

| 功能点 | 描述 | 需求来源 |
|--------|------|----------|
| 文件名显示 | 显示原始上传文件名 | 需求12 |
| 版本信息 | 显示版本号、包名 | 需求12 |
| 移除安装 | 移除设备选择及安装操作 | 需求12 |

---

## 3. 实施计划

### 3.1 阶段一：核心功能修复（高优先级）

| 任务 | 预估时间 | 描述 |
|------|----------|------|
| 脚本上传修复 | 2h | 修复脚本上传功能，支持FormData |
| 任务创建入口 | 2h | 添加任务创建入口和表单 |
| 报告列表修复 | 2h | 修复报告空白列表，添加必要字段 |
| 脚本执行器修复 | 3h | 实现本地脚本真机执行 |

### 3.2 阶段二：功能增强（中优先级）

| 任务 | 预估时间 | 描述 |
|------|----------|------|
| 日志模块开发 | 4h | 后端日志记录+前端日志页面 |
| 脚本编辑器优化 | 3h | 添加iOS/HarmonyOS语法高亮 |
| 仪表盘优化 | 2h | 设备去重+任务跳转 |
| APK管理优化 | 2h | 显示原始文件名、版本号、包名 |

### 3.3 阶段三：UI优化

| 任务 | 预估时间 | 描述 |
|------|----------|------|
| 任务列表优化 | 2h | 状态中文、设备展开/收起、进度显示 |
| 导航更新 | 1h | 添加日志页面导航 |

---

## 4. 测试计划

### 4.1 单元测试

- 脚本上传/下载功能测试
- 任务创建/执行/停止流程测试
- 报告生成/下载测试
- 日志记录查询测试

### 4.2 集成测试

- 完整流程测试：上传脚本→创建任务→执行→生成报告
- 设备去重逻辑测试
- 脚本类型区分测试

### 4.3 手动测试

- 各平台脚本语法高亮验证
- 移动端适配测试
- 异常边界条件测试

---

**文档版本: 1.0.0**  
**最后更新: 2026-05-19**