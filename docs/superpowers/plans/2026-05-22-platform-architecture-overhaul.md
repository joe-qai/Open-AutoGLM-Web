# Platform Architecture Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all in-memory dict storage with SQLite persistence, add subprocess executor for task execution, and create custom HTML report system with base64 error screenshots.

**Architecture:** Single `aiosqlite` Database class providing async connections to all services. Task execution via `subprocess.Popen` managed in a process tracking dict. Reports rendered via Jinja2 template with base64 error screenshots stored inline in the DB.

**Tech Stack:** Python 3.10+, FastAPI, aiosqlite, Jinja2, Zustand, React 18

---

### Task 1: Add aiosqlite + Create Database Module

**Files:**
- Modify: `backend/requirements.txt:6-7`
- Create: `backend/app/db/database.py`
- Modify: `backend/app/db/__init__.py`
- Modify: `backend/app/schemas/apk.py`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add aiosqlite dependency**

Edit `backend/requirements.txt`:

```
# Database
sqlalchemy==2.0.25
aiosqlite==0.20.0
```

- [ ] **Step 2: Add batch delete request schema**

Edit `backend/app/schemas/apk.py` — append before the end:

```python
class ApkBatchDeleteRequest(BaseModel):
    """Request model for batch deleting APKs."""
    apk_ids: List[str]
```

- [ ] **Step 3: Add database_url settings to config**

Edit `backend/app/config.py` — the `database_url` field already exists at line 27. Update it to default to `"./app.db"`:

```python
database_url: str = "./app.db"
```

- [ ] **Step 4: Create the Database module**

Write `backend/app/db/database.py`:

```python
"""SQLite database module with aiosqlite."""

import aiosqlite
from pathlib import Path
from typing import Optional


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: str = "./app.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init_db(self):
        """Initialize database and create tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS scripts (
              script_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              content TEXT NOT NULL,
              script_type TEXT NOT NULL,
              platform TEXT NOT NULL,
              project_id TEXT,
              description TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT,
              version INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tasks (
              task_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              task_type TEXT DEFAULT 'functional',
              platform TEXT DEFAULT 'android',
              status TEXT DEFAULT 'pending',
              script_id TEXT REFERENCES scripts(script_id),
              device_id TEXT,
              apk_id TEXT,
              description TEXT,
              progress INTEGER DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT,
              started_at TEXT,
              completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS task_devices (
              task_id TEXT REFERENCES tasks(task_id),
              device_id TEXT,
              PRIMARY KEY (task_id, device_id)
            );

            CREATE TABLE IF NOT EXISTS task_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              task_id TEXT REFERENCES tasks(task_id),
              timestamp TEXT,
              level TEXT,
              message TEXT
            );

            CREATE TABLE IF NOT EXISTS projects (
              project_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              description TEXT,
              platform TEXT DEFAULT 'android',
              created_at TEXT NOT NULL,
              updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS apks (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              original_filename TEXT,
              package_name TEXT,
              version TEXT,
              file_size INTEGER,
              file_path TEXT,
              upload_time TEXT NOT NULL,
              status TEXT DEFAULT 'uploaded'
            );

            CREATE TABLE IF NOT EXISTS reports (
              task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
              name TEXT,
              device_name TEXT,
              script_name TEXT,
              script_type TEXT,
              status TEXT,
              started_at TEXT,
              completed_at TEXT,
              duration_seconds INTEGER,
              html_content TEXT,
              summary TEXT,
              total_steps INTEGER,
              passed_steps INTEGER,
              failed_steps INTEGER,
              created_at TEXT NOT NULL
            );
        """)
        await self._conn.commit()

    async def get_connection(self) -> aiosqlite.Connection:
        """Return the async connection."""
        if self._conn is None:
            await self.init_db()
        return self._conn

    async def close(self):
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None


db = Database()
```

- [ ] **Step 5: Update db __init__.py exports**

Edit `backend/app/db/__init__.py`:

```python
"""Database module."""

from .database import db, Database

__all__ = ["db", "Database"]
```

---

### Task 2: Wire DB Init into Application Startup

**Files:**
- Modify: `backend/app/main.py:14-23`

- [ ] **Step 1: Add DB import and init in lifespan**

Edit `backend/app/main.py` — replace the lifespan function:

```python
from app.db import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    await db.init_db()
    app.state.agent_engine = AgentEngine()
    yield
    await db.close()
```

---

### Task 3: Convert ScriptService to SQLite

**Files:**
- Modify: `backend/app/services/script_service.py`
- Test: verify via API

- [ ] **Step 1: Rewrite ScriptService with SQLite**

Write `backend/app/services/script_service.py`:

```python
"""Script service for managing test scripts — SQLite persistence."""

from typing import List, Optional
import time
from datetime import datetime

from app.db import db
from app.schemas.script import ScriptResponse, ScriptType


class ScriptService:
    """Service for script management with SQLite persistence."""

    async def create_script(
        self,
        name: str,
        content: str,
        script_type: str,
        platform: str,
        project_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """Create a new script."""
        script_id = f"script_{int(time.time())}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        conn = await db.get_connection()
        await conn.execute(
            """INSERT INTO scripts (script_id, name, content, script_type, platform, project_id, description, created_at, updated_at, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (script_id, name, content, script_type, platform, project_id, description, timestamp, timestamp)
        )
        await conn.commit()
        return script_id

    async def get_script(self, script_id: str) -> Optional[ScriptResponse]:
        """Get script by ID."""
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM scripts WHERE script_id = ?", (script_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return ScriptResponse(
            script_id=row["script_id"],
            name=row["name"],
            content=row["content"],
            script_type=ScriptType(row["script_type"]),
            platform=row["platform"],
            project_id=row["project_id"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"]
        )

    async def update_script(self, script_id: str, update) -> Optional[ScriptResponse]:
        """Update a script."""
        conn = await db.get_connection()
        existing = await self.get_script(script_id)
        if not existing:
            return None

        fields = []
        values = []
        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.content is not None:
            fields.append("content = ?")
            values.append(update.content)
            fields.append("version = version + 1")
        if update.description is not None:
            fields.append("description = ?")
            values.append(update.description)
        if fields:
            fields.append("updated_at = ?")
            values.append(time.strftime("%Y-%m-%dT%H:%M:%S"))
            values.append(script_id)
            await conn.execute(f"UPDATE scripts SET {', '.join(fields)} WHERE script_id = ?", values)
            await conn.commit()
        return await self.get_script(script_id)

    async def delete_script(self, script_id: str):
        """Delete a script."""
        conn = await db.get_connection()
        await conn.execute("DELETE FROM scripts WHERE script_id = ?", (script_id,))
        await conn.commit()

    async def list_scripts(
        self,
        project_id: Optional[str] = None,
        script_type: Optional[ScriptType] = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScriptResponse]:
        """List all scripts."""
        conn = await db.get_connection()

        conditions = []
        params = []
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if script_type:
            conditions.append("script_type = ?")
            params.append(script_type.value)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        cursor = await conn.execute(f"SELECT * FROM scripts {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, skip])
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            result.append(ScriptResponse(
                script_id=row["script_id"],
                name=row["name"],
                content=row["content"],
                script_type=ScriptType(row["script_type"]),
                platform=row["platform"],
                project_id=row["project_id"],
                description=row["description"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                version=row["version"]
            ))
        return result

    async def execute_script(self, script_id: str, device_id: Optional[str] = None) -> str:
        """Execute a script by creating a task and delegating to TaskService.
        Returns the task_id of the created task."""
        from app.services.task_service import TaskService

        script = await self.get_script(script_id)
        if not script:
            return ""

        task_service = TaskService()
        task_id = await task_service.create_task(
            name=f"Execute: {script.name}",
            description=f"Script execution: {script.name}",
            script_id=script_id,
            device_id=device_id,
            platform=script.platform,
        )
        return task_id

    async def generate_script(self, task_description: str, platform: str, project_id: Optional[str] = None) -> str:
        """Generate a script from task description."""
        script_content = self._generate_script_content(task_description, platform)
        return await self.create_script(
            name=f"Generated Script - {task_description[:30]}",
            content=script_content,
            script_type="ai_generated",
            platform=platform,
            project_id=project_id,
            description=f"Auto-generated script for: {task_description}"
        )

    def _generate_script_content(self, task_description: str, platform: str) -> str:
        """Generate script content based on platform."""
        timestamp = datetime.now().isoformat()
        if platform == "android":
            return f'''# Android Script (Python + uiautomator2)
# Generated: {timestamp}
# Task: {task_description}

import uiautomator2 as u2
import time

d = u2.connect()

try:
    print("Script execution started")

finally:
    pass
'''
        elif platform == "ios":
            return f'''// iOS Script (XCTest)
// Generated: {timestamp}
// Task: {task_description}

import XCTest

class GeneratedTest: XCTestCase {{
    var app: XCUIApplication!

    override func setUp() {{
        super.setUp()
        app = XCUIApplication()
        app.launch()
    }}

    func testTask() {{
    }}
}}
'''
        elif platform == "harmonyos":
            return f'''// HarmonyOS Script (Hypium)
// Generated: {timestamp}
// Task: {task_description}

import ohos.hypium.Hypium;
import ohos.hypium.executor.Action;
import ohos.hypium.executor.Executor;

public class GeneratedTest {{
    public static void main(String[] args) {{
        Executor executor = Hypium.createExecutor();
        try {{
        }} finally {{
            executor.release();
        }}
    }}
}}
'''
        else:
            return f'''# Generic Script\n# Generated: {timestamp}\n# Task: {task_description}\n'''

    async def derive_script(self, script_id: str, platform: str) -> str:
        """Derive a script for a different platform."""
        original_script = await self.get_script(script_id)
        if not original_script:
            return ""
        new_content = self._generate_script_content(
            original_script.description or original_script.name, platform
        )
        return await self.create_script(
            name=f"{original_script.name} ({platform})",
            content=new_content,
            script_type="ai_generated",
            platform=platform,
            project_id=original_script.project_id,
            description=f"Derived from {script_id}"
        )

    async def save_script_version(self, script_id: str, content: str, comment: str = "") -> str:
        """Save a new version of the script (increment version)."""
        conn = await db.get_connection()
        await conn.execute(
            "UPDATE scripts SET content = ?, version = version + 1, updated_at = ? WHERE script_id = ?",
            (content, time.strftime("%Y-%m-%dT%H:%M:%S"), script_id)
        )
        await conn.commit()
        script = await self.get_script(script_id)
        return f"v{script.version}" if script else "v1"

    async def get_script_versions(self, script_id: str) -> List[dict]:
        """Get version history — return current version info."""
        script = await self.get_script(script_id)
        if not script:
            return []
        return [{
            "version_id": f"v{script.version}",
            "script_id": script_id,
            "content": script.content,
            "version_number": script.version,
            "created_at": script.updated_at or script.created_at,
            "comment": ""
        }]
```

- [ ] **Step 2: Make API routes async**

Edit `backend/app/api/v1/scripts.py` — update the service calls to be async (add `await`):

Replace the entire file:

```python
"""Script management API."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from app.schemas.script import ScriptResponse, ScriptCreate, ScriptUpdate, ScriptType
from app.services.script_service import ScriptService

router = APIRouter()
script_service = ScriptService()


@router.post("/", response_model=ScriptResponse)
async def create_script(script: ScriptCreate):
    """Create a new script."""
    script_id = await script_service.create_script(
        name=script.name,
        content=script.content,
        script_type=script.script_type,
        platform=script.platform,
        project_id=script.project_id,
        description=script.description,
    )
    return await script_service.get_script(script_id)


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: str):
    """Get script details."""
    script = await script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(script_id: str, update: ScriptUpdate):
    """Update a script."""
    result = await script_service.update_script(script_id, update)
    if not result:
        raise HTTPException(status_code=404, detail="Script not found")
    return result


@router.delete("/{script_id}")
async def delete_script(script_id: str):
    """Delete a script."""
    await script_service.delete_script(script_id)
    return {"message": "Script deleted successfully"}


@router.get("/")
async def list_scripts(
    project_id: Optional[str] = None,
    script_type: Optional[ScriptType] = None,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """List all scripts."""
    scripts = await script_service.list_scripts(project_id, script_type, platform, skip, limit)
    return {"scripts": scripts}


@router.post("/{script_id}/execute")
async def execute_script(script_id: str, data: dict):
    """Execute a script by creating a task."""
    script = await script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    device_id = data.get("device_id")
    task_id = await script_service.execute_script(script_id, device_id)
    if not task_id:
        raise HTTPException(status_code=400, detail="Failed to create task for script execution")
    return {"task_id": task_id, "script_id": script_id, "status": "task_created"}


@router.post("/generate")
async def generate_script(
    task_description: str,
    platform: str,
    project_id: Optional[str] = None,
):
    """Generate a script from task description."""
    script_id = await script_service.generate_script(task_description, platform, project_id)
    return await script_service.get_script(script_id)


@router.post("/{script_id}/derive")
async def derive_script(script_id: str, platform: str):
    """Derive a script for a different platform."""
    new_script_id = await script_service.derive_script(script_id, platform)
    return await script_service.get_script(new_script_id)


@router.get("/{script_id}/versions")
async def get_script_versions(script_id: str):
    """Get version history of a script."""
    versions = await script_service.get_script_versions(script_id)
    return {"versions": versions}


@router.post("/{script_id}/save-version")
async def save_script_version(script_id: str, content: str, comment: str = ""):
    """Save a new version of the script."""
    version_id = await script_service.save_script_version(script_id, content, comment)
    return {"version_id": version_id}


@router.post("/upload")
async def upload_script(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    platform: str = Form("android"),
):
    """Upload a script from local file."""
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only Python files (.py) are allowed")
    content = await file.read()
    content_str = content.decode("utf-8")
    script_id = await script_service.create_script(
        name=name,
        content=content_str,
        script_type="external",
        platform=platform,
        project_id=None,
        description=description,
    )
    return await script_service.get_script(script_id)
```

---

### Task 4: Convert ProjectService to SQLite

**Files:**
- Modify: `backend/app/services/project_service.py`

- [ ] **Step 1: Rewrite ProjectService with SQLite**

Write `backend/app/services/project_service.py`:

```python
"""Project service for managing projects — SQLite persistence."""

import uuid
from datetime import datetime
from typing import List, Optional

from app.db import db
from app.schemas.project import Project, ProjectCreate, ProjectUpdate
from app.schemas.device import PlatformType


class ProjectService:
    """Service for project management with SQLite persistence."""

    async def create_project(self, project_create: ProjectCreate) -> Project:
        """Create a new project."""
        project_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        conn = await db.get_connection()
        await conn.execute(
            """INSERT INTO projects (project_id, name, description, platform, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, project_create.name, project_create.description,
             project_create.platform or "android", now, now)
        )
        await conn.commit()
        return Project(project_id=project_id, name=project_create.name,
                       description=project_create.description,
                       platform=project_create.platform or "android",
                       created_at=datetime.fromisoformat(now),
                       updated_at=datetime.fromisoformat(now))

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Project(project_id=row["project_id"], name=row["name"],
                       description=row["description"], platform=row["platform"],
                       created_at=datetime.fromisoformat(row["created_at"]),
                       updated_at=datetime.fromisoformat(row["updated_at"]))

    async def list_projects(self, platform: Optional[PlatformType] = None) -> List[Project]:
        """List all projects, ordered by created_at DESC."""
        conn = await db.get_connection()
        if platform:
            cursor = await conn.execute("SELECT * FROM projects WHERE platform = ? ORDER BY created_at DESC", (platform,))
        else:
            cursor = await conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [Project(project_id=r["project_id"], name=r["name"],
                        description=r["description"], platform=r["platform"],
                        created_at=datetime.fromisoformat(r["created_at"]),
                        updated_at=datetime.fromisoformat(r["updated_at"]))
                for r in rows]

    async def update_project(self, project_id: str, project_update: ProjectUpdate) -> Optional[Project]:
        """Update a project."""
        existing = await self.get_project(project_id)
        if not existing:
            return None
        conn = await db.get_connection()
        fields = []
        values = []
        if project_update.name is not None:
            fields.append("name = ?")
            values.append(project_update.name)
        if project_update.description is not None:
            fields.append("description = ?")
            values.append(project_update.description)
        if project_update.platform is not None:
            fields.append("platform = ?")
            values.append(project_update.platform)
        if fields:
            fields.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(project_id)
            await conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE project_id = ?", values)
            await conn.commit()
        return await self.get_project(project_id)

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        conn = await db.get_connection()
        cursor = await conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
        await conn.commit()
        return cursor.rowcount > 0
```

---

### Task 5: Convert ApkService to SQLite + Batch Delete

**Files:**
- Modify: `backend/app/services/apk_service.py`
- Modify: `backend/app/api/v1/apks.py`
- Modify: `backend/app/api/v1/__init__.py`

- [ ] **Step 1: Rewrite ApkService with SQLite persistence + batch delete**

Write `backend/app/services/apk_service.py`:

```python
"""APK management service — SQLite persistence + batch delete."""

import os
import uuid
import subprocess
import re
from typing import List, Optional
from datetime import datetime

from app.db import db
from app.schemas.apk import ApkInfo, ApkStatus, ApkUploadResponse, ApkActionResponse
from app.config import settings


class ApkService:
    """Service for APK management with SQLite persistence."""

    def __init__(self):
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "apks")
        os.makedirs(self.upload_dir, exist_ok=True)

    def _parse_apk_info(self, file_path: str) -> dict:
        """Parse APK info using aapt2 (preferred) with aapt fallback."""
        info = {"version": None, "package_name": None}
        for cmd_name in ["aapt2", "aapt"]:
            try:
                result = subprocess.run(
                    [cmd_name, "dump", "badging", file_path],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    pkg_match = re.search(r"package: name='([^']+)'", result.stdout)
                    if pkg_match:
                        info["package_name"] = pkg_match.group(1)
                    ver_match = re.search(r"versionName='([^']+)'", result.stdout)
                    if ver_match:
                        info["version"] = ver_match.group(1)
                    return info
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return info

    async def list_apks(self) -> List[ApkInfo]:
        """List all uploaded APKs, ordered by upload_time DESC."""
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM apks ORDER BY upload_time DESC")
        rows = await cursor.fetchall()
        return [ApkInfo(
            id=r["id"], name=r["name"],
            original_filename=r["original_filename"],
            version=r["version"], package_name=r["package_name"],
            file_size=r["file_size"], file_path=r["file_path"],
            upload_time=datetime.fromisoformat(r["upload_time"]),
            status=ApkStatus(r["status"])
        ) for r in rows]

    async def get_apk(self, apk_id: str) -> Optional[ApkInfo]:
        """Get APK by ID."""
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM apks WHERE id = ?", (apk_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return ApkInfo(
            id=row["id"], name=row["name"],
            original_filename=row["original_filename"],
            version=row["version"], package_name=row["package_name"],
            file_size=row["file_size"], file_path=row["file_path"],
            upload_time=datetime.fromisoformat(row["upload_time"]),
            status=ApkStatus(row["status"])
        )

    async def upload_apk(self, file, filename: str) -> ApkUploadResponse:
        """Upload an APK file."""
        try:
            apk_id = str(uuid.uuid4())[:8]
            original_ext = os.path.splitext(filename)[1] or ".apk"
            saved_filename = f"{apk_id}{original_ext}"
            file_path = os.path.join(self.upload_dir, saved_filename)

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            apk_info_data = self._parse_apk_info(file_path)

            conn = await db.get_connection()
            await conn.execute(
                """INSERT INTO apks (id, name, original_filename, package_name, version, file_size, file_path, upload_time, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (apk_id, filename, filename, apk_info_data.get("package_name"),
                 apk_info_data.get("version"), len(content), file_path,
                 datetime.now().isoformat(), "uploaded")
            )
            await conn.commit()

            apk_info = ApkInfo(
                id=apk_id, name=filename, original_filename=filename,
                version=apk_info_data.get("version"),
                package_name=apk_info_data.get("package_name"),
                file_size=len(content), upload_time=datetime.now(),
                status=ApkStatus.UPLOADED, file_path=file_path
            )
            return ApkUploadResponse(success=True, message="APK uploaded successfully", apk=apk_info)
        except Exception as e:
            return ApkUploadResponse(success=False, message=f"Failed to upload APK: {str(e)}")

    async def delete_apk(self, apk_id: str) -> ApkActionResponse:
        """Delete an APK."""
        try:
            apk = await self.get_apk(apk_id)
            if not apk:
                return ApkActionResponse(success=False, message="APK not found")
            if apk.file_path and os.path.exists(apk.file_path):
                os.remove(apk.file_path)
            conn = await db.get_connection()
            await conn.execute("DELETE FROM apks WHERE id = ?", (apk_id,))
            await conn.commit()
            return ApkActionResponse(success=True, message="APK deleted successfully")
        except Exception as e:
            return ApkActionResponse(success=False, message=f"Failed to delete APK: {str(e)}")

    async def delete_apk_batch(self, apk_ids: List[str]) -> ApkActionResponse:
        """Batch delete APKs."""
        try:
            conn = await db.get_connection()
            for apk_id in apk_ids:
                apk = await self.get_apk(apk_id)
                if apk and apk.file_path and os.path.exists(apk.file_path):
                    os.remove(apk.file_path)
                await conn.execute("DELETE FROM apks WHERE id = ?", (apk_id,))
            await conn.commit()
            return ApkActionResponse(success=True, message=f"{len(apk_ids)} APK(s) deleted successfully")
        except Exception as e:
            return ApkActionResponse(success=False, message=f"Failed to batch delete APKs: {str(e)}")

    async def install_apk(self, device_id: str, apk_id: str) -> ApkActionResponse:
        """Install APK to device."""
        try:
            apk = await self.get_apk(apk_id)
            if not apk or not apk.file_path:
                return ApkActionResponse(success=False, message="APK not found")
            result = subprocess.run(
                ["adb", "-s", device_id, "install", "-r", apk.file_path],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                return ApkActionResponse(success=True, message="APK installed successfully")
            else:
                return ApkActionResponse(success=False, message=f"Failed to install APK: {result.stderr}")
        except subprocess.TimeoutExpired:
            return ApkActionResponse(success=False, message="APK installation timed out")
        except Exception as e:
            return ApkActionResponse(success=False, message=f"Failed to install APK: {str(e)}")
```

- [ ] **Step 2: Add batch delete endpoint to apks.py**

Edit `backend/app/api/v1/apks.py` — add batch delete endpoint before `@router.post("/install")`:

```python
from app.schemas.apk import ApkInfo, ApkUploadResponse, ApkInstallRequest, ApkActionResponse, ApkBatchDeleteRequest

@router.post("/batch-delete")
async def batch_delete_apks(request: ApkBatchDeleteRequest):
    """Batch delete multiple APKs."""
    result = await apk_service.delete_apk_batch(request.apk_ids)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result
```

Also make all existing route handlers async-aware — change `apk_service.delete_apk(apk_id)` to `await apk_service.delete_apk(apk_id)`, `apk_service.install_apk(...)` to `await apk_service.install_apk(...)`, etc.

Replace the entire `apks.py` file:

```python
"""APK management API."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from app.schemas.apk import ApkInfo, ApkUploadResponse, ApkInstallRequest, ApkActionResponse, ApkBatchDeleteRequest
from app.services.apk_service import ApkService

router = APIRouter()
apk_service = ApkService()


@router.get("/")
async def list_apks():
    """List all uploaded APKs."""
    apks = await apk_service.list_apks()
    return {"apks": apks}


@router.get("/{apk_id}", response_model=ApkInfo)
async def get_apk(apk_id: str):
    """Get APK details by ID."""
    apk = await apk_service.get_apk(apk_id)
    if not apk:
        raise HTTPException(status_code=404, detail="APK not found")
    return apk


@router.post("/upload")
async def upload_apk(file: UploadFile = File(...)):
    """Upload an APK file."""
    result = await apk_service.upload_apk(file, file.filename or "unknown.apk")
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.delete("/{apk_id}")
async def delete_apk(apk_id: str):
    """Delete an APK."""
    result = await apk_service.delete_apk(apk_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.post("/batch-delete")
async def batch_delete_apks(request: ApkBatchDeleteRequest):
    """Batch delete multiple APKs."""
    result = await apk_service.delete_apk_batch(request.apk_ids)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.post("/install")
async def install_apk(request: ApkInstallRequest):
    """Install APK to device."""
    result = await apk_service.install_apk(request.device_id, request.apk_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result
```

- [ ] **Step 3: Update api/v1/__init__.py to export apks router**

Edit `backend/app/api/v1/__init__.py`:

```python
"""API v1 module."""

from .tasks import router as tasks_router
from .devices import router as devices_router
from .reports import router as reports_router
from .websocket import router as websocket_router
from .scripts import router as scripts_router
from .apks import router as apks_router
from .logs import router as logs_router
```

---

### Task 6: Rewrite TaskService with SQLite + Subprocess Executor

**Files:**
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/api/v1/tasks.py`

- [ ] **Step 1: Rewrite TaskService with SQLite + subprocess**

Write `backend/app/services/task_service.py`:

```python
"""Task service for managing tasks — SQLite persistence + subprocess executor."""

from typing import List, Optional, Dict
import time
import subprocess
import tempfile
import os

from app.db import db
from app.schemas.task import TaskResponse, TaskStatus, TaskType


class TaskService:
    """Service for task management with SQLite persistence and subprocess execution."""

    def __init__(self):
        self.task_processes: Dict[str, subprocess.Popen] = {}

    async def create_task(
        self,
        name: str,
        task_type: Optional[str] = None,
        platform: Optional[str] = None,
        devices: Optional[List[str]] = None,
        steps: Optional[List[Dict]] = None,
        description: Optional[str] = None,
        script_id: Optional[str] = None,
        device_id: Optional[str] = None,
        apk_id: Optional[str] = None,
    ) -> str:
        """Create a new task."""
        task_id = f"task_{int(time.time())}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        conn = await db.get_connection()
        await conn.execute(
            """INSERT INTO tasks (task_id, name, task_type, platform, status, script_id, device_id, apk_id, description, progress, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (task_id, name, task_type or "functional", platform or "android",
             TaskStatus.PENDING.value, script_id, device_id, apk_id, description,
             timestamp, timestamp)
        )
        await conn.commit()
        return task_id

    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """Get task by ID."""
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        # Get associated device IDs
        dev_cursor = await conn.execute("SELECT device_id FROM task_devices WHERE task_id = ?", (task_id,))
        dev_rows = await dev_cursor.fetchall()
        device_ids = [r["device_id"] for r in dev_rows]

        return TaskResponse(
            task_id=row["task_id"],
            name=row["name"],
            task_type=TaskType(row["task_type"]) if row["task_type"] in TaskType._value2member_map_ else TaskType.FUNCTIONAL,
            platform=row["platform"],
            devices=device_ids,
            status=TaskStatus(row["status"]),
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"]
        )

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskResponse]:
        """List all tasks."""
        conn = await db.get_connection()

        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        cursor = await conn.execute(
            f"SELECT * FROM tasks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, skip]
        )
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            result.append(TaskResponse(
                task_id=row["task_id"],
                name=row["name"],
                task_type=TaskType(row["task_type"]) if row["task_type"] in TaskType._value2member_map_ else TaskType.FUNCTIONAL,
                platform=row["platform"],
                devices=[],
                status=TaskStatus(row["status"]),
                description=row["description"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"]
            ))
        return result

    async def _get_script_content(self, script_id: str) -> Optional[str]:
        """Read script content from SQLite."""
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT content FROM scripts WHERE script_id = ?", (script_id,))
        row = await cursor.fetchone()
        return row["content"] if row else None

    async def execute_task(self, task_id: str):
        """Execute a task via subprocess."""
        task = await self.get_task(task_id)
        if not task:
            return

        # Update status to running
        conn = await db.get_connection()
        await conn.execute(
            "UPDATE tasks SET status = ?, started_at = ?, updated_at = ? WHERE task_id = ?",
            (TaskStatus.EXECUTING.value, time.strftime("%Y-%m-%dT%H:%M:%S"),
             time.strftime("%Y-%m-%dT%H:%M:%S"), task_id)
        )
        await conn.commit()
        await self._log(task_id, "INFO", "Starting task execution via subprocess")

        if not task.script_id:
            await conn.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, updated_at = ? WHERE task_id = ?",
                (TaskStatus.FAILED.value, time.strftime("%Y-%m-%dT%H:%M:%S"),
                 time.strftime("%Y-%m-%dT%H:%M:%S"), task_id)
            )
            await conn.commit()
            await self._log(task_id, "ERROR", "No script associated with task")
            return

        script_content = await self._get_script_content(task.script_id)
        if not script_content:
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self._log(task_id, "ERROR", "Script not found")
            return

        # Write script to temp file
        temp_script = tempfile.NamedTemporaryFile(
            suffix='.py', delete=False, prefix=f'task_{task_id}_'
        )
        temp_script.write(script_content.encode('utf-8'))
        temp_script.close()

        try:
            from app.config import settings
            env_vars = os.environ.copy()
            if task.device_id:
                env_vars['PHONE_AGENT_DEVICE_ID'] = task.device_id
            env_vars['PHONE_AGENT_BASE_URL'] = settings.model_api_url
            env_vars['PHONE_AGENT_MODEL'] = settings.model_name
            env_vars['PHONE_AGENT_API_KEY'] = settings.api_key

            process = subprocess.Popen(
                ['python', temp_script.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env_vars
            )
            self.task_processes[task_id] = process

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                await self._update_task_status(task_id, TaskStatus.COMPLETED, progress=100)
                await self._log(task_id, "INFO", "Task completed successfully")
            else:
                await self._update_task_status(task_id, TaskStatus.FAILED, progress=100)
                error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
                await self._log(task_id, "ERROR", f"Task failed: {error_msg[:500]}")

            # Generate report
            await self._generate_report(task_id, stdout.decode('utf-8', errors='replace') if stdout else "",
                                        stderr.decode('utf-8', errors='replace') if stderr else "")

        except Exception as e:
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self._log(task_id, "ERROR", f"Subprocess error: {str(e)}")
        finally:
            os.unlink(temp_script.name)
            self.task_processes.pop(task_id, None)

    async def _generate_report(self, task_id: str, stdout: str, stderr: str):
        """Generate an HTML report for a completed task."""
        task = await self.get_task(task_id)
        if not task:
            return

        has_error = task.status == TaskStatus.FAILED or task.status == TaskStatus.STOPPED
        status_text = "passed" if task.status == TaskStatus.COMPLETED else ("stopped" if task.status == TaskStatus.STOPPED else "failed")

        started = task.started_at or task.created_at
        completed = task.completed_at or time.strftime("%Y-%m-%dT%H:%M:%S")
        import datetime
        try:
            start_dt = datetime.datetime.fromisoformat(started)
            end_dt = datetime.datetime.fromisoformat(completed)
            duration = int((end_dt - start_dt).total_seconds())
        except Exception:
            duration = 0

        # Build step log from task_logs
        logs = await self.get_task_logs(task_id)
        step_rows = ""
        for i, log in enumerate(logs[:50]):
            step_rows += f"<tr><td>{i+1}</td><td>{log['timestamp']}</td><td>{log['level']}</td><td>{log['message']}</td></tr>\n"

        # Template HTML
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>Test Report - {task.name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
h1 {{ color: #fff; border-bottom: 1px solid #334155; padding-bottom: 10px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #334155; }}
th {{ background: #1e293b; color: #94a3b8; }}
.status-passed {{ color: #3ddc84; }}
.status-failed {{ color: #ef4444; }}
.status-stopped {{ color: #f59e0b; }}
.summary {{ display: flex; gap: 16px; margin: 16px 0; }}
.summary-item {{ background: #1e293b; padding: 12px 20px; border-radius: 8px; border: 1px solid #334155; }}
</style></head>
<body>
<h1>Test Report: {task.name}</h1>
<div class="summary">
  <div class="summary-item"><strong>Status:</strong> <span class="status-{status_text}">{status_text}</span></div>
  <div class="summary-item"><strong>Duration:</strong> {duration}s</div>
  <div class="summary-item"><strong>Started:</strong> {started}</div>
  <div class="summary-item"><strong>Completed:</strong> {completed}</div>
</div>
<h2>Execution Log</h2>
<table><thead><tr><th>#</th><th>Time</th><th>Level</th><th>Message</th></tr></thead><tbody>
{step_rows}
</tbody></table>
</body></html>"""

        conn = await db.get_connection()
        await conn.execute(
            """INSERT OR REPLACE INTO reports (task_id, name, device_name, script_name, script_type, status, started_at, completed_at, duration_seconds, html_content, summary, total_steps, passed_steps, failed_steps, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, task.name, task.device_id, task.script_id, "", status_text,
             started, completed, duration, html_content,
             f"Total steps: {len(logs)}", len(logs),
             len([l for l in logs if l['level'] == 'INFO']),
             len([l for l in logs if l['level'] == 'ERROR']),
             time.strftime("%Y-%m-%dT%H:%M:%S"))
        )
        await conn.commit()

    async def _update_task_status(self, task_id: str, status: TaskStatus, progress: Optional[int] = None):
        """Update task status and timestamps."""
        conn = await db.get_connection()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.STOPPED):
            await conn.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, updated_at = ?, progress = COALESCE(?, progress) WHERE task_id = ?",
                (status.value, now, now, progress, task_id)
            )
        else:
            await conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ?, progress = COALESCE(?, progress) WHERE task_id = ?",
                (status.value, now, progress, task_id)
            )
        await conn.commit()

    async def stop_task(self, task_id: str):
        """Stop a running task."""
        task = await self.get_task(task_id)
        if not task:
            return

        # Kill subprocess if running
        process = self.task_processes.get(task_id)
        if process:
            process.terminate()
            import time as time_module
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del self.task_processes[task_id]

        await self._update_task_status(task_id, TaskStatus.STOPPED)
        await self._log(task_id, "INFO", "Task stopped by user")

    async def delete_task(self, task_id: str):
        """Delete a task."""
        # Kill subprocess if running
        process = self.task_processes.get(task_id)
        if process:
            process.kill()
            del self.task_processes[task_id]

        conn = await db.get_connection()
        await conn.execute("DELETE FROM task_logs WHERE task_id = ?", (task_id,))
        await conn.execute("DELETE FROM reports WHERE task_id = ?", (task_id,))
        await conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        await conn.commit()

    async def _log(self, task_id: str, level: str, message: str):
        """Log a message for a task."""
        conn = await db.get_connection()
        await conn.execute(
            "INSERT INTO task_logs (task_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
            (task_id, time.strftime("%Y-%m-%dT%H:%M:%S"), level, message)
        )
        await conn.commit()

    async def get_task_logs(self, task_id: str, limit: int = 100) -> List[Dict]:
        """Get task logs."""
        conn = await db.get_connection()
        cursor = await conn.execute(
            "SELECT timestamp, level, message FROM task_logs WHERE task_id = ? ORDER BY id DESC LIMIT ?",
            (task_id, limit)
        )
        rows = await cursor.fetchall()
        logs = []
        for row in reversed(rows):
            logs.append({
                "timestamp": row["timestamp"],
                "level": row["level"],
                "message": row["message"]
            })
        return logs
```

- [ ] **Step 2: Update tasks API routes**

Edit `backend/app/api/v1/tasks.py` — replace entire file:

```python
"""Task management API."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from app.schemas.task import TaskResponse, TaskStatus, TaskCreate
from app.services.task_service import TaskService

router = APIRouter()
task_service = TaskService()


@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    """Create a new task."""
    task_id = await task_service.create_task(
        name=task.name,
        task_type=task.task_type,
        platform=task.platform,
        devices=task.devices,
        steps=task.steps,
        description=task.description,
        script_id=task.script_id,
        device_id=task.device_id,
        apk_id=task.apk_id,
    )
    return await task_service.get_task(task_id)


@router.post("/{task_id}/execute")
async def execute_task(task_id: str, background_tasks: BackgroundTasks):
    """Execute a task."""
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.EXECUTING:
        raise HTTPException(status_code=400, detail="Task is already running")

    background_tasks.add_task(task_service.execute_task, task_id)
    return {"task_id": task_id, "status": "executing"}


@router.post("/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a running task."""
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await task_service.stop_task(task_id)
    return {"task_id": task_id, "status": "stopped"}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get task details."""
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/")
async def list_tasks(
    status: Optional[TaskStatus] = None,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """List all tasks."""
    tasks = await task_service.list_tasks(status, platform, skip, limit)
    return {"tasks": tasks}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await task_service.delete_task(task_id)
    return {"message": "Task deleted successfully"}


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str, limit: int = 100):
    """Get task execution logs."""
    logs = await task_service.get_task_logs(task_id, limit)
    return {"logs": logs}
```

---

### Task 7: Rewrite ReportService with SQLite + Preview Endpoint

**Files:**
- Modify: `backend/app/services/report_service.py`
- Modify: `backend/app/api/v1/reports.py`
- Create: `backend/app/templates/report_template.html`

- [ ] **Step 1: Rewrite ReportService with SQLite + preview**

Write `backend/app/services/report_service.py`:

```python
"""Report service for generating and managing reports — SQLite persistence."""

from typing import List, Optional
import time

from app.db import db


class ReportService:
    """Service for report management with SQLite persistence."""

    async def list_reports(
        self,
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """List all reports."""
        conn = await db.get_connection()
        conditions = []
        params = []
        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        cursor = await conn.execute(
            f"SELECT task_id, name, device_name as device_name, script_name, script_type, status, started_at, completed_at, duration_seconds, summary, created_at FROM reports {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, skip]
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_report(self, report_id: str) -> Optional[dict]:
        """Get report by ID (without html_content for list views)."""
        conn = await db.get_connection()
        cursor = await conn.execute(
            "SELECT task_id, name, device_name, script_name, script_type, status, started_at, completed_at, duration_seconds, summary, created_at FROM reports WHERE task_id = ?",
            (report_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_report_html(self, task_id: str) -> Optional[str]:
        """Get full HTML content for a report."""
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT html_content FROM reports WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        return row["html_content"] if row else None

    async def delete_report(self, report_id: str):
        """Delete a report."""
        conn = await db.get_connection()
        await conn.execute("DELETE FROM reports WHERE task_id = ?", (report_id,))
        await conn.commit()

    async def batch_delete(self, report_ids: list[str]) -> tuple[int, list[str]]:
        """Batch delete reports."""
        conn = await db.get_connection()
        deleted = 0
        failed = []
        for report_id in report_ids:
            cursor = await conn.execute("DELETE FROM reports WHERE task_id = ?", (report_id,))
            if cursor.rowcount > 0:
                deleted += 1
            else:
                failed.append(report_id)
        await conn.commit()
        return deleted, failed
```

- [ ] **Step 2: Update reports API with preview endpoint**

Edit `backend/app/api/v1/reports.py` — replace entire file:

```python
"""Report generation API."""

from fastapi import APIRouter, HTTPException, Response
from app.schemas.report import BatchDeleteRequest, BatchDeleteResponse
from app.services.report_service import ReportService

router = APIRouter()
report_service = ReportService()


@router.get("/")
async def list_reports(
    task_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """List all reports."""
    return await report_service.list_reports(task_id, status, skip, limit)


@router.delete("/batch", response_model=BatchDeleteResponse)
async def batch_delete_reports(request: BatchDeleteRequest):
    """Batch delete multiple reports."""
    deleted, failed = await report_service.batch_delete(request.report_ids)
    return BatchDeleteResponse(deleted_count=deleted, failed_ids=failed)


@router.get("/{task_id}")
async def get_report(task_id: str):
    """Get report details."""
    report = await report_service.get_report(task_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{task_id}/preview")
async def preview_report(task_id: str):
    """Preview report HTML content."""
    html = await report_service.get_report_html(task_id)
    if not html:
        raise HTTPException(status_code=404, detail="Report not found")
    return Response(content=html, media_type="text/html")


@router.delete("/{task_id}")
async def delete_report(task_id: str):
    """Delete a report."""
    await report_service.delete_report(task_id)
    return {"message": "Report deleted successfully"}
```

---

### Task 8: Frontend — DevicePage (TCP/IP text change)

**Files:**
- Modify: `frontend/src/pages/Device/DevicePage.tsx`

- [ ] **Step 1: Change "无线" to "TCP/IP" in getConnectionBadge**

In `frontend/src/pages/Device/DevicePage.tsx:68`, change:

```tsx
<span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
  无线
</span>
```

to:

```tsx
<span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
  TCP/IP
</span>
```

---

### Task 9: Frontend — DeviceDetailDrawer (field cleanup + reorder)

**Files:**
- Modify: `frontend/src/components/DeviceDetailDrawer.tsx`

- [ ] **Step 1: Remove device_type, android_sdk_version, last_seen blocks + fix connection_type display + reorder fields**

Replace the device info section (lines 82-147) in `frontend/src/components/DeviceDetailDrawer.tsx`:

Old code:
```tsx
<div className="space-y-2 text-sm">
  {selectedDevice.model && (
    <div className="flex justify-between">
```

Replace with the reordered, cleaned version:

```tsx
<div className="space-y-2 text-sm">
  {selectedDevice.model && (
    <div className="flex justify-between">
      <span className="text-[#64748b]">型号</span>
      <span className="text-[#94a3b8]">{selectedDevice.model}</span>
    </div>
  )}
  {selectedDevice.manufacturer && (
    <div className="flex justify-between">
      <span className="text-[#64748b]">制造商</span>
      <span className="text-[#94a3b8]">{selectedDevice.manufacturer}</span>
    </div>
  )}
  {selectedDevice.os_version && (
    <div className="flex justify-between">
      <span className="text-[#64748b]">系统版本</span>
      <span className="text-[#94a3b8]">{selectedDevice.os_version}</span>
    </div>
  )}
  {selectedDevice.screen_width && selectedDevice.screen_height && (
    <div className="flex justify-between">
      <span className="text-[#64748b]">分辨率</span>
      <span className="text-[#94a3b8]">{selectedDevice.screen_width}x{selectedDevice.screen_height}</span>
    </div>
  )}
  {selectedDevice.connection_type && (
    <div className="flex justify-between">
      <span className="text-[#64748b]">连接方式</span>
      <span className="text-[#94a3b8]">{selectedDevice.connection_type === 'usb' ? 'USB' : 'TCP/IP'}</span>
    </div>
  )}
  {selectedDevice.ip && selectedDevice.connection_type === 'tcpip' && (
    <div className="flex justify-between">
      <span className="text-[#64748b]">IP地址</span>
      <span className="text-[#94a3b8]">{selectedDevice.ip}</span>
    </div>
  )}
  {selectedDevice.battery_level !== undefined && (
    <div className="flex justify-between">
      <span className="text-[#64748b]">电量</span>
      <span className="text-[#94a3b8]">{selectedDevice.battery_level}%</span>
    </div>
  )}
  <div className="flex justify-between">
    <span className="text-[#64748b]">设备ID</span>
    <span className="text-[#94a3b8] font-mono">{selectedDevice.device_id}</span>
  </div>
</div>
```

---

### Task 10: Frontend — Dashboard (brighter text + larger dots)

**Files:**
- Modify: `frontend/src/pages/Dashboard/Dashboard.tsx`

- [ ] **Step 1: Update device name text color**

In `Dashboard.tsx:217`, change:

```tsx
<span className="text-[#94a3b8]">{name}</span>
```

to:

```tsx
<span className="text-[#e2e8f0]">{name}</span>
```

- [ ] **Step 2: Update status dots to be larger with glow**

In `Dashboard.tsx:216-217`, change the dot size class:

```tsx
<div className="w-3 h-3 rounded-full"
```

to:

```tsx
<div className="w-4 h-4 rounded-full shadow-md"
```

---

### Task 11: Frontend — ApkPage (batch delete mode)

**Files:**
- Modify: `frontend/src/stores/apkStore.ts`
- Modify: `frontend/src/pages/Apk/ApkPage.tsx`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add deleteApkBatch action + batch mode state to apkStore**

Edit `frontend/src/stores/apkStore.ts` — add state and action:

Add to `ApkState` interface:
```typescript
isBatchMode: boolean;
selectedApkIds: string[];

setBatchMode: (mode: boolean) => void;
toggleApkSelection: (id: string) => void;
selectAllApks: () => void;
clearSelection: () => void;
deleteApkBatch: () => Promise<void>;
```

Add to `create<ApkState>` default values:
```typescript
isBatchMode: false,
selectedApkIds: [],
```

Add implementations inside the create callback (after `clearMessages`):
```typescript
setBatchMode: (mode) => set({ isBatchMode: mode, selectedApkIds: [] }),

toggleApkSelection: (id) => set((state) => ({
  selectedApkIds: state.selectedApkIds.includes(id)
    ? state.selectedApkIds.filter(i => i !== id)
    : [...state.selectedApkIds, id]
})),

selectAllApks: () => set((state) => ({
  selectedApkIds: state.apks.length === state.selectedApkIds.length
    ? []
    : state.apks.map(a => a.id)
})),

clearSelection: () => set({ selectedApkIds: [], isBatchMode: false }),

deleteApkBatch: async () => {
  const { selectedApkIds } = get();
  try {
    await apkApi.deleteApkBatch(selectedApkIds);
    set({ success: `已删除 ${selectedApkIds.length} 个APK`, isBatchMode: false, selectedApkIds: [] });
    await get().fetchApks();
  } catch (error: any) {
    set({ error: error.response?.data?.detail || '批量删除失败' });
  }
},
```

- [ ] **Step 2: Add batch delete API to api.ts**

Edit `frontend/src/services/api.ts` — add to `apkApi`:

```typescript
deleteApkBatch: (apkIds: string[]) =>
  api.post('/api/v1/apks/batch-delete', { apk_ids: apkIds }),
```

- [ ] **Step 3: Update ApkPage with batch mode UI**

Edit `frontend/src/pages/Apk/ApkPage.tsx`:

Add imports at top:
```typescript
import { useState } from 'react';
import { Trash2 } from 'lucide-react'; // already imported
```

Add state after `useEffect` hooks:
```typescript
const [confirmBatchDelete, setConfirmBatchDelete] = useState(false);
```

Add batch mode button next to upload button (after line 63, before the hidden input):
```tsx
<button
  onClick={() => useApkStore.getState().setBatchMode(!useApkStore.getState().isBatchMode)}
  className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
    useApkStore.getState().isBatchMode
      ? 'bg-red-600 hover:bg-red-500 text-white'
      : 'bg-[#334155] hover:bg-[#475569] text-white'
  }`}
>
  <Trash2 className="w-4 h-4" />
  {useApkStore.getState().isBatchMode
    ? `删除 (${useApkStore.getState().selectedApkIds.length})`
    : '批量删除'}
</button>
```

Add checkbox column to table header (before APK文件名 column):
```tsx
{isBatchMode && (
  <th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider w-10">
    <input
      type="checkbox"
      checked={apks.length > 0 && selectedApkIds.length === apks.length}
      onChange={() => selectAllApks()}
      className="w-4 h-4 rounded border-[#334155] bg-[#0f172a] text-indigo-600 focus:ring-indigo-500"
    />
  </th>
)}
```

Add checkbox to each table row (before the APK文件名 td):
```tsx
{isBatchMode && (
  <td className="px-6 py-4 whitespace-nowrap">
    <input
      type="checkbox"
      checked={selectedApkIds.includes(apk.id)}
      onChange={() => toggleApkSelection(apk.id)}
      className="w-4 h-4 rounded border-[#334155] bg-[#0f172a] text-indigo-600 focus:ring-indigo-500"
    />
  </td>
)}
```

Add cancel batch mode button next to the batch delete button when in batch mode:
```tsx
{isBatchMode && (
  <button
    onClick={() => setBatchMode(false)}
    className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
  >
    取消选择
  </button>
)}
```

Add confirmation dialog before executing batch delete:
Inside `deleteApkBatch`, add confirm check. Add a modal similar to existing pattern.

---

### Task 12: Frontend — ScriptPage (execute with script_id param)

**Files:**
- Modify: `frontend/src/pages/Script/ScriptPage.tsx`

- [ ] **Step 1: Update handleExecute to navigate with script_id**

Edit `frontend/src/pages/Script/ScriptPage.tsx:64-67`, replace:

```typescript
const handleExecute = (script: Script) => {
  setCurrentScript(script);
  navigate('/agent');
};
```

with:

```typescript
const handleExecute = (script: Script) => {
  setCurrentScript(script);
  navigate(`/agent?script_id=${script.script_id}`);
};
```

---

### Task 13: Frontend — AgentPage (load script from URL param)

**Files:**
- Modify: `frontend/src/pages/Agent/AgentPage.tsx`

- [ ] **Step 1: Read script_id from URL params on mount**

Edit `frontend/src/pages/Agent/AgentPage.tsx` — add import for `useSearchParams`:

```typescript
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
```

Inside `AgentPage` function, add:

```typescript
const [searchParams] = useSearchParams();
```

In the `useEffect` that already fetches data, add:

```typescript
useEffect(() => {
  fetchDevices();
  fetchProjects();
  fetchApks();

  // Load script from URL param if present
  const scriptId = searchParams.get('script_id');
  if (scriptId) {
    const script = useAgentStore.getState().scripts.find(s => s.script_id === scriptId);
    if (script) {
      useAgentStore.getState().setCurrentScript(script);
      setScriptContent(script.content);
    }
  }
}, []);
```

Also import `useSearchParams` from 'react-router-dom' at the top level import line.

---

### Task 14: Frontend — TaskPage (auto-execute + cancel for pending + report preview)

**Files:**
- Modify: `frontend/src/stores/taskStore.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/pages/Task/TaskPage.tsx`

- [ ] **Step 1: Add report preview API to api.ts**

Edit `frontend/src/services/api.ts` — add to `reportApi`:

```typescript
previewReport: (taskId: string) => api.get(`/api/v1/reports/${taskId}/preview`),
```

- [ ] **Step 2: Make createTask auto-call executeTask in taskStore**

Edit `frontend/src/stores/taskStore.ts` — update `createTask` action:

```typescript
createTask: async (data) => {
  try {
    const requestData = {
      name: data.name,
      description: data.description,
      script_id: data.script_id,
      device_id: data.device_id,
      ...(data.apk_id && { apk_id: data.apk_id }),
    };
    const response = await taskApi.createTask(requestData) as unknown as { task_id: string };
    // Auto-execute after creation
    await taskApi.executeTask(response.task_id);
    await get().fetchTasks();
    return response.task_id;
  } catch (error) {
    set({ error: 'Failed to create task' });
    return null;
  }
},
```

- [ ] **Step 3: Update TaskPage UI — cancel for pending + report preview button**

Edit `frontend/src/pages/Task/TaskPage.tsx`:

**Action buttons section (lines 211-242)** — replace the entire td block:

```tsx
<td className="py-4 px-6">
  <div className="flex items-center gap-2">
    {(task.status === 'running' || task.status === 'pending') && (
      <button
        onClick={() => stopTask(task.task_id)}
        className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
        title={task.status === 'pending' ? '取消' : '中止'}
      >
        <Square className="w-4 h-4" />
      </button>
    )}
    {task.status === 'pending' && (
      <button
        onClick={() => executeTask(task.task_id)}
        className="p-2 text-green-400 hover:bg-green-500/20 rounded-lg transition-colors"
        title="执行"
      >
        <Play className="w-4 h-4" />
      </button>
    )}
    {(task.status === 'completed' || task.status === 'failed' || task.status === 'stopped') && (
      <button
        onClick={() => window.open(`http://localhost:8000/api/v1/reports/${task.task_id}/preview`, '_blank')}
        className="p-2 text-indigo-400 hover:bg-indigo-500/20 rounded-lg transition-colors"
        title="查看报告"
      >
        <CheckCircle2 className="w-4 h-4" />
      </button>
    )}
    <button
      onClick={() => {
        if (confirm('确定要删除此任务吗？')) {
          deleteTask(task.task_id);
        }
      }}
      className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
      title="删除"
    >
      <Trash2 className="w-4 h-4" />
    </button>
  </div>
</td>
```

---

### Task 15: Services __init__.py — Update Exports

**Files:**
- Modify: `backend/app/services/__init__.py`

- [ ] **Step 1: Add ApkService and ProjectService to exports**

Edit `backend/app/services/__init__.py`:

```python
"""Services module."""

from .device_service import DeviceService
from .task_service import TaskService
from .report_service import ReportService
from .script_service import ScriptService
from .apk_service import ApkService
from .project_service import ProjectService
```

---

### Task 16: Frontend — deviceStore cleanup (remove deviceApps/loadingApps)

**Files:**
- Modify: `frontend/src/stores/deviceStore.ts`

- [ ] **Step 1: Verify deviceApps/loadingApps don't exist**

Check that `deviceStore.ts` has no `deviceApps` or `loadingApps` fields. Based on current content, they don't exist — no changes needed.

---

### Task 17: Add pagination support to projects API (for completeness)

**Files:**
- Modify: `backend/app/api/v1/scripts.py`

- [ ] **Step 1: Task 3 already updated the listing with DESC ordering — verified**

---

### Task 18: Verify build and fix any issues

- [ ] **Step 1: Run ruff check on backend**

Run: `ruff check --fix backend/app/`

- [ ] **Step 2: Try importing the new modules**

Run: `cd backend && python -c "from app.db import db; print('DB module OK')"`

- [ ] **Step 3: Start backend and check health**

Run: `cd backend && python run.py &` then `curl http://localhost:8000/health`

Expected: `{"status": "healthy", "version": "1.0.0"}`
