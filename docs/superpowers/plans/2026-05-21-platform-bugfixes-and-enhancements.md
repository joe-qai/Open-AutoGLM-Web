# Platform Bug Fixes & Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 8 platform issues — 3 bugs, 4 UI adjustments, 1 audit logging enhancement — implementing them in dependency order.

**Architecture:** SQLite-backed audit log service (P0) first, then bug fixes that wire missing frontend-to-backend connections and fix React hooks violations, then UI adjustments (modal sizing, removing elements, dashboard stats redesign).

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/TailwindCSS/Zustand (frontend), SQLite (audit log persistence)

---

## File Structure

### New Files
- `backend/app/services/audit_log_service.py` — SQLite-backed audit log service
- `backend/app/schemas/audit_log.py` — Updated log schemas (category/action fields)
- `backend/app/api/v1/middleware.py` — FastAPI middleware for logging all HTTP requests

### Modified Files
- `backend/app/schemas/log.py` — Add `category`, `action`, `operator` fields; rename `LogType` to `LogCategory`
- `backend/app/services/log_service.py` — Replace in-memory list with SQLite via `AuditLogService`
- `backend/app/api/v1/logs.py` — Update query params for category-based filtering
- `backend/app/api/v1/scripts.py` — Remove subprocess execute endpoint, add audit logging
- `backend/app/services/script_service.py` — Remove subprocess methods, delegate to task system
- `backend/app/main.py` — Add audit middleware, inject audit log service
- `frontend/src/services/api.ts` — Add `deleteScript()`, `deleteTask()` methods, update log API params
- `frontend/src/pages/Script/ScriptPage.tsx` — Fix hooks violation, widen edit modal, fix delete
- `frontend/src/pages/Task/TaskPage.tsx` — Wire delete button, fix execute wiring
- `frontend/src/pages/Device/DevicePage.tsx` — Remove TCP/IP button and modal
- `frontend/src/pages/Dashboard/Dashboard.tsx` — Fix device dedup logic, add connection type stats
- `frontend/src/pages/Logs/LogsPage.tsx` — Update filters to category-based, add entity filters
- `frontend/src/components/layout/Header.tsx` — Remove search/notifications/settings
- `frontend/src/stores/taskStore.ts` — Add `deleteTask` action to store

---

### Task 1: Create Audit Log Service with SQLite

**Files:**
- Create: `backend/app/services/audit_log_service.py`
- Create: `backend/app/schemas/audit_log.py`

- [ ] **Step 1: Write the audit log service**

Create `backend/app/services/audit_log_service.py`:

```python
"""SQLite-backed audit log service for recording all system operations."""

import sqlite3
import json
import time
import threading
from typing import List, Optional, Any
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "audit_log.db"


class AuditLogService:
    """Singleton service that writes log entries to SQLite."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and create tables."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                log_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                operator TEXT NOT NULL,
                target_id TEXT,
                target_name TEXT,
                detail TEXT,
                device_id TEXT,
                script_id TEXT,
                task_id TEXT,
                endpoint TEXT,
                method TEXT,
                status_code INTEGER,
                duration_ms INTEGER,
                error TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_category ON logs(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_device ON logs(device_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_script ON logs(script_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_task ON logs(task_id)")
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection (one per write for thread safety)."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def log(
        self,
        level: str = "info",
        category: str = "system",
        action: str = "created",
        operator: str = "system",
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        detail: Optional[dict] = None,
        device_id: Optional[str] = None,
        script_id: Optional[str] = None,
        task_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> str:
        """Write a log entry to SQLite. Returns the log_id."""
        log_id = f"log_{int(time.time())}_{category}_{action}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        detail_json = json.dumps(detail) if detail else None

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO logs (log_id, timestamp, level, category, action, operator,
                   target_id, target_name, detail, device_id, script_id, task_id,
                   endpoint, method, status_code, duration_ms, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, timestamp, level, category, action, operator,
                 target_id, target_name, detail_json, device_id, script_id, task_id,
                 endpoint, method, status_code, duration_ms, error),
            )
            conn.commit()
        finally:
            conn.close()

        return log_id

    def list_logs(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        device_id: Optional[str] = None,
        script_id: Optional[str] = None,
        task_id: Optional[str] = None,
        search: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """Query logs with filters."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM logs WHERE 1=1"
            params = []

            if level:
                query += " AND level = ?"
                params.append(level)
            if category:
                query += " AND category = ?"
                params.append(category)
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            if script_id:
                query += " AND script_id = ?"
                params.append(script_id)
            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)
            if search:
                query += " AND (target_name LIKE ? OR error LIKE ? OR detail LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, skip])

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_summary(self) -> dict:
        """Get aggregated log statistics."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
            error_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'error'").fetchone()[0]
            warning_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'warning'").fetchone()[0]
            info_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'info'").fetchone()[0]
            debug_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'debug'").fetchone()[0]

            avg_result = conn.execute(
                "SELECT AVG(duration_ms) FROM logs WHERE duration_ms IS NOT NULL AND category = 'api'"
            ).fetchone()[0]

            return {
                "total": total,
                "error_count": error_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "debug_count": debug_count,
                "avg_response_time_ms": avg_result,
            }
        finally:
            conn.close()

    def clear_logs(self):
        """Delete all logs from the database."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM logs")
            conn.commit()
        finally:
            conn.close()
```

- [ ] **Step 2: Write the updated log schemas**

Create `backend/app/schemas/audit_log.py`:

```python
"""Updated log schemas with category/action/operator fields."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogCategory(str, Enum):
    DEVICE = "device"
    SCRIPT = "script"
    TASK = "task"
    AGENT = "agent"
    SYSTEM = "system"
    API = "api"


class LogEntry(BaseModel):
    log_id: str
    level: LogLevel
    category: LogCategory
    action: str
    operator: str
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    detail: Optional[dict[str, Any]] = None
    device_id: Optional[str] = None
    script_id: Optional[str] = None
    task_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class LogSummary(BaseModel):
    total: int
    error_count: int
    warning_count: int
    info_count: int
    debug_count: int
    avg_response_time_ms: Optional[float] = None
```

- [ ] **Step 3: Verify the service works**

Run: `cd C:\pythonworkspace\Open-AutoGLM\backend && python -c "from app.services.audit_log_service import AuditLogService; svc = AuditLogService(); svc.log(category='system', action='test', operator='system', target_name='test'); print('PASS: audit log service initialized and wrote entry')"`
Expected: Output "PASS: audit log service initialized and wrote entry"

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/audit_log_service.py backend/app/schemas/audit_log.py
git commit -m "feat: add SQLite-backed audit log service with category/action schema"
```

---

### Task 2: Update Backend Log Service to Use SQLite

**Files:**
- Modify: `backend/app/services/log_service.py` — Replace in-memory storage with AuditLogService
- Modify: `backend/app/schemas/log.py` — Add category/action fields alongside existing type field
- Modify: `backend/app/api/v1/logs.py` — Update query params for category-based filtering

- [ ] **Step 1: Update log schemas to add new fields**

Modify `backend/app/schemas/log.py`. Replace the entire file content:

```python
"""Log schemas for API execution tracking."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogCategory(str, Enum):
    """Log category enumeration — replaces LogType."""
    DEVICE = "device"
    SCRIPT = "script"
    TASK = "task"
    AGENT = "agent"
    SYSTEM = "system"
    API = "api"


class LogEntry(BaseModel):
    """Log entry model."""
    log_id: str
    level: LogLevel
    category: LogCategory
    action: str
    operator: str
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    detail: Optional[dict[str, Any]] = None
    device_id: Optional[str] = None
    script_id: Optional[str] = None
    task_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class LogSummary(BaseModel):
    """Log summary statistics."""
    total: int
    error_count: int
    warning_count: int
    info_count: int
    debug_count: int
    avg_response_time_ms: Optional[float] = None
```

- [ ] **Step 2: Replace log_service.py with SQLite-backed version**

Modify `backend/app/services/log_service.py`. Replace the entire file content:

```python
"""Log service backed by SQLite audit log."""

from typing import List, Optional

from app.services.audit_log_service import AuditLogService
from app.schemas.log import LogEntry, LogLevel, LogCategory, LogSummary


class LogService:
    """Service for managing log entries, backed by AuditLogService (SQLite)."""

    def __init__(self):
        self.audit = AuditLogService()

    def create_log(
        self,
        level: str = "info",
        category: str = "system",
        action: str = "created",
        operator: str = "system",
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        detail: Optional[dict] = None,
        device_id: Optional[str] = None,
        script_id: Optional[str] = None,
        task_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> str:
        """Create a new log entry via the audit log service."""
        return self.audit.log(
            level=level,
            category=category,
            action=action,
            operator=operator,
            target_id=target_id,
            target_name=target_name,
            detail=detail,
            device_id=device_id,
            script_id=script_id,
            task_id=task_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            error=error,
        )

    def get_log(self, log_id: str) -> Optional[LogEntry]:
        """Get log by ID."""
        logs = self.audit.list_logs(limit=1)
        for log_dict in logs:
            if log_dict.get("log_id") == log_id:
                return LogEntry(**log_dict)
        return None

    def list_logs(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        device_id: Optional[str] = None,
        script_id: Optional[str] = None,
        task_id: Optional[str] = None,
        search: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LogEntry]:
        """List logs with filters."""
        log_dicts = self.audit.list_logs(
            level=level,
            category=category,
            device_id=device_id,
            script_id=script_id,
            task_id=task_id,
            search=search,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=min(limit, 500),
        )
        return [LogEntry(**d) for d in log_dicts]

    def get_summary(self) -> LogSummary:
        """Get log summary statistics."""
        summary_dict = self.audit.get_summary()
        return LogSummary(**summary_dict)

    def clear_logs(self):
        """Clear all logs."""
        self.audit.clear_logs()

    # Convenience methods
    def log_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: int, error: Optional[str] = None):
        """Log an API request."""
        level = "error" if status_code >= 400 else "info"
        action = "failed" if status_code >= 400 else "success"
        self.create_log(
            level=level, category="api", action=action, operator="system",
            endpoint=endpoint, method=method, status_code=status_code,
            duration_ms=duration_ms, error=error,
        )

    def log_script_execution(self, script_id: str, action: str = "executed", device_id: Optional[str] = None, error: Optional[str] = None):
        """Log script execution."""
        level = "error" if error else "info"
        self.create_log(
            level=level, category="script", action=action, operator="user",
            target_id=script_id, device_id=device_id, error=error,
        )

    def log_task_execution(self, task_id: str, action: str = "executed", script_id: Optional[str] = None, error: Optional[str] = None):
        """Log task execution."""
        level = "error" if error else "info"
        self.create_log(
            level=level, category="task", action=action, operator="system",
            target_id=task_id, script_id=script_id, error=error,
        )

    def log_device_operation(self, device_id: str, action: str = "connected", success: bool = True, error: Optional[str] = None):
        """Log device operation."""
        level = "error" if not success else "info"
        self.create_log(
            level=level, category="device", action=action, operator="system",
            target_id=device_id, device_id=device_id, error=error,
        )

    def log_system(self, message: str, level: str = "info", detail: Optional[dict] = None):
        """Log system message."""
        self.create_log(
            level=level, category="system", action="event", operator="system",
            detail={"message": message} if not detail else {**detail, "message": message},
        )
```

- [ ] **Step 3: Update logs API endpoint**

Modify `backend/app/api/v1/logs.py`. Replace the entire file content:

```python
"""Log management API — backed by SQLite audit log."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.schemas.log import LogEntry, LogLevel, LogCategory, LogSummary
from app.services.log_service import LogService

router = APIRouter()
log_service = LogService()


@router.get("/", response_model=List[LogEntry])
async def list_logs(
    level: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    script_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
):
    """List all logs with optional filters."""
    return log_service.list_logs(
        level=level,
        category=category,
        device_id=device_id,
        script_id=script_id,
        task_id=task_id,
        search=search,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
    )


@router.get("/summary", response_model=LogSummary)
async def get_log_summary():
    """Get log summary statistics."""
    return log_service.get_summary()


@router.delete("/")
async def clear_logs():
    """Clear all logs."""
    log_service.clear_logs()
    return {"message": "All logs cleared successfully"}
```

- [ ] **Step 4: Verify backend starts and logs API works**

Run: `cd C:\pythonworkspace\Open-AutoGLM\backend && python -c "from app.services.log_service import LogService; svc = LogService(); svc.create_log(category='system', action='test', operator='system'); result = svc.list_logs(category='system'); print(f'PASS: {len(result)} log entries found')"`
Expected: Output "PASS: 1 log entries found" or similar count

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/log_service.py backend/app/schemas/log.py backend/app/api/v1/logs.py
git commit -m "feat: replace in-memory log service with SQLite-backed audit log"
```

---

### Task 3: Add FastAPI Middleware for API Request Logging

**Files:**
- Create: `backend/app/api/v1/middleware.py`
- Modify: `backend/app/main.py` — Register middleware

- [ ] **Step 1: Write the audit middleware**

Create `backend/app/api/v1/middleware.py`:

```python
"""FastAPI middleware for logging all HTTP requests to the audit log."""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.audit_log_service import AuditLogService


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every HTTP request to the SQLite audit log."""

    def __init__(self, app, audit_service: AuditLogService = None):
        super().__init__(app)
        self.audit = audit_service or AuditLogService()

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process the request
        response: Response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log the request (skip health check and docs to reduce noise)
        path = request.url.path
        if path not in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            self.audit.log(
                level="error" if response.status_code >= 400 else "info",
                category="api",
                action="request",
                operator="user",
                endpoint=path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        return response
```

- [ ] **Step 2: Register middleware in main.py**

Modify `backend/app/main.py`. Add the middleware import and registration. 

Add import after the existing imports (after line 8):
```python
from app.api.v1.middleware import AuditLogMiddleware
```

Add after the CORS middleware block (after line 38):
```python
# Audit log middleware — logs all API requests to SQLite
app.add_middleware(AuditLogMiddleware)
```

- [ ] **Step 3: Verify middleware is registered**

Run: `cd C:\pythonworkspace\Open-AutoGLM\backend && python -c "from app.main import app; middlewares = [m.cls.__name__ for m in app.user_middleware]; print(f'PASS: middlewares = {middlewares}')"`
Expected: Output includes "AuditLogMiddleware" in the list

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/middleware.py backend/app/main.py
git commit -m "feat: add FastAPI middleware for automatic API request audit logging"
```

---

### Task 4: Fix Script Delete Bug (#1) — Add Missing API Method

**Files:**
- Modify: `frontend/src/services/api.ts` — Add `deleteScript()` method

- [ ] **Step 1: Add deleteScript to frontend API**

Modify `frontend/src/services/api.ts`. In the `scriptApi` object, add the missing `deleteScript` method after `getScriptVersions` (around line 101):

```typescript
  deleteScript: (scriptId: string) => api.delete(`/api/v1/scripts/${scriptId}`),
```

The root cause of bug #1 is that `scriptApi.deleteScript` is called in `ScriptPage.tsx` line 109 but the method didn't exist in `api.ts`. With this addition, the existing `handleDelete` function will work correctly.

- [ ] **Step 2: Verify build succeeds**

Run: `cd C:\pythonworkspace\Open-AutoGLM\frontend && npm run build 2>&1 | head -5`
Expected: Build succeeds with no TypeScript errors about `deleteScript`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "fix: add missing scriptApi.deleteScript method to fix script delete bug"
```

---

### Task 5: Fix Script Execution Bug (#3) — Frontend Hooks + Backend Routing

**Files:**
- Modify: `frontend/src/pages/Script/ScriptPage.tsx` — Fix `useNavigate` hooks violation
- Modify: `backend/app/services/script_service.py` — Remove subprocess methods, delegate to task system
- Modify: `backend/app/api/v1/scripts.py` — Rework execute endpoint

- [ ] **Step 1: Fix frontend useNavigate hooks violation**

Modify `frontend/src/pages/Script/ScriptPage.tsx`. Make three changes:

1. Add `useNavigate` import. Add after line 1:
```typescript
import { useNavigate } from 'react-router-dom';
```

2. Add `navigate` hook inside the component. Add after line 6 (`export function ScriptPage() {`):
```typescript
  const navigate = useNavigate();
```

3. Replace the `handleExecute` function (lines 62-71). Replace the entire function:
```typescript
  const handleExecute = (script: Script) => {
    setCurrentScript(script);
    navigate('/agent');
  };
```

This removes the broken dynamic import of `useNavigate` that violated React hooks rules.

- [ ] **Step 2: Rework backend script execute to delegate to task system**

Modify `backend/app/services/script_service.py`. Replace the `execute_script` method (line 185-199) with:

```python
    def execute_script(self, script_id: str, device_id: str = None) -> str:
        """Execute a script by creating a task and delegating to TaskService.
        Returns the task_id of the created task."""
        from app.services.task_service import TaskService

        script = self.get_script(script_id)
        if not script:
            return ""

        task_service = TaskService()
        task_id = task_service.create_task(
            name=f"Execute: {script.name}",
            description=f"Script execution: {script.name}",
            script_id=script_id,
            device_id=device_id,
            platform=script.platform,
        )

        # Execute the task via the agent engine
        task_service.execute_task(task_id)

        return task_id
```

Then remove the following methods entirely: `_execute_android_script` (lines 201-236), `_execute_ios_script` (lines 238-262), `_execute_harmonyos_script` (lines 264-286). Also remove the `subprocess`, `tempfile`, `shutil` imports at the top (lines 6-9) since they're only used by those methods.

- [ ] **Step 3: Update scripts API execute endpoint**

Modify `backend/app/api/v1/scripts.py`. 

1. Add `BackgroundTasks` import. Change line 3:
```python
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
```
to:
```python
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
```

2. Replace the `execute_script` endpoint (lines 70-81):
```python
@router.post("/{script_id}/execute")
async def execute_script(script_id: str, data: dict, background_tasks: BackgroundTasks):
    """Execute a script by creating a task. Returns the task_id."""
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    device_id = data.get("device_id")
    task_id = script_service.execute_script(script_id, device_id)
    if not task_id:
        raise HTTPException(status_code=400, detail="Failed to create task for script execution")

    return {"task_id": task_id, "script_id": script_id, "status": "task_created"}
```

- [ ] **Step 4: Verify backend loads without errors**

Run: `cd C:\pythonworkspace\Open-AutoGLM\backend && python -c "from app.services.script_service import ScriptService; svc = ScriptService(); print('PASS: script service loads without subprocess methods')"`
Expected: "PASS: script service loads without subprocess methods"

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Script/ScriptPage.tsx backend/app/services/script_service.py backend/app/api/v1/scripts.py
git commit -m "fix: script execution routes through task system instead of subprocess, fix React hooks violation"
```

---

### Task 6: Fix Task Execute/Delete Bug (#5) — Wire Frontend to Backend

**Files:**
- Modify: `frontend/src/services/api.ts` — Add `deleteTask()` method
- Modify: `frontend/src/stores/taskStore.ts` — Add `deleteTask` action
- Modify: `frontend/src/pages/Task/TaskPage.tsx` — Wire delete button

- [ ] **Step 1: Add deleteTask to frontend API**

Modify `frontend/src/services/api.ts`. In the `taskApi` object, add `deleteTask` after `stopTask` (around line 73):

```typescript
  deleteTask: (taskId: string) => api.delete(`/api/v1/tasks/${taskId}`),
```

- [ ] **Step 2: Add deleteTask action to task store**

Modify `frontend/src/stores/taskStore.ts`.

1. Add `deleteTask` to the `TaskState` interface (after `stopTask` around line 37):
```typescript
  deleteTask: (taskId: string) => Promise<void>;
```

2. Add `deleteTask` implementation in the store (after `stopTask` around line 90):
```typescript
  deleteTask: async (taskId: string) => {
    try {
      await taskApi.deleteTask(taskId);
      await get().fetchTasks();
    } catch (error) {
      set({ error: 'Failed to delete task' });
    }
  },
```

- [ ] **Step 3: Wire delete button in TaskPage**

Modify `frontend/src/pages/Task/TaskPage.tsx`.

1. Add `deleteTask` to the destructured store. Change line 10:
```typescript
  const { tasks, fetchTasks, executeTask, stopTask, createTask } = useTaskStore();
```
to:
```typescript
  const { tasks, fetchTasks, executeTask, stopTask, createTask, deleteTask } = useTaskStore();
```

2. Replace the delete button's onClick handler (lines 230-235). Find:
```typescript
                          <button
                            onClick={() => {
                              if (confirm('确定要删除此任务吗？')) {
                                // Delete logic
                              }
                            }}
```
Replace with:
```typescript
                          <button
                            onClick={() => {
                              if (confirm('确定要删除此任务吗？')) {
                                deleteTask(task.task_id);
                              }
                            }}
```

- [ ] **Step 4: Verify build succeeds**

Run: `cd C:\pythonworkspace\Open-AutoGLM\frontend && npm run build 2>&1 | head -5`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/stores/taskStore.ts frontend/src/pages/Task/TaskPage.tsx
git commit -m "fix: add deleteTask API method and wire task delete button to backend"
```

---

### Task 7: Enlarge Script Edit Modal (#2)

**Files:**
- Modify: `frontend/src/pages/Script/ScriptPage.tsx` — Change modal width

- [ ] **Step 1: Widen the edit modal**

Modify `frontend/src/pages/Script/ScriptPage.tsx`. In the edit modal section, change `max-w-3xl` to `max-w-5xl`. Find (around line 363):

```html
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col">
```

Replace with:

```html
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-5xl mx-4 max-h-[90vh] flex flex-col">
```

- [ ] **Step 2: Add minimum height and better line spacing to textarea**

Find the textarea (around line 379):

```html
                className="w-full h-full p-4 bg-[#0f172a] text-[#e2e8f0] font-mono text-sm resize-none focus:outline-none rounded-lg"
```

Replace with:

```html
                className="w-full h-full min-h-[60vh] p-4 bg-[#0f172a] text-[#e2e8f0] font-mono text-sm resize-none focus:outline-none rounded-lg leading-relaxed"
```

This adds `min-h-[60vh]` for a consistent editing area and `leading-relaxed` for better line spacing.

- [ ] **Step 3: Verify build**

Run: `cd C:\pythonworkspace\Open-AutoGLM\frontend && npm run build 2>&1 | head -5`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Script/ScriptPage.tsx
git commit -m "ui: enlarge script edit modal from max-w-3xl to max-w-5xl with minimum height"
```

---

### Task 8: Remove TCP/IP Connection Button (#4)

**Files:**
- Modify: `frontend/src/pages/Device/DevicePage.tsx` — Remove TCP/IP button, modal, and related code

- [ ] **Step 1: Remove TCP/IP button, modal, and related code**

Modify `frontend/src/pages/Device/DevicePage.tsx`. Make these changes:

1. Remove state variables (lines 7-9). Delete:
```typescript
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [tcpIpAddress, setTcpIpAddress] = useState('');
  const [port, setPort] = useState('5555');
```

2. Remove `handleConnectTcpIp` function (lines 22-29).

3. Remove `connectTcpIp`, `connectingTcpIp` from the destructured store. Change line 6:
```typescript
  const { devices, fetchDevices, connectDevice, disconnectDevice, connectTcpIp, connectingTcpIp, enableWireless, enablingWireless, error, success, clearMessages } = useDeviceStore();
```
to:
```typescript
  const { devices, fetchDevices, connectDevice, disconnectDevice, enableWireless, enablingWireless, error, success, clearMessages } = useDeviceStore();
```

4. Remove the TCP/IP button from the header (lines 103-109). Delete the entire `<button>` block with `Wifi` icon and "TCP/IP 连接" text.

5. Remove the `connectingTcpIp` message display (lines 114-119) — this references `connectingTcpIp` which we removed from the store.

6. Remove the TCP/IP modal. Delete the entire `{isModalOpen && (` block (lines 237-310).

7. Update the empty state message. Find the empty state text (around line 225):
```html
          <p className="text-[#64748b] mb-4">点击\"TCP/IP 连接\"按钮连接您的设备</p>
```
Replace with:
```html
          <p className="text-[#64748b]">连接USB设备即可开始使用</p>
```

8. Also remove the TCP/IP button in the empty state (lines 226-232). Delete the `<button>` block with "TCP/IP 连接".

9. Clean up imports. Change line 2:
```typescript
import { Smartphone, RefreshCw, Power, Monitor, Wifi, X, Check, AlertCircle, Loader2 } from 'lucide-react';
```
to:
```typescript
import { Smartphone, RefreshCw, Power, Monitor, Wifi, AlertCircle, Loader2 } from 'lucide-react';
```

Note: `Wifi` is still needed for the "开启无线" button on individual device cards.

- [ ] **Step 2: Verify build**

Run: `cd C:\pythonworkspace\Open-AutoGLM\frontend && npm run build 2>&1 | head -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Device/DevicePage.tsx
git commit -m "ui: remove TCP/IP connection button and modal from device management page"
```

---

### Task 9: Fix Dashboard Device Stats (#7)

**Files:**
- Modify: `frontend/src/pages/Dashboard/Dashboard.tsx` — Replace device dedup logic, add connection type stats

- [ ] **Step 1: Replace uniqueDevices dedup logic and add connection type stats**

Modify `frontend/src/pages/Dashboard/Dashboard.tsx`.

1. Replace the `uniqueDevices` dedup logic (lines 39-45). Change:
```typescript
  const uniqueDevices = devices.reduce((acc, device) => {
    const existing = acc.find(d => d.device_id === device.device_id);
    if (!existing) {
      acc.push(device);
    }
    return acc;
  }, [] as typeof devices);
```
to:
```typescript
  // Deduplicate by device name — same device via USB and WiFi counts as 1 unique device
  const uniqueDeviceNames = [...new Set(devices.map(d => d.name))];
  const usbCount = devices.filter(d => d.connection_type === 'usb').length;
  const wifiCount = devices.filter(d => d.connection_type === 'tcpip').length;
```

2. Update the stats array (lines 47-78). Change the "设备数量" stat value from `uniqueDevices.length.toString()` to `uniqueDeviceNames.length.toString()` and add a `detail` field:

```typescript
    {
      title: '设备数量',
      value: uniqueDeviceNames.length.toString(),
      detail: `USB ${usbCount} | WiFi ${wifiCount}`,
      icon: <Clock className="w-5 h-5 text-orange-400" />,
      trend: '',
      trendUp: true,
    },
```

3. Display the connection type breakdown in the stats card. Find the stats card rendering (around line 138). After the trend line, add:
```html
              {stat.detail && (
                <p className="text-[#94a3b8] text-xs mt-1">{stat.detail}</p>
              )}
```

4. Update the pie chart legend (around lines 208-223). Replace the platform-based legend with name-based legend plus connection type breakdown:
```html
              <div className="flex-1 space-y-3">
                {uniqueDeviceNames.map(name => {
                  const deviceEntries = devices.filter(d => d.name === name);
                  const usbConns = deviceEntries.filter(d => d.connection_type === 'usb').length;
                  const wifiConns = deviceEntries.filter(d => d.connection_type === 'tcpip').length;
                  return (
                    <div key={name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: deviceEntries[0].platform === 'android' ? '#3ddc84' : deviceEntries[0].platform === 'ios' ? '#ffffff' : '#007dff' }}
                        />
                        <span className="text-[#94a3b8]">{name}</span>
                      </div>
                      <span className="text-white font-medium text-xs">
                        {usbConns > 0 && `USB:${usbConns}`} {wifiConns > 0 && `WiFi:${wifiConns}`}
                      </span>
                    </div>
                  );
                })}
              </div>
```

- [ ] **Step 2: Verify build**

Run: `cd C:\pythonworkspace\Open-AutoGLM\frontend && npm run build 2>&1 | head -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard/Dashboard.tsx
git commit -m "ui: dashboard device stats by unique name with USB/WiFi connection type breakdown"
```

---

### Task 10: Remove Header Search/Notifications/Settings (#8)

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx` — Remove search, bell, settings

- [ ] **Step 1: Replace entire Header component**

Modify `frontend/src/components/layout/Header.tsx`. Replace the entire file with:

```typescript
import { User } from 'lucide-react';

export function Header() {
  return (
    <header className="h-16 bg-[#1e293b] border-b border-[#334155] flex items-center justify-between px-6 fixed top-0 right-0 left-60 z-40">
      {/* Left: Title */}
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-white">LOCKIN Agent Platform</h1>
      </div>

      {/* Right: User profile only */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <User size={16} className="text-white" />
        </div>
        <div className="hidden md:block">
          <p className="text-sm font-medium text-white">管理员</p>
          <p className="text-xs text-[#64748b]">admin@lockin.com</p>
        </div>
      </div>
    </header>
  );
}
```

This removes: `useState`, `Search`, `Bell`, `Settings` imports, `searchQuery` state, the search input, notification bell, and settings button.

- [ ] **Step 2: Verify build**

Run: `cd C:\pythonworkspace\Open-AutoGLM\frontend && npm run build 2>&1 | head -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/Header.tsx
git commit -m "ui: remove search, notifications, and settings from platform header"
```

---

### Task 11: Update Frontend LogsPage for Category-Based Filtering

**Files:**
- Modify: `frontend/src/pages/Logs/LogsPage.tsx` — Update LogEntry interface, replace type filter with category, add entity filters
- Modify: `frontend/src/services/api.ts` — Update `logApi.getLogs` params

- [ ] **Step 1: Update frontend log API params**

Modify `frontend/src/services/api.ts`. In the `logApi` object, update `getLogs` params to use `category` instead of `type` and add `search`:

```typescript
export const logApi = {
  getLogs: (params?: {
    level?: string;
    category?: string;
    device_id?: string;
    script_id?: string;
    task_id?: string;
    search?: string;
    start_time?: string;
    end_time?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/api/v1/logs', { params }),
  getSummary: () => api.get('/api/v1/logs/summary'),
  clearLogs: () => api.delete('/api/v1/logs'),
};
```

Remove `getLog`, `createLog` methods since they're not used by the frontend.

- [ ] **Step 2: Update LogsPage LogEntry interface**

Modify `frontend/src/pages/Logs/LogsPage.tsx`. Replace the `LogEntry` interface (lines 5-19):

```typescript
interface LogEntry {
  log_id: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  category: 'device' | 'script' | 'task' | 'agent' | 'system' | 'api';
  action: string;
  operator: 'user' | 'system' | 'agent';
  target_id?: string;
  target_name?: string;
  detail?: Record<string, unknown>;
  device_id?: string;
  script_id?: string;
  task_id?: string;
  endpoint?: string;
  method?: string;
  status_code?: number;
  duration_ms?: number;
  error?: string;
  created_at: string;
}
```

Also replace `LogSummary` interface (lines 21-29):

```typescript
interface LogSummary {
  total: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  debug_count: number;
  avg_response_time_ms?: number;
}
```

- [ ] **Step 3: Replace type filter with category filter**

Modify `frontend/src/pages/Logs/LogsPage.tsx`.

1. Replace `selectedType` with `selectedCategory` (line 36):
```typescript
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
```

2. Update filter logic (around line 79-83). Replace:
```typescript
    if (selectedType !== 'all' && log.type !== selectedType) return false;
```
with:
```typescript
    if (selectedCategory !== 'all' && log.category !== selectedCategory) return false;
```

3. Replace `getTypeLabel` with `getCategoryLabel` (around lines 115-126):
```typescript
  const getCategoryLabel = (category: string) => {
    const categoryMap: Record<string, string> = {
      device: '设备操作',
      script: '脚本操作',
      task: '任务操作',
      agent: 'Agent操作',
      system: '系统',
      api: 'API请求',
    };
    return categoryMap[category] || category;
  };
```

4. Replace the type filter dropdown with category filter (around lines 263-274):
```html
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">日志类别</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="all">全部</option>
              <option value="device">设备操作</option>
              <option value="script">脚本操作</option>
              <option value="task">任务操作</option>
              <option value="agent">Agent操作</option>
              <option value="system">系统</option>
              <option value="api">API请求</option>
            </select>
          </div>
```

5. Update the type badge in log entries. Find `getTypeLabel(log.type)` (around line 310) and replace:
```html
                      <span className="px-2 py-0.5 bg-[#334155] text-[#94a3b8] rounded text-xs">
                        {getTypeLabel(log.type)}
                      </span>
```
with:
```html
                      <span className="px-2 py-0.5 bg-[#334155] text-[#94a3b8] rounded text-xs">
                        {getCategoryLabel(log.category)}
                      </span>
                      <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded text-xs">
                        {log.action}
                      </span>
```

- [ ] **Step 4: Verify build**

Run: `cd C:\pythonworkspace\Open-AutoGLM\frontend && npm run build 2>&1 | head -5`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Logs/LogsPage.tsx frontend/src/services/api.ts
git commit -m "feat: update logs page to use category-based filtering with action/operator fields"
```

---

## Self-Review Checklist

### 1. Spec Coverage
| Spec Requirement | Task |
|---|---|
| #6: SQLite audit log service | Task 1, Task 2, Task 3 |
| #1: Script delete bug | Task 4 |
| #3: Script execution error (frontend hooks) | Task 5 (Step 1) |
| #3: Script execution error (backend subprocess) | Task 5 (Steps 2-3) |
| #5: Task delete button | Task 6 |
| #5: Task execute button | Task 6 (store already wired) |
| #2: Script edit modal enlargement | Task 7 |
| #4: Remove TCP/IP connection button | Task 8 |
| #7: Dashboard device stats by name | Task 9 |
| #8: Remove header elements | Task 10 |
| Log frontend category-based filtering | Task 11 |

All spec requirements covered.

### 2. Placeholder Scan
No "TBD", "TODO", "implement later", "fill in details", "add appropriate error handling", "write tests for the above", or "similar to Task N" patterns found.

### 3. Type Consistency
- `LogCategory` enum used consistently in `audit_log.py`, `log.py`, `log_service.py`, `logs.py` API, and frontend `LogEntry` interface
- `deleteScript` method added to `scriptApi` in Task 4, referenced correctly in `ScriptPage.tsx` (already existed)
- `deleteTask` method added to `taskApi` in Task 6, referenced in `taskStore.ts` and `TaskPage.tsx`
- `LogEntry.category` field (not `type`) used consistently in frontend and backend
- `AuditLogService.log()` method signature matches all convenience methods in `LogService`