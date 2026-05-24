# FastAPI Middleware Audit Logging Design

**Date:** 2026-05-18
**Status:** Draft
**Approach:** 审计日志中间件设计

---

## Overview

为 FastAPI 后端添加自动化的 API 请求审计日志功能，记录所有 API 调用的时间、用户、操作类型、请求参数和响应状态。

## Change Summary

| # | Module | Issue | Fix |
|---|--------|-------|-----|
| 1 | API审计 | 无API调用记录 | 添加 FastAPI 中间件自动记录所有 API 请求 |
| 2 | 日志格式 | 日志分散 | 统一使用结构化日志格式，便于查询和分析 |

---

## 1. FastAPI Middleware Architecture

### 1.1 Middleware Location

**File:** `backend/app/api/v1/middleware.py`

```python
"""FastAPI middleware for automatic API request audit logging."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import json
from typing import Callable

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log all API requests."""

    def __init__(self, app: ASGIApp, audit_service=None):
        super().__init__(app)
        self.audit_service = audit_service
```

### 1.2 Log Entry Structure

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | 请求时间 |
| method | string | HTTP方法 (GET/POST/PUT/DELETE) |
| path | string | API路径 |
| client_ip | string | 客户端IP |
| user_agent | string | 用户代理 |
| status_code | int | 响应状态码 |
| duration_ms | int | 请求耗时(毫秒) |
| request_body | string | 请求体 (可选，脱敏) |
| response_body | string | 响应体 (可选，脱敏) |

### 1.3 Audit Category Mapping

| API Path Pattern | Category | Action |
|-----------------|----------|--------|
| /scripts/* | script | create/update/delete/execute |
| /tasks/* | task | create/update/delete/cancel |
| /devices/* | device | connect/disconnect/wireless |
| /apks/* | apk | upload/delete |
| /reports/* | report | generate/view/delete |
| /logs/* | log | query/export |

---

## 2. Implementation Files

| File | Change | Description |
|------|--------|-------------|
| `backend/app/api/v1/middleware.py` | Create | 审计日志中间件实现 |
| `backend/app/main.py` | Modify | 注册中间件到 FastAPI 应用 |
| `backend/app/services/audit_log_service.py` | Create | 审计日志服务层 |

---

## 3. Security Considerations

- 敏感字段（密码、token、密钥）不记录在日志中
- 请求体大小限制，避免内存溢出
- 日志轮转策略，防止磁盘空间耗尽
