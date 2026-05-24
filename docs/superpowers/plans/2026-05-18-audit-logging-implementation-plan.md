# FastAPI Middleware Audit Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 FastAPI 后端添加自动化的 API 请求审计日志功能

**Architecture:** Starlette BaseHTTPMiddleware 拦截所有请求，记录到 SQLite 数据库

**Tech Stack:** Python 3.10+, FastAPI, aiosqlite, BaseHTTPMiddleware

---

### Task 1: Create Audit Log Middleware

**Files:**
- Create: `backend/app/api/v1/middleware.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create audit logging middleware**

Create `backend/app/api/v1/middleware.py`:

```python
"""FastAPI middleware for automatic API request audit logging."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import json
from typing import Callable, Optional
import re

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log all API requests."""

    SENSITIVE_PATHS = ['/password', '/token', '/secret', '/key']
    SENSITIVE_HEADERS = ['authorization', 'x-api-key', 'cookie']

    def __init__(self, app: ASGIApp, audit_service=None):
        super().__init__(app)
        self.audit_service = audit_service

    def _is_sensitive_path(self, path: str) -> bool:
        return any(sensitive in path.lower() for sensitive in self.SENSITIVE_PATHS)

    def _sanitize_headers(self, headers: dict) -> dict:
        sanitized = {}
        for key, value in headers.items():
            if key.lower() not in self.SENSITIVE_HEADERS:
                sanitized[key] = value
            else:
                sanitized[key] = "[REDACTED]"
        return sanitized

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)

            if self.audit_service:
                category = self._get_category_from_path(path)
                action = self._get_action_from_method(method, path)

                await self.audit_service.log(
                    category=category,
                    action=action,
                    detail={
                        "method": method,
                        "path": path,
                        "client_ip": client_ip,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "user_agent": user_agent
                    }
                )

        return response

    def _get_category_from_path(self, path: str) -> str:
        path_lower = path.lower()
        if "/scripts" in path_lower:
            return "script"
        elif "/tasks" in path_lower:
            return "task"
        elif "/devices" in path_lower:
            return "device"
        elif "/apks" in path_lower:
            return "apk"
        elif "/reports" in path_lower:
            return "report"
        elif "/logs" in path_lower:
            return "log"
        elif "/projects" in path_lower:
            return "project"
        return "unknown"

    def _get_action_from_method(self, method: str, path: str) -> str:
        method_lower = method.lower()
        if "/login" in path.lower():
            return "login"
        elif method_lower == "post":
            return "create"
        elif method_lower == "put":
            return "update"
        elif method_lower == "delete":
            return "delete"
        elif method_lower == "get" and "/detail" in path.lower():
            return "view"
        return "query"
```

- [ ] **Step 2: Register middleware in main.py**

Edit `backend/app/main.py`:

```python
from backend.app.api.v1.middleware import AuditLoggingMiddleware

app = FastAPI(title="AutoGLM Platform API")

audit_service = AuditLogService()

app.add_middleware(AuditLoggingMiddleware, audit_service=audit_service)
```

---

### Task 2: Create Audit Log Service

**Files:**
- Create: `backend/app/services/audit_log_service.py`

- [ ] **Step 1: Create SQLite-backed audit log service**

Create `backend/app/services/audit_log_service.py`:

```python
"""SQLite-backed audit log service."""

import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid

class AuditLogService:
    """Service for managing audit logs in SQLite."""

    def __init__(self, db_path: str = "./audit.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        """Initialize database connection and create tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                operator TEXT,
                detail TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_logs(category);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
        """)

    async def log(self, category: str, action: str, detail: Dict[str, Any], operator: str = None):
        """Log an audit event."""
        if not self._conn:
            await self.init()

        log_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        detail_json = json.dumps(detail, ensure_ascii=False)

        await self._conn.execute(
            """INSERT INTO audit_logs (log_id, timestamp, category, action, operator, detail, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_id, timestamp, category, action, operator, detail_json, timestamp)
        )
        await self._conn.commit()

    async def query(
        self,
        category: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query audit logs with filters."""
        if not self._conn:
            await self.init()

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if action:
            query += " AND action = ?"
            params.append(action)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def close(self):
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
```

---

### Verification

- [ ] Verify middleware intercepts all API requests
- [ ] Verify sensitive data is properly redacted
- [ ] Verify logs are persisted to SQLite
- [ ] Verify audit log query API returns correct results
